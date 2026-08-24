---
name: mapping-qc-validator
description: Use when validating Curam-to-FHIR mapping JSON, progress tracking, domains, resources, Basic avoidance, and DataType avoidance.
---

# Mapping QC Validator Skill

Validate `tables_json.json` after each Word file and at final review.

Hard failures:

1. invalid JSON;
2. top-level JSON is not an array;
3. missing `table_name`;
4. duplicate `table_name`;
5. invalid `data_domain`;
6. invalid `match_type`;
7. forbidden final `fhir_target_resource`;
8. `Basic` as final target;
9. DataType as final target;
10. `FULL_MATCH` with extensions;
11. extensions missing target/purpose/example path;
12. quality_checks not true;
13. missing required schema fields.

Allowed data domains:

- Assessments
- Outcome Plan
- Case Management
- Documents
- Finance
- Legal
- People
- Provider
- System
- Users

Match types:

- FULL_MATCH
- PARTIAL_MATCH
- NO_MATCH

Forbidden final targets:

- Basic
- Resource
- DomainResource
- Element
- BackboneElement
- Extension
- Narrative
- Address
- HumanName
- Identifier
- ContactPoint
- CodeableConcept
- Coding
- Reference
- Period
- Quantity
- Annotation

## Semantic / BA-alignment checks (review-time)

The Python validator cannot catch these; the reviewer must flag them. Treat each as a finding that requires the mapper to revise (not just a note):

1. **Clinical-dismissal rationale.** Any `candidate_resources_considered` reason that rejects a resource for being "healthcare", "clinical", "claim", or "medical" oriented. Rejections must be structural/semantic. (This assessment repurposes FHIR for social welfare.)
2. **Restricted-resource misuse.** `Provenance`, `AuditEvent`, or `Consent` used when the table's core purpose is **not** security, access control, consent/privacy, or audit/provenance logging. History/snapshot/change-log/lifecycle/transaction-log tables must map to a business resource instead.
3. **Task misuse.** `Task` used for workflow-engine runtime, batch/scheduler internals, or milestones/stages. `Task` is reserved for CAS/caseworker work items; milestones → `Goal`; definitions → `PlanDefinition`/`ActivityDefinition`/`OperationDefinition`.
4. **Outcome Plan category.** Outcome Plan tables that do not use a Care Provision resource (CarePlan, CareTeam, Goal, ServiceRequest, RiskAssessment, RequestGroup) without a clear reason.

## Progress Tracking Validation

When `mapping_progress.json` exists, check:

1. `sorted_input_files` exists and is ordered by numeric file range.
2. Every file in `processed_files` exists in `sorted_input_files`.
3. Every file in `reviewed_files` exists in `processed_files`.
4. `pending_review_file`, if present, exists in `processed_files`.
5. If status is `pending_review`, `pending_review_file` must not be null.
6. If status is `ready_for_next_file`, `pending_review_file` should be null.
7. If status is `complete`, all files in `sorted_input_files` should be in `processed_files` and `reviewed_files`.
8. Mapper must not process a new file while status is `pending_review` or `blocked`.

If progress tracking and `tables_json.json` disagree, stop and ask for human confirmation.
