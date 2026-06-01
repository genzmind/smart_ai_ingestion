from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


class StreamingParquetWriter:
    """Append Parquet row groups as stream batches arrive."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._writer: pq.ParquetWriter | None = None
        self._rows = 0

    def write_batch(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        table = pa.Table.from_pylist(records)
        if self._writer is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._writer = pq.ParquetWriter(self._path, table.schema)
        else:
            table = _align_schema(table, self._writer.schema)
        self._writer.write_table(table)
        self._rows += len(records)

    def close(self) -> int:
        if self._writer is not None:
            self._writer.close()
        return self._rows


def _align_schema(table: pa.Table, schema: pa.Schema) -> pa.Table:
    """Add missing columns as nulls so batches with evolving schemas can be written."""
    names = schema.names
    columns = {}
    for name in names:
        if name in table.column_names:
            columns[name] = table.column(name)
        else:
            columns[name] = pa.nulls(table.num_rows)
    return pa.table(columns, schema=schema)
