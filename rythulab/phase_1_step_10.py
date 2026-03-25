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
		get_required_micro_features_by_cropid,
		get_suppressed_micro_features_by_cropid,
	)
except ModuleNotFoundError:
	import sys
	sheets_dir = Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"
	sys.path.append(str(sheets_dir))
	from crop_micro_feature_extract import (
		get_required_micro_features_by_cropid,
		get_suppressed_micro_features_by_cropid,
	)


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_LIST_PATH = SHEETS_DIR / "crop_details" / "0.List of All crops - Sheet1.csv"


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


# Lazy-loaded module-level caches
_REQUIRED_MF: Optional[Dict[str, List[str]]] = None
_SUPPRESSED_MF: Optional[Dict[str, List[str]]] = None
_CROP_LABELS: Optional[Dict[str, str]] = None


def _get_required_mf() -> Dict[str, List[str]]:
	global _REQUIRED_MF
	if _REQUIRED_MF is None:
		_REQUIRED_MF = get_required_micro_features_by_cropid()
	return _REQUIRED_MF


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


def _crop_label(crop_id: str) -> str:
	return _get_crop_labels().get(crop_id.upper(), crop_id)


def check_microfeature_conflicts(crop_ids: List[str]) -> List[Dict[str, Any]]:
	"""
	Find microfeature conflicts across selected crops (given by CropID).

	Rule: If crop A requires MF X and crop B suppresses MF X, flag conflict.

	Returns list of conflict dicts:
	  {
	    crop_requiring_id, crop_requiring_label,
	    crop_suppressing_id, crop_suppressing_label,
	    mf_code, mf_label,
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
	suppressed_mfs = _get_suppressed_mf()
	crop_labels = _get_crop_labels()
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
						"message": message,
					})

	return conflicts


if __name__ == "__main__":
	import json

	# Test: Paddy (CRP0001) requires MF8, MF9; suppresses MF3G, MF10, MF13, MF15
	# Maize (CRP0002) produces MF1, MF2, MF3U, MF11, MF12, MF14, etc.
	# Should show conflicts if any Requires/Suppresses overlap
	sample_crop_ids = ["CRP0001", "CRP0002", "CRP0003"]

	results = check_microfeature_conflicts(sample_crop_ids)
	print(json.dumps(results, indent=2))
	print(f"\nTotal conflicts: {len(results)}")
