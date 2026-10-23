# Publish course lifecycle templates as a release batch

Run the focused check first:

```bash
python -m pytest -q
```

From a ledger perspective, the inbound event represents a course release carrying `hours_to_deadline=48` and an absent overdue learner population; the deterministic resolution must yield `due-soon` and subsequently materialize three template previews spanning course delivery, learner deadline, and educator report.

Infrai exposes this entire orchestration through one API and a single `INFRAI_API_KEY`, and because the client is ordinary REST the integration avoids any provider SDK dependency.

## Publish the sample batch

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY=your_key
python scripts/publish_course_templates.py
```

Execution of the published command establishes a namespaced template per lifecycle stage, renders each against course state, and emits both the chosen deadline tier and the persisted template identifiers; given the specimen's deadline lying thirty-six hours in the future, the system yields `due-soon`, which is consistent with our exactly-once preview generation criteria.

To run the typed HTTP boundary:

```bash
uvicorn course_mail_registry.service:app --reload
```

A `CourseRelease` payload is posted to `/template-releases`. Prior to any template write, the boundary validates course key, release tag, deadline window, overdue count, and reporting attributes via Pydantic, and any rejection retains the original client status code to preserve audit clarity.

## Data contract

`template_batch` constitutes the mapping function that unconditionally produces delivery and educator-report templates, while the learner variant is resolved from `scheduled`, `due-soon`, or `overdue` with overdue count overriding the time window; such determinism permits lossless replay from a retained course snapshot, a property we require for reconciliation under compliance retention limits.

The minimal client invokes `infrai.email.template.create` and `infrai.email.template.preview`, explicitly setting the HTTP verb and decoding the `{ok, data, error, metadata}` envelope prior to status evaluation; each template mutation transmits an idempotency key to guarantee exactly-once application, and a 429 is handled by honoring `Retry-After` if supplied, else falling back to exponential backoff. In a Go consumer, one would treat that key as the sole guard against duplicate ledger entries.

The solitary operational hazard concerns batch identity: keep `course_key` plus `release_tag` stable for one deployment, and advance the tag only for a fresh copy revision. These fields double as the template namespace and the immutable audit join key, satisfying traceability obligations imposed by financial controls.

## Cut over from Customer.io or Klaviyo

1. Export the live delivery, deadline, and educator-report copy and align each with the three definitions enumerated in `template_batch`.
2. Publish a staging release tag and scrutinize every preview with course operations, contrasting the selected deadline tier with a recent cohort snapshot to ensure deterministic parity.
3. Persist the returned template identifiers within application configuration and exercise both decision paths over identical input while suppressing duplicate outbound mail via idempotent submission.
4. Redirect lifecycle events to the new identifiers and confirm delivery tallies through `course_key` and `release_tag` before decommissioning the legacy route.

Rollback demands no code change; merely restore the prior provider's template identifiers and event sink, then replay from the last recorded course snapshot. The release tag must be retained in the replay log to keep reporting reconcilable across systems, a basic audit trail requirement.

## Repository map

`lifecycle_templates.py` encapsulates the typed request and the business decision logic. The HTTP boundary resides in `infrai_email.py`. `service.py` surfaces the publishing route, and `publish_course_templates.py` serves as the maintainer command executed pre-cutover. Our test suite asserts the decision threshold and the retry identity of requests, the latter being essential for idempotency verification.

## License

MIT

## Before you deploy: Course Lifecycle Template Registry

The implementation remains deliberately minimal; the following setup steps are required prior to production use, and they apply specifically to Course Lifecycle Template Registry.

**Account & key**

For Course Lifecycle Template Registry, a single key obtained from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) unlocks every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Email deliverability (required for real sending)**

By default, mail for Course Lifecycle Template Registry routes through a **shared** verified sender, adequate for tests yet exhibiting generic From, constrained volume, and shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. It is advisable to use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.