"""Runtime compatibility shim for RAGAS and LangChain integrations.

Ensures clean importability of upstream ragas packages on modern langchain
environments without requiring manual patches to site-packages or installed dependencies.
"""

import sys
import types

# Upstream ragas 0.4.x imports ChatVertexAI from langchain_community.chat_models.vertexai
# which was deprecated/migrated in modern langchain-community. This shim provides a transparent
# fallback stub if the module is missing in the host environment.
if "langchain_community.chat_models.vertexai" not in sys.modules:
    try:
        import langchain_community.chat_models.vertexai  # type: ignore
    except (ImportError, ModuleNotFoundError):
        m_chat = types.ModuleType("langchain_community.chat_models.vertexai")
        m_chat.ChatVertexAI = type("ChatVertexAI", (), {})
        sys.modules["langchain_community.chat_models.vertexai"] = m_chat

if "langchain_community.llms.vertexai" not in sys.modules:
    try:
        import langchain_community.llms.vertexai  # type: ignore
    except (ImportError, ModuleNotFoundError):
        m_llm = types.ModuleType("langchain_community.llms.vertexai")
        m_llm.VertexAI = type("VertexAI", (), {})
        sys.modules["langchain_community.llms.vertexai"] = m_llm
