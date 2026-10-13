"""The commentary wrappers only pass arguments the installed SDKs' create() accept."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from app.services.commentary.anthropic_client import AnthropicCommentaryClient
from app.services.commentary.openai_client import OpenAICommentaryClient


class Recorder:
    def __init__(self, response):
        self.kwargs: dict = {}
        self._response = response

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self._response


def accepted(method) -> set[str]:
    return {n for n, p in inspect.signature(method).parameters.items() if p.kind == p.KEYWORD_ONLY}


def test_anthropic_wrapper_arguments_exist_on_messages_create(monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    monkeypatch.setattr("app.services.ops.usage_tracking.record_llm_usage_from_anthropic_response",
                        lambda *a, **k: None)
    client = AnthropicCommentaryClient("test-key")
    rec = Recorder(SimpleNamespace(content=[SimpleNamespace(type="text", text='{"ok": 1}')]))
    client._client = SimpleNamespace(messages=rec)
    assert client.generate(system_prompt="s", user_prompt="u") == {"ok": 1}
    unknown = set(rec.kwargs) - accepted(anthropic.resources.messages.Messages.create)
    assert not unknown, f"anthropic {anthropic.__version__} Messages.create() does not accept {sorted(unknown)}"


def test_openai_wrapper_arguments_exist_on_chat_completions_create():
    openai = pytest.importorskip("openai")
    client = OpenAICommentaryClient("test-key")
    msg = SimpleNamespace(message=SimpleNamespace(content='{"ok": 2}'))
    rec = Recorder(SimpleNamespace(choices=[msg]))
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=rec))
    assert client.generate(system_prompt="s", user_prompt="u") == {"ok": 2}
    unknown = set(rec.kwargs) - accepted(openai.resources.chat.completions.Completions.create)
    assert not unknown, f"openai {openai.__version__} chat.completions.create() does not accept {sorted(unknown)}"
