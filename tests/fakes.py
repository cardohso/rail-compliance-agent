"""Scripted stand-ins for the language models, so the agent is tested without any network."""

from collections.abc import Callable, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def tool_call(name: str, call_id: str = "c1", **args) -> dict:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def ai(*calls: dict, text: str = "") -> AIMessage:
    return AIMessage(content=text, tool_calls=list(calls))


class ScriptedAgentLLM:
    """An `AgentLLM` that replays a script. A step is an AIMessage, or a function of the
    conversation so far (to read ids such as R1 out of earlier tool results)."""

    name = "scripted:agent"

    def __init__(self, script: Sequence[AIMessage | Callable[[list[BaseMessage]], AIMessage]]):
        self.script = list(script)
        self.seen: list[list[BaseMessage]] = []

    def invoke(self, messages):
        self.seen.append(list(messages))
        if not self.script:
            raise AssertionError("the agent called the model more often than the script allows")
        step = self.script.pop(0)
        return step(list(messages)) if callable(step) else step


class ScriptedChatModel(BaseChatModel):
    """A LangChain chat model that returns scripted messages and records what it was given."""

    script: list = []
    received: list = []
    bound_tools: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = list(tools)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(messages)
        return ChatResult(generations=[ChatGeneration(message=self.script.pop(0))])
