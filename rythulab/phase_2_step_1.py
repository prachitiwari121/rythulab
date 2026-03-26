from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
	from rythulab.sheets.mf_labels.mf_label_extract import get_mf_label
except ModuleNotFoundError:
	import sys

	sheets_dir = Path(__file__).resolve().parent / "sheets"
	sys.path.append(str(sheets_dir / "mf_labels"))
	from mf_label_extract import get_mf_label

try:
	from crop_micro_feature_extract import (
		get_produced_micro_features_by_cropid,
		get_required_micro_features_by_cropid,
	)
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
	from crop_micro_feature_extract import (
		get_produced_micro_features_by_cropid,
		get_required_micro_features_by_cropid,
	)


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_LIST_PATH = SHEETS_DIR / "crop_details" / "0.List of All crops - Sheet1.csv"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"


def _sorted_unique(values: List[str]) -> List[str]:
	return sorted(set(values))


def _load_crop_label_map() -> Dict[str, str]:
	label_map: Dict[str, str] = {}
	if not CROP_LIST_PATH.exists():
		return label_map
	with CROP_LIST_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
		reader = csv.DictReader(fh)
		for row in reader:
			cid = str(row.get("CropID") or "").strip().upper()
			name = str(row.get("Crop Name") or "").strip()
			if cid:
				label_map[cid] = name
	return label_map


def _load_crop_height_map() -> Dict[str, float]:
	height_map: Dict[str, float] = {}
	if not CROP_DETAILS_DIR.exists():
		return height_map

	for csv_path in sorted(CROP_DETAILS_DIR.glob("*.csv")):
		with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
			rows = list(csv.reader(fh))

		if len(rows) < 2:
			continue

		cropid_row = None
		height_row = None

		for row in rows:
			if not row:
				continue
			first_cell = str(row[0]).strip().upper()
			if first_cell == "CROPID":
				cropid_row = row
			elif first_cell == "CROP HEIGHT METERS (VALUE)":
				height_row = row

		if not cropid_row or not height_row:
			continue

		max_len = min(len(cropid_row), len(height_row))
		for idx in range(1, max_len):
			cid = str(cropid_row[idx]).strip().upper()
			raw_height = str(height_row[idx]).strip()
			if not cid or not raw_height:
				continue

			numbers = [float(m) for m in re.findall(r"\d+(?:\.\d+)?", raw_height)]
			if not numbers:
				continue

			numeric_height = sum(numbers[:2]) / 2 if len(numbers) >= 2 else numbers[0]
			height_map[cid] = max(height_map.get(cid, numeric_height), numeric_height)

	return height_map


_CROP_HEIGHTS: Optional[Dict[str, float]] = None


def _get_crop_heights() -> Dict[str, float]:
	global _CROP_HEIGHTS
	if _CROP_HEIGHTS is None:
		_CROP_HEIGHTS = _load_crop_height_map()
	return _CROP_HEIGHTS


def find_missing_mfs_and_producers(crop_ids: List[str]) -> Dict[str, Any]:
	"""
	Given a list of crop IDs (main crops), compute:
	  - Required MFs: union of all "Requires" MF lists across selected crops
	  - Produced/Available MFs: union of all "Produces" MF lists across selected crops
	  - Missing MFs: Required − Produced (not covered by any selected crop)
	  - For each missing MF: which OTHER crops in the database produce it

	Returns a dict with:
	  selected_crop_ids, required_mfs, available_mfs, missing_mfs,
	  missing_mf_details, recommended_crops
	"""
	selected_ids = [str(cid).strip().upper() for cid in crop_ids if str(cid).strip()]
	selected_set = set(selected_ids)

	crop_label_map = _load_crop_label_map()
	produced_by_cropid = get_produced_micro_features_by_cropid()
	required_by_cropid = get_required_micro_features_by_cropid()
	crop_heights = _get_crop_heights()

	# Aggregate required and available MFs across all selected crops
	required_mfs: set = set()
	available_mfs: set = set()
	required_by_mf: Dict[str, List[str]] = {}  # mf_code -> [reason strings]

	for crop_id in selected_ids:
		crop_name = crop_label_map.get(crop_id, crop_id)

		for mf_code in (required_by_cropid.get(crop_id) or []):
			required_mfs.add(mf_code)
			mf_label = get_mf_label(mf_code) or mf_code
			required_by_mf.setdefault(mf_code, []).append(f"{crop_name} requires {mf_label}")

		for mf_code in (produced_by_cropid.get(crop_id) or []):
			available_mfs.add(mf_code)

	missing_mfs = _sorted_unique(required_mfs - available_mfs)

	# For each missing MF, find which crops (outside selection) produce it
	producers_by_mf: Dict[str, List[Dict]] = {}
	recommended: Dict[str, Dict] = {}  # crop_id -> recommendation entry

	for mf_code in missing_mfs:
		producers: List[Dict] = []

		for candidate_id, produced_mfs in produced_by_cropid.items():
			if candidate_id in selected_set:
				continue
			if mf_code not in produced_mfs:
				continue

			candidate_name = crop_label_map.get(candidate_id, candidate_id)
			producers.append({"crop_id": candidate_id, "crop_name": candidate_name})

			rec = recommended.setdefault(
				candidate_id,
				{
					"crop_id": candidate_id,
					"crop_name": candidate_name,
					"covers_missing_mfs": [],
					"reasons": [],
				},
			)
			mf_label = get_mf_label(mf_code)
			rec["covers_missing_mfs"].append(mf_code)
			rec["reasons"].append(
				f"Produces missing MF ({mf_label or 'unknown'})"
			)

		producers_by_mf[mf_code] = {
			"mf_code": mf_code,
			"mf_label": get_mf_label(mf_code),
			"required_by_reasons": sorted(required_by_mf.get(mf_code, [])),
			"producer_crops": producers,
		}

	# Height-based MF4 recommendation:
	# If crop X requires MF1 or MF2, recommend crop Y where height(Y) > height(X) and Y produces MF4
	for crop_x in selected_ids:
		x_required = set(required_by_cropid.get(crop_x) or [])
		mf1_or_mf2_present = {"MF1", "MF2"} & x_required
		if not mf1_or_mf2_present:
			continue

		height_x = crop_heights.get(crop_x)
		crop_x_name = crop_label_map.get(crop_x, crop_x)

		for candidate_id, candidate_produced in produced_by_cropid.items():
			if candidate_id in selected_set:
				continue
			if "MF4" not in candidate_produced:
				continue

			height_y = crop_heights.get(candidate_id)
			if height_y is None or height_x is None or height_y <= height_x:
				continue

			candidate_name = crop_label_map.get(candidate_id, candidate_id)
			mf_codes = sorted(mf1_or_mf2_present)
			reason = (
				f"{crop_x_name} requires {', '.join(mf_codes)} — "
				f"{candidate_name} is taller ({height_y}m) and produces MF4"
			)

			rec = recommended.setdefault(
				candidate_id,
				{
					"crop_id": candidate_id,
					"crop_name": candidate_name,
					"covers_missing_mfs": [],
					"reasons": [],
				},
			)
			if "MF4" not in rec["covers_missing_mfs"]:
				rec["covers_missing_mfs"].append("MF4")
			if reason not in rec["reasons"]:
				rec["reasons"].append(reason)

	# Deduplicate and sort recommended crops by coverage count
	recommended_list = []
	for rec in recommended.values():
		covered = _sorted_unique(rec["covers_missing_mfs"])
		rec["covers_missing_mfs"] = covered
		rec["reasons"] = [
			f"Produces ({get_mf_label(mf) or 'unknown'})" for mf in covered
		]
		recommended_list.append(rec)

	recommended_list.sort(key=lambda r: (-len(r["covers_missing_mfs"]), r["crop_name"]))

	return {
		"selected_crop_ids": selected_ids,
		"required_mfs": _sorted_unique(required_mfs),
		"available_mfs": _sorted_unique(available_mfs),
		"missing_mfs": missing_mfs,
		"missing_mf_details": [producers_by_mf[mf] for mf in missing_mfs],
		"recommended_crops": recommended_list,
	}


if __name__ == "__main__":
	import json

	# --- Original MF-gap test ---
	print("=== Test 1: MF gap (Cereals) ===")
	sample_crop_ids = ["CRP0001", "CRP0002", "CRP0003"]
	result = find_missing_mfs_and_producers(sample_crop_ids)
	print(json.dumps(result, indent=2))
	print(f"\nMissing MFs: {result['missing_mfs']}")
	print(f"Recommended crops: {len(result['recommended_crops'])}")

	# --- Height-based MF4 recommendation test ---
	# Ginger (CRP0032) requires MF1 and is short (~0.8 m).
	# Taller crops that produce MF4 (e.g. Teak CRP0097, Silver Oak CRP0103)
	# should appear in recommended_crops via the height-MF4 rule.
	print("\n=== Test 2: Height-based MF4 recommendation (Ginger + Turmeric) ===")
	height_mf4_sample = ["CRP0032", "CRP0031"]
	result2 = find_missing_mfs_and_producers(height_mf4_sample)
	print(json.dumps(result2, indent=2))
	print(f"\nMissing MFs: {result2['missing_mfs']}")
	print(f"Recommended crops (total): {len(result2['recommended_crops'])}")

	height_mf4_recs = [
		r for r in result2["recommended_crops"]
		if any("MF4" in reason or "taller" in reason for reason in r.get("reasons", []))
	]
	print(f"Height-MF4 triggered recommendations: {len(height_mf4_recs)}")
	for r in height_mf4_recs:
		print(f"  {r['crop_name']} ({r['crop_id']}): {r['reasons']}")

