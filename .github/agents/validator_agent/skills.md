# Capability Registry: Validator-Gamma

## Skill: `standardize_data_types`
- **Description:** Casts mapped values into the exact primitive or formatted types required by the target schema.
- **Tools:** Python `datetime`, regex, `int()`, `float()`, string normalization utilities.
- **Execution:** Read schema types -> Trim and normalize raw values -> Attempt type casts -> Convert dates/timestamps to canonical format -> Record cast failures explicitly.

## Skill: `validate_required_and_format_rules`
- **Description:** Enforces presence, nullability, and format-level constraints on the mapped payload.
- **Tools:** rule-based validators, regex patterns, schema definition metadata.
- **Execution:** Check required fields -> Validate allowed formats and lengths -> Reject rows that violate mandatory constraints.

## Skill: `detect_anomalies`
- **Description:** Flags logically impossible or statistically suspicious values before persistence.
- **Tools:** rule engine, threshold checks, optional statistical baselines.
- **Execution:** Evaluate domain rules such as non-negative ages, valid date ordering, reasonable numeric ranges -> Attach anomaly reasons to failed rows.

## Skill: `evaluate_confidence_gate`
- **Description:** Reviews mapper confidence scores and combines them with validation outcomes to determine routing eligibility.
- **Tools:** rule-based confidence policy engine.
- **Execution:** Read mapping audit scores -> Compare with threshold -> If confidence below policy or validation fails, mark row for DLQ -> Otherwise mark row as verified.

## Skill: `partition_verified_and_rejected_rows`
- **Description:** Splits the mapped payload into accepted and rejected record groups with explicit reasons.
- **Tools:** Python list/dict processing.
- **Execution:** Iterate through validated rows -> Collect passing rows into verified batch -> Collect failing rows with structured rejection reasons.

## Skill: `execute_routing`
- **Description:** Sends verified and rejected records to the appropriate downstream infrastructure endpoints.
- **Tools:** `requests` library, internal API endpoints.
- **Execution:** Build verified payload -> POST to `/api/v1/ingest/verified` -> Build rejected payload with failure reasons -> POST to `/api/v1/dlq/flagged` -> Surface delivery errors if either request fails.
