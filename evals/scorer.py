#!/usr/bin/env python3
"""Validate and score the synthetic SGI gold-fixture suite.

The scorer is intentionally policy-agnostic: the fixture catalog carries the
gold expectations, while this module checks coverage and compares a candidate
run with those expectations. It does not manufacture MWM decisions.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def suite_objects() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        load_json(EVALS / "fixture_catalog.json"),
        load_json(EVALS / "rule_fixture_crosswalk.json"),
        load_json(EVALS / "adversarial_negative_controls.json"),
        load_json(EVALS / "integration_cases.json"),
        load_json(ROOT / "02_RULES" / "ruleset.json"),
    )


def validate_suite() -> dict[str, Any]:
    catalog, crosswalk, controls, integrations, ruleset = suite_objects()
    fixtures = catalog.get("fixtures", [])
    fixture_map = {item.get("fixture_id"): item for item in fixtures}
    rule_ids = [rule.get("id") for rule in ruleset.get("rules", [])]
    errors: list[str] = []

    if len(fixture_map) != len(fixtures):
        errors.append("fixture IDs are not unique")
    if not all(item.get("synthetic") is True for item in fixtures):
        errors.append("every fixture must be marked synthetic=true")

    expected_counts = catalog.get("fixture_counts", {})
    actual_counts = Counter(item.get("kind") for item in fixtures)
    for kind, expected in expected_counts.items():
        if actual_counts.get(kind, 0) != expected:
            errors.append(f"fixture count for {kind}: expected {expected}, got {actual_counts.get(kind, 0)}")

    for fixture in fixtures:
        if not fixture.get("gold", {}).get("expected_release_status"):
            errors.append(f"{fixture.get('fixture_id')}: missing expected release status")
        unknown_rules = set(fixture.get("gold", {}).get("expected_rule_ids", [])) - set(rule_ids)
        unknown_rules |= set(fixture.get("gold", {}).get("must_not_emit_rule_ids", [])) - set(rule_ids)
        if unknown_rules:
            errors.append(f"{fixture.get('fixture_id')}: unknown rule IDs {sorted(unknown_rules)}")

    rows = crosswalk.get("rows", [])
    crosswalk_ids = [row.get("rule_id") for row in rows]
    if len(set(crosswalk_ids)) != len(crosswalk_ids):
        errors.append("crosswalk rule IDs are not unique")
    if set(crosswalk_ids) != set(rule_ids):
        errors.append("crosswalk does not cover exactly the ruleset")
    for row in rows:
        for column in ("positive", "negative", "adversarial"):
            ids = row.get(column, [])
            if not ids:
                errors.append(f"{row.get('rule_id')}: missing {column} fixture")
            for fixture_id in ids:
                if fixture_id not in fixture_map:
                    errors.append(f"{row.get('rule_id')}: unknown crosswalk fixture {fixture_id}")
        for fixture_id in row.get("integration", []):
            if fixture_id not in fixture_map or fixture_map[fixture_id].get("kind") != "integration":
                errors.append(f"{row.get('rule_id')}: integration fixture is invalid: {fixture_id}")

    control_adversarial = set(controls.get("adversarial_fixture_ids", []))
    actual_adversarial = {item["fixture_id"] for item in fixtures if item.get("kind") == "adversarial"}
    if control_adversarial != actual_adversarial:
        errors.append("adversarial control set does not match catalog")
    control_negative = set(controls.get("negative_control_fixture_ids", []))
    actual_negative = {item["fixture_id"] for item in fixtures if item.get("kind") == "negative_control"}
    if control_negative != actual_negative:
        errors.append("negative control set does not match catalog")

    integration_ids = {case.get("fixture_id") for case in integrations.get("cases", [])}
    actual_integration = {item["fixture_id"] for item in fixtures if item.get("kind") == "integration"}
    if integration_ids != actual_integration:
        errors.append("integration case set does not match catalog")

    return {
        "pass": not errors,
        "evaluation_set_id": catalog.get("evaluation_set_id"),
        "fixture_count": len(fixtures),
        "fixture_counts": dict(actual_counts),
        "rule_count": len(rule_ids),
        "crosswalk_rows": len(rows),
        "errors": errors,
    }


def _as_set(value: Any) -> set[str]:
    return {str(item) for item in (value or [])}


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    catalog, _, _, _, _ = suite_objects()
    fixtures = {item["fixture_id"]: item for item in catalog.get("fixtures", [])}
    results = {item.get("fixture_id"): item for item in candidate.get("results", [])}
    details: list[dict[str, Any]] = []
    zero_tolerance_total = 0
    zero_tolerance_passed = 0

    for fixture_id, fixture in fixtures.items():
        gold = fixture["gold"]
        result = results.get(fixture_id, {})
        expected_rules = _as_set(gold.get("expected_rule_ids"))
        emitted_rules = _as_set(result.get("detected_rule_ids"))
        forbidden_rules = _as_set(gold.get("must_not_emit_rule_ids"))
        expected_actions = _as_set(gold.get("expected_actions"))
        actual_actions = _as_set(result.get("actions"))
        expected_statuses = _as_set(gold.get("expected_statuses"))
        actual_statuses = _as_set(result.get("statuses"))
        expected_hooks = _as_set(gold.get("required_decision_hooks"))
        actual_hooks = _as_set(result.get("decision_hooks"))
        expected_routes = _as_set(gold.get("expected_routes"))
        actual_routes = _as_set(result.get("routes"))

        mismatches: list[str] = []
        if result.get("release_status") != gold.get("expected_release_status"):
            mismatches.append("release_status")
        if not expected_rules.issubset(emitted_rules):
            mismatches.append("missing_expected_rule_ids")
        if forbidden_rules & emitted_rules:
            mismatches.append("forbidden_rule_ids_emitted")
        if not expected_actions.issubset(actual_actions):
            mismatches.append("missing_expected_actions")
        if expected_statuses and not expected_statuses.issubset(actual_statuses):
            mismatches.append("missing_expected_statuses")
        if expected_hooks and not expected_hooks.issubset(actual_hooks):
            mismatches.append("missing_required_decision_hooks")
        if expected_routes and not expected_routes.issubset(actual_routes):
            mismatches.append("missing_expected_routes")

        passed = not mismatches
        if gold.get("zero_tolerance"):
            zero_tolerance_total += 1
            if passed:
                zero_tolerance_passed += 1
        details.append({"fixture_id": fixture_id, "pass": passed, "mismatches": mismatches})

    unknown_result_ids = sorted(set(results) - set(fixtures))
    if unknown_result_ids:
        details.append({"fixture_id": "<candidate>", "pass": False, "mismatches": [f"unknown_fixture_ids:{','.join(unknown_result_ids)}"]})

    passed_count = sum(1 for item in details if item["pass"])
    return {
        "pass": passed_count == len(fixtures) and not unknown_result_ids,
        "fixture_count": len(fixtures),
        "scored_count": len(results),
        "passed_count": passed_count,
        "accuracy": round(passed_count / len(fixtures), 6) if fixtures else 0.0,
        "zero_tolerance": {"passed": zero_tolerance_passed, "total": zero_tolerance_total},
        "details": details,
    }


def synthetic_gold_candidate() -> dict[str, Any]:
    """Build an in-memory candidate from the catalog for scorer self-testing."""
    catalog, _, _, _, _ = suite_objects()
    results = []
    for fixture in catalog.get("fixtures", []):
        gold = fixture["gold"]
        results.append({
            "fixture_id": fixture["fixture_id"],
            "detected_rule_ids": gold.get("expected_rule_ids", []),
            "release_status": gold["expected_release_status"],
            "actions": gold.get("expected_actions", []),
            "statuses": gold.get("expected_statuses", []),
            "decision_hooks": gold.get("required_decision_hooks", []),
            "routes": gold.get("expected_routes", []),
        })
    return {"candidate_id": "synthetic-gold-self-test", "results": results}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-suite", action="store_true", help="validate fixture, crosswalk, and control coverage")
    parser.add_argument("--self-test", action="store_true", help="score the catalog's in-memory gold expectations")
    parser.add_argument("--score", type=Path, help="score a candidate JSON file")
    args = parser.parse_args()
    if not args.validate_suite and not args.score and not args.self_test:
        parser.error("choose --validate-suite, --score, or --self-test")

    output: dict[str, Any] = {}
    if args.validate_suite:
        output["suite_validation"] = validate_suite()
    if args.score:
        output["candidate_score"] = score_candidate(load_json(args.score))
    if args.self_test:
        output["self_test"] = score_candidate(synthetic_gold_candidate())
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if all(section.get("pass") for section in output.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
