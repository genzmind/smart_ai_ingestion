# Capability Registry: Mapper-Beta

## Skill: `enumerate_source_and_target_fields`
- **Description:** Extracts the source-field universe and target-schema field universe needed for mapping analysis.
- **Tools:** JSON traversal utilities.
- **Execution:** Read extracted payload keys -> Read target schema fields -> Build comparable source/target field inventories.

## Skill: `semantic_similarity_search`
- **Description:** Uses embeddings or similarity heuristics to identify likely target matches for ambiguous source fields.
- **Tools:** sentence-transformer embeddings, cosine similarity, semantic alias dictionaries.
- **Execution:** Embed source field name and context -> Compare against target schema field descriptors -> Return ranked candidate matches and scores.

## Skill: `generate_mapping_dictionary`
- **Description:** Produces the field crosswalk from source keys to target schema keys.
- **Tools:** LLM completion endpoint, rule engine, JSON validator.
- **Execution:** Construct prompt with source keys, sample values, and target schema -> Generate mapping JSON -> Validate structure -> Reject malformed output.

## Skill: `assign_confidence_scores`
- **Description:** Produces a field-level confidence score for every mapping decision.
- **Tools:** heuristic scoring model, similarity scores, rule-based confidence adjustment.
- **Execution:** Combine exact-match confidence, semantic-match confidence, and ambiguity penalties -> Emit score per mapping entry.

## Skill: `transform_payload`
- **Description:** Applies the mapping dictionary to the extracted records without changing the underlying values.
- **Tools:** Python dictionary transformation utilities.
- **Execution:** Iterate through each record -> Rename mapped keys -> Group unmapped keys into reserved structure -> Emit target-aligned record.

## Skill: `write_mapping_audit_log`
- **Description:** Captures how and why each mapping decision was made.
- **Tools:** JSON serialization.
- **Execution:** Record source key -> target key -> confidence score -> rationale or method used -> Persist as `mapping_audit_log.json`.
