# Style-Guide Implementation Changelog

## 0.1.0 — 2026-08-13 — Initial package

- Added the governing SGI specification copy.
- Added a 22-rule machine-readable registry with authority, lifecycle, policy-status, protection, routing, evidence, change, and release controls.
- Added ten explicit project-decision hooks for unresolved MWM policy.
- Added run, rule, terminology, exception, finding, change, result, and cross-family contracts.
- Added 42 synthetic gold fixtures: clean, single-error, adversarial, negative-control, and integration cases.
- Added rule-to-fixture coverage for every registry rule.
- Added regression intake and production-failure capture contracts.

Status: draft-for-editorial-review. No unresolved MWM policy is silently resolved by this package.

## 2026-08-14 packaging update

- Added `01_SPECIFICATION.docx` as a source-preserving Word version of the governing specification. The Markdown specification remains the design authority; no editorial rule or open MWM decision was changed.
