# Capability Registry: Streamer-Parquet-JSON

## Skill: `validate_stream_source`
- **Description:** Validates that the stream source is either an HTTP(S) live endpoint or a local NDJSON/JSONL file.
- **Tools:** `StreamJsonAgentBase.validate`.
- **Execution:** Confirm one source exists -> Validate `stream_url` scheme or local file suffix -> Reject invalid combinations.

## Skill: `resolve_stream_runtime_options`
- **Description:** Computes effective batch size and stopping conditions for stream consumption.
- **Tools:** `smart_ingestion.connectors.stream_json.stream_options`.
- **Execution:** Read `intent.options` -> Merge with configured defaults -> Return `batch_size`, `max_records`, `duration_seconds`.

## Skill: `consume_incremental_stream_records`
- **Description:** Iterates stream records in real time for filter-only or no-transform execution.
- **Tools:** `StreamJsonAgentBase._iter_records`, `stream_filter_record`.
- **Execution:** Open live stream or local NDJSON file -> Parse each JSON record -> Apply per-record filter -> Keep accepted records only.

## Skill: `collect_full_buffer_for_complex_transforms`
- **Description:** Buffers the entire stream when join or aggregate transforms require full dataset context.
- **Tools:** `smart_ingestion.connectors.ingestion_pipeline.stream_collect_and_transform`.
- **Execution:** Consume records until EOF or stop condition -> Materialize all records -> Apply full transform pipeline -> Return transformed records.

## Skill: `write_parquet_batches`
- **Description:** Persists records to a Parquet file in configurable batches.
- **Tools:** `smart_ingestion.connectors.parquet_writer.StreamingParquetWriter`, `smart_ingestion.connectors.stream_json.batched`.
- **Execution:** Initialize writer -> Group records by batch size -> Write each batch -> Close writer -> Return final row count.

## Skill: `normalize_parquet_destination`
- **Description:** Ensures the output artifact uses a Parquet-compatible destination path.
- **Tools:** `smart_ingestion.utils.resolve_write_path`.
- **Execution:** Resolve writable path -> If suffix is not `.parquet`, replace suffix with `.parquet`.

## Skill: `report_stream_result`
- **Description:** Returns the final streaming ingestion outcome to the orchestrator.
- **Tools:** `smart_ingestion.models.IngestionResult`.
- **Execution:** If rows written > 0 -> emit success with path/count -> Else emit explicit empty-stream failure -> Surface exceptions directly when raised.
