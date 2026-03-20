from __future__ import annotations

import csv
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RANGE_RE = re.compile(r"^\s*(.+?)\s+to\s+(.+?)\s*$", re.IGNORECASE)


def _is_class_row(parameter: str) -> bool:
    return "class" in (parameter or "").lower()


def _normalize_range_value(value: str) -> str:
    if not isinstance(value, str):
        return value

    match = RANGE_RE.match(value)
    if not match:
        return value

    return match.group(2).strip()


def normalize_csv_file(csv_path: Path) -> tuple[int, bool]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    if not rows:
        return 0, False

    updated_cells = 0
    for row in rows[1:]:
        if not row:
            continue

        parameter = row[0] if len(row) > 0 else ""
        if not _is_class_row(parameter):
            continue

        for index in range(1, len(row)):
            original = row[index]
            normalized = _normalize_range_value(original)
            if normalized != original:
                row[index] = normalized
                updated_cells += 1

    if updated_cells > 0:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)
        return updated_cells, True

    return 0, False


def main() -> None:
    total_cells = 0
    touched_files = 0

    for csv_path in sorted(BASE_DIR.glob("*.csv")):
        updated_cells, changed = normalize_csv_file(csv_path)
        total_cells += updated_cells
        if changed:
            touched_files += 1
            print(f"Updated {csv_path.name}: {updated_cells} cell(s)")

    print(f"Done. Files updated: {touched_files}, cells updated: {total_cells}")


if __name__ == "__main__":
    main()
