#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml
from jsonschema import (
    Draft202012Validator,
    FormatChecker,
    SchemaError,
)


ROOT_DIR = Path(__file__).resolve().parents[1]

VALIDATION_TARGETS = [
    {
        "name": "Economic Event Translation Record",
        "schema": ROOT_DIR
        / "schemas"
        / "economic-event-translation-record.schema.json",
        "example": ROOT_DIR
        / "examples"
        / "economic-event-translation-record.example.yaml",
    },
    {
        "name": "Structural Role Classification Record",
        "schema": ROOT_DIR
        / "schemas"
        / "structural-role-classification-record.schema.json",
        "example": ROOT_DIR
        / "examples"
        / "structural-role-classification-record.example.yaml",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")

    return value


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = yaml.safe_load(file)

    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")

    return value


def format_error_path(error: Any) -> str:
    if not error.absolute_path:
        return "<root>"

    return ".".join(str(part) for part in error.absolute_path)


def find_duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(
        value
        for value, count in counts.items()
        if count > 1
    )


def validate_structural_role_semantics(
    record: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    subjects = record.get("classification_subjects", [])
    assignments = record.get("role_assignments", [])
    unresolved_items = record.get("unresolved_items", [])
    review = record.get("review", {})

    subject_refs = [
        subject.get("subject_ref")
        for subject in subjects
        if isinstance(subject.get("subject_ref"), str)
    ]

    duplicate_subject_refs = find_duplicates(subject_refs)

    for subject_ref in duplicate_subject_refs:
        errors.append(
            "classification_subjects contains duplicate "
            f"subject_ref: {subject_ref}"
        )

    assignment_ids = [
        assignment.get("assignment_id")
        for assignment in assignments
        if isinstance(assignment.get("assignment_id"), str)
    ]

    duplicate_assignment_ids = find_duplicates(assignment_ids)

    for assignment_id in duplicate_assignment_ids:
        errors.append(
            "role_assignments contains duplicate "
            f"assignment_id: {assignment_id}"
        )

    known_subject_refs = set(subject_refs)

    for index, assignment in enumerate(assignments):
        subject_ref = assignment.get("subject_ref")

        if subject_ref not in known_subject_refs:
            errors.append(
                f"role_assignments[{index}].subject_ref "
                f"does not exist in classification_subjects: "
                f"{subject_ref}"
            )

    primary_assignments: dict[str, list[str]] = defaultdict(list)

    for assignment in assignments:
        if assignment.get("primary") is not True:
            continue

        subject_ref = assignment.get("subject_ref")
        assignment_id = assignment.get("assignment_id")

        if isinstance(subject_ref, str):
            primary_assignments[subject_ref].append(
                str(assignment_id)
            )

    for subject_ref, ids in primary_assignments.items():
        if len(ids) > 1:
            errors.append(
                f"subject_ref {subject_ref} has multiple "
                f"primary role assignments: {', '.join(ids)}"
            )

    requires_review = any(
        assignment.get("review_required") is True
        for assignment in assignments
    )

    if (
        requires_review
        and review.get("review_status") == "not_required"
    ):
        errors.append(
            "At least one role assignment requires review, "
            "but review.review_status is not_required."
        )

    classification_status = record.get(
        "classification_status"
    )

    if classification_status == "accepted":
        incomplete_role_statuses = {
            "proposed",
            "disputed",
            "superseded",
        }

        for index, assignment in enumerate(assignments):
            role_status = assignment.get("role_status")

            if role_status in incomplete_role_statuses:
                errors.append(
                    "Accepted classification contains an "
                    f"unresolved role assignment at index {index}: "
                    f"{role_status}"
                )

        for index, item in enumerate(unresolved_items):
            resolution_status = item.get("resolution_status")

            if resolution_status in {
                "open",
                "under_review",
            }:
                errors.append(
                    "Accepted classification contains an "
                    f"unresolved item at index {index}: "
                    f"{resolution_status}"
                )

    return errors


def validate_semantics(
    example: dict[str, Any],
) -> list[str]:
    record_type = example.get("record_type")

    if record_type == "structural_role_classification_record":
        return validate_structural_role_semantics(example)

    return []


def validate_target(
    name: str,
    schema_path: Path,
    example_path: Path,
) -> bool:
    print(f"[validate] {name}")
    print(f"  schema : {schema_path.relative_to(ROOT_DIR)}")
    print(f"  example: {example_path.relative_to(ROOT_DIR)}")

    if not schema_path.exists():
        print(f"[error] Schema file not found: {schema_path}")
        return False

    if not example_path.exists():
        print(f"[error] Example file not found: {example_path}")
        return False

    try:
        schema = load_json(schema_path)
        example = load_yaml(example_path)

        Draft202012Validator.check_schema(schema)
        print("[schema-ok]")

        validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )

        schema_errors = sorted(
            validator.iter_errors(example),
            key=lambda error: list(error.absolute_path),
        )

        if schema_errors:
            print("[validation-failed]")

            for error in schema_errors:
                path = format_error_path(error)
                print(f"  - path: {path}")
                print(f"    message: {error.message}")

            return False

        print("[example-schema-ok]")

        semantic_errors = validate_semantics(example)

        if semantic_errors:
            print("[semantic-validation-failed]")

            for error in semantic_errors:
                print(f"  - {error}")

            return False

        print("[semantic-ok]")
        print("[example-ok]")
        return True

    except SchemaError as error:
        print("[schema-invalid]")
        print(f"  message: {error.message}")
        return False

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as error:
        print("[load-error]")
        print(f"  message: {error}")
        return False


def main() -> int:
    print(
        "=== Economic Trace Translation "
        "Protocol Validation ==="
    )
    print()

    all_valid = True

    for target in VALIDATION_TARGETS:
        valid = validate_target(
            name=target["name"],
            schema_path=target["schema"],
            example_path=target["example"],
        )

        all_valid = all_valid and valid
        print()

    if not all_valid:
        print("[result] Validation failed.")
        return 1

    print(
        "[result] All schemas, examples, "
        "and semantic checks are valid."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
