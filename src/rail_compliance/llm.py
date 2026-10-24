"""The two ways the agent uses a language model, and the providers behind them.

- `AgentLLM`: one chat turn with tools bound; the agent's decision-maker.
- `StructuredLLM` (see tools/extract.py): text in, a validated Pydantic object out.

Both take any LangChain chat model, retry rate limits with backoff, and can be wrapped in a disk
cache keyed by model and full prompt, so re-running an evaluation costs no quota.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, messages_from_dict, messages_to_dict
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from rail_compliance.config import Settings
from rail_compliance.retry import with_retries
from rail_compliance.tools.extract import StructuredOutputError

DEFAULT_MODELS = {"gemini": "gemini-3.5-flash-lite", "groq": "openai/gpt-oss-120b"}
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class ConfigError(RuntimeError):
    pass


class AgentLLM(Protocol):
    name: str

    def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage: ...


class ChatAgentLLM:
    """A chat model with the agent's tools bound. Tool calls come back on `AIMessage.tool_calls`."""

    def __init__(self, chat_model: BaseChatModel, tools: Sequence[BaseTool], name: str):
        self.name = name
        self._model = chat_model.bind_tools(list(tools))

    def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        reply = with_retries(lambda: self._model.invoke(list(messages)))
        if not isinstance(reply, AIMessage):
            raise TypeError(f"expected an AIMessage, got {type(reply).__name__}")
        return reply


class LangChainStructuredLLM:
    """Implements `StructuredLLM` with the model's structured-output mode."""

    def __init__(self, chat_model: BaseChatModel, name: str):
        self.name = name
        self._model = chat_model

    def extract[T: BaseModel](self, system: str, user: str, schema: type[T]) -> T:
        runnable = self._model.with_structured_output(schema)
        try:
            reply = with_retries(lambda: runnable.invoke([("system", system), ("human", user)]))
        except OutputParserException as exc:
            raise StructuredOutputError(str(exc)) from exc
        return reply if isinstance(reply, schema) else schema.model_validate(reply)


def _key(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


class CachedAgentLLM:
    def __init__(self, inner: AgentLLM, cache_dir: Path):
        self.inner, self.cache_dir, self.name = inner, Path(cache_dir), inner.name
        self.hits = self.misses = 0

    def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        payload = json.dumps(messages_to_dict(list(messages)), sort_keys=True, default=str)
        path = self.cache_dir / f"agent-{_key(self.inner.name, payload)}.json"
        if path.exists():
            self.hits += 1
            return messages_from_dict([json.loads(path.read_text(encoding="utf-8"))])[0]
        self.misses += 1
        reply = self.inner.invoke(messages)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(messages_to_dict([reply])[0], default=str), encoding="utf-8")
        return reply


class CachedStructuredLLM:
    def __init__(self, inner, cache_dir: Path):
        self.inner, self.cache_dir = inner, Path(cache_dir)
        self.name = getattr(inner, "name", "structured")
        self.hits = self.misses = 0

    def extract[T: BaseModel](self, system: str, user: str, schema: type[T]) -> T:
        path = self.cache_dir / f"extract-{_key(self.name, schema.__name__, system, user)}.json"
        if path.exists():
            self.hits += 1
            return schema.model_validate_json(path.read_text(encoding="utf-8"))
        self.misses += 1
        result = self.inner.extract(system, user, schema)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(), encoding="utf-8")
        return result


def make_chat_model(settings: Settings) -> tuple[BaseChatModel, str]:
    """The configured provider's chat model (temperature 0) and its "<provider>:<model>" name."""
    provider = settings.agent_provider
    key = settings.api_key(provider)
    if not key:
        raise ConfigError(
            f"no API key for '{provider}': copy .env.example to .env and set "
            f"{provider.upper()}_API_KEY (the file is git-ignored)"
        )
    model = settings.agent_model or DEFAULT_MODELS[provider]
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        # no temperature: this model family fixes its sampling and warns if one is passed
        chat = ChatGoogleGenerativeAI(model=model, google_api_key=key)
    else:
        from langchain_openai import ChatOpenAI

        chat = ChatOpenAI(model=model, api_key=key, base_url=GROQ_BASE_URL, temperature=0.0)
    return chat, f"{provider}:{model}"
