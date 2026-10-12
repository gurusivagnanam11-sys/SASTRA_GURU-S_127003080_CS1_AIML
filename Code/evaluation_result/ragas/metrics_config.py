"""RAGAS metrics and LLM judge configuration for AUTOSAR HLD Assistant.

Configures:
- Ragas metrics (Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall, AnswerCorrectness)
- Project SentenceTransformer embeddings (BAAI/bge-small-en-v1.5, 384 dimensions)
- Local Ollama, Cloud Gemini, or Mock LLM judge wrappers
- Explicit metadata documenting judge type, required inputs, and compliance boundaries
"""

import os
import sys
import json
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Activate runtime compatibility shim before third-party imports
import evaluation_result.ragas.compat  # noqa: F401

os.environ["HF_HUB_OFFLINE"] = "1"

from embeddings.embedder import HLDEmbedder
from ragas.embeddings.base import BaseRagasEmbedding
from ragas.llms.base import BaseRagasLLM, LangchainLLMWrapper
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# 1. Project Embedding Model Wrapper for Ragas
# ------------------------------------------------------------------------------

class ProjectRagasEmbedding(BaseRagasEmbedding):
    """Embeddings wrapper using the active project BAAI/bge-small-en-v1.5 model."""

    def __init__(self):
        self._embedder = HLDEmbedder()
        self.dimension = 384
        self.model_name = "BAAI/bge-small-en-v1.5"

    def embed_text(self, text: str) -> List[float]:
        return self._embedder.embed_query(text).tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embedder.embed_query(t).tolist() for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_text(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_texts(texts)

    async def aembed_text(self, text: str) -> List[float]:
        return self.embed_text(text)

    async def aembed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.embed_texts(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return self.embed_query(text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_documents(texts)


# ------------------------------------------------------------------------------
# 2. Complete Evidence-Aware Mock Judge for Offline Smoke Testing & CI/CD
# ------------------------------------------------------------------------------

class CompleteMockJudge(BaseChatModel):
    """Deterministic mock judge chat model matching Ragas prompt schemas.

    Strictly reserved for smoke tests and pipeline/schema verification.
    Inspects prompt content dynamically rather than unconditionally approving all inputs.
    """

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        full_text = " ".join([str(m.content) for m in messages if isinstance(m.content, str)])
        prompt_lower = full_text.lower()

        # 1. Statement generator prompt (extract statements from answer)
        if "break down each sentence" in prompt_lower or "statement_generator_prompt" in prompt_lower or "complexity" in prompt_lower:
            # Extract sentence fragments or provide canonical architectural statements
            sentences = [s.strip() for s in re.split(r"[.!?\n]", full_text) if len(s.strip()) > 15]
            if not sentences:
                sentences = ["The component and interface configuration is defined in the HLD."]
            content = json.dumps({"statements": sentences[:3]})

        # 2. Faithfulness / Natural Language Inference prompt (statement vs context)
        elif "judge the faithfulness" in prompt_lower or "n_l_i_statement_prompt" in prompt_lower or "verdict as 1" in prompt_lower:
            verdict = 0 if any(bad in prompt_lower for bad in ["unfaithful", "unsupported", "contradicts", "hallucinated"]) else 1
            reason = "Statement facts align with retrieved context." if verdict == 1 else "Context lacks sufficient evidence for statement."
            content = json.dumps({"statements": [{"statement": "Evaluated statement", "reason": reason, "verdict": verdict}]})

        # 3. Answer Relevancy prompt
        elif "noncommittal" in prompt_lower or "response_relevance_prompt" in prompt_lower:
            is_noncommittal = 1 if ("not specify" in prompt_lower or "insufficient evidence" in prompt_lower or "cannot answer" in prompt_lower) else 0
            content = json.dumps({"question": "What is the architectural configuration?", "noncommittal": is_noncommittal})

        # 4. Context Precision prompt (was context useful for answering question?)
        elif "useful" in prompt_lower or "context_precision" in prompt_lower:
            verdict = 0 if any(bad in prompt_lower for bad in ["irrelevant", "unhelpful", "not useful", "noisy"]) else 1
            reason = "Context provides relevant architectural definitions." if verdict == 1 else "Context is tangential or uninformative."
            content = json.dumps({"reason": reason, "verdict": verdict})

        # 5. Context Recall prompt (is reference statement attributed to context?)
        elif "attributed" in prompt_lower or "context_recall_classification" in prompt_lower:
            attr = 0 if any(bad in prompt_lower for bad in ["unattributed", "not attributed", "missing from context"]) else 1
            reason = "Directly attributed to retrieved specification chunks." if attr == 1 else "Information missing from retrieved context."
            content = json.dumps({"classifications": [{"statement": "Specification requirement", "reason": reason, "attributed": attr}]})

        # 6. Answer Correctness prompt (TP, FP, FN against reference ground truth)
        elif "true positive" in prompt_lower or "tp" in prompt_lower or "correctness_classifier" in prompt_lower:
            tp_statements = [{"statement": "Core architectural facts match ground truth.", "reason": "Agreement with reference."}]
            fp_statements = []
            fn_statements = []
            # Check if answer missed key elements or contained contradictions
            if "not specify" in prompt_lower and "expected" in prompt_lower:
                fn_statements.append({"statement": "Missed reference specification details.", "reason": "System abstained when reference specified answer."})
            content = json.dumps({"TP": tp_statements, "FP": fp_statements, "FN": fn_statements})

        # Default fallback schema
        else:
            content = json.dumps({"statements": [{"statement": "Architectural requirement", "verdict": 1, "reason": "Supported"}], "verdict": 1, "score": 1})

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "complete-mock-judge"


# ------------------------------------------------------------------------------
# 3. Judge Configuration Factory
# ------------------------------------------------------------------------------

@dataclass
class JudgeConfiguration:
    """Metadata regarding the active evaluation judge."""
    judge_type: str  # 'LIVE_LLM_JUDGE' or 'OFFLINE_MOCK_JUDGE'
    provider: str    # 'ollama', 'gemini', 'mock'
    model_name: str
    endpoint: Optional[str] = None
    is_live: bool = False
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judge_type": self.judge_type,
            "provider": self.provider,
            "model_name": self.model_name,
            "endpoint": self.endpoint,
            "is_live": self.is_live,
            "warning": self.warning,
        }


def get_ragas_judge(
    preference: str = "auto"
) -> Tuple[BaseRagasLLM, JudgeConfiguration]:
    """Configure and return the LLM judge for RAGAS evaluation.

    Preference precedence:
    - 'ollama': Force local Ollama instance (e.g. qwen2.5:3b)
    - 'gemini': Force Google Gemini API
    - 'mock': Force offline deterministic mock judge
    - 'auto': Automatically select Ollama if active; else Gemini if key set; else mock.
    """
    pref = preference.lower().strip()

    # 1. Local Ollama Path (Preferred for zero external data egress and deterministic local hosting)
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    if pref in ["ollama", "auto"]:
        try:
            import httpx
            resp = httpx.get(f"{ollama_base_url}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                available_names = [m.get("name") for m in tags]
                # Match requested model or pick the first available local model
                selected_model = ollama_model
                if available_names and ollama_model not in available_names:
                    # Pick closest match or first model
                    matched = [m for m in available_names if "qwen" in m or "llama" in m]
                    selected_model = matched[0] if matched else available_names[0]

                from langchain_ollama import ChatOllama
                ollama_llm = ChatOllama(
                    model=selected_model,
                    base_url=ollama_base_url,
                    temperature=0.0,
                )
                judge_wrapper = LangchainLLMWrapper(ollama_llm)
                config = JudgeConfiguration(
                    judge_type="LIVE_LLM_JUDGE",
                    provider="ollama",
                    model_name=selected_model,
                    endpoint=ollama_base_url,
                    is_live=True,
                    warning=None,
                )
                logger.info(f"Initialized live Ollama LLM judge: {selected_model} @ {ollama_base_url}")
                return judge_wrapper, config
        except Exception as exc:
            logger.info(f"Local Ollama is not active on {ollama_base_url}: {exc}")
            if pref == "ollama":
                raise RuntimeError(f"Ollama requested but unavailable at {ollama_base_url}: {exc}") from exc

    # 2. Cloud Gemini Path
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if pref in ["gemini", "auto"] and gemini_key and "replace" not in gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            gemini_llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=gemini_key,
                temperature=0.0,
            )
            judge_wrapper = LangchainLLMWrapper(gemini_llm)
            config = JudgeConfiguration(
                judge_type="LIVE_LLM_JUDGE",
                provider="gemini",
                model_name=model_name,
                endpoint="https://generativelanguage.googleapis.com",
                is_live=True,
                warning=None,
            )
            logger.info(f"Initialized live Gemini LLM judge: {model_name}")
            return judge_wrapper, config
        except Exception as exc:
            logger.warning(f"Could not initialize Gemini judge: {exc}")
            if pref == "gemini":
                raise

    # 3. Fallback / Explicit Mock Judge Path
    mock_model = CompleteMockJudge()
    judge_wrapper = LangchainLLMWrapper(mock_model)
    config = JudgeConfiguration(
        judge_type="OFFLINE_MOCK_JUDGE",
        provider="mock",
        model_name="mock-judge-v1",
        endpoint=None,
        is_live=False,
        warning=(
            "Evaluated using deterministic offline mock judge. "
            "These scores reflect pipeline execution and schema verification only, "
            "and MUST NOT be presented as genuine LLM quality measurements."
        ),
    )
    logger.info("Initialized offline mock judge wrapper (schema verification mode).")
    return judge_wrapper, config


# ------------------------------------------------------------------------------
# 4. Metric Configuration & Binding
# ------------------------------------------------------------------------------

def configure_and_get_metrics(
    judge: BaseRagasLLM,
    embeddings: BaseRagasEmbedding,
    selected_metrics: Optional[List[str]] = None,
) -> List[Any]:
    """Bind judge and embeddings to metrics and return selected metric objects."""
    faithfulness.llm = judge
    answer_relevancy.llm = judge
    answer_relevancy.embeddings = embeddings
    context_precision.llm = judge
    context_recall.llm = judge
    answer_correctness.llm = judge
    answer_correctness.embeddings = embeddings

    metric_map = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "answer_correctness": answer_correctness,
    }

    if not selected_metrics:
        return list(metric_map.values())

    chosen = []
    for m in selected_metrics:
        key = m.lower().strip()
        if key in metric_map:
            chosen.append(metric_map[key])
        else:
            logger.warning(f"Unknown metric '{m}' requested; skipping.")
    return chosen
