from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


class TemplatePublisher(Protocol):
    def create_template(
        self, *, name: str, subject: str, html: str, idempotency_key: str
    ) -> dict:
        raise AssertionError("Protocol declaration")

    def preview_template(
        self, *, template_id: str, template_vars: dict[str, str]
    ) -> dict:
        raise AssertionError("Protocol declaration")


class CourseRelease(BaseModel):
    course_key: str = Field(pattern=r"^[a-z0-9-]+$")
    release_tag: str = Field(pattern=r"^[a-z0-9-]+$")
    course_name: str = Field(min_length=1)
    module_name: str = Field(min_length=1)
    deadline_at: str = Field(min_length=1)
    hours_to_deadline: int = Field(ge=0)
    overdue_learners: int = Field(ge=0)
    educator_name: str = Field(min_length=1)


class PublishedTemplate(BaseModel):
    stage: str
    name: str
    template_id: str


class PublishResult(BaseModel):
    course_key: str
    deadline_tier: str
    templates: list[PublishedTemplate]


@dataclass(frozen=True)
class TemplateDefinition:
    stage: str
    subject: str
    html: str
    sample_vars: dict[str, str]


def deadline_tier(release: CourseRelease) -> str:
    if release.overdue_learners > 0:
        return "overdue"
    if release.hours_to_deadline <= 48:
        return "due-soon"
    return "scheduled"


def template_batch(
    release: CourseRelease,
) -> tuple[TemplateDefinition, TemplateDefinition, TemplateDefinition]:
    tier = deadline_tier(release)
    deadline_subject = {
        "scheduled": "Plan for {{course_name}} before {{deadline_at}}",
        "due-soon": "{{course_name}} is due soon",
        "overdue": "Action needed for {{course_name}}",
    }[tier]
    common = {
        "course_name": release.course_name,
        "module_name": release.module_name,
        "deadline_at": release.deadline_at,
        "educator_name": release.educator_name,
        "overdue_learners": str(release.overdue_learners),
    }
    return (
        TemplateDefinition(
            stage="course-delivery",
            subject="{{module_name}} is open in {{course_name}}",
            html="<h1>{{module_name}}</h1><p>Your next course module is ready.</p>",
            sample_vars=common,
        ),
        TemplateDefinition(
            stage=f"learner-deadline-{tier}",
            subject=deadline_subject,
            html="<p>Complete {{module_name}} by {{deadline_at}}.</p>",
            sample_vars=common,
        ),
        TemplateDefinition(
            stage="educator-report",
            subject="{{course_name}} deadline report",
            html=(
                "<p>Hi {{educator_name}}, {{overdue_learners}} learners "
                "are past the current deadline.</p>"
            ),
            sample_vars=common,
        ),
    )


def publish_release(
    publisher: TemplatePublisher, release: CourseRelease
) -> PublishResult:
    published: list[PublishedTemplate] = []
    for definition in template_batch(release):
        name = (
            f"{release.course_key}-{release.release_tag}-{definition.stage}"
        )
        created = publisher.create_template(
            name=name,
            subject=definition.subject,
            html=definition.html,
            idempotency_key=f"course-template:{name}",
        )
        template_id = str(created["template_id"])
        publisher.preview_template(
            template_id=template_id,
            template_vars=definition.sample_vars,
        )
        published.append(
            PublishedTemplate(
                stage=definition.stage,
                name=name,
                template_id=template_id,
            )
        )
    return PublishResult(
        course_key=release.course_key,
        deadline_tier=deadline_tier(release),
        templates=published,
    )
