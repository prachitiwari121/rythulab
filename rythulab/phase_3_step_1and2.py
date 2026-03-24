from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"
CROP_LIST_PATH = CROP_DETAILS_DIR / "0.List of All crops - Sheet1.csv"

EXCLUDED_SUBCATEGORIES = {"canopy trees"}


def _n(value: Any) -> str:
	return str(value or "").strip().lower()


def _normalize_crop_id(crop_id: Any) -> str:
	return str(crop_id or "").strip().upper()


def _dedupe_keep_order(values: List[str]) -> List[str]:
	seen: Set[str] = set()
	out: List[str] = []
	for value in values:
		if value in seen:
			continue
		seen.add(value)
		out.append(value)
	return out


def _find_attr_key(param: str) -> Optional[str]:
	key = _n(param)
	if not key:
		return None

	if "crop family name" in key:
		return "family"

	if "crop functional group" in key:
		return "functional_group"

	if "canopy layer class" in key:
		return "canopy_layer_class"

	# Most current matrices use Crop Height Class instead of explicit canopy layer class.
	if "crop height class" in key:
		return "canopy_layer_class"

	if "root depth class" in key:
		return "root_depth_class"

	return None


def _load_crop_list_metadata() -> Dict[str, Dict[str, str]]:
	out: Dict[str, Dict[str, str]] = {}
	if not CROP_LIST_PATH.exists():
		return out

	with CROP_LIST_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
		reader = csv.DictReader(fh)
		for row in reader:
			crop_id = _normalize_crop_id(row.get("CropID"))
			if not crop_id:
				continue

			out[crop_id] = {
				"crop_id": crop_id,
				"crop_name": str(row.get("Crop Name") or "").strip(),
				"sub_category": str(row.get("Sub-Category") or "").strip(),
			}
	return out


def _parse_crop_matrix(path: Path, out: Dict[str, Dict[str, str]]) -> None:
	with path.open("r", encoding="utf-8-sig", newline="") as fh:
		rows = list(csv.reader(fh))

	if not rows:
		return

	cropid_row: Optional[List[str]] = None
	for row in rows:
		if row and _n(row[0]) == "cropid":
			cropid_row = row
			break

	if cropid_row is None:
		return

	col_to_crop_id: Dict[int, str] = {}
	for col_index, raw in enumerate(cropid_row[1:], start=1):
		crop_id = _normalize_crop_id(raw)
		if crop_id:
			col_to_crop_id[col_index] = crop_id

	if not col_to_crop_id:
		return

	for row in rows:
		if not row:
			continue

		attr_key = _find_attr_key(row[0])
		if attr_key is None:
			continue

		for col_index, crop_id in col_to_crop_id.items():
			if col_index >= len(row):
				continue
			value = str(row[col_index] or "").strip()
			if not value:
				continue
			out.setdefault(crop_id, {})[attr_key] = value


def _load_crop_attributes() -> Dict[str, Dict[str, str]]:
	out: Dict[str, Dict[str, str]] = {}
	for csv_path in sorted(CROP_DETAILS_DIR.glob("*.csv")):
		if csv_path.name.startswith("0."):
			continue
		try:
			_parse_crop_matrix(csv_path, out)
		except Exception:
			continue
	return out


def _build_crop_catalog() -> Dict[str, Dict[str, str]]:
	base_meta = _load_crop_list_metadata()
	attrs = _load_crop_attributes()

	catalog: Dict[str, Dict[str, str]] = {}
	all_ids = set(base_meta.keys()) | set(attrs.keys())
	for crop_id in sorted(all_ids):
		combined = {
			"crop_id": crop_id,
			"crop_name": "",
			"sub_category": "",
			"functional_group": "",
			"family": "",
			"canopy_layer_class": "",
			"root_depth_class": "",
		}
		combined.update(base_meta.get(crop_id, {}))
		combined.update(attrs.get(crop_id, {}))
		catalog[crop_id] = combined

	return catalog


def _should_include_in_universe(crop: Dict[str, str]) -> bool:
	sub_category = _n(crop.get("sub_category"))
	return sub_category not in EXCLUDED_SUBCATEGORIES


def _get_dimension_values(
	catalog: Dict[str, Dict[str, str]],
	key: str,
	selected_ids: Optional[Set[str]] = None,
) -> List[str]:
	values: List[str] = []
	for crop_id, crop in catalog.items():
		if not _should_include_in_universe(crop):
			continue
		if selected_ids is not None and crop_id not in selected_ids:
			continue
		value = str(crop.get(key) or "").strip()
		if value:
			values.append(value)

	return sorted(set(values), key=lambda v: v.lower())


def analyze_biodiversity_coverage(crop_ids: List[str]) -> Dict[str, Any]:
	"""
	Step 1.
	Given selected crop IDs, return covered and not-covered values for:
	  - functional group
	  - family
	  - canopy layer class
	  - root depth class
	"""
	catalog = _build_crop_catalog()

	normalized_ids = _dedupe_keep_order([
		_normalize_crop_id(crop_id) for crop_id in (crop_ids or []) if _normalize_crop_id(crop_id)
	])
	selected_set = set(normalized_ids)

	known_ids = [crop_id for crop_id in normalized_ids if crop_id in catalog]
	unknown_ids = [crop_id for crop_id in normalized_ids if crop_id not in catalog]

	dimensions = [
		("functional_group", "Functional Group"),
		("family", "Family"),
		("canopy_layer_class", "Canopy Layer Class"),
		("root_depth_class", "Root Depth Class"),
	]

	coverage: Dict[str, Dict[str, Any]] = {}
	for key, label in dimensions:
		all_values = _get_dimension_values(catalog, key)
		covered = _get_dimension_values(catalog, key, selected_set)
		missing = [value for value in all_values if value not in set(covered)]
		coverage[key] = {
			"label": label,
			"all_values": all_values,
			"covered": covered,
			"not_covered": missing,
		}

	selected_crops = [
		{
			"crop_id": crop_id,
			"crop_name": catalog[crop_id].get("crop_name") or crop_id,
			"sub_category": catalog[crop_id].get("sub_category") or "",
			"functional_group": catalog[crop_id].get("functional_group") or "",
			"family": catalog[crop_id].get("family") or "",
			"canopy_layer_class": catalog[crop_id].get("canopy_layer_class") or "",
			"root_depth_class": catalog[crop_id].get("root_depth_class") or "",
		}
		for crop_id in known_ids
	]

	return {
		"selected_crop_ids": normalized_ids,
		"known_crop_ids": known_ids,
		"unknown_crop_ids": unknown_ids,
		"selected_crops": selected_crops,
		"coverage": coverage,
	}


def recommend_crops_for_biodiversity_gaps(crop_ids: List[str]) -> Dict[str, Any]:
	"""
	Step 2.
	Based on Step 1 gaps, return crops that fill those gaps.
	"""
	coverage_result = analyze_biodiversity_coverage(crop_ids)
	catalog = _build_crop_catalog()

	selected_ids = set(coverage_result["known_crop_ids"])
	coverage = coverage_result["coverage"]

	missing_values = {
		"functional_group": set(coverage["functional_group"]["not_covered"]),
		"family": set(coverage["family"]["not_covered"]),
		"canopy_layer_class": set(coverage["canopy_layer_class"]["not_covered"]),
		"root_depth_class": set(coverage["root_depth_class"]["not_covered"]),
	}

	recommendations: List[Dict[str, Any]] = []

	for crop_id, crop in catalog.items():
		if crop_id in selected_ids:
			continue
		if not _should_include_in_universe(crop):
			continue

		fills = {
			"functional_group": [],
			"family": [],
			"canopy_layer_class": [],
			"root_depth_class": [],
		}

		for key in fills:
			value = str(crop.get(key) or "").strip()
			if value and value in missing_values[key]:
				fills[key].append(value)

		score = sum(len(values) for values in fills.values())
		if score == 0:
			continue

		reasons: List[str] = []
		if fills["functional_group"]:
			reasons.extend([f"Fills functional group gap: {value}" for value in fills["functional_group"]])
		if fills["family"]:
			reasons.extend([f"Fills family gap: {value}" for value in fills["family"]])
		if fills["canopy_layer_class"]:
			reasons.extend([f"Fills canopy layer gap: {value}" for value in fills["canopy_layer_class"]])
		if fills["root_depth_class"]:
			reasons.extend([f"Fills root depth gap: {value}" for value in fills["root_depth_class"]])

		recommendations.append(
			{
				"crop_id": crop_id,
				"crop_name": crop.get("crop_name") or crop_id,
				"sub_category": crop.get("sub_category") or "",
				"fills": fills,
				"reasons": reasons,
				"gap_fill_score": score,
			}
		)

	recommendations.sort(
		key=lambda item: (
			-item["gap_fill_score"],
			item["crop_name"].lower(),
			item["crop_id"],
		)
	)

	return {
		"coverage": coverage_result,
		"gap_summary": {
			"functional_group_not_covered": coverage["functional_group"]["not_covered"],
			"family_not_covered": coverage["family"]["not_covered"],
			"canopy_layer_class_not_covered": coverage["canopy_layer_class"]["not_covered"],
			"root_depth_class_not_covered": coverage["root_depth_class"]["not_covered"],
		},
		"recommended_crops": recommendations,
	}


def analyze_and_recommend_biodiversity(crop_ids: List[str]) -> Dict[str, Any]:
	"""
	Convenience wrapper returning both steps in one response payload.
	"""
	return {
		"step1_coverage": analyze_biodiversity_coverage(crop_ids),
		"step2_gap_filling_crops": recommend_crops_for_biodiversity_gaps(crop_ids),
	}


if __name__ == "__main__":
	import json

	sample_crop_ids = ["CRP0001", "CRP0015", "CRP0029"]
	print(json.dumps(analyze_and_recommend_biodiversity(sample_crop_ids), indent=2))
