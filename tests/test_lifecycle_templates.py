from __future__ import annotations

from typing import Any

from course_mail_registry.lifecycle_templates import CourseRelease, publish_release


class RecordingPublisher:
    def __init__(self) -> None:
        self.creates: list[dict[str, Any]] = []
        self.previews: list[dict[str, Any]] = []

    def create_template(self, **request: Any) -> dict[str, str]:
        self.creates.append(request)
        return {"template_id": f"tpl-{len(self.creates)}"}

    def preview_template(self, **request: Any) -> dict[str, str]:
        self.previews.append(request)
        return {"html": "rendered"}


def release(**changes: Any) -> CourseRelease:
    values = {
        "course_key": "analytics-201",
        "release_tag": "2026-10-01",
        "course_name": "Learning Analytics 201",
        "module_name": "Cohort retention",
        "deadline_at": "2026-10-05 17:00 UTC",
        "hours_to_deadline": 72,
        "overdue_learners": 0,
        "educator_name": "Dr. Chen",
    }
    values.update(changes)
    return CourseRelease(**values)


def test_due_soon_release_publishes_three_previewed_templates() -> None:
    publisher = RecordingPublisher()

    result = publish_release(publisher, release(hours_to_deadline=48))

    assert result.deadline_tier == "due-soon"
    assert [item.stage for item in result.templates] == [
        "course-delivery",
        "learner-deadline-due-soon",
        "educator-report",
    ]
    assert len(publisher.creates) == len(publisher.previews) == 3
    assert publisher.creates[1]["name"] == (
        "analytics-201-2026-10-01-learner-deadline-due-soon"
    )
    assert publisher.creates[1]["idempotency_key"].startswith("course-template:")
    assert publisher.previews[1]["template_vars"]["module_name"] == (
        "Cohort retention"
    )


def test_overdue_count_takes_precedence_over_hours_remaining() -> None:
    publisher = RecordingPublisher()

    result = publish_release(
        publisher,
        release(hours_to_deadline=96, overdue_learners=7),
    )

    assert result.deadline_tier == "overdue"
    assert result.templates[1].stage == "learner-deadline-overdue"
