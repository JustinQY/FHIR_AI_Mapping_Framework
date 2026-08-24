#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ALLOWED_DATA_DOMAINS = {
    "Assessments", "Outcome Plan", "Case Management", "Documents", "Finance",
    "Legal", "People", "Provider", "System", "Users"
}
ALLOWED_MATCH_TYPES = {"FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH"}
ALLOWED_CONFIDENCE = {"High", "Medium", "Low"}
FORBIDDEN_FINAL_TARGETS = {
    "Basic", "Resource", "DomainResource", "Element", "BackboneElement",
    "Extension", "Narrative", "Address", "HumanName", "Identifier",
    "ContactPoint", "CodeableConcept", "Coding", "Reference", "Period",
    "Quantity", "Annotation"
}
REQUIRED_FIELDS = {
    "table_name", "data_domain", "data_domain_confidence", "data_domain_rationale",
    "match_type", "fhir_target_resource", "fhir_target_path",
    "embedded_fhir_structure_used", "candidate_resources_considered",
    "native_mappings", "extension_required_mappings", "reference_learning_applied",
    "quality_checks", "overall_notes"
}
REQUIRED_QUALITY_CHECKS = {
    "actual_resource_used", "basic_resource_avoided",
    "datatype_not_used_as_final_target", "domain_from_allowed_list",
    "one_object_per_table"
}

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"File not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}")

def validate(data):
    errors = []
    warnings = []
    if not isinstance(data, list):
        return ["Top-level JSON must be an array."], warnings

    names = []
    for i, item in enumerate(data):
        label = f"Row {i}"
        if not isinstance(item, dict):
            errors.append(f"{label}: item must be an object.")
            continue

        name = item.get("table_name")
        if isinstance(name, str) and name.strip():
            label = name
            names.append(name)
        else:
            errors.append(f"{label}: missing or empty table_name.")

        missing = REQUIRED_FIELDS - set(item)
        if missing:
            errors.append(f"{label}: missing required fields: {', '.join(sorted(missing))}.")

        if item.get("data_domain") not in ALLOWED_DATA_DOMAINS:
            errors.append(f"{label}: invalid data_domain {item.get('data_domain')!r}.")

        if item.get("data_domain_confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"{label}: invalid data_domain_confidence {item.get('data_domain_confidence')!r}.")

        match_type = item.get("match_type")
        if match_type not in ALLOWED_MATCH_TYPES:
            errors.append(f"{label}: invalid match_type {match_type!r}.")

        target = item.get("fhir_target_resource")
        if not isinstance(target, str) or not target.strip():
            errors.append(f"{label}: missing fhir_target_resource.")
        elif target in FORBIDDEN_FINAL_TARGETS:
            errors.append(f"{label}: forbidden final fhir_target_resource {target!r}.")

        ext = item.get("extension_required_mappings")
        if not isinstance(ext, list):
            errors.append(f"{label}: extension_required_mappings must be a list.")
        else:
            if ext and match_type != "PARTIAL_MATCH":
                errors.append(f"{label}: rows with extensions must use PARTIAL_MATCH.")
            if ext and match_type == "FULL_MATCH":
                errors.append(f"{label}: FULL_MATCH cannot contain extensions.")
            for j, e in enumerate(ext):
                if not isinstance(e, dict):
                    errors.append(f"{label}: extension_required_mappings[{j}] must be object.")
                    continue
                for field in ["curam_attribute", "extension_target", "suggested_extension_usage", "example_fhir_path"]:
                    if not isinstance(e.get(field), str) or not e.get(field).strip():
                        errors.append(f"{label}: extension_required_mappings[{j}].{field} is missing.")

        qc = item.get("quality_checks")
        if not isinstance(qc, dict):
            errors.append(f"{label}: quality_checks must be object.")
        else:
            for field in REQUIRED_QUALITY_CHECKS:
                if qc.get(field) is not True:
                    errors.append(f"{label}: quality_checks.{field} must be true.")

        if not isinstance(item.get("candidate_resources_considered"), list):
            warnings.append(f"{label}: candidate_resources_considered should be a list.")
        if not isinstance(item.get("native_mappings"), list):
            warnings.append(f"{label}: native_mappings should be a list.")
        if not isinstance(item.get("reference_learning_applied"), dict):
            warnings.append(f"{label}: reference_learning_applied should be an object.")

    for name, count in Counter(names).items():
        if count > 1:
            errors.append(f"Duplicate table_name found: {name!r}.")

    return errors, warnings

def build_report(path, data, errors, warnings):
    lines = ["# Curam FHIR Mapping JSON Validation Report", ""]
    status = "PASS" if not errors else "FAIL"
    if not errors and warnings:
        status = "PASS_WITH_WARNINGS"
    lines += ["## Status", "", status, ""]
    lines += ["## Mapping File", "", f"`{path}`", ""]
    lines += ["## Counts", "", f"- Objects: {len(data) if isinstance(data, list) else 'N/A'}", f"- Errors: {len(errors)}", f"- Warnings: {len(warnings)}", ""]
    lines += ["## Errors", ""]
    lines += [f"- {e}" for e in errors] or ["- None"]
    lines += ["", "## Warnings", ""]
    lines += [f"- {w}" for w in warnings] or ["- None"]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", default="tables_json.json")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--report")
    args = parser.parse_args()

    try:
        data = load_json(Path(args.mapping))
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    errors, warnings = validate(data)

    if args.expected_count is not None and isinstance(data, list) and len(data) != args.expected_count:
        errors.append(f"Expected {args.expected_count} objects, found {len(data)}.")

    report = build_report(args.mapping, data, errors, warnings)
    print(report)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(report, encoding="utf-8")

    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
