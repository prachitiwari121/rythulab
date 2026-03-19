from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List, Tuple


def read_csv(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_csv(path: Path, rows: List[List[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def is_crop_row_format(rows: List[List[str]]) -> bool:
    if not rows or not rows[0]:
        return False
    first_header = rows[0][0].strip().lower()
    return first_header in {"crop", "crop name"}


def to_crop_row_format(rows: List[List[str]]) -> List[List[str]]:
    if not rows or len(rows) < 2 or len(rows[0]) < 2:
        return rows

    header = rows[0]
    crops = [cell.strip() for cell in header[1:] if cell.strip()]

    feature_rows = []
    for row in rows[1:]:
        if not row:
            continue
        feature_name = row[0].strip() if len(row) > 0 else ""
        if not feature_name:
            continue
        feature_rows.append((feature_name, row))

    converted = [["Crop"] + [name for name, _ in feature_rows]]

    for crop_idx, crop_name in enumerate(crops, start=1):
        new_row = [crop_name]
        for _, source_row in feature_rows:
            value = source_row[crop_idx].strip() if crop_idx < len(source_row) else ""
            new_row.append(value)
        converted.append(new_row)

    return converted


def convert_file(path: Path) -> Tuple[bool, int, int]:
    rows = read_csv(path)
    if not rows:
        return False, 0, 0

    if is_crop_row_format(rows):
        return False, max(len(rows) - 1, 0), max(len(rows[0]) - 1, 0)

    converted = to_crop_row_format(rows)
    write_csv(path, converted)
    return True, max(len(converted) - 1, 0), max(len(converted[0]) - 1, 0)


def plan_file(path: Path) -> Tuple[bool, int, int]:
    rows = read_csv(path)
    if not rows:
        return False, 0, 0
    if is_crop_row_format(rows):
        return False, max(len(rows) - 1, 0), max(len(rows[0]) - 1, 0)
    converted = to_crop_row_format(rows)
    return True, max(len(converted) - 1, 0), max(len(converted[0]) - 1, 0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Step1 CSV files to format: crops in rows, features in columns."
    )
    parser.add_argument(
        "--step1-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "step1",
        help="Directory containing Step1 CSV files",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to files. If omitted, runs in dry-run mode.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak files before overwriting converted files (only with --apply).",
    )

    args = parser.parse_args()

    if not args.step1_dir.exists():
        raise FileNotFoundError(f"Step1 directory not found: {args.step1_dir}")

    csv_files = sorted(args.step1_dir.glob("*.csv"))
    converted_count = 0

    for csv_path in csv_files:
        will_convert, crop_rows, feature_cols = plan_file(csv_path)

        if not args.apply:
            state = "WILL CONVERT" if will_convert else "ALREADY ROW-FORMAT"
            print(f"{csv_path.name}: {state} | crops={crop_rows}, features={feature_cols}")
            continue

        if not will_convert:
            print(f"{csv_path.name}: SKIPPED (already row-format)")
            continue

        if args.backup:
            backup_path = csv_path.with_suffix(csv_path.suffix + ".bak")
            backup_path.write_bytes(csv_path.read_bytes())

        changed, crop_rows, feature_cols = convert_file(csv_path)
        if changed:
            converted_count += 1
            print(f"{csv_path.name}: CONVERTED | crops={crop_rows}, features={feature_cols}")

    if args.apply:
        print(f"Done. Converted {converted_count} file(s).")


if __name__ == "__main__":
    main()
