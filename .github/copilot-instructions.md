# Repository Instructions: Curam to HL7 FHIR R4 Mapping

This repository is used for IBM Curam database table mapping assessment against HL7 FHIR R4.

These instructions are the source of truth for all Copilot agents in this repository. Do not use old Phase 1 / Phase 2 / Phase 3 prompts if they conflict with this file, the custom agents, or the skills.

## Core Objective

Map IBM Curam database tables to HL7 FHIR R4 with:

1. exactly one allowed business data domain;
2. an actual HL7 FHIR R4 resource target;
3. a specific resource-level path;
4. match classification;
5. native mappings;
6. extension-required mappings;
7. reference precedent usage;
8. validation-ready JSON output.

## Allowed Data Domains

Every mapping object must include exactly one `data_domain`.

Allowed values:

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

Do not invent additional domains. Do not output Contact Information, Administration, Other, Unknown, Miscellaneous, or N/A as data_domain.

## FHIR Version and Target Rules

Use HL7 FHIR R4 only.

Do not use FHIR R5, FHIR R4B-only resources, custom profiles, or non-FHIR pseudo-resources.

The final `fhir_target_resource` must be an actual HL7 FHIR R4 Resource.

Do not use these as final targets:

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
- Any other FHIR DataType

DataTypes and BackboneElements may appear only in `embedded_fhir_structure_used` or inside a resource-level path, for example `Patient.address`, `Practitioner.name`, `Organization.telecom`, `CarePlan.activity`, `Questionnaire.item`, or `QuestionnaireResponse.item.answer`.

## Basic Resource Restriction

Do not use `Basic` as a generic fallback.

Treat `Basic` as a red-flag resource. Prefer an actual resource with `PARTIAL_MATCH`, or `NO_MATCH` if no actual FHIR R4 resource can reasonably represent the concept. Do not use Basic merely because the Curam table is administrative, generic, non-clinical, or requires extensions.

## FHIR for Social Welfare and Resource Selection Principles

This assessment repurposes HL7 FHIR R4 for a social welfare / human services program, not a hospital. Apply these principles (also encoded in the skills and agents):

1. Repurpose by fit, not by clinical domain. Choose the resource whose structure and semantics best carry the Curam data, even if it was designed for a clinical context. Never reject a candidate resource in `candidate_resources_considered` merely because it is "healthcare", "clinical", "claim", or "medical" oriented; every rejection reason must be structural or semantic.
2. Domain drives FHIR category. Select the target from the FHIR module that matches the data domain. In particular, Outcome Plan tables should come from the Care Provision category (CarePlan, CareTeam, Goal, ServiceRequest, RiskAssessment, RequestGroup).
3. Security-only resources. Use `Provenance`, `AuditEvent`, and `Consent` only when the table's core purpose is security, access control, consent/privacy, or audit/provenance logging. Map history, snapshot, status-history, change-log, lifecycle, and transaction-log tables to their base business resource instead.
4. Task is for caseworker work items. Use `Task` only for CAS / caseworker work items (assignments, to-dos, reviews, referrals, manual approvals). Do not use `Task` for workflow-engine runtime, batch or scheduler internals, or milestones and stages. Milestones map to `Goal`; process and batch definitions map to `PlanDefinition`, `ActivityDefinition`, or `OperationDefinition`.

## Match Type Rules

Use exactly one of:

- FULL_MATCH
- PARTIAL_MATCH
- NO_MATCH

`FULL_MATCH` means every meaningful Curam attribute maps to native elements of the selected actual FHIR R4 resource without extensions, semantic loss, indirect representation, or narrative-only representation.

`PARTIAL_MATCH` must be used when any meaningful attribute requires an extension, semantic loss, indirect representation, narrative-only representation, or a less precise but still reasonable actual FHIR resource.

If `extension_required_mappings` is non-empty, `match_type` must be `PARTIAL_MATCH`.

`NO_MATCH` is allowed only when no actual HL7 FHIR R4 resource can reasonably represent the core Curam concept, even when extensions are allowed. Do not use NO_MATCH merely because the table is administrative, generic, system-oriented, or DataType-like.

## Extension Rules

When an extension is required:

- set `match_type` to `PARTIAL_MATCH`;
- list the Curam attribute under `extension_required_mappings`;
- specify the target FHIR resource or element;
- explain the semantic purpose;
- provide an example FHIR path.

Attach extensions to the most semantically appropriate resource or element. Avoid arbitrary catch-all extensions.

## Reference Workbook

Use `assessment_result_for_referrence.xlsx` (in the active assessment folder; current round: `data/Curam_FHIR_Feasibility_Assessment_Batch1_2/`) as reviewed, high-quality precedent.

Use it to learn Curam table naming patterns, reviewed data domain choices, reviewed FHIR target tendencies, repeated Curam business concepts, and how similar tables were mapped.

Do not blindly copy reference mappings. If the reference target is DataType-like, convert it into an actual resource-level target.

Examples:

- `~.address` → `Patient.address`, `RelatedPerson.address`, `Practitioner.address`, `Organization.address`, or `Location.address`
- `~.telecom` → `Patient.telecom`, `Practitioner.telecom`, `Organization.telecom`, etc.
- `HumanName` → `Patient.name`, `Practitioner.name`, `RelatedPerson.name`, etc.
- `Annotation` → `CarePlan.note`, `Observation.note`, `RiskAssessment.note`, or another resource-level note path.

## Strict Mapping Object Schema

Every mapping object appended to `tables_json.json` should include:

```json
{
  "source_file": "string",
  "source_table_index": 1,
  "table_name": "string",
  "data_domain": "Assessments | Outcome Plan | Case Management | Documents | Finance | Legal | People | Provider | System | Users",
  "data_domain_confidence": "High | Medium | Low",
  "data_domain_rationale": "string",
  "match_type": "FULL_MATCH | PARTIAL_MATCH | NO_MATCH",
  "fhir_target_resource": "string",
  "fhir_target_path": "string",
  "embedded_fhir_structure_used": "string or null",
  "candidate_resources_considered": [
    {
      "resource": "string",
      "decision": "Selected | Rejected",
      "reason": "string"
    }
  ],
  "native_mappings": [
    {
      "curam_attribute": "string",
      "fhir_path": "string",
      "notes": "string"
    }
  ],
  "extension_required_mappings": [
    {
      "curam_attribute": "string",
      "extension_target": "string",
      "suggested_extension_usage": "string",
      "example_fhir_path": "string"
    }
  ],
  "reference_learning_applied": {
    "used_reference": true,
    "matched_reference_tables": ["string"],
    "learned_pattern": "string",
    "differences_from_reference": "string"
  },
  "quality_checks": {
    "actual_resource_used": true,
    "basic_resource_avoided": true,
    "datatype_not_used_as_final_target": true,
    "domain_from_allowed_list": true,
    "one_object_per_table": true
  },
  "overall_notes": "string"
}
```

`source_file` must be the Word file from which the Curam table was extracted. `source_table_index` should be the table's ordinal position within that Word file. `table_name` must remain the exact Curam table name, not the Word file name.

## Output Discipline

When mapping output is requested:

- append to `tables_json.json`;
- keep `tables_json.json` as a valid JSON array;
- produce exactly one JSON object per Curam table;
- preserve table names exactly;
- do not skip tables;
- do not merge multiple tables;
- do not create mappings for tables not present in the current Word file;
- do not paste full JSON into chat unless explicitly requested.

## Automatic Word File Processing Workflow

Curam table definitions are stored in Word files named like `curam_tables_001_035.docx` through `curam_tables_491_500.docx`.

Agents must not require the user to manually provide the next file name each time.

Agents should:

1. discover all files matching `curam_tables_*.docx`;
2. sort them by numeric range;
3. maintain `mapping_progress.json`;
4. use `mapping_progress.json` and `tables_json.json` to determine the next unprocessed Word file;
5. process exactly one Word file per mapper run unless explicitly requested otherwise;
6. append mapping objects to `tables_json.json`;
7. validate after each Word file;
8. require reviewer approval before moving to the next file.

### Optional automation: orchestrator agent

To process the whole remaining queue without manually switching between the mapper and
reviewer, invoke the `curam-fhir-orchestrator` agent. It drives the `curam-fhir-mapper`
and `curam-fhir-reviewer` agents as subagents, one file at a time, gated by
`scripts/validate_mapping_json.py`, and stops only when every file is reviewed or a
validator/reviewer failure occurs. The orchestrator never maps or reviews itself, and it
still honors the one-file-per-step and reviewer-approval rules above. The mapper and
reviewer remain usable manually.

## mapping_progress.json

Recommended structure:

```json
{
  "input_file_pattern": "curam_tables_*.docx",
  "sorted_input_files": [],
  "processed_files": [],
  "reviewed_files": [],
  "pending_review_file": null,
  "last_processed_file": null,
  "last_reviewed_file": null,
  "tables_json_path": "tables_json.json",
  "status": "not_started",
  "notes": []
}
```

Status values: `not_started`, `ready_for_mapping`, `pending_review`, `ready_for_next_file`, `blocked`, `complete`.

Mapper behavior:
- If status is `pending_review`, do not process the next file.
- If status is `ready_for_mapping` or `ready_for_next_file`, select the next file not in `processed_files`.
- After successful append, set `pending_review_file` to the processed file and status to `pending_review`.

Reviewer behavior:
- Review `pending_review_file`.
- If review passes, move it to `reviewed_files`, clear `pending_review_file`, update `last_reviewed_file`, and set status to `ready_for_next_file`.
- If review fails, set status to `blocked`.
