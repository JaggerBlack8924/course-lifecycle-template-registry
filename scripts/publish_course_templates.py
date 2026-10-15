from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from course_mail_registry.infrai_email import InfraiEmailClient  # noqa: E402
from course_mail_registry.lifecycle_templates import (  # noqa: E402
    CourseRelease,
    publish_release,
)


def main() -> None:
    release = CourseRelease(
        course_key="analytics-201",
        release_tag="2026-10-01",
        course_name="Learning Analytics 201",
        module_name="Cohort retention",
        deadline_at="2026-10-05 17:00 UTC",
        hours_to_deadline=36,
        overdue_learners=0,
        educator_name="Dr. Chen",
    )
    client = InfraiEmailClient()
    try:
        result = publish_release(client, release)
        print(json.dumps(result.model_dump(), indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
