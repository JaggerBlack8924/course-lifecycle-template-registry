from __future__ import annotations

import json

import httpx

from course_mail_registry.infrai_email import InfraiEmailClient


def test_create_retries_429_with_same_idempotency_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={
                    "ok": False,
                    "data": None,
                    "error": {"code": "RATE_LIMITED"},
                    "metadata": {},
                },
            )
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"template_id": "tpl-91"},
                "error": None,
                "metadata": {},
            },
        )

    client = InfraiEmailClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    try:
        result = client.create_template(
            name="analytics-201-2026-10-01-course-delivery",
            subject="Module ready",
            html="<p>Ready</p>",
            idempotency_key="course-template:delivery",
        )
    finally:
        client.close()

    assert result == {"template_id": "tpl-91"}
    assert [request.method for request in seen] == ["POST", "POST"]
    assert {request.headers["Idempotency-Key"] for request in seen} == {
        "course-template:delivery"
    }
    assert json.loads(seen[0].content) == {
        "name": "analytics-201-2026-10-01-course-delivery",
        "subject": "Module ready",
        "html": "<p>Ready</p>",
    }


def test_preview_sends_vars() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"subject": "Module ready", "html": "<p>Ready</p>"},
                "error": None,
                "metadata": {},
            },
        )

    client = InfraiEmailClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    try:
        client.preview_template(
            template_id="tpl-91",
            template_vars={"module_name": "Cohort retention"},
        )
    finally:
        client.close()

    assert seen[0].url.path == "/v1/email/template/preview/tpl-91"
    assert json.loads(seen[0].content) == {
        "vars": {"module_name": "Cohort retention"}
    }
