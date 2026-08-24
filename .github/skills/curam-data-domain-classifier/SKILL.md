---
name: curam-data-domain-classifier
description: Use when assigning IBM Curam tables to the allowed business data domains.
---

# Curam Data Domain Classifier Skill

Assign each Curam table exactly one data_domain from:

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

Do not invent domains. Do not use Contact Information, Administration, Miscellaneous, Unknown, Other, or N/A.

Use table name, description, attributes, Curam concept, and reference precedent.

Guidance:

- Assessments: assessment cases, factors, results, risk, questionnaires.
- Outcome Plan: action plans, goals, agreements, plan activities, services/referrals within plans.
- Case Management: case header, integrated case, case status, case participant role, case ownership/events.
- Documents: uploaded/generated documents, attachments, document metadata, document links.
- Finance: payments, invoices, accounts, claims, benefits, reconciliation, billing.
- Legal: legal actions, investigations, allegations, hearings, appeals, orders, consent/contracts.
- People: clients, persons, participants, names, addresses, telecom, demographics, relationships.
- Provider: provider organizations, provider services, provider locations, provider roles.
- System: configuration, code tables, audit, logs, workflow infrastructure, technical metadata.
- Users: caseworkers, internal users, staff roles, user assignment, administration responsibility.

The domain drives the FHIR category used for resource selection (see the fhir-r4-resource-selector skill). In particular, **Outcome Plan maps into the FHIR Care Provision category** (CarePlan, CareTeam, Goal, ServiceRequest, RiskAssessment, RequestGroup).

History / snapshot / status-history tables keep the **same domain as their base concept** (e.g., an absence-period history stays Provider, an assessment-status history stays Assessments).

For contact information:
- client contact → People
- provider contact → Provider
- staff contact → Users
- case-specific contact event → Case Management
- system notification destination → System

Confidence:
- High: clear table name/description and reference agreement.
- Medium: plausible but some ambiguity.
- Low: generic table, sparse description, or multiple plausible domains.
