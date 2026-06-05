# Capability Registry: Transformer-CSV-CSV

## Skill: `resolve_csv_io_paths`
- **Description:** Resolves safe source and destination file paths for CSV transformation.
- **Tools:** `smart_ingestion.utils.resolve_read_path`, `smart_ingestion.utils.resolve_write_path`.
- **Execution:** Validate readable source -> Validate writable destination -> Prepare parent directories for output.

## Skill: `read_source_csv_rows`
- **Description:** Parses the source CSV file into ordered row dictionaries.
- **Tools:** Python `csv.DictReader`.
- **Execution:** Open source file -> Parse header and rows -> Materialize rows -> Reject empty datasets.

## Skill: `compute_effective_fieldnames`
- **Description:** Determines the output header based on requested column projection.
- **Tools:** request `options.columns`, source header list.
- **Execution:** If no projection -> keep full header -> Else filter requested columns against actual header -> Preserve requested order.

## Skill: `write_projected_csv`
- **Description:** Writes a new CSV file using the effective field set.
- **Tools:** Python `csv.DictWriter`.
- **Execution:** Open destination -> Write header -> For each row emit only selected fields -> Ignore extras safely.

## Skill: `preserve_row_count_reporting`
- **Description:** Reports the number of data rows written to the new CSV artifact.
- **Tools:** in-memory row list length.
- **Execution:** Count parsed rows -> Attach destination path -> Generate success result.
