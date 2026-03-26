from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
	from rythulab.sheets.mf_labels.mf_label_extract import get_mf_label
except ModuleNotFoundError:
	import sys

	sheets_dir = Path(__file__).resolve().parent / "sheets"
	sys.path.append(str(sheets_dir / "mf_labels"))
	from mf_label_extract import get_mf_label

try:
	from rythulab.phase_1_step_1 import load_step1_results
except ModuleNotFoundError:
	import sys
	sys.path.append(str(Path(__file__).resolve().parent))
	from phase_1_step_1 import load_step1_results

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


def _load_crop_height_map() -> Dict[str, int]:
	"""Returns ordinal height class per crop ID (1=Extra Low … 6=Very Tall)."""
	height_map: Dict[str, int] = {}
	if not CROP_DETAILS_DIR.exists():
		return height_map

	for csv_path in sorted(CROP_DETAILS_DIR.glob("*.csv")):
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
			# Keep highest class seen if a crop appears in multiple sheets
			height_map[cid] = max(height_map.get(cid, ordinal), ordinal)

	return height_map


_CROP_HEIGHTS: Optional[Dict[str, int]] = None


def _get_crop_heights() -> Dict[str, int]:
	global _CROP_HEIGHTS
	if _CROP_HEIGHTS is None:
		_CROP_HEIGHTS = _load_crop_height_map()
	return _CROP_HEIGHTS


def find_cross_compatible_associate_crops(crop_ids: List[str]) -> Dict[str, Any]:
	"""
	Given selected main crop IDs, find associate crops that:
	1) Have at least one required MF satisfied by selected crops' produced MFs
	2) Do not introduce required-vs-suppressed MF conflicts with the selected system
	"""
	selected_ids = [str(cid).strip().upper() for cid in crop_ids if str(cid).strip()]
	selected_set = set(selected_ids)

	step1_scores = load_step1_results()  # {crop_id: score} — allowed universe
	crop_label_map = _load_crop_label_map()
	produced_by_cropid = get_produced_micro_features_by_cropid()
	required_by_cropid = get_required_micro_features_by_cropid()
	suppressed_by_cropid = get_suppressed_micro_features_by_cropid()
	crop_heights = _get_crop_heights()

	selected_produced_mfs: Set[str] = set()
	selected_required_mfs: Set[str] = set()
	selected_suppressed_mfs: Set[str] = set()

	for crop_id in selected_ids:
		selected_produced_mfs.update(produced_by_cropid.get(crop_id, []))
		selected_required_mfs.update(required_by_cropid.get(crop_id, []))
		selected_suppressed_mfs.update(suppressed_by_cropid.get(crop_id, []))

	candidate_ids = (
		set(produced_by_cropid.keys()) | set(required_by_cropid.keys())
	) & (set(step1_scores.keys()) if step1_scores else set(produced_by_cropid.keys()) | set(required_by_cropid.keys()))
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
				"step1_score": step1_scores.get(candidate_id),
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

	# Height-based MF1/MF2 rule:
	# If selected crop X produces MF1 or MF2, and candidate Y requires MF1 or MF2,
	# and height(X) > height(Y), then Y qualifies as an associate under X's canopy.
	already_added: Set[str] = {item["crop_id"] for item in associated_crops}

	# Build list of selected crops that produce MF1 or MF2 with their heights
	mf12_producers: List[Dict] = []
	for crop_x in selected_ids:
		x_produced = set(produced_by_cropid.get(crop_x, []))
		x_mf12 = x_produced & {"MF1", "MF2"}
		if not x_mf12:
			continue
		height_x = crop_heights.get(crop_x)
		if height_x is None:
			continue
		mf12_producers.append({"crop_id": crop_x, "height_class": height_x, "mf12": x_mf12})

	if mf12_producers:
		for candidate_id in candidate_ids:
			if candidate_id in selected_set:
				continue

			candidate_required_mfs = set(required_by_cropid.get(candidate_id, []))
			candidate_mf12_needed = candidate_required_mfs & {"MF1", "MF2"}
			if not candidate_mf12_needed:
				continue

			# Skip if candidate introduces conflicts with selected system
			candidate_suppressed_mfs = set(suppressed_by_cropid.get(candidate_id, []))
			candidate_mfs_conflict = (
				(candidate_suppressed_mfs & selected_required_mfs)
				| (candidate_required_mfs & selected_suppressed_mfs)
			)
			if candidate_mfs_conflict:
				continue

			height_y = crop_heights.get(candidate_id)
			if height_y is None:
				continue

			# Find selected crops with higher height class than candidate that produce MF1/MF2 it needs
			matching_producers = [
				p for p in mf12_producers
				if p["height_class"] > height_y and p["mf12"] & candidate_mf12_needed
			]
			if not matching_producers:
				continue

			candidate_name = crop_label_map.get(candidate_id, candidate_id)
			candidate_produced_mfs = set(produced_by_cropid.get(candidate_id, []))
			satisfied_mfs = _sorted_unique(candidate_mf12_needed)

			reasons: List[str] = []
			for p in matching_producers:
				x_name = crop_label_map.get(p["crop_id"], p["crop_id"])
				mf_codes = sorted(p["mf12"] & candidate_mf12_needed)
				x_class = HEIGHT_CLASS_LABEL.get(p["height_class"], str(p["height_class"]))
				y_class = HEIGHT_CLASS_LABEL.get(height_y, str(height_y))
				reasons.append(
					f"{x_name} (height class: {x_class}) produces {', '.join(mf_codes)} "
					f"and is taller than {candidate_name} (height class: {y_class}) — "
					f"height-based MF benefit satisfied"
				)

			if candidate_id in already_added:
				# Append height-based reasons to existing entry
				for item in associated_crops:
					if item["crop_id"] == candidate_id:
						item["reasons"].extend(reasons)
						break
			else:
				associated_crops.append(
					{
						"crop_id": candidate_id,
						"crop_name": candidate_name,
						"step1_score": step1_scores.get(candidate_id),
						"required_mfs_satisfied": [
							{"mf_code": mf, "mf_label": get_mf_label(mf)} for mf in satisfied_mfs
						],
						"candidate_produced_mfs": [
							{"mf_code": mf, "mf_label": get_mf_label(mf)}
							for mf in _sorted_unique(candidate_produced_mfs)
						],
						"reasons": reasons,
					}
				)
				already_added.add(candidate_id)

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

	# --- Test 1: Original MF-benefit associate test ---
	# Green Gram (CRP0015) produces several MFs; check which crops benefit from it.
	print("=== Test 1: Associate crops for Green Gram (CRP0015) ===")
	result1 = find_cross_compatible_associate_crops(["CRP0015"])
	print(json.dumps(result1, indent=2))
	print(f"\nAssociated crops: {len(result1['associated_crops'])}\n")

	# --- Test 2: Height-based MF1/MF2 rule ---
	# Maize (CRP0002) produces MF1, MF2 and is ~2.5m tall.
	# Ginger (CRP0032) requires MF1 and is only ~0.8m tall.
	# Ginger should appear as a height-based associate under Maize's canopy.
	print("=== Test 2: Height-based MF1/MF2 — Maize (CRP0002) + Sugarcane (CRP0030) ===")
	result2 = find_cross_compatible_associate_crops(["CRP0002", "CRP0030"])
	height_based = [
		c for c in result2["associated_crops"]
		if any("taller" in r for r in c.get("reasons", []))
	]
	print(f"Total associated: {len(result2['associated_crops'])}")
	print(f"Height-rule triggered: {len(height_based)}")
	for c in height_based:
		print(f"  {c['crop_name']} ({c['crop_id']})")
		for r in c["reasons"]:
			if "taller" in r:
				print(f"    -> {r}")
