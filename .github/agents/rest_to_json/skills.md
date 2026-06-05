# Capability Registry: Fetcher-REST-JSON

## Skill: `validate_http_endpoint`
- **Description:** Ensures the requested REST endpoint uses a supported transport scheme.
- **Tools:** simple prefix validation.
- **Execution:** Read `api_url` -> Confirm `http://` or `https://` prefix -> Reject unsupported schemes.

## Skill: `resolve_output_destination`
- **Description:** Resolves and prepares the JSON output path under approved write roots.
- **Tools:** `smart_ingestion.utils.resolve_write_path`.
- **Execution:** Normalize path -> Enforce allowed write roots -> Create parent directories -> Return absolute destination.

## Skill: `fetch_json_payload`
- **Description:** Performs the network request and parses the response body as JSON.
- **Tools:** `httpx.Client`.
- **Execution:** Open client with timeout -> Send GET request -> Raise on HTTP failure -> Call `response.json()` -> Return parsed payload.

## Skill: `persist_json_artifact`
- **Description:** Writes the parsed JSON payload to disk in a human-readable form.
- **Tools:** Python `json.dump`.
- **Execution:** Open destination file -> Dump payload with indentation -> Close file cleanly.

## Skill: `calculate_payload_size`
- **Description:** Produces a user-facing count for the retrieved payload.
- **Tools:** Python type inspection.
- **Execution:** If payload is list -> return `len(payload)` -> Else return `1`.

## Skill: `report_fetch_result`
- **Description:** Returns the final fetch outcome to the orchestrator.
- **Tools:** `smart_ingestion.models.IngestionResult`.
- **Execution:** Attach destination path and count -> Produce success message, or surface request/parsing/write failures.
