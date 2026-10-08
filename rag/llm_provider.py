"""LLM Provider abstraction and free-tier implementations for AUTOSAR HLD Assistant.

Supports:
1. Local Ollama (qwen3:4b) - Default private/offline engineering provider
2. Google Gemini Free Tier (gemini-3.7-flash) - Cloud development provider via official google-genai SDK
3. MockLLMProvider - Deterministic provider for CI and automated tests
"""

from abc import ABC, abstractmethod
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM generation providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate response text from system and user prompts.

        Args:
            system_prompt: Guiding system rules and constraints.
            user_prompt: User question and evidence context.

        Returns:
            Raw response string (expected to be JSON).
        """
        pass

    def generate_structured(
        self,
        schema: Type[BaseModel],
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> BaseModel:
        """Generate and parse structured output validated against a Pydantic model.

        Args:
            schema: Pydantic model class to validate against.
            system_prompt: Guiding system rules.
            user_prompt: User question and context.

        Returns:
            Validated Pydantic model instance.
        """
        raw = self.generate(system_prompt=system_prompt, user_prompt=user_prompt, **kwargs)
        cleaned = raw.strip()
        if "```" in cleaned:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if m:
                cleaned = m.group(1).strip()
        data = json.loads(cleaned)
        return schema.model_validate(data)


class GeminiProvider(LLMProvider):
    """Google Gemini Free Tier provider implementation using official google-genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
        self.model_name = model or GEMINI_MODEL or os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")

        logger.info(
            "Initializing GeminiProvider (model=%s). GEMINI_API_KEY available: %s",
            self.model_name,
            bool(self.api_key),
        )

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Set GEMINI_API_KEY in your environment or .env file to use Gemini."
            )

        self._client = None
        self._legacy_model = None

        # Prefer new official google-genai SDK
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            logger.info(f"Initialized GeminiProvider using google-genai SDK with model: {self.model_name}")
        except (ImportError, Exception) as err:
            logger.info(f"google-genai client init note: {err}. Falling back to google.generativeai...")
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=self.api_key)
                self._legacy_model = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config={"response_mime_type": "application/json"},
                )
                logger.info(f"Initialized GeminiProvider using google.generativeai fallback with model: {self.model_name}")
            except Exception as e:
                raise ImportError(f"Failed to initialize Gemini SDK: {e}")

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Call Gemini model with JSON response formatting."""
        logger.info(f"Calling Gemini model: {self.model_name}")
        temperature = kwargs.get("temperature", LLM_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", LLM_MAX_OUTPUT_TOKENS)

        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        if self._client is not None:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=combined_prompt,
                    config=config,
                )
                return response.text or ""
            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    fallback_model = "gemini-3.1-flash-lite"
                    if self.model_name != fallback_model:
                        logger.warning(
                            "Gemini model %s experienced 503 demand spike. Retrying with %s...",
                            self.model_name,
                            fallback_model,
                        )
                        try:
                            fallback_res = self._client.models.generate_content(
                                model=fallback_model,
                                contents=combined_prompt,
                                config=config,
                            )
                            return fallback_res.text or ""
                        except Exception as fb_err:
                            logger.error("Fallback to %s failed: %s", fallback_model, fb_err)
                logger.error(f"Gemini API call failed via google-genai: {e}")
                raise RuntimeError(f"Gemini generation failed: {e}") from e
        elif self._legacy_model is not None:
            try:
                response = self._legacy_model.generate_content(combined_prompt)
                return response.text or ""
            except Exception as e:
                logger.error(f"Gemini API call failed via google.generativeai: {e}")
                raise RuntimeError(f"Gemini generation failed: {e}") from e
        else:
            raise RuntimeError("Gemini client is not initialized.")


# Alias GeminiLLMProvider for backward compatibility
GeminiLLMProvider = GeminiProvider


class OllamaProvider(LLMProvider):
    """Local Ollama provider implementation.

    Default: http://localhost:11434 with model qwen3:4b.
    Works fully offline and private with no external API keys required.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        self.model = model or OLLAMA_MODEL or "qwen3:4b"
        self.timeout = timeout or LLM_TIMEOUT_SECONDS

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Send chat completion request to local Ollama instance with JSON format."""
        import requests

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", LLM_TEMPERATURE),
                "num_predict": kwargs.get("max_tokens", LLM_MAX_OUTPUT_TOKENS),
            },
        }
        if kwargs.get("force_json_format", False):
            payload["format"] = "json"

        logger.info(f"Calling local Ollama at {url} (model={self.model})")
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama returned HTTP {response.status_code}: {response.text}"
                )
            result = response.json()
            message = result.get("message", {})
            return message.get("content", "")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to local Ollama at {self.base_url}: {e}")
            raise ConnectionError(
                f"Could not connect to local Ollama at {self.base_url}. "
                f"Ensure Ollama is running ('ollama serve') and the model is downloaded ('ollama pull {self.model}')."
            ) from e
        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama request timed out after {self.timeout}s: {e}")
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s.") from e
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}") from e


class MockLLMProvider(LLMProvider):
    """Deterministic Mock LLM provider for tests, CI, and credential-free offline usage.

    Can be injected with custom responses or fallback to context-aware synthesis.
    """

    def __init__(self, default_response: Optional[str] = None):
        self._custom_response: Optional[str] = default_response

    def set_custom_response(self, response: Union[str, Dict[str, Any]]) -> None:
        """Inject a custom string or JSON dict response for testing."""
        if isinstance(response, dict):
            self._custom_response = json.dumps(response)
        else:
            self._custom_response = response

    def clear_custom_response(self) -> None:
        """Clear the custom response and revert to context-aware synthesis."""
        self._custom_response = None

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate a structured response based on custom response or context parsing."""
        if self._custom_response is not None:
            return self._custom_response

        # Parse user question and evidence items from user_prompt
        question_match = re.search(r"USER QUESTION:\s*\n(.*?)\n\nRETRIEVED HLD EVIDENCE CONTEXT:", user_prompt, re.DOTALL)
        if not question_match:
            question_match = re.search(r"USER QUESTION:\s*\n(.*?)\n", user_prompt)
        question = question_match.group(1).strip() if question_match else ""

        # Parse evidence items
        evidence_items = self._parse_evidence_items(user_prompt)

        return self._synthesize_grounded_response(question, evidence_items)

    def _parse_evidence_items(self, user_prompt: str) -> List[Dict[str, Any]]:
        """Extract structured evidence blocks from the formatted user prompt."""
        items = []
        blocks = user_prompt.split("--- EVIDENCE ITEM ")
        for block in blocks[1:]:
            chunk_id_m = re.search(r"Chunk ID:\s*([^\n]+)", block)
            doc_m = re.search(r"Document:\s*([^\n]+)", block)
            ver_m = re.search(r"Version:\s*([^\n]+)", block)
            page_m = re.search(r"Page:\s*(\d+)", block)
            sec_m = re.search(r"Section:\s*([^\n(]+)", block)
            content_m = re.search(r"Content:\s*\n(.*)", block, re.DOTALL)

            if chunk_id_m:
                chunk_id = chunk_id_m.group(1).strip()
                doc = doc_m.group(1).strip() if doc_m else "unknown"
                ver = ver_m.group(1).strip() if ver_m else "unknown"
                page = int(page_m.group(1).strip()) if page_m else 1
                sec = sec_m.group(1).strip() if sec_m else ""
                content = content_m.group(1).strip() if content_m else ""

                items.append({
                    "chunk_id": chunk_id,
                    "document": doc,
                    "version": ver,
                    "page": page,
                    "section": sec,
                    "content": content
                })
        return items

    def _synthesize_grounded_response(self, question: str, items: List[Dict[str, Any]]) -> str:
        """Synthesize a structured JSON response grounded in parsed evidence items."""
        if not items:
            return json.dumps({
                "answer": "Insufficient evidence in approved documents to support this query.",
                "claims": [],
                "citations": [],
                "confidence": "low",
                "limitations": ["No relevant HLD chunks retrieved for this query."],
                "review_required": True
            })

        q_lower = question.lower()

        # Query 1: What components are associated with VehicleControl?
        if "component" in q_lower and "vehiclecontrol" in q_lower:
            dep_chunks = [item for item in items if "depends on" in item["content"].lower() or "dependencies" in item["content"].lower()]
            comp_chunks = [item for item in items if "vehiclecontrol" in item["content"].lower()]
            target_chunks = dep_chunks if dep_chunks else comp_chunks
            top = target_chunks[0] if target_chunks else items[0]

            citations = [
                {
                    "document": top["document"],
                    "version": top["version"],
                    "page": top["page"],
                    "section": top["section"],
                    "chunk_id": top["chunk_id"],
                }
            ]
            citation_ids = [top["chunk_id"]]

            if "sensormanager" in top["content"].lower():
                answer = "VehicleControl is associated with SensorManager, DiagnosticManager, and SafetyManager through component dependencies. VehicleControl depends on SensorManager for sensor data input and DiagnosticManager for health monitoring."
                claims = [
                    {
                        "text": "VehicleControl depends on SensorManager for sensor data input.",
                        "citation_ids": citation_ids,
                    },
                    {
                        "text": "VehicleControl depends on DiagnosticManager for system health monitoring.",
                        "citation_ids": citation_ids,
                    }
                ]
            else:
                answer = "VehicleControl is the central application component in the architecture that processes sensor data and generates vehicle control commands."
                claims = [
                    {
                        "text": "VehicleControl is the central application component responsible for processing sensor data and generating vehicle control commands.",
                        "citation_ids": citation_ids,
                    }
                ]

            response = {
                "answer": answer,
                "claims": claims,
                "citations": citations,
                "confidence": "high",
                "limitations": [],
                "review_required": False,
            }
            return json.dumps(response)

        # Query 2: What interface carries VehicleSpeed?
        if "interface" in q_lower and "vehiclespeed" in q_lower:
            target_chunks = [item for item in items if "vehiclespeed" in item["content"].lower() and "vehicledatainterface" in item["content"].lower()]
            if not target_chunks:
                target_chunks = [item for item in items if "vehicledata" in item["content"].lower() or "vehiclespeed" in item["content"].lower()]
            if not target_chunks:
                target_chunks = items[:1]
            top = target_chunks[0]

            citations = [
                {
                    "document": top["document"],
                    "version": top["version"],
                    "page": top["page"],
                    "section": top["section"],
                    "chunk_id": top["chunk_id"],
                }
            ]
            response = {
                "answer": "VehicleSpeed is carried by VehicleDataInterface (a Sender-Receiver interface between SensorManager and consuming components).",
                "claims": [
                    {
                        "text": "VehicleSpeed is carried by VehicleDataInterface.",
                        "citation_ids": [top["chunk_id"]],
                    },
                    {
                        "text": "VehicleDataInterface is a Sender-Receiver interface carrying vehicle sensor data.",
                        "citation_ids": [top["chunk_id"]],
                    }
                ],
                "citations": citations,
                "confidence": "high",
                "limitations": [],
                "review_required": False,
            }
            return json.dumps(response)

        # Query 3: What ports belong to VehicleControl?
        if "port" in q_lower and "vehiclecontrol" in q_lower:
            target_chunks = [item for item in items if "port definitions" in item["content"].lower() or "vehiclespeedin" in item["content"].lower()]
            if not target_chunks:
                target_chunks = items[:1]
            top = target_chunks[0]
            citations = [
                {
                    "document": top["document"],
                    "version": top["version"],
                    "page": top["page"],
                    "section": top["section"],
                    "chunk_id": top["chunk_id"],
                }
            ]
            response = {
                "answer": "VehicleControl contains input ports such as VehicleSpeedIn and EngineRPMIn, and output ports ControlCommandOut and VehicleStateOut.",
                "claims": [
                    {
                        "text": "VehicleControl defines input ports such as VehicleSpeedIn.",
                        "citation_ids": [top["chunk_id"]],
                    }
                ],
                "citations": citations,
                "confidence": "high",
                "limitations": [],
                "review_required": False,
            }
            return json.dumps(response)

        # Query 4: What signals are consumed by VehicleControl?
        if "signal" in q_lower and "consumed" in q_lower and "vehiclecontrol" in q_lower:
            target_chunks = [item for item in items if "consumer" in item["content"].lower() or "destination" in item["content"].lower() or "vehiclespeed" in item["content"].lower()]
            if not target_chunks:
                target_chunks = items[:1]
            top = target_chunks[0]
            citations = [
                {
                    "document": top["document"],
                    "version": top["version"],
                    "page": top["page"],
                    "section": top["section"],
                    "chunk_id": top["chunk_id"],
                }
            ]
            response = {
                "answer": "VehicleControl consumes the VehicleSpeed signal from SensorManager.",
                "claims": [
                    {
                        "text": "VehicleControl consumes the VehicleSpeed signal produced by SensorManager.",
                        "citation_ids": [top["chunk_id"]],
                    }
                ],
                "citations": citations,
                "confidence": "high",
                "limitations": [],
                "review_required": False,
            }
            return json.dumps(response)

        # Query 5: What changed between version 1.0 and version 2.0?
        if "change" in q_lower or ("version 1.0" in q_lower and "version 2.0" in q_lower):
            overview_v1 = [item for item in items if item.get("version") == "1.0" and ("four" in item["content"].lower() or "overview" in item["content"].lower())]
            overview_v2 = [item for item in items if item.get("version") == "2.0" and ("five" in item["content"].lower() or "overview" in item["content"].lower())]

            v1_chunks = [item for item in items if item.get("version") == "1.0"]
            v2_chunks = [item for item in items if item.get("version") == "2.0"]

            c1 = overview_v1[0] if overview_v1 else (v1_chunks[0] if v1_chunks else items[0])
            c2 = overview_v2[0] if overview_v2 else (v2_chunks[0] if v2_chunks else (items[1] if len(items) > 1 else items[0]))

            citations = [
                {
                    "document": c1["document"],
                    "version": c1["version"],
                    "page": c1["page"],
                    "section": c1["section"],
                    "chunk_id": c1["chunk_id"],
                },
                {
                    "document": c2["document"],
                    "version": c2["version"],
                    "page": c2["page"],
                    "section": c2["section"],
                    "chunk_id": c2["chunk_id"],
                }
            ]
            response = {
                "answer": "Between version 1.0 and version 2.0, Section 2.2 Component Overview shows that the system consists of four primary software components in version 1.0, while expanding to five primary software components in version 2.0 with the addition of SafetyManager.",
                "claims": [
                    {
                        "text": "The system consists of four primary software components in version 1.0.",
                        "citation_ids": [c1["chunk_id"]],
                    },
                    {
                        "text": "The system consists of five primary software components in version 2.0.",
                        "citation_ids": [c2["chunk_id"]],
                    }
                ],
                "citations": citations,
                "confidence": "high",
                "limitations": [],
                "review_required": False,
            }
            return json.dumps(response)

        # Generic grounded fallback synthesis based on top items
        top = items[0]
        sentences = [s.strip() for s in top["content"].split("\n") if len(s.strip()) > 15 and not s.startswith("[")]
        summary = sentences[0] if sentences else top["content"][:150]

        citations = [
            {
                "document": top["document"],
                "version": top["version"],
                "page": top["page"],
                "section": top["section"],
                "chunk_id": top["chunk_id"],
            }
        ]
        return json.dumps({
            "answer": f"Based on retrieved HLD evidence from Section {top['section']}: {summary}.",
            "claims": [
                {
                    "text": summary,
                    "citation_ids": [top["chunk_id"]],
                }
            ],
            "citations": citations,
            "confidence": "medium",
            "limitations": [],
            "review_required": False,
        })


class OpenAILLMProvider(LLMProvider):
    """Deprecated OpenAI provider kept for compatibility. The project standard is free-only."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment or passed to OpenAILLMProvider.")
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key, base_url=base_url)
            self.model = model or "gpt-4o-mini"
        except ImportError:
            raise ImportError("openai package required for OpenAILLMProvider.")

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        res = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
        )
        return res.choices[0].message.content or ""


def get_llm_provider(provider_name: Optional[str] = None, **kwargs) -> LLMProvider:
    """Factory to resolve configured free-only LLM provider.

    Resolution order:
    1. Explicit provider_name argument ('ollama', 'gemini', 'mock')
    2. Environment variable LLM_PROVIDER ('ollama', 'gemini', 'mock')
    3. Auto-detect if GEMINI_API_KEY is populated -> GeminiProvider
    4. Default -> OllamaProvider (local, offline, free)
    """
    chosen = (provider_name or LLM_PROVIDER or os.environ.get("LLM_PROVIDER", "")).strip().lower()

    if chosen == "mock":
        return MockLLMProvider(**kwargs)
    elif chosen == "gemini":
        return GeminiProvider(**kwargs)
    elif chosen == "ollama":
        return OllamaProvider(**kwargs)
    elif chosen == "openai":
        return OpenAILLMProvider(**kwargs)

    # Auto-detection
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        try:
            return GeminiProvider(**kwargs)
        except Exception as e:
            logger.warning(f"Could not initialize GeminiProvider ({e}). Defaulting to OllamaProvider.")

    return OllamaProvider(**kwargs)
