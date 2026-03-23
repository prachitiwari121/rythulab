from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Set

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
		get_suppressed_micro_features_by_cropid,
	)
except ModuleNotFoundError:
	import sys

	sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
	from crop_micro_feature_extract import (
		get_produced_micro_features_by_cropid,
		get_required_micro_features_by_cropid,
		get_suppressed_micro_features_by_cropid,
	)


BASE_DIR = Path(__file__).resolve().parent
SHEETS_DIR = BASE_DIR / "sheets"
CROP_LIST_PATH = SHEETS_DIR / "crop_details" / "0.List of All crops - Sheet1.csv"


def _sorted_unique(values: Set[str] | List[str]) -> List[str]:
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


def find_cross_compatible_associate_crops(crop_ids: List[str]) -> Dict[str, Any]:
	"""
	Given selected main crop IDs, find associate crops that:
	1) Have at least one required MF satisfied by selected crops' produced MFs
	2) Do not introduce required-vs-suppressed MF conflicts with the selected system
	"""
	selected_ids = [str(cid).strip().upper() for cid in crop_ids if str(cid).strip()]
	selected_set = set(selected_ids)

	crop_label_map = _load_crop_label_map()
	produced_by_cropid = get_produced_micro_features_by_cropid()
	required_by_cropid = get_required_micro_features_by_cropid()
	suppressed_by_cropid = get_suppressed_micro_features_by_cropid()

	selected_produced_mfs: Set[str] = set()
	selected_required_mfs: Set[str] = set()
	selected_suppressed_mfs: Set[str] = set()

	for crop_id in selected_ids:
		selected_produced_mfs.update(produced_by_cropid.get(crop_id, []))
		selected_required_mfs.update(required_by_cropid.get(crop_id, []))
		selected_suppressed_mfs.update(suppressed_by_cropid.get(crop_id, []))

	candidate_ids = set(produced_by_cropid.keys()) | set(required_by_cropid.keys())
	associated_crops: List[Dict[str, Any]] = []

	for candidate_id in candidate_ids:
		if candidate_id in selected_set:
			continue

		candidate_required_mfs = set(required_by_cropid.get(candidate_id, []))
		candidate_suppressed_mfs = set(suppressed_by_cropid.get(candidate_id, []))
		candidate_produced_mfs = set(produced_by_cropid.get(candidate_id, []))

		# Only reject conflicts introduced by candidate, not pre-existing conflicts among selected crops.
		introduced_conflicts = _sorted_unique(
			(candidate_suppressed_mfs & selected_required_mfs)
			| (candidate_required_mfs & selected_suppressed_mfs)
		)
		if introduced_conflicts:
			continue

		# Candidate must receive direct benefit from selected crops: at least one required MF must be satisfied.
		benefit_received = candidate_required_mfs & selected_produced_mfs
		if not benefit_received:
			continue

		required_satisfied = _sorted_unique(benefit_received)
		crop_name = crop_label_map.get(candidate_id, candidate_id)

		reasons: List[str] = [
			f"Requires {get_mf_label(mf) or mf}, which is available from selected crops"
			for mf in required_satisfied
		]

		associated_crops.append(
			{
				"crop_id": candidate_id,
				"crop_name": crop_name,
				"required_mfs_satisfied": [
					{"mf_code": mf, "mf_label": get_mf_label(mf)} for mf in required_satisfied
				],
				"candidate_produced_mfs": [
					{"mf_code": mf, "mf_label": get_mf_label(mf)}
					for mf in _sorted_unique(candidate_produced_mfs)
				],
				"reasons": reasons,
			}
		)

	associated_crops.sort(
		key=lambda item: (-len(item["required_mfs_satisfied"]), item["crop_name"])
	)

	return {
		"selected_crop_ids": selected_ids,
		"selected_produced_mfs": [
			{"mf_code": mf, "mf_label": get_mf_label(mf)}
			for mf in _sorted_unique(selected_produced_mfs)
		],
		"selected_required_mfs": [
			{"mf_code": mf, "mf_label": get_mf_label(mf)}
			for mf in _sorted_unique(selected_required_mfs)
		],
		"associated_crops": associated_crops,
	}


if __name__ == "__main__":
	import json

	sample_crop_ids = ["CRP0015"]
	print(json.dumps(find_cross_compatible_associate_crops(sample_crop_ids), indent=2))
