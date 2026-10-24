"""Wire settings into a ready-to-run agent."""

from __future__ import annotations

from pathlib import Path

from rail_compliance.agent import ComplianceAgent, tool_definitions
from rail_compliance.config import Settings
from rail_compliance.llm import (
    CachedAgentLLM,
    CachedStructuredLLM,
    ChatAgentLLM,
    ConfigError,
    LangChainStructuredLLM,
    make_chat_model,
)
from rail_compliance.throttle import Throttle
from rail_compliance.tools.search import (
    CachingBackend,
    LiveBackend,
    LocalBackend,
    ReplayBackend,
    SearchBackend,
)


def make_search_backend(
    settings: Settings, *, replay_file: Path | None = None, use_cache: bool = True
) -> SearchBackend:
    kind = settings.search_backend
    if kind == "replay":
        if replay_file is None:
            raise ConfigError("SEARCH_BACKEND=replay needs a recorded-results file (--replay)")
        return ReplayBackend.from_file(replay_file)  # already on disk: no cache needed
    backend: SearchBackend = (
        LocalBackend.from_rail_rag(settings.rail_rag_data_dir)
        if kind == "local"
        else LiveBackend(settings.rail_api_url)
    )
    return CachingBackend(backend, settings.search_cache_dir) if use_cache else backend


def build_agent(
    settings: Settings,
    *,
    use_cache: bool = True,
    replay_file: Path | None = None,
    k: int = 8,
    max_calls: int = 10,
) -> ComplianceAgent:
    chat, name = make_chat_model(settings)
    throttle = Throttle(settings.llm_requests_per_minute)  # shared: both roles use one quota
    llm = ChatAgentLLM(chat, tool_definitions(), name, throttle)
    extractor = LangChainStructuredLLM(chat, name, throttle)
    if use_cache:
        llm = CachedAgentLLM(llm, settings.llm_cache_dir)
        extractor = CachedStructuredLLM(extractor, settings.llm_cache_dir)
    search = make_search_backend(settings, replay_file=replay_file, use_cache=use_cache)
    return ComplianceAgent(llm, extractor, search, k=k, max_calls=max_calls)
