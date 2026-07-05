"""Regression test: some providers (e.g. Anthropic via LiteLLM) wrap JSON-mode
completions in a ```json ... ``` markdown fence, sometimes with leading or
trailing prose outside the fence, instead of returning bare JSON.
_extract_json_object must pull out the JSON object regardless of the
surrounding text so LLMClient.complete_json's json.loads doesn't fail
against a real model."""

from agents.common.llm_client import _extract_json_object


def test_strips_json_language_tagged_fence():
    content = '```json\n{"summary": "hello"}\n```'
    assert _extract_json_object(content) == '{"summary": "hello"}'


def test_strips_bare_fence_without_language_tag():
    content = '```\n{"summary": "hello"}\n```'
    assert _extract_json_object(content) == '{"summary": "hello"}'


def test_leaves_bare_json_untouched():
    content = '{"summary": "hello"}'
    assert _extract_json_object(content) == '{"summary": "hello"}'


def test_extracts_object_with_trailing_prose_after_fence():
    content = '```json\n{"summary": "hello"}\n```\nLet me know if you need anything else!'
    assert _extract_json_object(content) == '{"summary": "hello"}'


def test_extracts_object_with_leading_prose_before_fence():
    content = 'Sure, here is the JSON:\n```json\n{"summary": "hello"}\n```'
    assert _extract_json_object(content) == '{"summary": "hello"}'


def test_handles_nested_braces_and_braces_inside_strings():
    content = '```json\n{"summary": "uses a {placeholder}", "nested": {"a": 1}}\n```\nDone.'
    assert _extract_json_object(content) == '{"summary": "uses a {placeholder}", "nested": {"a": 1}}'
