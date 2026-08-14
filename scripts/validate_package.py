#!/usr/bin/env python3
"""Run structural and schema QA for the Style-Guide Implementation package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SPEC_SHA256 = "BAC905635461D84C84EDF1C49AE268B38B136B70C84319B2E622A9EAE9EEBC9A"


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def schema_error_text(errors: list[Any]) -> list[str]:
    return [f"{'.'.join(str(part) for part in error.absolute_path)}: {error.message}" for error in errors]


def validate_schema(instance: Any, schema: dict[str, Any], registry: Any) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment failure
        return [f"jsonschema unavailable: {exc}"]
    validator = Draft202012Validator(schema, registry=registry)
    return schema_error_text(sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)))


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    required_files = [
        "01_SPECIFICATION.md",
        "SKILL.md",
        "agents/openai.yaml",
        "02_RULES/ruleset.json",
        "02_RULES/decision_hooks.json",
        "02_RULES/authority_registry.json",
        "02_RULES/terminology_register.json",
        "evals/fixture_catalog.json",
        "evals/rule_fixture_crosswalk.json",
        "evals/adversarial_negative_controls.json",
        "evals/integration_cases.json",
        "evals/fixture_contract.schema.json",
        "evals/scorer.py",
        "CHANGELOG_REGRESSION/CHANGELOG.md",
        "CHANGELOG_REGRESSION/regression-intake.schema.json",
        "CHANGELOG_REGRESSION/regression-intake.template.json",
        "CHANGELOG_REGRESSION/production-failure.schema.json",
        "CHANGELOG_REGRESSION/production-failure.template.json",
        "CHANGELOG_REGRESSION/regression_policy.json",
        "scripts/validate_package.py",
        "package_manifest.json",
    ]
    required_files.extend(f"schemas/{name}" for name in [
        "run-manifest.schema.json",
        "rule-record.schema.json",
        "terminology-record.schema.json",
        "exception-record.schema.json",
        "finding.schema.json",
        "change-record.schema.json",
        "run-result.schema.json",
        "cross-family-contracts.json",
    ])
    required_files.extend(f"schemas/examples/{name}" for name in [
        "run-manifest.example.json",
        "rule-record.example.json",
        "terminology-record.example.json",
        "exception-record.example.json",
        "finding.example.json",
        "change-record.example.json",
        "run-result.example.json",
    ])
    for relative in required_files:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    spec_path = ROOT / "01_SPECIFICATION.md"
    if spec_path.is_file() and sha256(spec_path) != EXPECTED_SPEC_SHA256:
        errors.append(f"governing specification hash mismatch: {sha256(spec_path)}")

    skill_path = ROOT / "SKILL.md"
    if skill_path.is_file():
        skill_text = skill_path.read_text(encoding="utf-8")
        if len(skill_text.splitlines()) > 500:
            errors.append("SKILL.md exceeds the 500-line limit")
        if not skill_text.startswith("---\n") or "\n---\n" not in skill_text[4:]:
            errors.append("SKILL.md is missing the required YAML frontmatter")
        if re.search(r"\b(TODO|TBD|FIXME)\b", skill_text, flags=re.IGNORECASE):
            errors.append("SKILL.md contains unresolved implementation placeholders")
        if "$style-guide-implementation" not in skill_text:
            warnings.append("SKILL.md does not include an explicit invocation example")

    metadata_path = ROOT / "agents/openai.yaml"
    if metadata_path.is_file():
        metadata = metadata_path.read_text(encoding="utf-8")
        for marker in ["interface:", "display_name:", "short_description:", "default_prompt:", "policy:", "allow_implicit_invocation:"]:
            if marker not in metadata:
                errors.append(f"agents/openai.yaml missing {marker}")
        if "$style-guide-implementation" not in metadata:
            errors.append("agents/openai.yaml default_prompt must name the skill")

    try:
        from referencing import Registry, Resource
    except ImportError as exc:  # pragma: no cover - environment failure
        errors.append(f"referencing unavailable: {exc}")
        Registry = None
        Resource = None

    json_documents: dict[Path, dict[str, Any]] = {}
    for path in sorted(ROOT.rglob("*.json")):
        try:
            json_documents[path] = read_json(path)
        except Exception as exc:
            errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")

    registry = None
    if Registry is not None and Resource is not None:
        registry = Registry()
        for document in json_documents.values():
            if "$id" in document:
                try:
                    registry = registry.with_resource(document["$id"], Resource.from_contents(document))
                except Exception as exc:
                    errors.append(f"cannot register schema {document.get('$id')}: {exc}")

    schema_map: dict[str, dict[str, Any]] = {}
    for path, document in json_documents.items():
        if path.name.endswith(".schema.json"):
            schema_map[path.name] = document

    if registry is not None:
        examples = {
            "run-manifest.example.json": "run-manifest.schema.json",
            "rule-record.example.json": "rule-record.schema.json",
            "terminology-record.example.json": "terminology-record.schema.json",
            "exception-record.example.json": "exception-record.schema.json",
            "finding.example.json": "finding.schema.json",
            "change-record.example.json": "change-record.schema.json",
            "run-result.example.json": "run-result.schema.json",
        }
        for example_name, schema_name in examples.items():
            matches = list((ROOT / "schemas" / "examples").glob(example_name))
            if matches and schema_name in schema_map:
                errors.extend(f"{example_name}: {item}" for item in validate_schema(read_json(matches[0]), schema_map[schema_name], registry))
        fixture_schema = schema_map.get("fixture_contract.schema.json")
        if fixture_schema:
            catalog = json_documents.get(ROOT / "evals" / "fixture_catalog.json")
            for fixture in (catalog or {}).get("fixtures", []):
                errors.extend(f"{fixture.get('fixture_id')}: {item}" for item in validate_schema(fixture, fixture_schema, registry))
        for directory, schema_name, template_name in [
            (ROOT / "CHANGELOG_REGRESSION", "regression-intake.schema.json", "regression-intake.template.json"),
            (ROOT / "CHANGELOG_REGRESSION", "production-failure.schema.json", "production-failure.template.json"),
        ]:
            schema = schema_map.get(schema_name)
            template = directory / template_name
            if schema and template.is_file():
                errors.extend(f"{template_name}: {item}" for item in validate_schema(read_json(template), schema, registry))

    ruleset = json_documents.get(ROOT / "02_RULES" / "ruleset.json", {})
    rules = ruleset.get("rules", [])
    rule_ids = [rule.get("id") for rule in rules]
    if len(rules) != 22:
        errors.append(f"expected 22 SGI rules, found {len(rules)}")
    if len(set(rule_ids)) != len(rule_ids):
        errors.append("SGI rule IDs are not unique")
    if ruleset.get("version") != "0.1.0":
        errors.append("ruleset version must be 0.1.0 for this package")

    hooks = json_documents.get(ROOT / "02_RULES" / "decision_hooks.json", {})
    hook_records = hooks.get("hooks", hooks.get("decision_hooks", []))
    if len(hook_records) != 10:
        errors.append(f"expected 10 SGI decision hooks, found {len(hook_records)}")

    catalog = json_documents.get(ROOT / "evals" / "fixture_catalog.json", {})
    fixtures = catalog.get("fixtures", [])
    crosswalk = json_documents.get(ROOT / "evals" / "rule_fixture_crosswalk.json", {})
    rows = crosswalk.get("rows", [])
    if len(fixtures) != 42:
        errors.append(f"expected 42 SGI fixtures, found {len(fixtures)}")
    if len(rows) != len(rules):
        errors.append("SGI crosswalk row count does not equal rule count")

    result = {
        "pass": not errors,
        "package": "style-guide-implementation",
        "specification_sha256": sha256(spec_path) if spec_path.is_file() else None,
        "rule_count": len(rules),
        "decision_hook_count": len(hook_records),
        "fixture_count": len(fixtures),
        "crosswalk_rows": len(rows),
        "json_file_count": len(json_documents),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
