# Capability Registry: Streamer-JSON-JSON

## Skill: `validate_stream_json_source`
- **Description:** Confirms the request contains a supported live stream URL or NDJSON/JSONL file source.
- **Tools:** `StreamJsonAgentBase.validate`.
- **Execution:** Check source presence -> Validate scheme or suffix -> Reject unsupported source types.

## Skill: `resolve_json_stream_format`
- **Description:** Computes the effective output format for streamed JSON persistence.
- **Tools:** `smart_ingestion.connectors.stream_json.stream_options`.
- **Execution:** Read `intent.options.json_format` -> Accept `ndjson` or `json_array` -> Fall back to `ndjson` when invalid or absent.

## Skill: `normalize_json_destination`
- **Description:** Aligns the destination path with the effective JSON stream output format.
- **Tools:** `smart_ingestion.utils.resolve_write_path`.
- **Execution:** Resolve writable destination -> If format is `ndjson` and suffix is incompatible, change suffix to `.ndjson`.

## Skill: `persist_incremental_stream_records`
- **Description:** Writes accepted records one-by-one for no-transform or filter-only streaming flows.
- **Tools:** `StreamJsonAgentBase._iter_records`, `stream_filter_record`, `StreamingJsonWriter`.
- **Execution:** Iterate records -> Apply per-record filter when present -> Write kept records immediately -> Continue until stop condition or EOF.

## Skill: `buffer_and_transform_stream_records`
- **Description:** Handles join and aggregate scenarios by collecting the full stream before writing.
- **Tools:** `smart_ingestion.connectors.ingestion_pipeline.stream_collect_and_transform`.
- **Execution:** Consume all eligible stream records -> Apply full transform pipeline -> Write transformed records through the JSON writer.

## Skill: `finalize_stream_json_artifact`
- **Description:** Closes the JSON writer correctly for NDJSON or JSON array output.
- **Tools:** `smart_ingestion.connectors.stream_json_writer.StreamingJsonWriter`.
- **Execution:** Flush final writer state -> Close enclosing JSON array when needed -> Return total written row count.

## Skill: `report_json_stream_result`
- **Description:** Returns the final status for streamed JSON persistence.
- **Tools:** `smart_ingestion.models.IngestionResult`.
- **Execution:** If row count > 0 -> emit success with path/count -> Else return explicit empty-stream failure -> Surface exceptions on error.
