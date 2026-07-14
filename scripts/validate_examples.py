#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
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
    }
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

        errors = sorted(
            validator.iter_errors(example),
            key=lambda error: list(error.absolute_path),
        )

        if errors:
            print("[validation-failed]")

            for error in errors:
                path = format_error_path(error)
                print(f"  - path: {path}")
                print(f"    message: {error.message}")

            return False

        print("[example-ok]")
        return True

    except SchemaError as error:
        print("[schema-invalid]")
        print(f"  message: {error.message}")
        return False

    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as error:
        print("[load-error]")
        print(f"  message: {error}")
        return False


def main() -> int:
    print("=== Economic Trace Translation Protocol Validation ===")
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

    print("[result] All schemas and examples are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
