from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
	from rythulab.sheets.mf_labels.mf_label_extract import get_mf_label
except ModuleNotFoundError:
	import sys

	sheets_dir = Path(__file__).resolve().parent / "sheets"
	mf_labels_dir = sheets_dir / "mf_labels"
	sys.path.append(str(sheets_dir))
	sys.path.append(str(mf_labels_dir))

	from mf_label_extract import get_mf_label

try:
	from crop_micro_feature_extract import (
		get_produced_micro_features_by_cropid,
		get_required_micro_features_by_cropid,
		get_suppressed_micro_features_by_cropid,
	)
except ModuleNotFoundError:
	import sys
	sheets_dir = Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"
	sys.path.append(str(sheets_dir))
	from crop_micro_feature_extract import (
		get_produced_micro_features_by_cropid,
		get_required_micro_features_by_cropid,
		get_suppressed_micro_features_by_cropid,
	)


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_LIST_PATH = SHEETS_DIR / "crop_details" / "0.List of All crops - Sheet1.csv"
CROP_DETAILS_DIR = SHEETS_DIR / "crop_details"

# Ordinal rank for height class comparison (higher = taller)
HEIGHT_CLASS_ORDER: Dict[str, int] = {
	"EXTRA LOW": 1,
	"LOW": 2,
	"MEDIUM LOW": 3,
	"MEDIUM": 4,
	"TALL": 5,
	"VERY TALL": 6,
}
HEIGHT_CLASS_LABEL: Dict[int, str] = {v: k.title() for k, v in HEIGHT_CLASS_ORDER.items()}


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


def _load_crop_height_map() -> Dict[str, int]:
	"""Returns ordinal height class per crop ID (1=Extra Low … 6=Very Tall)."""
	height_map: Dict[str, int] = {}
	if not CROP_DETAILS_DIR.exists():
		return height_map

	for csv_path in sorted(CROP_DETAILS_DIR.glob("*.csv")):
		# Matrix sheets are transposed: first column has parameter names,
		# subsequent columns are crop values.
		with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
			rows = list(csv.reader(fh))

		if len(rows) < 2:
			continue

		cropid_row: Optional[List[str]] = None
		height_class_row: Optional[List[str]] = None

		for row in rows:
			if not row:
				continue
			first_cell = str(row[0]).strip().upper()
			if first_cell == "CROPID":
				cropid_row = row
			elif first_cell.startswith("CROP HEIGHT CLASS"):
				height_class_row = row

		if not cropid_row or not height_class_row:
			continue

		max_len = min(len(cropid_row), len(height_class_row))
		for idx in range(1, max_len):
			cid = str(cropid_row[idx]).strip().upper()
			raw_class = str(height_class_row[idx]).strip().upper()
			if not cid or not raw_class:
				continue
			ordinal = HEIGHT_CLASS_ORDER.get(raw_class)
			if ordinal is None:
				continue
			# Keep highest class seen if crop appears in multiple sheets.
			height_map[cid] = max(height_map.get(cid, ordinal), ordinal)

	return height_map


# Lazy-loaded module-level caches
_REQUIRED_MF: Optional[Dict[str, List[str]]] = None
_SUPPRESSED_MF: Optional[Dict[str, List[str]]] = None
_PRODUCED_MF: Optional[Dict[str, List[str]]] = None
_CROP_LABELS: Optional[Dict[str, str]] = None
_CROP_HEIGHTS: Optional[Dict[str, float]] = None


def _get_required_mf() -> Dict[str, List[str]]:
	global _REQUIRED_MF
	if _REQUIRED_MF is None:
		_REQUIRED_MF = get_required_micro_features_by_cropid()
	return _REQUIRED_MF


def _get_produced_mf() -> Dict[str, List[str]]:
	global _PRODUCED_MF
	if _PRODUCED_MF is None:
		_PRODUCED_MF = get_produced_micro_features_by_cropid()
	return _PRODUCED_MF


def _get_suppressed_mf() -> Dict[str, List[str]]:
	global _SUPPRESSED_MF
	if _SUPPRESSED_MF is None:
		_SUPPRESSED_MF = get_suppressed_micro_features_by_cropid()
	return _SUPPRESSED_MF


def _get_crop_labels() -> Dict[str, str]:
	global _CROP_LABELS
	if _CROP_LABELS is None:
		_CROP_LABELS = _load_crop_label_map()
	return _CROP_LABELS


def _get_crop_heights() -> Dict[str, float]:
	global _CROP_HEIGHTS
	if _CROP_HEIGHTS is None:
		_CROP_HEIGHTS = _load_crop_height_map()
	return _CROP_HEIGHTS


def _crop_label(crop_id: str) -> str:
	return _get_crop_labels().get(crop_id.upper(), crop_id)


def _crop_height(crop_id: str) -> Optional[int]:
	return _get_crop_heights().get(crop_id.upper())


def check_microfeature_conflicts(crop_ids: List[str]) -> List[Dict[str, Any]]:
	"""
	Find microfeature conflicts across selected crops (given by CropID).

	Rule: If crop A requires MF X and crop B suppresses MF X, flag conflict.

	Returns list of conflict dicts:
	  {
	    crop_requiring_id, crop_requiring_label,
	    crop_suppressing_id, crop_suppressing_label,
	    mf_code, mf_label,
	    conflict_type,
	    message
	  }
	"""
	# Deduplicate and normalize crop IDs
	seen: set = set()
	unique_ids: List[str] = []
	for cid in crop_ids:
		cid_upper = cid.strip().upper()
		if cid_upper and cid_upper not in seen:
			seen.add(cid_upper)
			unique_ids.append(cid_upper)

	if len(unique_ids) < 2:
		return []

	required_mfs = _get_required_mf()
	produced_mfs = _get_produced_mf()
	suppressed_mfs = _get_suppressed_mf()
	crop_labels = _get_crop_labels()
	crop_heights = _get_crop_heights()
	conflicts: List[Dict[str, Any]] = []

	# Map MF code -> list of (crop_id, "requires"/"suppresses")
	mf_to_crops: Dict[str, List[tuple]] = {}

	for crop_id in unique_ids:
		for mf_code in (required_mfs.get(crop_id) or []):
			mf_to_crops.setdefault(mf_code, []).append((crop_id, "requires"))
		for mf_code in (suppressed_mfs.get(crop_id) or []):
			mf_to_crops.setdefault(mf_code, []).append((crop_id, "suppresses"))

	# Find conflicts: required ∩ suppressed
	for mf_code, crop_list in mf_to_crops.items():
		requiring_crops = [cid for cid, action in crop_list if action == "requires"]
		suppressing_crops = [cid for cid, action in crop_list if action == "suppresses"]

		if requiring_crops and suppressing_crops:
			# Conflict detected
			for req_cid in requiring_crops:
				for supp_cid in suppressing_crops:
					if req_cid == supp_cid:
						continue
					mf_label = get_mf_label(mf_code)
					message = (
						f"{crop_labels.get(req_cid, req_cid)} requires {mf_label or 'unknown'}, but "
						f"{crop_labels.get(supp_cid, supp_cid)} suppresses this same MF. "
						f"Required MF ∩ Suppress MF is not empty — conflict between "
						f"{crop_labels.get(req_cid, req_cid)} (requires) and "
						f"{crop_labels.get(supp_cid, supp_cid)} (suppresses). "
						f"Note the warning with reason."
					)

					conflicts.append({
						"crop_requiring_id": req_cid,
						"crop_requiring_label": crop_labels.get(req_cid, req_cid),
						"crop_suppressing_id": supp_cid,
						"crop_suppressing_label": crop_labels.get(supp_cid, supp_cid),
						"mf_code": mf_code,
						"mf_label": mf_label,
						"conflict_type": "mf_require_vs_suppress",
						"message": message,
					})

	# Height-directional shade/light conflict:
	# if crop X(height) > crop Y(height), and X has MF2 while Y has MF3,
	# then X can cast dense shade on Y that requires light exposure.
	for crop_x in unique_ids:
		height_x = crop_heights.get(crop_x)
		if height_x is None:
			continue

		for crop_y in unique_ids:
			if crop_x == crop_y:
				continue

			height_y = crop_heights.get(crop_y)
			if height_y is None or height_x <= height_y:
				continue

			x_produced = set(produced_mfs.get(crop_x) or [])
			y_required = set(required_mfs.get(crop_y) or [])

			x_has_mf2_dense_shade = "MF2" in x_produced
			y_has_mf3_light_exposure = any(code.startswith("MF3") for code in y_required)

			if x_has_mf2_dense_shade and y_has_mf3_light_exposure:
				x_class = HEIGHT_CLASS_LABEL.get(height_x, str(height_x))
				y_class = HEIGHT_CLASS_LABEL.get(height_y, str(height_y))
				message = (
					f"{crop_labels.get(crop_x, crop_x)} (height class: {x_class}) is taller than "
					f"{crop_labels.get(crop_y, crop_y)} (height class: {y_class}). "
					f"{crop_labels.get(crop_x, crop_x)} has MF2 (dense shade) while "
					f"{crop_labels.get(crop_y, crop_y)} has MF3 (light exposure). "
					"This creates a shade-light conflict."
				)

				conflicts.append({
					"crop_requiring_id": crop_y,
					"crop_requiring_label": crop_labels.get(crop_y, crop_y),
					"crop_suppressing_id": crop_x,
					"crop_suppressing_label": crop_labels.get(crop_x, crop_x),
					"mf_code": "MF2-MF3",
					"mf_label": "Dense shade vs light exposure",
					"conflict_type": "height_shade_light",
					"message": message,
				})

	return conflicts


if __name__ == "__main__":
	import json

	# Test: Paddy (CRP0001) requires MF8, MF9; suppresses MF3G, MF10, MF13, MF15
	# Maize (CRP0002) produces MF1, MF2, MF3U, MF11, MF12, MF14, etc.
	# Additional directional height test: non-canopy taller crop vs shorter crop
	# Silver Oak (CRP0103, Sub-Canopy) vs Vitex (CRP0107, Pioneer)
	# Should show conflicts if any Requires/Suppresses overlap and/or MF2-MF3 height rule is met
	sample_crop_ids = ["CRP0103", "CRP0107", "CRP0001", "CRP0002"]

	results = check_microfeature_conflicts(sample_crop_ids)
	print(json.dumps(results, indent=2))
	print(f"\nTotal conflicts: {len(results)}")
