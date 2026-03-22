from __future__ import annotations

import argparse
import csv
import difflib
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple


RATINGS = ["P", "H", "M", "S", "U", "T"]


def read_csv(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_csv(path: Path, rows: List[List[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def norm(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def loose_norm(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def crop_id(index: int) -> str:
    return f"CRP{index:04d}"


def load_crop_details_with_ids(crop_details_dir: Path, apply: bool) -> Tuple[Dict[str, str], Dict[str, str], int]:
    list_file = crop_details_dir / "0.List of All crops - Sheet1.csv"
    if not list_file.exists():
        raise FileNotFoundError(f"Missing file: {list_file}")

    rows = read_csv(list_file)
    if not rows:
        raise ValueError(f"Empty file: {list_file}")

    header = rows[0]
    if "Crop Name" not in header:
        raise ValueError("Expected 'Crop Name' column in 0.List file")

    if "CropID" not in header:
        header = ["CropID", *header]
        data_rows = [["", *row] for row in rows[1:]]
    else:
        data_rows = rows[1:]

    idx_id = header.index("CropID")
    idx_name = header.index("Crop Name")

    canonical_to_id: Dict[str, str] = {}
    norm_to_canonical: Dict[str, str] = {}
    changed = 0

    for row_idx, row in enumerate(data_rows, start=1):
        if len(row) < len(header):
            row.extend([""] * (len(header) - len(row)))

        name = row[idx_name].strip() if idx_name < len(row) else ""
        if not name:
            continue

        cid = row[idx_id].strip() if idx_id < len(row) else ""
        if not cid:
            cid = crop_id(row_idx)
            row[idx_id] = cid
            changed += 1

        canonical_to_id[name] = cid
        norm_to_canonical[norm(name)] = name

    if apply:
        write_csv(list_file, [header, *data_rows])

    return canonical_to_id, norm_to_canonical, changed


def build_alias_map(crop_details_dir: Path, norm_to_canonical: Dict[str, str]) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}

    manual_aliases = {
        "rice": "Paddy/Rice",
        "paddy rice": "Paddy/Rice",
        "jowar": "Jowar (Sorghum)",
        "sorghum": "Jowar (Sorghum)",
        "bajra": "Bajra (Pearl Millet)",
        "finger millet": "Ragi (Finger Millet)",
        "ragi": "Ragi (Finger Millet)",
        "redgram": "Red Gram (Pigeon Pea)",
        "blackgram": "Black Gram (Urad)",
        "greengram": "Green Gram (Moong)",
        "bengal gram": "Chickpeas (Garbanzo Beans) (Cicer arietinum)",
        "brinjal": "Brinjal (Eggplant)",
        "chilli": "Chilli (Commercial)",
        "chillies": "Chilli (Commercial)",
        "arecanut": "Areca Nut",
        "amla": "Amla (Indian Gooseberry)",
        "cluster beans": "Cluster Bean",
        "beans": "Field Bean",
    }

    for key, canonical in manual_aliases.items():
        canonical_norm = norm(canonical)
        if canonical_norm in norm_to_canonical:
            alias_map[norm(key)] = norm_to_canonical[canonical_norm]

    for details_file in sorted(crop_details_dir.glob("*.csv")):
        if details_file.name.startswith("0.List"):
            continue
        rows = read_csv(details_file)
        if not rows:
            continue

        header = rows[0]
        headers_crops = [h.strip() for h in header[1:]]

        # Try mapping header crops
        mapped_headers: List[str] = []
        for crop in headers_crops:
            mapped = resolve_canonical(crop, norm_to_canonical, alias_map)
            mapped_headers.append(mapped)
            if mapped:
                alias_map[norm(crop)] = mapped

        # If a Crop Common Name row exists, map those names to same canonical crop
        for row in rows[1:]:
            if not row:
                continue
            param = row[0].strip().lower()
            if param != "crop common name":
                continue
            for col_idx, common in enumerate(row[1:], start=0):
                common = common.strip()
                if not common:
                    continue
                mapped = mapped_headers[col_idx] if col_idx < len(mapped_headers) else ""
                if mapped:
                    alias_map[norm(common)] = mapped
            break

    return alias_map


def resolve_canonical(name: str, norm_to_canonical: Dict[str, str], alias_map: Dict[str, str]) -> str:
    key = norm(name)
    if not key:
        return ""

    if key in norm_to_canonical:
        return norm_to_canonical[key]

    if key in alias_map:
        return alias_map[key]

    loose_key = loose_norm(name)
    if loose_key:
        loose_matches = [canonical for canonical in norm_to_canonical.values() if loose_norm(canonical) == loose_key]
        if len(loose_matches) == 1:
            return loose_matches[0]

    candidates = list(norm_to_canonical.keys())
    best = difflib.get_close_matches(key, candidates, n=1, cutoff=0.9)
    if best:
        return norm_to_canonical[best[0]]

    return ""


def process_row_oriented_sheet(
    rows: List[List[str]],
    canonical_to_id: Dict[str, str],
    canonical_order: List[str],
    norm_to_canonical: Dict[str, str],
    alias_map: Dict[str, str],
) -> Tuple[List[List[str]], int, int, int, List[str]]:
    header = rows[0][:]
    data = rows[1:]

    if "Crop" in header:
        crop_idx = header.index("Crop")
    elif "Crop Name" in header:
        crop_idx = header.index("Crop Name")
    else:
        crop_idx = 0

    if "CropID" in header:
        id_idx = header.index("CropID")
    else:
        id_idx = 0
        header.insert(0, "CropID")
        crop_idx += 1

    renamed = 0
    mapped = 0
    missing = 0
    unresolved_names: List[str] = []

    out_data = []
    present_crops = set()
    for row in data:
        if not any((c or "").strip() for c in row):
            continue

        if len(row) < len(header) - 1:
            row = row + [""] * (len(header) - 1 - len(row))

        if "CropID" not in rows[0]:
            row = ["", *row]

        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))

        crop_name = row[crop_idx].strip()
        canonical = resolve_canonical(crop_name, norm_to_canonical, alias_map)

        if canonical:
            if canonical != crop_name:
                row[crop_idx] = canonical
                renamed += 1
            row[id_idx] = canonical_to_id.get(canonical, "")
            mapped += 1 if row[id_idx] else 0
            if not row[id_idx]:
                missing += 1
            present_crops.add(canonical)
        else:
            row[id_idx] = ""
            if crop_name:
                missing += 1
                unresolved_names.append(crop_name)
                present_crops.add(crop_name)

        out_data.append(row)

    # Add crops from crop_details that are not present in this sheet.
    total_cols = len(header)
    random_cols = [idx for idx in range(total_cols) if idx not in {id_idx, crop_idx}]
    for crop in canonical_order:
        if crop in present_crops:
            continue
        new_row = [""] * total_cols
        new_row[id_idx] = canonical_to_id.get(crop, "")
        new_row[crop_idx] = crop
        for idx in random_cols:
            new_row[idx] = random.choice(RATINGS)
        out_data.append(new_row)
        mapped += 1 if new_row[id_idx] else 0

    return [header, *out_data], renamed, mapped, missing, unresolved_names


def process_column_oriented_sheet(
    rows: List[List[str]],
    canonical_to_id: Dict[str, str],
    canonical_order: List[str],
    norm_to_canonical: Dict[str, str],
    alias_map: Dict[str, str],
) -> Tuple[List[List[str]], int, int, int, List[str]]:
    header = rows[0][:]
    data = rows[1:]

    renamed = 0
    mapped = 0
    missing = 0
    unresolved_names: List[str] = []

    updated_header = [header[0]]
    crop_ids = ["CropID"]
    present_crops = set()

    for crop in header[1:]:
        crop_name = crop.strip()
        canonical = resolve_canonical(crop_name, norm_to_canonical, alias_map)
        if canonical:
            if canonical != crop_name:
                renamed += 1
            updated_header.append(canonical)
            cid = canonical_to_id.get(canonical, "")
            crop_ids.append(cid)
            mapped += 1 if cid else 0
            if not cid:
                missing += 1
            present_crops.add(canonical)
        else:
            updated_header.append(crop_name)
            crop_ids.append("")
            if crop_name:
                missing += 1
                unresolved_names.append(crop_name)
                present_crops.add(crop_name)

    # Add crops from crop_details that are not present in this sheet.
    for crop in canonical_order:
        if crop in present_crops:
            continue
        updated_header.append(crop)
        cid = canonical_to_id.get(crop, "")
        crop_ids.append(cid)
        mapped += 1 if cid else 0

    # Remove existing CropID row if present, then insert normalized one.
    filtered_data = []
    for row in data:
        first = row[0].strip().lower() if row else ""
        if first == "cropid":
            continue
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        filtered_data.append(row)

    # Fill random values for newly added crop columns.
    for row in filtered_data:
        existing_len = len(row)
        if existing_len < len(updated_header):
            row.extend([random.choice(RATINGS) for _ in range(len(updated_header) - existing_len)])

    out_rows = [updated_header, crop_ids, *filtered_data]
    return out_rows, renamed, mapped, missing, unresolved_names


def write_unresolved_report(report_path: Path, unresolved_by_file: Dict[str, List[str]]) -> None:
    rows: List[List[str]] = [["file", "unresolved_crop_name"]]
    for file_name in sorted(unresolved_by_file.keys()):
        names = sorted(set(unresolved_by_file[file_name]), key=str.lower)
        for name in names:
            rows.append([file_name, name])
    write_csv(report_path, rows)


def process_step1(
    step1_dir: Path,
    canonical_to_id: Dict[str, str],
    canonical_order: List[str],
    norm_to_canonical: Dict[str, str],
    alias_map: Dict[str, str],
    apply: bool,
    backup: bool,
) -> Dict[str, List[str]]:
    unresolved_by_file: Dict[str, List[str]] = {}

    for csv_path in sorted(step1_dir.glob("*.csv")):
        rows = read_csv(csv_path)
        if not rows or not rows[0]:
            continue

        first = rows[0][0].strip().lower()

        if first in {"crop", "crop name"}:
            out_rows, renamed, mapped, missing, unresolved_names = process_row_oriented_sheet(
                rows,
                canonical_to_id,
                canonical_order,
                norm_to_canonical,
                alias_map,
            )
        else:
            out_rows, renamed, mapped, missing, unresolved_names = process_column_oriented_sheet(
                rows,
                canonical_to_id,
                canonical_order,
                norm_to_canonical,
                alias_map,
            )

        unresolved_by_file[csv_path.name] = unresolved_names

        if apply:
            if backup:
                backup_path = csv_path.with_suffix(csv_path.suffix + ".bak")
                backup_path.write_bytes(csv_path.read_bytes())
            write_csv(csv_path, out_rows)

        print(
            f"{csv_path.name}: renamed={renamed}, mapped={mapped}, unresolved={missing}, mode={'apply' if apply else 'dry-run'}"
        )

    return unresolved_by_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add CropID in crop_details and map CropID/name into Step1 sheets."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing crop_details and step1 folders",
    )
    parser.add_argument("--apply", action="store_true", help="Write changes to files")
    parser.add_argument("--backup", action="store_true", help="Create .bak files before changes")
    parser.add_argument(
        "--unresolved-report",
        type=Path,
        default=Path(__file__).resolve().parent / "step1_unresolved_report.csv",
        help="Path to write unresolved crop-name report CSV",
    )
    args = parser.parse_args()

    crop_details_dir = args.base_dir / "crop_details"
    step1_dir = args.base_dir / "step1"

    canonical_to_id, norm_to_canonical, ids_created = load_crop_details_with_ids(
        crop_details_dir, apply=args.apply
    )
    canonical_order = list(canonical_to_id.keys())

    alias_map = build_alias_map(crop_details_dir, norm_to_canonical)

    print(
        f"crop_details/0.List: crop_count={len(canonical_to_id)}, crop_ids_created_or_filled={ids_created}, mode={'apply' if args.apply else 'dry-run'}"
    )

    unresolved_by_file = process_step1(
        step1_dir=step1_dir,
        canonical_to_id=canonical_to_id,
        canonical_order=canonical_order,
        norm_to_canonical=norm_to_canonical,
        alias_map=alias_map,
        apply=args.apply,
        backup=args.backup,
    )

    write_unresolved_report(args.unresolved_report, unresolved_by_file)
    total_unresolved = sum(len(v) for v in unresolved_by_file.values())
    print(f"unresolved_report={args.unresolved_report}, unresolved_entries={total_unresolved}")


if __name__ == "__main__":
    main()
