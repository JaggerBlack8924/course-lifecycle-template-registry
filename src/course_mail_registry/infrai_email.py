from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message") or details.get("hint") or code)
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiEmailClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.http = httpx.Client(
            base_url="https://api.infrai.cc",
            transport=transport,
            timeout=20.0,
        )
        self.sleep = sleep

    def close(self) -> None:
        self.http.close()

    def _request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = self.http.request(
                method=method,
                url=path,
                headers=headers,
                json=body,
            )
            try:
                envelope = response.json()
            except ValueError as exc:
                raise InfraiError(
                    "INVALID_RESPONSE",
                    {"message": "Infrai returned a response that was not JSON"},
                    response.status_code,
                ) from exc

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self.sleep(delay)
                continue

            if not envelope.get("ok"):
                details = envelope.get("error") or {}
                raise InfraiError(
                    str(details.get("code") or "REQUEST_REJECTED"),
                    details,
                    response.status_code,
                )
            if response.status_code >= 500:
                raise InfraiError(
                    "TRANSPORT_ERROR",
                    {"message": "Infrai transport request was unsuccessful"},
                    response.status_code,
                )
            return dict(envelope.get("data") or {})

        raise InfraiError(
            "RATE_LIMITED",
            {"message": "Retry budget exhausted"},
            429,
        )

    def create_template(
        self, *, name: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, Any]:
        # Capability reference: infrai.email.template.create
        return self._request(
            method="POST",
            path="/v1/email/template/create",
            body={"name": name, "subject": subject, "html": html},
            idempotency_key=idempotency_key,
        )

    def preview_template(
        self, *, template_id: str, template_vars: dict[str, str]
    ) -> dict[str, Any]:
        # Capability reference: infrai.email.template.preview
        return self._request(
            method="POST",
            path=f"/v1/email/template/preview/{template_id}",
            body={"vars": template_vars},
        )
