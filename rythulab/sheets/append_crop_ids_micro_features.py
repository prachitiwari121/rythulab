from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

from map_crop_ids_step1 import build_alias_map, load_crop_details_with_ids, resolve_canonical


MICRO_FEATURES_DIRNAME = "Crop Micro Features"


def read_csv(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_csv(path: Path, rows: List[List[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def write_unresolved_report(report_path: Path, unresolved_by_file: Dict[str, List[str]]) -> None:
    rows: List[List[str]] = [["file", "crop_name"]]
    for file_name in sorted(unresolved_by_file):
        for crop_name in sorted(set(unresolved_by_file[file_name]), key=str.lower):
            rows.append([file_name, crop_name])
    write_csv(report_path, rows)


def extend_alias_map(alias_map: Dict[str, str], norm_to_canonical: Dict[str, str]) -> None:
    folder_aliases = {
        "black pepper": "Pepper",
        "citrus": "Citrus (various)",
    }

    for alias, canonical_name in folder_aliases.items():
        canonical_key = canonical_name.strip().lower()
        for normalized_name, stored_canonical in norm_to_canonical.items():
            if stored_canonical.strip().lower() == canonical_key:
                alias_map[alias] = stored_canonical
                break


def process_micro_features_file(
    csv_path: Path,
    canonical_to_id: Dict[str, str],
    norm_to_canonical: Dict[str, str],
    alias_map: Dict[str, str],
    apply: bool,
    backup: bool,
) -> Tuple[int, int, bool, List[str]]:
    rows = read_csv(csv_path)
    if not rows:
        return 0, 0, False, []

    header = rows[0][:]
    if "Crop" in header:
        crop_idx = header.index("Crop")
    elif "Crop Name" in header:
        crop_idx = header.index("Crop Name")
    else:
        raise ValueError(f"Expected 'Crop' or 'Crop Name' column in {csv_path.name}")

    inserted_cropid = "CropID" not in header
    if inserted_cropid:
        id_idx = crop_idx
        header.insert(id_idx, "CropID")
        crop_idx += 1
    else:
        id_idx = header.index("CropID")

    mapped = 0
    unresolved_names: List[str] = []
    out_rows = [header]

    for row in rows[1:]:
        normalized_row = row[:]
        if inserted_cropid:
            normalized_row.insert(id_idx, "")

        if len(normalized_row) < len(header):
            normalized_row.extend([""] * (len(header) - len(normalized_row)))

        crop_name = normalized_row[crop_idx].strip()
        canonical_name = resolve_canonical(crop_name, norm_to_canonical, alias_map)
        crop_id = canonical_to_id.get(canonical_name, "") if canonical_name else ""
        normalized_row[id_idx] = crop_id

        if crop_id:
            mapped += 1
        elif crop_name:
            unresolved_names.append(crop_name)

        out_rows.append(normalized_row)

    if apply:
        if backup:
            backup_path = csv_path.with_suffix(csv_path.suffix + ".bak")
            backup_path.write_bytes(csv_path.read_bytes())
        write_csv(csv_path, out_rows)

    return mapped, len(unresolved_names), inserted_cropid, unresolved_names


def process_micro_features_folder(
    micro_features_dir: Path,
    canonical_to_id: Dict[str, str],
    norm_to_canonical: Dict[str, str],
    alias_map: Dict[str, str],
    apply: bool,
    backup: bool,
) -> Dict[str, List[str]]:
    unresolved_by_file: Dict[str, List[str]] = {}

    for csv_path in sorted(micro_features_dir.glob("*.csv")):
        mapped, unresolved_count, inserted_cropid, unresolved_names = process_micro_features_file(
            csv_path=csv_path,
            canonical_to_id=canonical_to_id,
            norm_to_canonical=norm_to_canonical,
            alias_map=alias_map,
            apply=apply,
            backup=backup,
        )
        unresolved_by_file[csv_path.name] = unresolved_names
        print(
            f"{csv_path.name}: mapped={mapped}, unresolved={unresolved_count}, cropid_column={'inserted' if inserted_cropid else 'updated'}, mode={'apply' if apply else 'dry-run'}"
        )

    return unresolved_by_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append CropID values to Crop Micro Features sheets using the crop_details master list."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing crop_details and the Crop Micro Features folder",
    )
    parser.add_argument("--apply", action="store_true", help="Write changes to files")
    parser.add_argument("--backup", action="store_true", help="Create .bak files before changes")
    parser.add_argument(
        "--unresolved-report",
        type=Path,
        default=Path(__file__).resolve().parent / "crop_micro_features_unresolved_report.csv",
        help="Path to write unresolved crop-name report CSV",
    )
    args = parser.parse_args()

    crop_details_dir = args.base_dir / "crop_details"
    micro_features_dir = args.base_dir / MICRO_FEATURES_DIRNAME
    if not micro_features_dir.exists():
        raise FileNotFoundError(f"Missing folder: {micro_features_dir}")

    canonical_to_id, norm_to_canonical, _ = load_crop_details_with_ids(crop_details_dir, apply=False)
    alias_map = build_alias_map(crop_details_dir, norm_to_canonical)
    extend_alias_map(alias_map, norm_to_canonical)

    unresolved_by_file = process_micro_features_folder(
        micro_features_dir=micro_features_dir,
        canonical_to_id=canonical_to_id,
        norm_to_canonical=norm_to_canonical,
        alias_map=alias_map,
        apply=args.apply,
        backup=args.backup,
    )

    write_unresolved_report(args.unresolved_report, unresolved_by_file)
    total_unresolved = sum(len(names) for names in unresolved_by_file.values())
    print(f"unresolved_report={args.unresolved_report}, unresolved_entries={total_unresolved}")


if __name__ == "__main__":
    main()