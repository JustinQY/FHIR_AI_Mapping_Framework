---
name: fhir-r4-resource-selector
description: Use when selecting actual HL7 FHIR R4 resource targets for Curam tables.
---

# FHIR R4 Resource Selector Skill

The final `fhir_target_resource` must be an actual HL7 FHIR R4 Resource.

## Guiding principle: FHIR for Social Welfare

This assessment repurposes HL7 FHIR R4 for a **social welfare / human services** program, not a hospital. Choose the resource whose **structure and semantics** best carry the Curam data, even when that resource was designed for a clinical context.

- Do **not** reject a candidate resource merely because it is "healthcare", "clinical", "claim", or "medical" oriented. That is never a valid rejection reason.
- Reject a candidate only for a real structural/semantic reason (for example: "models a request, but this row is a completed result", or "models a single item, but this is a grouping").
- Worked example — corrected reasoning for a child-support payment (`AbParChildSupport`):
  - `Contract` — Selected: a recurring, often court-ordered support obligation with amount/term maps to `Contract.term`.
  - `PaymentReconciliation` — Rejected: it reconciles issued payment transactions, whereas this row is the standing obligation, not a payment event (NOT "because it is healthcare-oriented").
  - `Invoice` — Rejected: an Invoice bills for goods/services; received support income is a different structure (NOT "because it is healthcare billing").

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

DataTypes may only be embedded structures, never final targets.

## Restricted resources — security / audit / consent only

Use these **only when the table's core purpose is security, access control, consent/privacy, or audit/provenance logging**:

- `Provenance`
- `AuditEvent`
- `Consent`

Do **not** reach for them as defaults. In particular:

- history / snapshot / status-history / change-log tables → map to the **same base business resource** as the parent concept (a versioned instance), or to the business resource the data is about;
- lifecycle events (approve, suspend, cancel, reopen, print, transport, sync) → map to the business resource the event acts on;
- transaction logs that carry business values (amounts, statuses) → map to the relevant business resource.

`AuditEvent` is appropriate only for an explicit data-access / read-write audit table. `Consent` is appropriate only for an explicit consent, privacy, or security-permission table.

## Task usage — caseworker work items only

Use `Task` primarily for **CAS / caseworker work items**: assignments, to-dos, reviews a worker must perform, referrals a worker actions, and manual approvals a worker owns.

Do **not** use `Task` for:

- workflow-engine runtime data (activity instances/occurrences, process instances);
- batch jobs or scheduler internals (batch process, chunk, bulk operation, chunk key);
- **milestones or stages within a workflow** → use `Goal` (Care Provision) for plan milestones, or `PlanDefinition.action` for definitional stages.

For those non-`Task` cases:

- process / workflow / batch **definitions** → `PlanDefinition`, `ActivityDefinition`, or `OperationDefinition`;
- pure system/runtime internals with no business meaning → prefer a Foundation/System resource (`Parameters`, `Binary`, `Library`) or, if nothing reasonably fits, `NO_MATCH`.

## Data domain → FHIR category → candidate resources

Pick the resource from the FHIR module/category that matches the domain. **Outcome Plan especially should come from the Care Provision category.**

- Assessments → Clinical/Diagnostics + Definitional: Observation, QuestionnaireResponse, Questionnaire, RiskAssessment, Condition.
- Outcome Plan → **Care Provision** (+ Definitional): CarePlan, CareTeam, Goal, ServiceRequest, RiskAssessment, RequestGroup; PlanDefinition / ActivityDefinition for definitions.
- Case Management → Management + Workflow + Request & Response: EpisodeOfCare, Encounter, Flag, List, Communication; Task only for caseworker items.
- Documents → Foundation/Documents + Other: DocumentReference, Composition, DocumentManifest, Binary.
- Finance → Financial (Support/Billing/Payment/General): Account, Invoice, Claim, ClaimResponse, PaymentNotice, PaymentReconciliation, Contract, ExplanationOfBenefit, Coverage, CoverageEligibilityRequest, CoverageEligibilityResponse, ChargeItem, ChargeItemDefinition, InsurancePlan, EnrollmentRequest, EnrollmentResponse.
- Legal → Financial/General + Documents + Workflow: Contract, DocumentReference, Task (caseworker item); Consent only when explicitly about consent/security.
- People → Base/Individuals: Patient, RelatedPerson, Person, Group.
- Provider → Base/Entities + Individuals: Organization, HealthcareService, Endpoint, Location, Practitioner, PractitionerRole.
- System → Foundation (Terminology/Conformance/Other) + Management: CodeSystem, ValueSet, ConceptMap, NamingSystem, StructureDefinition, StructureMap, OperationDefinition, PlanDefinition, Library, Parameters, Binary, OperationOutcome, Subscription, MessageHeader, Linkage, List. Use Provenance/AuditEvent/Consent only for genuine security/audit/consent tables.
- Users → Base/Individuals + Care Provision + Workflow: Practitioner, PractitionerRole, Person, CareTeam; Task for caseworker assignments.

## DataType → resource-level path examples

- Address-like person table → Patient.address / RelatedPerson.address / Person.address.
- Provider address → Organization.address / Location.address.
- Name-like person table → Patient.name / Practitioner.name / RelatedPerson.name.
- Telecom-like table → Patient.telecom / Practitioner.telecom / Organization.telecom.

Always include `candidate_resources_considered` with selected and rejected candidates when ambiguity exists, and make every rejection reason a structural/semantic one — never "too clinical / healthcare-oriented".
