from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    from crop_micro_feature_extract import get_produced_micro_features_by_cropid
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
    from crop_micro_feature_extract import get_produced_micro_features_by_cropid

try:
    from rythulab.sheets.mf_labels.mf_label_extract import annotate_mf_codes, build_mf_label_map
except ModuleNotFoundError:
    import sys

    sheets_dir = Path(__file__).resolve().parent / "sheets"
    sys.path.append(str(sheets_dir / "mf_labels"))
    from mf_label_extract import annotate_mf_codes, build_mf_label_map


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"
CROP_LIST_PATH = CROP_DETAILS_DIR / "0.List of All crops - Sheet1.csv"
DISEASE_TRIGGER_PATH = (
    SHEETS_DIR / "Disease" / "AP_Disease_CF_MF_Triggers - AP_Disease_CF_MF_Triggers.csv"
)
MICRO_FEATURES_DIR = SHEETS_DIR / "Crop Micro Features"


def _extract_mf_codes(raw_value: object) -> List[str]:
    return sorted(set(re.findall(r"MF\d+[A-Z]*", str(raw_value).upper())))


def _normalize_key(text: object) -> str:
    value = str(text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _split_csv_items(value: object) -> List[str]:
    raw = str(value or "").strip()
    if not raw:
        return []

    parts = [part.strip() for part in raw.split(",")]
    items: List[str] = []
    buffer: List[str] = []
    depth = 0

    for part in parts:
        if not part:
            continue
        depth += part.count("(") - part.count(")")
        buffer.append(part)
        if depth <= 0:
            items.append(", ".join(buffer).strip())
            buffer = []
            depth = 0

    if buffer:
        items.append(", ".join(buffer).strip())

    return items


def _parse_disease_token(token: str) -> Dict[str, str]:
    match = re.match(r"^(DIS\d{4})(?:\s*\(([^)]*)\))?$", str(token).strip(), flags=re.I)
    if not match:
        return {}
    return {
        "disease_id": match.group(1).upper(),
        "severity": str(match.group(2) or "").strip(),
    }


def _is_high_risk(severity: str) -> bool:
    normalized = str(severity or "").strip().upper()
    return normalized in {"HIGH", "VERY HIGH"}


def _load_crop_label_map() -> Dict[str, str]:
    label_map: Dict[str, str] = {}
    if not CROP_LIST_PATH.exists():
        return label_map

    with CROP_LIST_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            crop_id = str(row.get("CropID") or "").strip().upper()
            crop_name = str(row.get("Crop Name") or "").strip()
            if crop_id:
                label_map[crop_id] = crop_name or crop_id
    return label_map


def _load_crop_name_to_id_map() -> Dict[str, str]:
    crop_name_to_id: Dict[str, str] = {}
    if not CROP_LIST_PATH.exists():
        return crop_name_to_id

    with CROP_LIST_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            crop_id = str(row.get("CropID") or "").strip().upper()
            crop_name = str(row.get("Crop Name") or "").strip()
            if crop_id and crop_name:
                crop_name_to_id[_normalize_key(crop_name)] = crop_id
    return crop_name_to_id


def _to_crop_ids(crops: List[object]) -> List[str]:
    crop_name_to_id = _load_crop_name_to_id_map()
    crop_ids: List[str] = []

    for crop in crops:
        value = str(crop or "").strip()
        if not value:
            continue

        candidate_id = value.upper()
        if re.match(r"^CRP\d+$", candidate_id):
            crop_ids.append(candidate_id)
            continue

        mapped_id = crop_name_to_id.get(_normalize_key(value))
        if mapped_id:
            crop_ids.append(mapped_id)

    seen: set[str] = set()
    unique_ids: List[str] = []
    for crop_id in crop_ids:
        if crop_id in seen:
            continue
        seen.add(crop_id)
        unique_ids.append(crop_id)
    return unique_ids


def build_disease_master_map(
    disease_trigger_path: Path | str = DISEASE_TRIGGER_PATH,
) -> Dict[str, Dict[str, Any]]:
    disease_trigger_path = Path(disease_trigger_path)
    disease_map: Dict[str, Dict[str, Any]] = {}

    with disease_trigger_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            disease_id = str(row.get("DiseaseID") or "").strip().upper()
            disease_name = str(row.get("Disease") or "").strip()
            if not disease_id or not disease_name:
                continue

            disease_map[disease_id] = {
                "disease_id": disease_id,
                "disease": disease_name,
                "mf_decreases_occurrence": _extract_mf_codes(
                    row.get("MF_DecreasesOccurance", "")
                ),
            }

    return disease_map


def build_crop_high_risk_disease_map(
    crop_details_dir: Path | str = CROP_DETAILS_DIR,
) -> Dict[str, List[Dict[str, str]]]:
    crop_details_dir = Path(crop_details_dir)
    crop_disease_map: Dict[str, List[Dict[str, str]]] = {}

    for csv_path in sorted(crop_details_dir.glob("*.csv")):
        if csv_path.name.startswith("0."):
            continue

        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))

        crop_ids_row: List[str] | None = None
        disease_row: List[str] | None = None
        for row in rows:
            if not row:
                continue
            key = str(row[0]).strip()
            if key == "CropID":
                crop_ids_row = row
            elif "Mention 5 Major Diseases" in key:
                disease_row = row

        if not crop_ids_row or not disease_row:
            continue

        max_columns = min(len(crop_ids_row), len(disease_row))
        for idx in range(1, max_columns):
            crop_id = str(crop_ids_row[idx]).strip().upper()
            if not crop_id:
                continue

            for token in _split_csv_items(disease_row[idx]):
                parsed = _parse_disease_token(token)
                if not parsed:
                    continue
                if not _is_high_risk(parsed.get("severity", "")):
                    continue

                existing = crop_disease_map.setdefault(crop_id, [])
                if parsed not in existing:
                    existing.append(parsed)

    return crop_disease_map


def find_disease_mitigating_crops(
    crops: List[object],
    disease_trigger_path: Path | str = DISEASE_TRIGGER_PATH,
    crop_details_dir: Path | str = CROP_DETAILS_DIR,
    micro_features_dir: Path | str = MICRO_FEATURES_DIR,
) -> Dict[str, Any]:
    """
    Uses crop detail sheets to map selected crops to HIGH/VERY HIGH disease IDs,
    then recommends crops producing MFs that reduce occurrence of those diseases.
    """
    selected_crop_ids = _to_crop_ids(crops)
    selected_set = set(selected_crop_ids)
    crop_label_map = _load_crop_label_map()

    disease_master_map = build_disease_master_map(disease_trigger_path)
    crop_high_risk_disease_map = build_crop_high_risk_disease_map(crop_details_dir)
    produced_by_cropid = get_produced_micro_features_by_cropid(micro_features_dir)
    mf_label_map = build_mf_label_map()

    result: Dict[str, Any] = {
        "selected_crop_ids": selected_crop_ids,
        "crop_disease_mitigations": [],
    }

    for crop_id in selected_crop_ids:
        high_risk_refs = crop_high_risk_disease_map.get(crop_id, [])
        disease_entries: List[Dict[str, Any]] = []
        all_mitigating_mfs: set[str] = set()
        disease_mf_map: Dict[str, List[str]] = {}

        for ref in high_risk_refs:
            disease_id = ref.get("disease_id", "")
            severity = ref.get("severity", "")
            disease_detail = disease_master_map.get(disease_id)
            if not disease_detail:
                continue

            decreasing_mfs = disease_detail.get("mf_decreases_occurrence", [])
            all_mitigating_mfs.update(decreasing_mfs)
            disease_mf_map[disease_id] = list(decreasing_mfs)

            disease_entries.append(
                {
                    "disease_id": disease_id,
                    "disease": disease_detail["disease"],
                    "severity": severity,
                    "mitigating_mfs": annotate_mf_codes(decreasing_mfs),
                }
            )

        mitigating_crops: List[Dict[str, Any]] = []
        for producer_crop_id, produced_mfs in produced_by_cropid.items():
            if producer_crop_id in selected_set:
                continue

            relevant_mfs = sorted(set(produced_mfs) & all_mitigating_mfs)
            if not relevant_mfs:
                continue

            reasons: List[str] = []
            for mf_code in relevant_mfs:
                helped_disease_ids = [
                    disease_id for disease_id, mfs in disease_mf_map.items() if mf_code in mfs
                ]
                helped_diseases = [
                    disease_master_map[disease_id]["disease"]
                    for disease_id in helped_disease_ids
                    if disease_id in disease_master_map
                ]
                reasons.append(
                    f"Produces {mf_code} ({mf_label_map.get(mf_code, mf_code)}), which decreases occurrence of: {', '.join(helped_diseases)}"
                )

            mitigating_crops.append(
                {
                    "crop_id": producer_crop_id,
                    "crop_name": crop_label_map.get(producer_crop_id, producer_crop_id),
                    "produces_mfs": annotate_mf_codes(relevant_mfs),
                    "reasons": reasons,
                }
            )

        mitigating_crops.sort(key=lambda item: (-len(item["produces_mfs"]), item["crop_name"]))

        result["crop_disease_mitigations"].append(
            {
                "crop_id": crop_id,
                "crop_name": crop_label_map.get(crop_id, crop_id),
                "high_risk_diseases": disease_entries,
                "mfs_needed_for_mitigation": annotate_mf_codes(sorted(all_mitigating_mfs)),
                "crops_that_produce_mitigating_mfs": mitigating_crops,
            }
        )

    return result


def analyze_disease_mitigating_crops(
    crops: List[object],
    disease_trigger_path: Path | str = DISEASE_TRIGGER_PATH,
    micro_features_dir: Path | str = MICRO_FEATURES_DIR,
) -> Dict[str, Any]:
    return find_disease_mitigating_crops(
        crops,
        disease_trigger_path=disease_trigger_path,
        crop_details_dir=CROP_DETAILS_DIR,
        micro_features_dir=micro_features_dir,
    )


if __name__ == "__main__":
    sample_crop_ids = ["CRP0001", "CRP0023", "CRP0060"]
    print(json.dumps(find_disease_mitigating_crops(sample_crop_ids), indent=2))
