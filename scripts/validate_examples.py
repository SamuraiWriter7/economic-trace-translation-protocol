#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
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
        "schema": (
            ROOT_DIR
            / "schemas"
            / "economic-event-translation-record.schema.json"
        ),
        "example": (
            ROOT_DIR
            / "examples"
            / "economic-event-translation-record.example.yaml"
        ),
    },
    {
        "name": "Structural Role Classification Record",
        "schema": (
            ROOT_DIR
            / "schemas"
            / "structural-role-classification-record.schema.json"
        ),
        "example": (
            ROOT_DIR
            / "examples"
            / "structural-role-classification-record.example.yaml"
        ),
    },
    {
        "name": "Cross-Domain Causal Binding Record",
        "schema": (
            ROOT_DIR
            / "schemas"
            / "cross-domain-causal-binding-record.schema.json"
        ),
        "example": (
            ROOT_DIR
            / "examples"
            / "cross-domain-causal-binding-record.example.yaml"
        ),
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


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
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

    for subject_ref in find_duplicates(subject_refs):
        errors.append(
            "classification_subjects contains duplicate "
            f"subject_ref: {subject_ref}"
        )

    assignment_ids = [
        assignment.get("assignment_id")
        for assignment in assignments
        if isinstance(assignment.get("assignment_id"), str)
    ]

    for assignment_id in find_duplicates(assignment_ids):
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
                "does not exist in classification_subjects: "
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

    for subject_ref, assignment_ids_for_subject in (
        primary_assignments.items()
    ):
        if len(assignment_ids_for_subject) > 1:
            errors.append(
                f"subject_ref {subject_ref} has multiple "
                "primary role assignments: "
                f"{', '.join(assignment_ids_for_subject)}"
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

    if record.get("classification_status") == "accepted":
        incomplete_statuses = {
            "proposed",
            "disputed",
            "superseded",
        }

        for index, assignment in enumerate(assignments):
            role_status = assignment.get("role_status")

            if role_status in incomplete_statuses:
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


def validate_cross_domain_causal_semantics(
    record: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    source_records = record.get("source_records", [])
    nodes = record.get("causal_nodes", [])
    edges = record.get("causal_edges", [])
    paths = record.get("causal_paths", [])
    assessments = record.get("continuity_assessments", [])
    unresolved_items = record.get("unresolved_items", [])
    review = record.get("review", {})

    source_record_types = {
        item.get("record_type")
        for item in source_records
    }

    if (
        "economic_event_translation_record"
        not in source_record_types
    ):
        errors.append(
            "source_records must include at least one "
            "economic_event_translation_record."
        )

    if (
        "structural_role_classification_record"
        not in source_record_types
    ):
        errors.append(
            "source_records must include at least one "
            "structural_role_classification_record."
        )

    node_ids = [
        node.get("node_id")
        for node in nodes
        if isinstance(node.get("node_id"), str)
    ]

    edge_ids = [
        edge.get("edge_id")
        for edge in edges
        if isinstance(edge.get("edge_id"), str)
    ]

    path_ids = [
        path.get("path_id")
        for path in paths
        if isinstance(path.get("path_id"), str)
    ]

    assessment_ids = [
        assessment.get("assessment_id")
        for assessment in assessments
        if isinstance(
            assessment.get("assessment_id"),
            str,
        )
    ]

    for node_id in find_duplicates(node_ids):
        errors.append(f"Duplicate node_id: {node_id}")

    for edge_id in find_duplicates(edge_ids):
        errors.append(f"Duplicate edge_id: {edge_id}")

    for path_id in find_duplicates(path_ids):
        errors.append(f"Duplicate path_id: {path_id}")

    for assessment_id in find_duplicates(assessment_ids):
        errors.append(
            f"Duplicate assessment_id: {assessment_id}"
        )

    node_map = {
        node["node_id"]: node
        for node in nodes
        if isinstance(node.get("node_id"), str)
    }

    edge_map = {
        edge["edge_id"]: edge
        for edge in edges
        if isinstance(edge.get("edge_id"), str)
    }

    path_map = {
        path["path_id"]: path
        for path in paths
        if isinstance(path.get("path_id"), str)
    }

    represented_domains = {
        node.get("domain")
        for node in nodes
        if isinstance(node.get("domain"), str)
    }

    if len(represented_domains) < 2:
        errors.append(
            "causal_nodes must span at least two domains."
        )

    for index, node in enumerate(nodes):
        temporal_context = node.get("temporal_context", {})

        if temporal_context.get("time_status") == "interval":
            start_at = temporal_context.get("start_at")
            end_at = temporal_context.get("end_at")

            if (
                isinstance(start_at, str)
                and isinstance(end_at, str)
                and parse_datetime(start_at)
                > parse_datetime(end_at)
            ):
                errors.append(
                    f"causal_nodes[{index}] interval "
                    "start_at occurs after end_at."
                )

    review_required = False

    for index, edge in enumerate(edges):
        source_ref = edge.get("source_node_ref")
        target_ref = edge.get("target_node_ref")

        if source_ref not in node_map:
            errors.append(
                f"causal_edges[{index}].source_node_ref "
                f"does not exist: {source_ref}"
            )

        if target_ref not in node_map:
            errors.append(
                f"causal_edges[{index}].target_node_ref "
                f"does not exist: {target_ref}"
            )

        if source_ref == target_ref:
            errors.append(
                f"causal_edges[{index}] contains a self-edge: "
                f"{source_ref}"
            )

        if edge.get("review_required") is True:
            review_required = True

        if (
            edge.get("temporal_relation")
            == "source_before_target"
            and source_ref in node_map
            and target_ref in node_map
        ):
            source_time = (
                node_map[source_ref]
                .get("temporal_context", {})
                .get("occurred_at")
            )

            target_time = (
                node_map[target_ref]
                .get("temporal_context", {})
                .get("occurred_at")
            )

            if (
                isinstance(source_time, str)
                and isinstance(target_time, str)
                and parse_datetime(source_time)
                > parse_datetime(target_time)
            ):
                errors.append(
                    f"causal_edges[{index}] has a temporal "
                    "conflict: the source occurs after the target."
                )

    for index, path in enumerate(paths):
        node_sequence = path.get("node_sequence", [])
        edge_sequence = path.get("edge_sequence", [])

        if len(edge_sequence) != len(node_sequence) - 1:
            errors.append(
                f"causal_paths[{index}].edge_sequence length "
                "must equal node_sequence length minus one."
            )
            continue

        for node_ref in node_sequence:
            if node_ref not in node_map:
                errors.append(
                    f"causal_paths[{index}] references "
                    f"an unknown node: {node_ref}"
                )

        for edge_index, edge_ref in enumerate(
            edge_sequence
        ):
            if edge_ref not in edge_map:
                errors.append(
                    f"causal_paths[{index}] references "
                    f"an unknown edge: {edge_ref}"
                )
                continue

            edge = edge_map[edge_ref]

            expected_source = node_sequence[edge_index]
            expected_target = node_sequence[edge_index + 1]

            if (
                edge.get("source_node_ref")
                != expected_source
                or edge.get("target_node_ref")
                != expected_target
            ):
                errors.append(
                    f"causal_paths[{index}] edge {edge_ref} "
                    "does not connect the corresponding "
                    "node_sequence entries."
                )

        path_domains = {
            node_map[node_ref].get("domain")
            for node_ref in node_sequence
            if node_ref in node_map
        }

        if len(path_domains) < 2:
            errors.append(
                f"causal_paths[{index}] must span "
                "at least two domains."
            )

        outcome_ref = path.get("outcome_node_ref")

        if (
            isinstance(outcome_ref, str)
            and node_sequence
            and outcome_ref != node_sequence[-1]
        ):
            errors.append(
                f"causal_paths[{index}].outcome_node_ref "
                "must reference the final node in node_sequence."
            )

    for index, assessment in enumerate(assessments):
        path_ref = assessment.get("path_ref")
        from_node_ref = assessment.get("from_node_ref")
        to_node_ref = assessment.get("to_node_ref")

        if path_ref not in path_map:
            errors.append(
                f"continuity_assessments[{index}].path_ref "
                f"does not exist: {path_ref}"
            )

        if from_node_ref not in node_map:
            errors.append(
                f"continuity_assessments[{index}].from_node_ref "
                f"does not exist: {from_node_ref}"
            )

        if to_node_ref not in node_map:
            errors.append(
                f"continuity_assessments[{index}].to_node_ref "
                f"does not exist: {to_node_ref}"
            )

        if assessment.get("review_required") is True:
            review_required = True

    if (
        review_required
        and review.get("review_status") == "not_required"
    ):
        errors.append(
            "At least one causal edge or continuity assessment "
            "requires review, but review_status is not_required."
        )

    if record.get("binding_status") == "accepted":
        accepted_primary_path_found = False

        for path in paths:
            if (
                path.get("path_type") == "primary"
                and path.get("path_status") == "accepted"
            ):
                accepted_primary_path_found = True

                for edge_ref in path.get(
                    "edge_sequence",
                    [],
                ):
                    edge = edge_map.get(edge_ref, {})
                    claim_status = edge.get("claim_status")

                    if claim_status not in {
                        "supported",
                        "accepted",
                    }:
                        errors.append(
                            "An accepted primary path contains "
                            "an unresolved causal edge: "
                            f"{edge_ref}"
                        )

        if not accepted_primary_path_found:
            errors.append(
                "An accepted binding requires at least one "
                "accepted primary path."
            )

        for item in unresolved_items:
            if item.get("resolution_status") in {
                "open",
                "under_review",
            }:
                errors.append(
                    "An accepted binding contains "
                    "an unresolved item."
                )

    return errors


def validate_semantics(
    example: dict[str, Any],
) -> list[str]:
    record_type = example.get("record_type")

    if (
        record_type
        == "structural_role_classification_record"
    ):
        return validate_structural_role_semantics(example)

    if (
        record_type
        == "cross_domain_causal_binding_record"
    ):
        return validate_cross_domain_causal_semantics(
            example
        )

    return []


def validate_target(
    name: str,
    schema_path: Path,
    example_path: Path,
) -> bool:
    print(f"[validate] {name}")
    print(
        f"  schema : {schema_path.relative_to(ROOT_DIR)}"
    )
    print(
        f"  example: {example_path.relative_to(ROOT_DIR)}"
    )

    if not schema_path.exists():
        print(
            f"[error] Schema file not found: {schema_path}"
        )
        return False

    if not example_path.exists():
        print(
            f"[error] Example file not found: {example_path}"
        )
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
