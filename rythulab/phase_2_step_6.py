from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List

try:
	from crop_micro_feature_extract import get_produced_micro_features_by_cropid
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
	from crop_micro_feature_extract import get_produced_micro_features_by_cropid

try:
	from rythulab.sheets.mf_labels.mf_label_extract import build_mf_label_map
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "mf_labels"))
	from mf_label_extract import build_mf_label_map

try:
	from rythulab.phase_1_step_1 import load_step1_results
except ModuleNotFoundError:
	from phase_1_step_1 import load_step1_results


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
PESTS_DIR = SHEETS_DIR / "Pests"
ZONE_CHARACTERISTICS_PATH = PESTS_DIR / "crop suitability sheets - zone characteristics.csv"
PEST_TRIGGERS_PATH = PESTS_DIR / "AP_Disease_CF_MF_Triggers_filled - AP_Pest_CF_MF_Triggers.csv"
MICRO_FEATURES_DIR = SHEETS_DIR / "Crop Micro Features"

PEST_ID_RE = re.compile(r"PEST\d+", re.IGNORECASE)
MF_CODE_RE = re.compile(r"MF\d+[A-Z]*", re.IGNORECASE)
STEP6_PRIORITY_MF_CODES = {"MF19", "MF20"}

# Step 1 zone labels -> Pests zone labels
STEP1_TO_PESTS_ZONE_MAP = {
	"north coastal": "North Coastal Zone",
	"north coastal zone": "North Coastal Zone",
	"godavari": "Godavari Delta Zone",
	"godavari delta": "Godavari Delta Zone",
	"godavari delta zone": "Godavari Delta Zone",
	"krishna": "Krishna Zone",
	"krishna zone": "Krishna Zone",
	"southern": "Southern Zone",
	"southern zone": "Southern Zone",
	"scarce rainfall": "Scarce Rainfall Zone (Rayalaseema)",
	"scarce rainfall zone": "Scarce Rainfall Zone (Rayalaseema)",
	"rayalaseema": "Scarce Rainfall Zone (Rayalaseema)",
	"scarce rainfall zone (rayalaseema)": "Scarce Rainfall Zone (Rayalaseema)",
	"high altitude and tribal areas": "High Altitude / Tribal Areas",
	"high altitude & tribal": "High Altitude / Tribal Areas"
}


def _normalize_text(value: str) -> str:
	return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _resolve_pests_zone_name(zone: str) -> str:
	normalized_zone = _normalize_text(zone)
	if not normalized_zone:
		return str(zone or "").strip()

	mapped = STEP1_TO_PESTS_ZONE_MAP.get(normalized_zone)
	if mapped:
		return mapped

	if normalized_zone.endswith(" zone"):
		base_zone = normalized_zone[: -len(" zone")].strip()
		mapped = STEP1_TO_PESTS_ZONE_MAP.get(base_zone)
		if mapped:
			return mapped

	return str(zone or "").strip()


def _extract_mf_codes(text: str) -> List[str]:
	raw = str(text or "").upper()

	raw = re.sub(r"MF(\d+[A-Z]*)/(\d+[A-Z]*)", r"MF\1, MF\2", raw)
	raw = re.sub(r"MF(\d+)([A-Z])/([A-Z])", r"MF\1\2, MF\1\3", raw)

	found = MF_CODE_RE.findall(raw)
	seen = set()
	ordered = []
	for code in found:
		normalized = code.strip().upper()
		if normalized and normalized not in seen:
			seen.add(normalized)
			ordered.append(normalized)
	return ordered


def _parse_zone_pest_tokens(raw_value: str) -> List[str]:
	text = str(raw_value or "")
	pest_ids = [token.strip().upper() for token in PEST_ID_RE.findall(text)]
	if pest_ids:
		return pest_ids
	return [token.strip() for token in text.split(",") if token.strip()]


def _load_zone_row(zone: str, zone_characteristics_path: Path | str = ZONE_CHARACTERISTICS_PATH) -> Dict[str, str]:
	zone_characteristics_path = Path(zone_characteristics_path)
	resolved_zone_name = _resolve_pests_zone_name(zone)
	target = _normalize_text(resolved_zone_name)

	with zone_characteristics_path.open(newline="", encoding="utf-8-sig") as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			if _normalize_text(row.get("Agro-climatic zone", "")) == target:
				return row

	raise ValueError(
		f"Zone '{zone}' (resolved as '{resolved_zone_name}') not found in {zone_characteristics_path.name}"
	)


def _load_pest_maps(pest_triggers_path: Path | str = PEST_TRIGGERS_PATH):
	pest_triggers_path = Path(pest_triggers_path)
	by_id: Dict[str, Dict[str, str]] = {}
	name_to_id: Dict[str, str] = {}

	with pest_triggers_path.open(newline="", encoding="utf-8-sig") as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			pest_id = str(row.get("PestID") or "").strip().upper()
			pest_name = str(row.get("Pest") or "").strip()
			if not pest_name:
				continue

			if pest_id:
				by_id[pest_id] = row
			normalized_name = _normalize_text(pest_name)
			if normalized_name and normalized_name not in name_to_id and pest_id:
				name_to_id[normalized_name] = pest_id

	return by_id, name_to_id


def find_zone_pest_mitigating_crops(
	agro_climatic_zone: str,
	zone_characteristics_path: Path | str = ZONE_CHARACTERISTICS_PATH,
	pest_triggers_path: Path | str = PEST_TRIGGERS_PATH,
	micro_features_dir: Path | str = MICRO_FEATURES_DIR,
):
	zone_row = _load_zone_row(agro_climatic_zone, zone_characteristics_path)
	pest_tokens = _parse_zone_pest_tokens(zone_row.get("Common insect pests", ""))

	pest_by_id, pest_name_to_id = _load_pest_maps(pest_triggers_path)
	mf_label_map = build_mf_label_map()
	step1_scores = load_step1_results()

	zone_pests = []
	mf_to_pests: Dict[str, set[str]] = {}
	pest_id_to_label: Dict[str, str] = {}

	for token in pest_tokens:
		pest_id = token.upper() if token.upper().startswith("PEST") else pest_name_to_id.get(_normalize_text(token))
		if not pest_id:
			continue

		pest_row = pest_by_id.get(pest_id)
		if not pest_row:
			continue

		pest_name = str(pest_row.get("Pest") or pest_id).strip()
		reducing_mfs = _extract_mf_codes(pest_row.get("MF Produced → Reduces Risk (-)", ""))

		zone_pests.append(
			{
				"pest_id": pest_id,
				"pest_name": pest_name,
				"mitigating_mf_codes": reducing_mfs,
			}
		)
		pest_id_to_label[pest_id] = pest_name

		for mf_code in reducing_mfs:
			mf_to_pests.setdefault(mf_code, set()).add(pest_id)

	all_mitigating_mfs = sorted(mf_to_pests.keys())
	produced_by_crop = get_produced_micro_features_by_cropid(micro_features_dir)

	cropid_to_name = {}
	try:
		from rythulab.sheets.extraction_utils import get_cropid_to_name_map

		cropid_to_name = get_cropid_to_name_map()
	except Exception:
		cropid_to_name = {}

	recommended_crops = []
	for crop_id, produced_mfs in (produced_by_crop or {}).items():
		if step1_scores and crop_id not in step1_scores:
			continue
		produced_set = set(produced_mfs or [])
		overlap = sorted(produced_set & set(all_mitigating_mfs))
		priority_overlap = sorted(produced_set & STEP6_PRIORITY_MF_CODES)
		recommended_mf_codes = sorted(set(overlap + priority_overlap))
		if not recommended_mf_codes:
			continue

		supported_pests = sorted({pest_id for mf in overlap for pest_id in mf_to_pests.get(mf, set())})
		recommended_crops.append(
			{
				"crop_id": crop_id,
				"crop_name": cropid_to_name.get(crop_id, crop_id),
				"step1_score": step1_scores.get(crop_id),
				"produced_mitigating_mfs": [
					{"mf_code": mf_code, "mf_label": mf_label_map.get(mf_code, mf_code)} for mf_code in recommended_mf_codes
				],
				"priority_mf_codes": priority_overlap,
				"supports_pest_ids": supported_pests,
				"supports_pest_labels": [pest_id_to_label.get(pest_id, pest_id) for pest_id in supported_pests],
			}
		)

	recommended_crops.sort(
		key=lambda item: (
			-len(item.get("produced_mitigating_mfs", [])),
			-len(item.get("supports_pest_ids", [])),
			item.get("crop_id", ""),
		)
	)

	return {
		"agro_climatic_zone": zone_row.get("Agro-climatic zone", agro_climatic_zone),
		"common_pests": zone_pests,
		"mitigating_mfs": [
			{
				"mf_code": mf_code,
				"mf_label": mf_label_map.get(mf_code, mf_code),
				"mitigates_pest_ids": sorted(mf_to_pests.get(mf_code, set())),
				"mitigates_pest_labels": [
					pest_id_to_label.get(pest_id, pest_id) for pest_id in sorted(mf_to_pests.get(mf_code, set()))
				],
			}
			for mf_code in all_mitigating_mfs
		],
		"recommended_crops": recommended_crops,
	}


if __name__ == "__main__":
	sample_zone = "North Coastal Zone"
	print(json.dumps(find_zone_pest_mitigating_crops(sample_zone), indent=2))
