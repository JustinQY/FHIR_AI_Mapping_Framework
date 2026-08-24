---
name: reference-mapping-precedent
description: Use when learning from assessment_result_for_referrence.xlsx or reference_mapping_examples.json.
---

# Reference Mapping Precedent Skill

Use reviewed mappings as precedent, not as an unconditional rule.

Reference source:

- `assessment_result_for_referrence.xlsx` in the **active assessment folder**
  (current round: `data/Curam_FHIR_Feasibility_Assessment_Batch1_2/assessment_result_for_referrence.xlsx`).

Precedent is guidance only. When precedent conflicts with the current mapping principles, the principles win:

- repurpose FHIR for social welfare — never reject a candidate for being "too clinical";
- use `Provenance` / `AuditEvent` / `Consent` only for genuine security/audit/consent tables;
- use `Task` only for caseworker work items (not workflow runtime, batch, or milestones);
- prefer the Care Provision category for Outcome Plan tables.

Expected fields:

- review status
- reviewed data domain
- Curam table name
- table description
- reviewed FHIR target

For each new table, search for exact table name match, shared prefix/suffix, similar description, domain patterns, and resource patterns.

Convert old DataType-like targets to actual resource-level paths:

- `~.address` / Address → Patient.address, RelatedPerson.address, Practitioner.address, Organization.address, Location.address.
- `~.telecom` / ContactPoint → Patient.telecom, Practitioner.telecom, Organization.telecom.
- HumanName → Patient.name, Practitioner.name, RelatedPerson.name.
- Identifier → resource-level identifier path.
- Annotation → resource-level note/comment path.

Every mapping object should include `reference_learning_applied`.

If no precedent applies, set `used_reference` to false and explain that no strong reviewed precedent was found.
