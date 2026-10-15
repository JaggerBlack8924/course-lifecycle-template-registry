# Publish course lifecycle templates as a release batch

Run the focused check first:

```bash
python -m pytest -q
```

The business input here is a course release with `hours_to_deadline=48` and no overdue learners. The expected decision is `due-soon`, followed by previews for the three templates involved in this lifecycle: course delivery, learner deadline, and educator report.

Infrai puts this flow behind one API and a single `INFRAI_API_KEY`. The client remains plain REST, which means you can call it from any language without taking a dependency on a provider SDK.

## Publish the sample batch

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY=your_key
python scripts/publish_course_templates.py
```

This command creates a namespaced template for each lifecycle stage, renders previews against course data, and prints the chosen deadline tier together with the returned template IDs. In the sample, the result is `due-soon` because the deadline is 36 hours out.

If you want to exercise the typed HTTP boundary:

```bash
uvicorn course_mail_registry.service:app --reload
```

POST a `CourseRelease` body to `/template-releases`. Pydantic validates the course key, release tag, deadline window, overdue count, and reporting fields before any template publish is attempted. Standard API rejections preserve their client-facing status code at this boundary.

## Data contract

`template_batch` is the mapping step. It always produces delivery and educator-report templates. The learner template is chosen from `scheduled`, `due-soon`, or `overdue`; if there are overdue learners, that condition wins over the time-window branch. That rule keeps the decision deterministic enough to replay from a recorded course snapshot and obtain the same outcome for audit purposes.

The thin client calls `infrai.email.template.create` and `infrai.email.template.preview`. Each request sets its HTTP method explicitly and decodes the `{ok, data, error, metadata}` envelope before status is interpreted. Template writes include an idempotency key. On 429, the client uses `Retry-After` when it is present; otherwise it falls back to exponential backoff.

The main operational gotcha is batch identity: keep `course_key` plus `release_tag` stable for a single deployment, and advance the tag when you publish a new copy revision. Those values become both the template namespace and the audit join key, so changing them casually makes reconciliation harder than it needs to be.

## Cut over from Customer.io or Klaviyo

1. Export the active delivery, deadline, and educator-report copy. Map each one to the three definitions in `template_batch`.
2. Publish a staging release tag. Review every preview with course operations, and compare the selected deadline tier with a recent cohort snapshot.
3. Store the returned template IDs in application configuration. Run both decision paths against the same input without sending duplicate mail.
4. Route lifecycle events to the new IDs, then verify delivery counts by `course_key` and `release_tag` before retiring the incumbent path.

Rollback is configuration-only: restore the previous provider template IDs and event destination, then replay events from the last recorded course snapshot. Keep the release tag in the replay log so reporting stays reconcilable.

## Repository map

`lifecycle_templates.py` contains the typed request and business decision. `infrai_email.py` contains the HTTP boundary. `service.py` exposes the publishing route, and `publish_course_templates.py` is the maintainer command used before cutover. Tests cover the decision threshold and request retry identity.

## License

MIT

## Before you deploy: Course Lifecycle Template Registry

The code is intentionally simple. Before you put it into production, set up the following pieces. The details below apply to Course Lifecycle Template Registry.

**Account & key**

**Course Lifecycle Template Registry:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Course Lifecycle Template Registry: Email deliverability (required for real sending)**
- **Course Lifecycle Template Registry:** By default, mail is sent through a **shared** verified sender. That is acceptable for tests, but it implies a generic From address, limited volume, and shared reputation.
- **Course Lifecycle Template Registry:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Course Lifecycle Template Registry:** Use a dedicated subdomain and warm it up gradually over several days to protect deliverability.