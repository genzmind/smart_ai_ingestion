# Capability Registry: Extractor-Alpha

## Skill: `detect_source_format`
- **Description:** Determines the effective source type using MIME metadata, file extension, and parser-compatible heuristics.
- **Tools:** MIME metadata, filename parsing, content sniffing heuristics.
- **Execution:** Read provided MIME type -> Validate against extension -> Apply fallback signature checks when needed -> Route to the correct extraction strategy.

## Skill: `parse_structured_file`
- **Description:** Extracts records from structured and semi-structured machine-readable files such as CSV, Excel, and JSON.
- **Tools:** `pandas.read_csv`, `pandas.read_excel`, `json.loads`.
- **Execution:** Open structured file -> Parse rows/objects -> Normalize missing values -> Convert to JSON array -> Preserve header-driven field names.

## Skill: `parse_unstructured_document`
- **Description:** Extracts text and tabular content from PDFs and images that are not directly machine-readable.
- **Tools:** `pdfplumber`, `pytesseract`, multimodal LLM or OCR service.
- **Execution:** Render document pages -> Detect regions of interest -> Extract text blocks and tables -> Convert page-level content into structured record candidates -> Flatten into JSON array form.

## Skill: `flatten_nested_content`
- **Description:** Normalizes nested extraction results into a downstream-friendly base JSON array.
- **Tools:** Python dict/list traversal utilities.
- **Execution:** Inspect nested extracted structures -> Flatten or segment records according to document semantics -> Preserve traceable keys and hierarchy markers where needed.

## Skill: `extract_metadata`
- **Description:** Captures provenance and system metadata for the extracted artifact.
- **Tools:** `os.stat`, `hashlib`, timestamp utilities.
- **Execution:** Read file metadata -> Compute SHA-256 hash -> Attach `source_uri` -> Attach extraction timestamp and file descriptors.

## Skill: `emit_extracted_payload`
- **Description:** Produces the final extraction artifact for downstream schema mapping.
- **Tools:** JSON serialization.
- **Execution:** Validate extracted record array shape -> Serialize to `extracted_payload.json` -> Attach metadata or warnings in companion context when supported.
