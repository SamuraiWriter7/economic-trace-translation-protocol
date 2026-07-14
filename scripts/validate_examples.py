#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml
from jsonschema import (
    Draft202012Validator,
    FormatChecker,
    SchemaError,
)


ROOT_DIR = Path(__file__).resolve().parents[1]

JSONMapping = dict[str, Any]
SemanticValidator = Callable[[JSONMapping], list[str]]


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
    {
        "name": "Contribution Translation Profile",
        "schema": (
            ROOT_DIR
            / "schemas"
            / "contribution-translation-profile.schema.json"
        ),
        "example": (
            ROOT_DIR
            / "examples"
            / "contribution-translation-profile.example.yaml"
        ),
    },
    {
        "name": "Royalty Readiness Bridge Record",
        "schema": (
            ROOT_DIR
            / "schemas"
            / "royalty-readiness-bridge.schema.json"
        ),
        "example": (
            ROOT_DIR
            / "examples"
            / "royalty-readiness-bridge.example.yaml"
        ),
    },
]


def load_json(path: Path) -> JSONMapping:
    """Load a JSON object from the specified path."""

    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")

    return value


def load_yaml(path: Path) -> JSONMapping:
    """Load a YAML mapping from the specified path."""

    with path.open("r", encoding="utf-8") as file:
        value = yaml.safe_load(file)

    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping.")

    return value


def format_error_path(error: Any) -> str:
    """Convert a jsonschema error path into a readable dotted path."""

    if not error.absolute_path:
        return "<root>"

    return ".".join(str(part) for part in error.absolute_path)


def find_duplicates(values: list[str]) -> list[str]:
    """Return sorted duplicate values from a string list."""

    counts = Counter(values)

    return sorted(
        value
        for value, count in counts.items()
        if count > 1
    )


def parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime, including values ending in Z."""

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def validate_structural_role_semantics(
    record: JSONMapping,
) -> list[str]:
    """Validate v0.2 cross-reference and state semantics."""

    errors: list[str] = []

    subjects = record.get(
        "classification_subjects",
        [],
    )
    assignments = record.get(
        "role_assignments",
        [],
    )
    unresolved_items = record.get(
        "unresolved_items",
        [],
    )
    review = record.get("review", {})

    subject_refs = [
        subject.get("subject_ref")
        for subject in subjects
        if isinstance(subject.get("subject_ref"), str)
    ]

    assignment_ids = [
        assignment.get("assignment_id")
        for assignment in assignments
        if isinstance(assignment.get("assignment_id"), str)
    ]

    for subject_ref in find_duplicates(subject_refs):
        errors.append(
            "classification_subjects contains duplicate "
            f"subject_ref: {subject_ref}"
        )

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

    primary_assignments: dict[str, list[str]] = defaultdict(
        list
    )

    for assignment in assignments:
        if assignment.get("primary") is not True:
            continue

        subject_ref = assignment.get("subject_ref")
        assignment_id = assignment.get("assignment_id")

        if isinstance(subject_ref, str):
            primary_assignments[subject_ref].append(
                str(assignment_id)
            )

    for subject_ref, primary_ids in primary_assignments.items():
        if len(primary_ids) > 1:
            errors.append(
                f"subject_ref {subject_ref} has multiple "
                "primary role assignments: "
                f"{', '.join(primary_ids)}"
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
        unresolved_role_statuses = {
            "proposed",
            "disputed",
            "superseded",
        }

        for index, assignment in enumerate(assignments):
            role_status = assignment.get("role_status")

            if role_status in unresolved_role_statuses:
                errors.append(
                    "Accepted classification contains an "
                    f"unresolved role assignment at index {index}: "
                    f"{role_status}"
                )

        for index, item in enumerate(unresolved_items):
            resolution_status = item.get(
                "resolution_status"
            )

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
    record: JSONMapping,
) -> list[str]:
    """Validate v0.3 graph, temporal, and continuity semantics."""

    errors: list[str] = []

    source_records = record.get("source_records", [])
    nodes = record.get("causal_nodes", [])
    edges = record.get("causal_edges", [])
    paths = record.get("causal_paths", [])
    assessments = record.get(
        "continuity_assessments",
        [],
    )
    unresolved_items = record.get(
        "unresolved_items",
        [],
    )
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

    for assessment_id in find_duplicates(
        assessment_ids
    ):
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
        temporal_context = node.get(
            "temporal_context",
            {},
        )

        if temporal_context.get("time_status") != "interval":
            continue

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
            != "source_before_target"
        ):
            continue

        if (
            source_ref not in node_map
            or target_ref not in node_map
        ):
            continue

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
        node_sequence = path.get(
            "node_sequence",
            [],
        )
        edge_sequence = path.get(
            "edge_sequence",
            [],
        )

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
            expected_target = node_sequence[
                edge_index + 1
            ]

            if (
                edge.get("source_node_ref")
                != expected_source
                or edge.get("target_node_ref")
                != expected_target
            ):
                errors.append(
                    f"causal_paths[{index}] edge "
                    f"{edge_ref} does not connect the "
                    "corresponding node_sequence entries."
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
                "must reference the final node in "
                "node_sequence."
            )

    for index, assessment in enumerate(assessments):
        path_ref = assessment.get("path_ref")
        from_node_ref = assessment.get("from_node_ref")
        to_node_ref = assessment.get("to_node_ref")

        if path_ref not in path_map:
            errors.append(
                "continuity_assessments"
                f"[{index}].path_ref does not exist: "
                f"{path_ref}"
            )

        if from_node_ref not in node_map:
            errors.append(
                "continuity_assessments"
                f"[{index}].from_node_ref does not exist: "
                f"{from_node_ref}"
            )

        if to_node_ref not in node_map:
            errors.append(
                "continuity_assessments"
                f"[{index}].to_node_ref does not exist: "
                f"{to_node_ref}"
            )

        if assessment.get("review_required") is True:
            review_required = True

    if (
        review_required
        and review.get("review_status") == "not_required"
    ):
        errors.append(
            "At least one causal edge or continuity "
            "assessment requires review, but "
            "review.review_status is not_required."
        )

    if record.get("binding_status") == "accepted":
        accepted_primary_path_found = False

        for path in paths:
            if (
                path.get("path_type") != "primary"
                or path.get("path_status") != "accepted"
            ):
                continue

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
                "An accepted binding requires at least "
                "one accepted primary path."
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


def validate_contribution_translation_semantics(
    record: JSONMapping,
) -> list[str]:
    """Validate v0.4 contribution references and review semantics."""

    errors: list[str] = []

    source_binding = record.get("source_binding", {})
    translation_profile = record.get(
        "translation_profile",
        {},
    )
    subjects = record.get(
        "contribution_subjects",
        [],
    )
    claims = record.get(
        "contribution_claims",
        [],
    )
    unresolved_items = record.get(
        "unresolved_items",
        [],
    )
    bundle_summary = record.get(
        "bundle_summary",
        {},
    )
    review = record.get("review", {})

    known_node_refs = set(
        source_binding.get(
            "included_node_refs",
            [],
        )
    )
    known_edge_refs = set(
        source_binding.get(
            "included_edge_refs",
            [],
        )
    )
    known_path_refs = set(
        source_binding.get(
            "included_path_refs",
            [],
        )
    )
    known_outcome_refs = set(
        source_binding.get(
            "outcome_refs",
            [],
        )
    )

    subject_refs = [
        subject.get("subject_ref")
        for subject in subjects
        if isinstance(subject.get("subject_ref"), str)
    ]

    claim_ids = [
        claim.get("claim_id")
        for claim in claims
        if isinstance(claim.get("claim_id"), str)
    ]

    issue_ids = [
        item.get("issue_id")
        for item in unresolved_items
        if isinstance(item.get("issue_id"), str)
    ]

    for subject_ref in find_duplicates(subject_refs):
        errors.append(
            "Duplicate contribution subject_ref: "
            f"{subject_ref}"
        )

    for claim_id in find_duplicates(claim_ids):
        errors.append(
            f"Duplicate contribution claim_id: {claim_id}"
        )

    for issue_id in find_duplicates(issue_ids):
        errors.append(
            f"Duplicate unresolved issue_id: {issue_id}"
        )

    known_subject_refs = set(subject_refs)
    known_claim_ids = set(claim_ids)
    known_issue_ids = set(issue_ids)

    for index, subject in enumerate(subjects):
        for node_ref in subject.get(
            "source_node_refs",
            [],
        ):
            if node_ref not in known_node_refs:
                errors.append(
                    "contribution_subjects"
                    f"[{index}] references an unknown "
                    f"source node: {node_ref}"
                )

    primary_claims: dict[str, list[str]] = defaultdict(
        list
    )

    review_required = False

    for index, claim in enumerate(claims):
        claim_id = claim.get("claim_id")
        subject_ref = claim.get("subject_ref")

        if subject_ref not in known_subject_refs:
            errors.append(
                f"contribution_claims[{index}].subject_ref "
                f"does not exist: {subject_ref}"
            )

        if claim.get("primary") is True:
            primary_claims[str(subject_ref)].append(
                str(claim_id)
            )

        if claim.get("review_required") is True:
            review_required = True

        scope = claim.get("scope", {})

        for node_ref in scope.get("node_refs", []):
            if node_ref not in known_node_refs:
                errors.append(
                    f"Claim {claim_id} scope references "
                    f"an unknown node: {node_ref}"
                )

        for edge_ref in scope.get("edge_refs", []):
            if edge_ref not in known_edge_refs:
                errors.append(
                    f"Claim {claim_id} scope references "
                    f"an unknown edge: {edge_ref}"
                )

        for path_ref in scope.get("path_refs", []):
            if path_ref not in known_path_refs:
                errors.append(
                    f"Claim {claim_id} scope references "
                    f"an unknown path: {path_ref}"
                )

        for outcome_ref in scope.get(
            "outcome_refs",
            [],
        ):
            if (
                known_outcome_refs
                and outcome_ref not in known_outcome_refs
            ):
                errors.append(
                    f"Claim {claim_id} scope references "
                    f"an unknown outcome: {outcome_ref}"
                )

        basis = claim.get(
            "attribution_basis",
            {},
        )

        for node_ref in basis.get(
            "causal_node_refs",
            [],
        ):
            if node_ref not in known_node_refs:
                errors.append(
                    f"Claim {claim_id} basis references "
                    f"an unknown node: {node_ref}"
                )

        for edge_ref in basis.get(
            "causal_edge_refs",
            [],
        ):
            if edge_ref not in known_edge_refs:
                errors.append(
                    f"Claim {claim_id} basis references "
                    f"an unknown edge: {edge_ref}"
                )

        for path_ref in basis.get(
            "causal_path_refs",
            [],
        ):
            if path_ref not in known_path_refs:
                errors.append(
                    f"Claim {claim_id} basis references "
                    f"an unknown path: {path_ref}"
                )

        overlap = claim.get(
            "overlap_assessment",
            {},
        )

        overlap_status = overlap.get(
            "overlap_status"
        )
        overlapping_claim_refs = overlap.get(
            "overlapping_claim_refs",
            [],
        )

        if (
            overlap_status in {
                "possible",
                "confirmed",
            }
            and not overlapping_claim_refs
        ):
            errors.append(
                f"Claim {claim_id} has overlap status "
                f"{overlap_status} but lists no "
                "overlapping claims."
            )

        if (
            overlap_status == "none"
            and overlapping_claim_refs
        ):
            errors.append(
                f"Claim {claim_id} declares no overlap "
                "but lists overlapping claims."
            )

        for overlapping_ref in overlapping_claim_refs:
            if overlapping_ref not in known_claim_ids:
                errors.append(
                    f"Claim {claim_id} references an "
                    "unknown overlapping claim: "
                    f"{overlapping_ref}"
                )

            if overlapping_ref == claim_id:
                errors.append(
                    f"Claim {claim_id} cannot overlap itself."
                )

        measurement = claim.get("measurement", {})
        effect_estimate = measurement.get(
            "effect_estimate",
            {},
        )

        range_low = effect_estimate.get("range_low")
        range_high = effect_estimate.get("range_high")
        value = effect_estimate.get("value")

        if (
            isinstance(range_low, (int, float))
            and isinstance(range_high, (int, float))
            and range_low > range_high
        ):
            errors.append(
                f"Claim {claim_id} has range_low "
                "greater than range_high."
            )

        if isinstance(value, (int, float)):
            if (
                isinstance(range_low, (int, float))
                and value < range_low
            ):
                errors.append(
                    f"Claim {claim_id} value is below "
                    "range_low."
                )

            if (
                isinstance(range_high, (int, float))
                and value > range_high
            ):
                errors.append(
                    f"Claim {claim_id} value is above "
                    "range_high."
                )

            if (
                effect_estimate.get("estimate_type")
                == "share_of_observed_effect"
                and not 0 <= value <= 1
            ):
                errors.append(
                    f"Claim {claim_id} "
                    "share_of_observed_effect must "
                    "be between 0 and 1."
                )

    for subject_ref, primary_ids in primary_claims.items():
        if len(primary_ids) > 1:
            errors.append(
                f"Subject {subject_ref} has multiple "
                "primary contribution claims: "
                f"{', '.join(primary_ids)}"
            )

    measurement_window = translation_profile.get(
        "measurement_window"
    )

    if isinstance(measurement_window, dict):
        start_at = measurement_window.get("start_at")
        end_at = measurement_window.get("end_at")

        if (
            isinstance(start_at, str)
            and isinstance(end_at, str)
            and parse_datetime(start_at)
            > parse_datetime(end_at)
        ):
            errors.append(
                "translation_profile.measurement_window "
                "start_at occurs after end_at."
            )

    for blocking_issue_ref in bundle_summary.get(
        "blocking_issue_refs",
        [],
    ):
        if blocking_issue_ref not in known_issue_ids:
            errors.append(
                "bundle_summary references an unknown "
                f"blocking issue: {blocking_issue_ref}"
            )

    if (
        review_required
        and review.get("review_status") == "not_required"
    ):
        errors.append(
            "At least one contribution claim requires "
            "review, but review.review_status is "
            "not_required."
        )

    if record.get("profile_status") == "accepted":
        if source_binding.get("binding_status") != "accepted":
            errors.append(
                "An accepted contribution profile requires "
                "an accepted causal binding."
            )

        if bundle_summary.get("bundle_status") != "accepted":
            errors.append(
                "An accepted contribution profile requires "
                "bundle_summary.bundle_status to be accepted."
            )

        accepted_claim_found = any(
            claim.get("claim_status") == "accepted"
            for claim in claims
        )

        if not accepted_claim_found:
            errors.append(
                "An accepted contribution profile requires "
                "at least one accepted claim."
            )

        for index, claim in enumerate(claims):
            if claim.get("claim_status") in {
                "proposed",
                "disputed",
            }:
                errors.append(
                    "Accepted contribution profile contains "
                    f"an unresolved claim at index {index}."
                )

        for index, item in enumerate(unresolved_items):
            if item.get("resolution_status") in {
                "open",
                "under_review",
            }:
                errors.append(
                    "Accepted contribution profile contains "
                    f"an unresolved item at index {index}."
                )

    return errors


def validate_royalty_readiness_semantics(
    record: JSONMapping,
) -> list[str]:
    """Validate v0.5 gates, candidates, assessments, and handoff."""

    errors: list[str] = []

    source_profile = record.get(
        "source_contribution_profile",
        {},
    )
    source_claims = source_profile.get("claims", [])
    candidates = record.get(
        "royalty_candidates",
        [],
    )
    gates = record.get("readiness_gates", [])
    assessments = record.get(
        "claim_readiness_assessments",
        [],
    )
    unresolved_items = record.get(
        "unresolved_items",
        [],
    )
    summary = record.get(
        "readiness_summary",
        {},
    )
    handoff = record.get("royalty_handoff", {})
    review = record.get("review", {})

    claim_refs = [
        claim.get("claim_ref")
        for claim in source_claims
        if isinstance(claim.get("claim_ref"), str)
    ]

    candidate_ids = [
        candidate.get("candidate_id")
        for candidate in candidates
        if isinstance(
            candidate.get("candidate_id"),
            str,
        )
    ]

    gate_ids = [
        gate.get("gate_id")
        for gate in gates
        if isinstance(gate.get("gate_id"), str)
    ]

    assessment_ids = [
        assessment.get("assessment_id")
        for assessment in assessments
        if isinstance(
            assessment.get("assessment_id"),
            str,
        )
    ]

    issue_ids = [
        item.get("issue_id")
        for item in unresolved_items
        if isinstance(item.get("issue_id"), str)
    ]

    duplicate_groups = [
        ("source claim_ref", claim_refs),
        ("candidate_id", candidate_ids),
        ("gate_id", gate_ids),
        ("assessment_id", assessment_ids),
        ("issue_id", issue_ids),
    ]

    for label, values in duplicate_groups:
        for value in find_duplicates(values):
            errors.append(
                f"Duplicate {label}: {value}"
            )

    claim_map = {
        claim["claim_ref"]: claim
        for claim in source_claims
        if isinstance(claim.get("claim_ref"), str)
    }

    candidate_map = {
        candidate["candidate_id"]: candidate
        for candidate in candidates
        if isinstance(
            candidate.get("candidate_id"),
            str,
        )
    }

    gate_map = {
        gate["gate_id"]: gate
        for gate in gates
        if isinstance(gate.get("gate_id"), str)
    }

    issue_map = {
        item["issue_id"]: item
        for item in unresolved_items
        if isinstance(item.get("issue_id"), str)
    }

    endpoint_map: dict[str, JSONMapping] = {}

    for index, candidate in enumerate(candidates):
        candidate_id = candidate.get("candidate_id")
        candidate_subject = candidate.get(
            "subject_ref"
        )

        for claim_ref in candidate.get(
            "claim_refs",
            [],
        ):
            if claim_ref not in claim_map:
                errors.append(
                    f"royalty_candidates[{index}] references "
                    f"an unknown claim: {claim_ref}"
                )
                continue

            if (
                claim_map[claim_ref].get("subject_ref")
                != candidate_subject
            ):
                errors.append(
                    f"Candidate {candidate_id} subject_ref "
                    f"does not match source claim "
                    f"{claim_ref}."
                )

        endpoint = candidate.get("endpoint")

        if isinstance(endpoint, dict):
            endpoint_ref = endpoint.get("endpoint_ref")

            if isinstance(endpoint_ref, str):
                endpoint_map[endpoint_ref] = endpoint

        if candidate.get("candidate_status") == "eligible":
            if (
                not isinstance(endpoint, dict)
                or endpoint.get("resolution_status")
                != "verified"
            ):
                errors.append(
                    f"Eligible candidate {candidate_id} "
                    "requires a verified endpoint."
                )

    assessment_by_claim: dict[
        str,
        JSONMapping,
    ] = {}

    review_required = False

    counts = {
        "ready": 0,
        "conditionally_ready": 0,
        "blocked": 0,
        "excluded": 0,
    }

    for assessment in assessments:
        assessment_id = assessment.get("assessment_id")
        claim_ref = assessment.get("claim_ref")
        subject_ref = assessment.get("subject_ref")
        candidate_ref = assessment.get("candidate_ref")

        if claim_ref in assessment_by_claim:
            errors.append(
                "Multiple readiness assessments exist "
                f"for claim: {claim_ref}"
            )

        if isinstance(claim_ref, str):
            assessment_by_claim[claim_ref] = assessment

        if claim_ref not in claim_map:
            errors.append(
                f"Assessment {assessment_id} references "
                f"an unknown claim: {claim_ref}"
            )
        elif (
            claim_map[claim_ref].get("subject_ref")
            != subject_ref
        ):
            errors.append(
                f"Assessment {assessment_id} subject_ref "
                "does not match the source claim."
            )

        if candidate_ref not in candidate_map:
            errors.append(
                f"Assessment {assessment_id} references "
                f"an unknown candidate: {candidate_ref}"
            )
        else:
            candidate = candidate_map[candidate_ref]

            if claim_ref not in candidate.get(
                "claim_refs",
                [],
            ):
                errors.append(
                    f"Assessment {assessment_id} claim "
                    f"is not assigned to candidate "
                    f"{candidate_ref}."
                )

            if candidate.get("subject_ref") != subject_ref:
                errors.append(
                    f"Assessment {assessment_id} subject_ref "
                    "does not match the candidate."
                )

        for gate_ref in assessment.get(
            "gate_refs",
            [],
        ):
            if gate_ref not in gate_map:
                errors.append(
                    f"Assessment {assessment_id} references "
                    f"an unknown gate: {gate_ref}"
                )

        for issue_ref in assessment.get(
            "blocking_reason_refs",
            [],
        ):
            if issue_ref not in issue_map:
                errors.append(
                    f"Assessment {assessment_id} references "
                    f"an unknown blocking issue: "
                    f"{issue_ref}"
                )

        readiness_status = assessment.get(
            "readiness_status"
        )

        if readiness_status in counts:
            counts[readiness_status] += 1

        blocking_gates = [
            gate_map[gate_ref]
            for gate_ref in assessment.get(
                "gate_refs",
                [],
            )
            if (
                gate_ref in gate_map
                and gate_map[gate_ref].get("blocking")
                is True
            )
        ]

        if readiness_status == "ready":
            source_claim_status = claim_map.get(
                claim_ref,
                {},
            ).get("claim_status")

            if source_claim_status not in {
                "supported",
                "accepted",
            }:
                errors.append(
                    f"Ready assessment {assessment_id} "
                    "requires a supported or accepted "
                    "source contribution claim."
                )

            if (
                candidate_map.get(
                    candidate_ref,
                    {},
                ).get("candidate_status")
                != "eligible"
            ):
                errors.append(
                    f"Ready assessment {assessment_id} "
                    "requires an eligible candidate."
                )

            if (
                assessment.get(
                    "allocation_basis_status"
                )
                != "sufficient"
            ):
                errors.append(
                    f"Ready assessment {assessment_id} "
                    "requires a sufficient allocation "
                    "basis."
                )

            for gate in blocking_gates:
                if gate.get("gate_status") not in {
                    "passed",
                    "waived",
                    "not_applicable",
                }:
                    errors.append(
                        f"Ready assessment {assessment_id} "
                        "references an unresolved blocking "
                        f"gate: {gate.get('gate_id')}"
                    )

        if readiness_status == "conditionally_ready":
            candidate_status = candidate_map.get(
                candidate_ref,
                {},
            ).get("candidate_status")

            if candidate_status not in {
                "eligible",
                "conditionally_eligible",
            }:
                errors.append(
                    f"Conditionally ready assessment "
                    f"{assessment_id} requires an eligible "
                    "or conditionally eligible candidate."
                )

            if assessment.get(
                "allocation_basis_status"
            ) not in {
                "sufficient",
                "conditionally_sufficient",
            }:
                errors.append(
                    f"Conditionally ready assessment "
                    f"{assessment_id} requires a sufficient "
                    "or conditionally sufficient allocation "
                    "basis."
                )

        if readiness_status == "blocked":
            unresolved_gate_found = any(
                gate.get("gate_status")
                in {
                    "failed",
                    "conditional",
                    "not_assessed",
                }
                for gate in blocking_gates
            )

            if (
                not assessment.get(
                    "blocking_reason_refs"
                )
                and not unresolved_gate_found
            ):
                errors.append(
                    f"Blocked assessment {assessment_id} "
                    "requires a blocking issue or an "
                    "unresolved blocking gate."
                )

        if (
            readiness_status == "excluded"
            and candidate_map.get(
                candidate_ref,
                {},
            ).get("candidate_status")
            != "excluded"
        ):
            errors.append(
                f"Excluded assessment {assessment_id} "
                "requires an excluded candidate."
            )

        if assessment.get("review_required") is True:
            review_required = True

    for gate in gates:
        if gate.get("review_required") is True:
            review_required = True

        if (
            gate.get("gate_status") == "conditional"
            and not gate.get("conditions")
        ):
            errors.append(
                f"Conditional gate {gate.get('gate_id')} "
                "requires one or more conditions."
            )

    for candidate in candidates:
        if candidate.get("review_required") is True:
            review_required = True

    if (
        review_required
        and review.get("review_status") == "not_required"
    ):
        errors.append(
            "At least one readiness item requires review, "
            "but review.review_status is not_required."
        )

    summary_count_fields = {
        "ready_claim_count": "ready",
        "conditional_claim_count": (
            "conditionally_ready"
        ),
        "blocked_claim_count": "blocked",
        "excluded_claim_count": "excluded",
    }

    for summary_field, status_name in (
        summary_count_fields.items()
    ):
        if summary.get(summary_field) != counts[
            status_name
        ]:
            errors.append(
                f"readiness_summary.{summary_field} "
                "does not match the assessments."
            )

    for gate_ref in summary.get(
        "blocking_gate_refs",
        [],
    ):
        if gate_ref not in gate_map:
            errors.append(
                "readiness_summary references an unknown "
                f"blocking gate: {gate_ref}"
            )
        elif gate_map[gate_ref].get("blocking") is not True:
            errors.append(
                "readiness_summary blocking_gate_ref "
                "is not marked as blocking: "
                f"{gate_ref}"
            )

    for issue_ref in summary.get(
        "blocking_issue_refs",
        [],
    ):
        if issue_ref not in issue_map:
            errors.append(
                "readiness_summary references an unknown "
                f"blocking issue: {issue_ref}"
            )
        elif issue_map[issue_ref].get(
            "blocking"
        ) is not True:
            errors.append(
                "readiness_summary blocking_issue_ref "
                "is not marked as blocking: "
                f"{issue_ref}"
            )

    for candidate_ref in summary.get(
        "ready_candidate_refs",
        [],
    ):
        if candidate_ref not in candidate_map:
            errors.append(
                "readiness_summary references an unknown "
                f"ready candidate: {candidate_ref}"
            )
        elif candidate_map[candidate_ref].get(
            "candidate_status"
        ) != "eligible":
            errors.append(
                "readiness_summary ready_candidate_ref "
                "is not marked eligible: "
                f"{candidate_ref}"
            )

    handoff_claim_refs = set(
        handoff.get(
            "included_claim_refs",
            [],
        )
    )
    handoff_candidate_refs = set(
        handoff.get(
            "included_candidate_refs",
            [],
        )
    )

    for claim_ref in handoff_claim_refs:
        if claim_ref not in assessment_by_claim:
            errors.append(
                "royalty_handoff references an "
                f"unassessed claim: {claim_ref}"
            )
            continue

        assessment = assessment_by_claim[claim_ref]
        claim_readiness = assessment.get(
            "readiness_status"
        )

        if claim_readiness not in {
            "ready",
            "conditionally_ready",
        }:
            errors.append(
                "royalty_handoff includes a non-ready "
                f"claim: {claim_ref}"
            )

        candidate_ref = assessment.get("candidate_ref")

        if candidate_ref not in handoff_candidate_refs:
            errors.append(
                f"royalty_handoff includes claim "
                f"{claim_ref} but not its candidate "
                f"{candidate_ref}."
            )

    for candidate_ref in handoff_candidate_refs:
        if candidate_ref not in candidate_map:
            errors.append(
                "royalty_handoff references an unknown "
                f"candidate: {candidate_ref}"
            )
            continue

        if candidate_map[candidate_ref].get(
            "candidate_status"
        ) not in {
            "eligible",
            "conditionally_eligible",
        }:
            errors.append(
                "royalty_handoff includes an ineligible "
                f"candidate: {candidate_ref}"
            )

        candidate_claim_refs = set(
            candidate_map[candidate_ref].get(
                "claim_refs",
                [],
            )
        )

        if not (
            candidate_claim_refs
            & handoff_claim_refs
        ):
            errors.append(
                "royalty_handoff includes candidate "
                f"{candidate_ref} without an associated "
                "included claim."
            )

    allowed_endpoint_refs = {
        candidate_map[candidate_ref]
        .get("endpoint", {})
        .get("endpoint_ref")
        for candidate_ref in handoff_candidate_refs
        if candidate_ref in candidate_map
    }

    for endpoint_ref in handoff.get(
        "endpoint_refs",
        [],
    ):
        if endpoint_ref not in endpoint_map:
            errors.append(
                "royalty_handoff references an unknown "
                f"endpoint: {endpoint_ref}"
            )
        elif endpoint_ref not in allowed_endpoint_refs:
            errors.append(
                "royalty_handoff endpoint is not "
                "associated with an included candidate: "
                f"{endpoint_ref}"
            )

    bridge_status = record.get("bridge_status")
    overall_status = summary.get("overall_status")

    if bridge_status == "ready":
        if source_profile.get("profile_status") != "accepted":
            errors.append(
                "A ready bridge requires an accepted "
                "source contribution profile."
            )

        if overall_status != "ready":
            errors.append(
                "A ready bridge requires "
                "readiness_summary.overall_status "
                "to be ready."
            )

        if not any(
            assessment.get("readiness_status") == "ready"
            for assessment in assessments
        ):
            errors.append(
                "A ready bridge requires at least "
                "one ready claim."
            )

        if any(
            assessment.get("readiness_status")
            in {
                "conditionally_ready",
                "blocked",
            }
            for assessment in assessments
        ):
            errors.append(
                "A ready bridge cannot contain conditional "
                "or blocked claim assessments."
            )

        for gate in gates:
            if (
                gate.get("blocking") is True
                and gate.get("gate_status")
                not in {
                    "passed",
                    "waived",
                    "not_applicable",
                }
            ):
                errors.append(
                    "A ready bridge contains an unresolved "
                    "blocking gate: "
                    f"{gate.get('gate_id')}"
                )

        for item in unresolved_items:
            if (
                item.get("blocking") is True
                and item.get("resolution_status")
                in {
                    "open",
                    "under_review",
                }
            ):
                errors.append(
                    "A ready bridge contains an unresolved "
                    "blocking issue: "
                    f"{item.get('issue_id')}"
                )

        if handoff.get("handoff_status") not in {
            "ready",
            "transmitted",
        }:
            errors.append(
                "A ready bridge requires a ready "
                "or transmitted handoff."
            )

        if review.get("review_status") not in {
            "not_required",
            "approved",
        }:
            errors.append(
                "A ready bridge requires an approved "
                "or not-required review."
            )

    elif bridge_status == "conditionally_ready":
        if overall_status != "conditionally_ready":
            errors.append(
                "A conditionally ready bridge requires "
                "a matching overall_status."
            )

        usable_claim_found = any(
            assessment.get("readiness_status")
            in {
                "ready",
                "conditionally_ready",
            }
            for assessment in assessments
        )

        if not usable_claim_found:
            errors.append(
                "A conditionally ready bridge requires "
                "at least one usable claim."
            )

        if handoff.get("handoff_status") not in {
            "draft",
            "prepared",
            "ready",
        }:
            errors.append(
                "A conditionally ready bridge requires "
                "a draft, prepared, or ready handoff."
            )

    elif bridge_status == "blocked":
        if overall_status != "blocked":
            errors.append(
                "A blocked bridge requires "
                "readiness_summary.overall_status "
                "to be blocked."
            )

        if handoff.get("handoff_status") not in {
            "not_prepared",
            "draft",
            "blocked",
        }:
            errors.append(
                "A blocked bridge cannot have a ready "
                "or transmitted handoff."
            )

    return errors


SEMANTIC_VALIDATORS: dict[
    str,
    SemanticValidator,
] = {
    "structural_role_classification_record": (
        validate_structural_role_semantics
    ),
    "cross_domain_causal_binding_record": (
        validate_cross_domain_causal_semantics
    ),
    "contribution_translation_profile": (
        validate_contribution_translation_semantics
    ),
    "royalty_readiness_bridge_record": (
        validate_royalty_readiness_semantics
    ),
}


def validate_semantics(
    example: JSONMapping,
) -> list[str]:
    """Run the semantic validator associated with a record type."""

    record_type = example.get("record_type")

    if not isinstance(record_type, str):
        return []

    validator = SEMANTIC_VALIDATORS.get(record_type)

    if validator is None:
        return []

    return validator(example)


def validate_target(
    name: str,
    schema_path: Path,
    example_path: Path,
) -> bool:
    """Validate one schema/example pair."""

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
            key=lambda error: list(
                error.absolute_path
            ),
        )

        if schema_errors:
            print("[validation-failed]")

            for error in schema_errors:
                path = format_error_path(error)

                print(f"  - path: {path}")
                print(
                    f"    message: {error.message}"
                )

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
    """Validate all protocol schemas and examples."""

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
