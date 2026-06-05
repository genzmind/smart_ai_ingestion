# Capability Registry: Uploader-S3-CSV

## Skill: `resolve_local_csv_file`
- **Description:** Validates and resolves the source CSV file from safe local read roots.
- **Tools:** `smart_ingestion.utils.resolve_read_path`.
- **Execution:** Normalize path -> Enforce allowed roots -> Confirm existence -> Return source file handle path.

## Skill: `select_s3_storage_backend`
- **Description:** Uses the configured S3 adapter, which may point to AWS or the local mock storage.
- **Tools:** `smart_ingestion.connectors.s3.s3_storage`.
- **Execution:** Read config-backed storage mode -> Route upload to local mock or boto3-backed S3 client path.

## Skill: `upload_csv_artifact`
- **Description:** Copies the source CSV to the requested bucket/key without mutating contents.
- **Tools:** `S3Storage.upload_file`.
- **Execution:** Accept source path -> Create destination object path -> Upload/copy bytes -> Return storage location string.

## Skill: `count_uploaded_rows`
- **Description:** Produces a row count for the CSV payload that excludes the header line.
- **Tools:** Python file iteration.
- **Execution:** Open source file -> Count lines -> Subtract header -> Clamp lower bound at zero.

## Skill: `return_storage_result`
- **Description:** Emits a success or failure result describing the transfer outcome.
- **Tools:** `smart_ingestion.models.IngestionResult`.
- **Execution:** Capture storage location -> Attach row count -> Generate success message, or emit surfaced exception on failure.
