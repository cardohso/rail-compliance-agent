import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from rail_compliance.config import Settings
from rail_compliance.llm import (
    CachedAgentLLM,
    CachedStructuredLLM,
    ChatAgentLLM,
    ConfigError,
    LangChainStructuredLLM,
    make_chat_model,
)
from rail_compliance.retry import LLMUnavailable
from tests.fakes import ScriptedAgentLLM, ScriptedChatModel, ai, tool_call


class Answer(BaseModel):
    value: float


def test_chat_agent_llm_binds_tools_and_returns_tool_calls():
    chat = ScriptedChatModel(script=[ai(tool_call("search_regulation", question="door width"))])
    llm = ChatAgentLLM(chat, tools=["tool-a", "tool-b"], name="scripted:x")
    reply = llm.invoke([SystemMessage("s"), HumanMessage("h")])
    assert chat.bound_tools == ["tool-a", "tool-b"]
    assert reply.tool_calls[0]["name"] == "search_regulation"
    assert reply.tool_calls[0]["args"] == {"question": "door width"}


def test_chat_agent_llm_retries_a_rate_limit(monkeypatch):
    class RateLimited(Exception):
        status_code = 429

    calls = []
    chat = ScriptedChatModel(script=[ai(text="done")])
    original = chat._generate

    def flaky(*a, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise RateLimited("slow down")
        return original(*a, **kw)

    monkeypatch.setattr(chat, "_generate", flaky)
    monkeypatch.setattr("rail_compliance.retry.time.sleep", lambda s: None)
    assert ChatAgentLLM(chat, [], "x").invoke([HumanMessage("h")]).content == "done"
    assert len(calls) == 2


def test_chat_agent_llm_gives_up_with_llm_unavailable(monkeypatch):
    class RateLimited(Exception):
        status_code = 429

    chat = ScriptedChatModel(script=[])
    monkeypatch.setattr(chat, "_generate", lambda *a, **k: (_ for _ in ()).throw(RateLimited("x")))
    monkeypatch.setattr("rail_compliance.retry.time.sleep", lambda s: None)
    with pytest.raises(LLMUnavailable):
        ChatAgentLLM(chat, [], "x").invoke([HumanMessage("h")])


def test_structured_llm_returns_the_parsed_object():
    class Structured:
        def with_structured_output(self, schema):
            return type("R", (), {"invoke": lambda self, msgs: schema(value=800)})()

    out = LangChainStructuredLLM(Structured(), "x").extract("sys", "user", Answer)
    assert out == Answer(value=800)


def test_structured_llm_validates_a_plain_dict_reply():
    class Structured:
        def with_structured_output(self, schema):
            return type("R", (), {"invoke": lambda self, msgs: {"value": 5}})()

    assert LangChainStructuredLLM(Structured(), "x").extract("s", "u", Answer) == Answer(value=5)


def test_cached_agent_llm_replays_identical_conversations(tmp_path):
    inner = ScriptedAgentLLM(
        [ai(tool_call("check", parameter="p", spec_value=1.0, requirement_id="R1"))]
    )
    cached = CachedAgentLLM(inner, tmp_path)
    convo = [SystemMessage("s"), HumanMessage("h")]
    first = cached.invoke(convo)
    second = cached.invoke(convo)  # the script is empty: a second model call would raise
    assert second.tool_calls == first.tool_calls
    assert (cached.hits, cached.misses) == (1, 1)


def test_cached_agent_llm_keys_on_the_whole_conversation(tmp_path):
    inner = ScriptedAgentLLM([AIMessage("one"), AIMessage("two")])
    cached = CachedAgentLLM(inner, tmp_path)
    assert cached.invoke([HumanMessage("a")]).content == "one"
    assert cached.invoke([HumanMessage("b")]).content == "two"


def test_cached_structured_llm_calls_the_model_once(tmp_path):
    calls = []

    class Inner:
        name = "m"

        def extract(self, system, user, schema):
            calls.append(user)
            return schema(value=1)

    cached = CachedStructuredLLM(Inner(), tmp_path)
    assert cached.extract("s", "u", Answer) == Answer(value=1)
    assert cached.extract("s", "u", Answer) == Answer(value=1)
    cached.extract("s", "other", Answer)
    assert calls == ["u", "other"]


def test_make_chat_model_without_a_key_explains_how_to_fix_it():
    settings = Settings(_env_file=None, gemini_api_key="", agent_provider="gemini")
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        make_chat_model(settings)


def test_make_chat_model_builds_the_configured_provider_without_calling_it():
    gemini = Settings(_env_file=None, gemini_api_key="not-a-real-key", agent_provider="gemini")
    chat, name = make_chat_model(gemini)
    assert name == "gemini:gemini-3.5-flash-lite"
    assert chat is not None
    groq = Settings(_env_file=None, groq_api_key="not-a-real-key", agent_provider="groq")
    assert make_chat_model(groq)[1] == "groq:openai/gpt-oss-120b"


def test_unparseable_model_output_becomes_a_structured_output_error():
    from langchain_core.exceptions import OutputParserException

    from rail_compliance.tools.extract import StructuredOutputError

    class Broken:
        def with_structured_output(self, schema):
            def boom(msgs):
                raise OutputParserException("Failed to parse: both value and bands")

            return type("R", (), {"invoke": lambda self, msgs: boom(msgs)})()

    with pytest.raises(StructuredOutputError, match="both value and bands"):
        LangChainStructuredLLM(Broken(), "x").extract("s", "u", Answer)
