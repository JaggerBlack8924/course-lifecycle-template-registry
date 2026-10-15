from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .infrai_email import InfraiEmailClient, InfraiError
from .lifecycle_templates import CourseRelease, PublishResult, publish_release


app = FastAPI(title="Course lifecycle template registry")


@app.post("/template-releases", response_model=PublishResult)
def create_template_release(release: CourseRelease) -> PublishResult:
    client = InfraiEmailClient()
    try:
        return publish_release(client, release)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    finally:
        client.close()
