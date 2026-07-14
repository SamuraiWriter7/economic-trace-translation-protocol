# Changelog

All notable changes to the Economic Trace Translation Protocol are documented in this file.

The format is based on Keep a Changelog and uses candidate versions for the first protocol arc.

## [Unreleased]

### Planned

* Additional documentation for cross-repository integration
* Expanded positive and negative example records
* Test fixtures for invalid semantic states
* Reference mappings for downstream allocation protocols
* Documentation for dispute and supersession workflows
* Future protocol arc evaluation after v0.5

---

## [0.5.0-candidate] — 2026-07-14

### Added

* `schemas/royalty-readiness-bridge.schema.json`
* `examples/royalty-readiness-bridge.example.yaml`
* Royalty candidate mapping
* Royalty endpoint candidate records
* Claim-level readiness assessments
* Bridge-level readiness gates
* Partial royalty handoff packages
* Blocking and non-blocking readiness issues
* Downstream protocol targeting
* Human review and audit references
* Handoff execution boundaries

### Supported readiness gates

* source trace integrity
* governance eligibility
* causal-binding validity
* contribution-claim acceptance
* overlap resolution
* dispute clearance
* subject identity resolution
* royalty endpoint resolution
* audit completion
* human approval
* allocation-policy availability
* negative-externality review

### Added readiness states

* `not_assessed`
* `conditionally_ready`
* `ready`
* `blocked`
* `excluded`

### Added bridge states

* `draft`
* `review_required`
* `conditionally_ready`
* `ready`
* `blocked`
* `rejected`
* `disputed`
* `superseded`

### Added semantic validation

* duplicate candidate, gate, assessment, and issue detection
* claim-to-candidate consistency
* subject-to-candidate consistency
* eligible candidate endpoint verification
* unknown gate and issue reference detection
* readiness summary count verification
* blocking-gate verification
* blocking-issue verification
* candidate and endpoint handoff consistency
* partial-handoff integrity
* exclusion of blocked claims from handoff
* ready and conditionally ready bridge-state verification
* review requirement consistency

### Design decisions

* Separated contribution subjects from downstream royalty candidates.
* Separated royalty candidates from royalty endpoints.
* Allowed partial handoff when some claims are ready and others remain blocked.
* Prevented blocked or excluded claims from entering a royalty handoff.
* Required verified endpoints for fully eligible candidates.
* Preserved downstream responsibility for allocation calculations and settlement.

### Boundaries

v0.5 does not determine:

* ownership
* intellectual-property rights
* allocation percentages
* royalty amounts
* taxation
* sanctions compliance
* settlement instructions
* payment authorization
* payment execution

---

## [0.4.0-candidate] — 2026-07-14

### Added

* `schemas/contribution-translation-profile.schema.json`
* `examples/contribution-translation-profile.example.yaml`
* Contribution subject records
* Contribution claim records
* Contribution types and classes
* Claim scope definitions
* Attribution basis records
* Measurement records
* Effect estimates
* Counterfactual assessments
* Overlap assessments
* Uncertainty assessments
* Contribution claim bundle summaries
* Contribution review and dispute references

### Supported contribution types

* `origin_input`
* `data_support`
* `human_intent`
* `human_decision`
* `processing`
* `transformation`
* `infrastructure`
* `distribution`
* `verification`
* `governance`
* `risk_reduction`
* `outcome_enablement`
* `negative_externality`

### Supported measurement methods

* qualitative review
* counterfactual analysis
* controlled experiment
* observational analysis
* rule-based estimate
* model-based estimate
* direct accounting
* mixed methods

### Added semantic validation

* duplicate contribution subject detection
* duplicate claim ID detection
* unknown causal node, edge, path, and outcome references
* multiple primary contribution claim detection
* overlapping-claim reference verification
* self-overlap prevention
* effect-estimate range verification
* observed-effect share range validation
* measurement-window ordering
* blocking-issue reference validation
* accepted-profile state validation
* review requirement consistency

### Design decisions

* Distinguished causal participation from contribution.
* Distinguished contribution strength from economic value.
* Distinguished economic value from allocation share.
* Required contribution claims to reference v0.3 causal structures.
* Added counterfactual and alternative-explanation support.
* Added explicit handling for overlapping human and AI influence.
* Added negative-externality contribution claims.

### Boundaries

v0.4 does not determine:

* legal ownership
* intellectual-property rights
* allocation percentages
* royalty eligibility
* royalty amounts
* payment obligations

---

## [0.3.0-candidate] — 2026-07-14

### Added

* `schemas/cross-domain-causal-binding-record.schema.json`
* `examples/cross-domain-causal-binding-record.example.yaml`
* Cross-domain causal nodes
* Causal edges
* Causal paths
* Temporal context records
* Causal claim status
* Causal strength classification
* Counterfactual assessments
* Counterevidence references
* Alternative-explanation references
* Purpose continuity assessments
* Governance continuity assessments
* Privacy-transformation continuity assessments
* Processing-constraint continuity assessments
* Human review and unresolved-issue records

### Supported causal relationships

* `initiates`
* `enables`
* `triggers`
* `informs`
* `transforms`
* `routes`
* `constrains`
* `verifies`
* `prevents`
* `influences`
* `follows`
* `correlates_with`

### Added semantic validation

* duplicate node, edge, path, and assessment ID detection
* missing node reference detection
* self-edge detection
* path length consistency
* edge-to-node sequence consistency
* cross-domain path verification
* outcome-node placement verification
* temporal conflict detection
* continuity-assessment reference validation
* accepted-primary-path requirements
* unresolved accepted-binding detection
* review requirement consistency

### Design decisions

* Represented causal relationships as graphs rather than fixed linear chains.
* Distinguished temporal sequence from causal influence.
* Added counterfactual and alternative-explanation fields.
* Added continuity tracking across domain boundaries.
* Required v0.3 records to include v0.1 translation and v0.2 classification sources.
* Preserved human authority for contested causal claims.

### Boundaries

v0.3 does not establish:

* ownership
* economic contribution
* contribution weight
* allocation eligibility
* royalty entitlement
* payment obligation

---

## [0.2.0-candidate] — 2026-07-14

### Added

* `schemas/structural-role-classification-record.schema.json`
* `examples/structural-role-classification-record.example.yaml`
* Classification subjects
* Context-dependent role assignments
* Assignment scope
* Classification basis
* Evidence and counterevidence references
* Role confidence
* Primary and secondary role designation
* Human review
* Unresolved classification issues
* Supersession references

### Supported structural roles

* `origin`
* `derivative`
* `supporting`
* `verification`
* `audit`
* `distribution`
* `infrastructure`
* `royalty_endpoint`

### Added semantic validation

* duplicate classification subject detection
* duplicate assignment ID detection
* missing subject-reference detection
* multiple primary role detection
* review requirement consistency
* unresolved accepted-classification detection
* accepted role-state verification

### Design decisions

* Separated actor type from structural role.
* Allowed the same actor to perform different roles in different events.
* Allowed multiple roles for the same subject when supported by scope and evidence.
* Required role assignments to include rationale, evidence, confidence, and status.
* Prevented structural classifications from implying ownership or payment rights.

### Boundaries

v0.2 does not establish:

* legal ownership
* causal effect
* economic contribution
* allocation eligibility
* royalty entitlement
* payment obligation

---

## [0.1.0-candidate] — 2026-07-14

### Added

* `schemas/economic-event-translation-record.schema.json`
* `examples/economic-event-translation-record.example.yaml`
* `scripts/validate_examples.py`
* `.github/workflows/validate.yml`
* `requirements.txt`
* Initial `README.md`
* Initial `CHANGELOG.md`

### Added event translation structure

* source event identity
* event type
* event domain
* source system
* jurisdiction
* participating actors
* raw event references
* payload digests
* normalized event type
* normalized action
* result status
* economic effect
* purpose context
* governance context
* consent status
* asserted legal basis
* determination authority
* processing eligibility
* privacy transformations
* re-identification controls
* personal-targeting constraints
* data classification
* evidence references
* audit references
* translation status

### Supported source event types

* telecom events
* payment events
* financial events
* agent actions
* recommendation events
* tool calls
* human decisions
* platform events
* reward events
* AI training inputs
* model evaluations
* data transfers

### Governance design

* Replaced an authoritative `legal_basis` assertion with `asserted_legal_basis`.
* Added `determination_authority`.
* Added `determination_status`.
* Added `review_status`.
* Added `processing_eligibility`.
* Preserved the distinction between protocol records and final legal determinations.

### Privacy design

* Added identifier removal
* Added pseudonymization
* Added aggregation
* Added generalization
* Added masking
* Added tokenization
* Added differential privacy
* Added encryption
* Added access control
* Added re-identification controls
* Added personal-targeting constraints
* Added sensitive, minor, and biometric data flags

### Validation

* Added JSON Schema Draft 2020-12 validation.
* Added YAML example loading.
* Added URI and date-time format checking.
* Added GitHub Actions validation workflow.

### Design decisions

* Defined v0.1 as factual event translation.
* Deferred structural role classification to v0.2.
* Deferred causal binding to v0.3.
* Deferred contribution assessment to v0.4.
* Deferred royalty readiness to v0.5.

### Boundaries

v0.1 does not determine:

* whether an asserted legal basis is legally correct
* structural role
* causal effect
* economic contribution
* allocation eligibility
* royalty entitlement
* payment obligation
