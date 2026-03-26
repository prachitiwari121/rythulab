from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict, List
import sys


def _load_produced_mf_helper():
	try:
		module = importlib.import_module("crop_micro_feature_extract")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
		module = importlib.import_module("crop_micro_feature_extract")
	return module.get_produced_micro_features_by_cropid


def _load_crop_name_helper():
	try:
		module = importlib.import_module("rythulab.sheets.extraction_utils")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent / "sheets"))
		module = importlib.import_module("extraction_utils")
	return module.get_cropid_to_name_map


def _load_crop_catalog_helper():
	try:
		module = importlib.import_module("rythulab.phase_3_step_1")
	except ModuleNotFoundError:
		module = importlib.import_module("phase_3_step_1")
	return module._build_crop_catalog


def _load_annotate_mf_helper():
	try:
		module = importlib.import_module("rythulab.sheets.mf_labels.mf_label_extract")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "mf_labels"))
		module = importlib.import_module("mf_label_extract")
	return module.annotate_mf_codes


def _load_step1_results_helper():
	try:
		module = importlib.import_module("rythulab.phase_1_step_1")
	except ModuleNotFoundError:
		module = importlib.import_module("phase_1_step_1")
	return module.load_step1_results


get_produced_micro_features_by_cropid = _load_produced_mf_helper()
get_cropid_to_name_map = _load_crop_name_helper()
_build_crop_catalog = _load_crop_catalog_helper()
annotate_mf_codes = _load_annotate_mf_helper()
load_step1_results = _load_step1_results_helper()


TARGET_MF_CODES = ["MF18", "MF19", "MF20", "MF24", "MF29"]


def get_crops_producing_priority_biodiversity_mfs(
	mf_codes: List[str] | None = None,
	selected_crop_ids: List[str] | None = None,
) -> Dict[str, Any]:
	"""
	Check if selected crops cover the target MF codes, then return crops
	that fill the remaining gaps.

	Default target MF codes:
	MF18, MF19, MF20, MF24, MF29
	"""
	target_codes = [
		str(mf_code or "").strip().upper()
		for mf_code in (mf_codes or TARGET_MF_CODES)
		if str(mf_code or "").strip()
	]
	target_set = set(target_codes)
	selected_set = {
		str(crop_id or "").strip().upper()
		for crop_id in (selected_crop_ids or [])
		if str(crop_id or "").strip()
	}

	produced_by_cropid = get_produced_micro_features_by_cropid()
	crop_labels = get_cropid_to_name_map()
	crop_catalog = _build_crop_catalog()
	step1_scores = load_step1_results()

	# ── Check coverage for selected crops ─────────────────────────
	mf_coverage_map: Dict[str, List[str]] = {code: [] for code in target_codes}
	for crop_id in selected_set:
		produced_mfs = produced_by_cropid.get(crop_id, [])
		for mf in produced_mfs:
			if mf in mf_coverage_map:
				mf_coverage_map[mf].append(crop_labels.get(crop_id, crop_id))

	covered_mfs = {code for code, crops in mf_coverage_map.items() if crops}
	missing_mfs = target_set - covered_mfs

	# Build per-MF coverage list annotated with labels
	target_mf_annotated = annotate_mf_codes(target_codes)
	mf_coverage: List[Dict[str, Any]] = []
	for mf_info in target_mf_annotated:
		code = mf_info.get("mf_code", "")
		mf_coverage.append({
			"mf_code": code,
			"mf_label": mf_info.get("mf_label", code),
			"covered": code in covered_mfs,
			"covered_by": mf_coverage_map.get(code, []),
		})

	# ── Recommend crops only for the missing MFs ──────────────────
	matching_crops: List[Dict[str, Any]] = []
	for crop_id, produced_mfs in (produced_by_cropid or {}).items():
		if crop_id in selected_set:
			continue
		if step1_scores and crop_id not in step1_scores:
			continue
		matched_codes = sorted(set(produced_mfs or []) & missing_mfs)
		if not matched_codes:
			continue

		crop_meta = crop_catalog.get(crop_id, {})

		matching_crops.append(
			{
				"crop_id": crop_id,
				"crop_name": crop_labels.get(crop_id, crop_id),
				"step1_score": step1_scores.get(crop_id),
				"family": crop_meta.get("family") or "",
				"functional_group": crop_meta.get("functional_group") or "",
				"canopy_layer_class": crop_meta.get("canopy_layer_class") or "",
				"root_depth_class": crop_meta.get("root_depth_class") or "",
				"matched_mfs": annotate_mf_codes(matched_codes),
			}
		)

	matching_crops.sort(
		key=lambda item: (-len(item["matched_mfs"]), item["crop_name"], item["crop_id"])
	)

	return {
		"target_mfs": target_mf_annotated,
		"mf_coverage": mf_coverage,
		"recommended_crops": matching_crops,
	}


def build_frontend_payload(
	mf_codes: List[str] | None = None,
	selected_crop_ids: List[str] | None = None,
) -> Dict[str, Any]:
	result = get_crops_producing_priority_biodiversity_mfs(mf_codes, selected_crop_ids)
	recommendations: List[Dict[str, Any]] = []

	for item in result.get("recommended_crops", []) or []:
		matched = item.get("matched_mfs") or []
		reasons = [
			'Produces MF "' + str(mf.get("mf_label") or mf.get("mf_code") or "") + '" — supports system biodiversity'
			for mf in matched
		]
		recommendations.append(
			{
				"crop": {
					"id": item.get("crop_id"),
					"name": item.get("crop_name") or item.get("crop_id"),
					"family": item.get("family") or "",
					"group": item.get("functional_group") or "",
					"h": item.get("canopy_layer_class") or "",
					"rootD": item.get("root_depth_class") or "",
					"mfp": [mf.get("mf_code") for mf in matched if mf.get("mf_code")],
					"cfImprove": [],
					"desc": "",
					"step1_score": item.get("step1_score"),
				},
				"reasons": reasons,
			}
		)

	return {
		"target_mfs": result.get("target_mfs", []),
		"mf_coverage": result.get("mf_coverage", []),
		"recommendations": recommendations,
	}


if __name__ == "__main__":
	import json

	print(json.dumps(build_frontend_payload(), indent=2))
