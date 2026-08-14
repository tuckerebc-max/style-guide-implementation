---
name: style-guide-implementation
description: Atomize, apply, and maintain the Modeling What Matters style system as versioned scoped rules with evidence, protected-text handling, terminology control, exceptions, contradiction detection, compliance findings, and release gates. Use for MWM style-guide implementation, rule authoring, chapter style compliance, terminology review, or style-rule maintenance; do not use for copyediting, developmental editing, fact-checking, technical-editing ownership, or substantive terminology adjudication.
---

# Style-Guide Implementation

Run SGI as a rule-registry and compliance workflow. Treat `01_SPECIFICATION.md` as the design authority, `02_RULES/` as the versioned authority/configuration layer, `schemas/` as contracts, `evals/` as acceptance tests, and `CHANGELOG_REGRESSION/` as the maintenance record.

## Execute

1. Load the MWM project/volume profile, active rule registry, exception register, template/production profile, prior unresolved findings, target surfaces, language profile, stage, parser version, and registry version. Validate the run manifest.
2. Return `not_ready` or `partial` when the registry, target surface, stage, language profile, exception scope, or parser coverage is missing. Never call an uninspected surface compliant.
3. Atomize or validate every in-scope rule. Require one observable decision, authority and locator, lifecycle state, policy status, scope tags, preferred treatment, protected text, exceptions, owner, effective date, examples, and fixture IDs.
4. Parse each defined surface with stable locators and raw text: prose, headings, lists, tables, captions, notes, quotations, references as routed from RCI, front matter, biographies, acknowledgments, and production components. Record partial coverage.
5. Select the highest applicable rule by authority, lifecycle, scope specificity, document type, component, stage, audience, and language profile. Apply an approved exception only when its rule, scope, owner, effective period, and review condition match.
6. Classify observed treatment as required violation, preferred departure, permitted variation, discouraged use, informational context, protected text, unknown term, conflict, or insufficient evidence. Do not treat preference as a hard violation.
7. Preserve direct quotations, formal titles, proper names, source terminology, and registered technical labels. Do not replace an unknown domain term from model memory.
8. Run scoped consistency checks across body, headings, tables, captions, and notes. Respect intentional variation in quotations, titles, source names, and component-specific profiles.
9. Detect contradictions among MWM, delegated APA/technical rules, templates, chapter exceptions, author conventions, and active rule versions. Equal-level conflicts require escalation; external exemplars never silently become MWM rules.
10. Emit findings with observed text, rule/version, authority, scope, policy status, exception result, evidence, severity, confidence, action, owner, and disposition. Validate findings against `schemas/finding.schema.json`.
11. Route out-of-scope issues to Copyediting, Technical Editing, Scholarly/Editorial Integrity, RCI, Chapter Completeness, Proof, or Editorial QA & Orchestration. Do not rewrite a chapter wholesale in the name of style consistency.
12. For rule-authoring or rule-change runs, update rule history, rationale, scope, impact, examples, fixtures, compact views, and changelog. Require the change gate before activating new behavior.
13. Apply the release gate: active required rules are testable, required violations are dispositioned, exceptions are current, protected text is preserved, conflicts are resolved or escalated, fixture and registry versions are recorded, and the report is reproducible.

## Routing

- `SGI-01`: atomize or readiness-check a rule.
- `SGI-02`: apply the highest scoped active rule.
- `SGI-03`: verify chapter exceptions and editorial decisions.
- `SGI-04`: detect authority, template, author, or rule-version conflicts.
- `SGI-05`: apply terminology and word-list statuses without substantive replacement.
- `SGI-06`: validate the compliance report and disposition ledger.
- `SGI-07`: manage rule changes, impact, fixtures, and release.

## Boundaries

SGI does not perform sentence-level grammar or style rewriting, developmental editing, claim or fact validation, technical decisions about figures/tables/cross-references, permissions, citation integrity, or substantive judgment about whether a concept or term is correct. Route those questions to the owning family. SGI may pass active style rules, term statuses, exceptions, findings, and release conditions downstream; consumers must not reinterpret a preferred term as a substantive requirement or an unapproved external convention as MWM authority.

## Output and acceptance

Invoke as `$style-guide-implementation` for MWM style-rule application or maintenance. Return a validated run result using `schemas/run-result.schema.json`, with rule, terminology, exception, finding, and change records as applicable. Use dispositions `ready`, `ready_with_conditions`, or `not_ready`; actions `AUTO_FIX`, `SUGGEST`, `FLAG`, `ESCALATE`, `BLOCK`, or `CLOSE`. Before handoff, run `evals/scorer.py --validate-suite`, `scripts/validate_package.py`, and the standard Codex skill validator. Clean controls must remain clean, permitted variation must not be overreported, protected text must remain untouched, every active rule must have fixtures, and open MWM decisions must remain explicit.