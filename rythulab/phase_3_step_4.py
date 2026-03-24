from __future__ import annotations

import importlib
from pathlib import Path
import sys
from typing import Any, Dict, List, Set

def _load_produced_mf_helper():
	try:
		module = importlib.import_module("crop_micro_feature_extract")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "Crop Micro Features"))
		module = importlib.import_module("crop_micro_feature_extract")
	return module.get_produced_micro_features_by_cropid


def _load_phase2_step4_module():
	try:
		return importlib.import_module("rythulab.phase_2_step_4")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent))
		return importlib.import_module("phase_2_step_4")


def _load_crop_catalog_helper():
	try:
		module = importlib.import_module("rythulab.phase_3_step_1")
	except ModuleNotFoundError:
		module = importlib.import_module("phase_3_step_1")
	return module._build_crop_catalog


def _load_annotate_cf_helper():
	try:
		module = importlib.import_module("rythulab.sheets.cf_label_extract")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent / "sheets"))
		module = importlib.import_module("cf_label_extract")
	return module.annotate_cf_code


def _load_crop_name_helper():
	try:
		module = importlib.import_module("rythulab.sheets.extraction_utils")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent / "sheets"))
		module = importlib.import_module("extraction_utils")
	return module.get_cropid_to_name_map


def _load_annotate_mf_helper():
	try:
		module = importlib.import_module("rythulab.sheets.mf_labels.mf_label_extract")
	except ModuleNotFoundError:
		sys.path.append(str(Path(__file__).resolve().parent / "sheets" / "mf_labels"))
		module = importlib.import_module("mf_label_extract")
	return module.annotate_mf_codes


get_produced_micro_features_by_cropid = _load_produced_mf_helper()
_phase2_step4 = _load_phase2_step4_module()
CF_FARM_FEATURES_PATH = _phase2_step4.CF_FARM_FEATURES_PATH
CF_MF_IMPACT_MATRIX_PATH = _phase2_step4.CF_MF_IMPACT_MATRIX_PATH
WEAK_STATUSES = _phase2_step4.WEAK_STATUSES
_normalize_farm_cf_values = _phase2_step4._normalize_farm_cf_values
build_cf_mf_impact_map = _phase2_step4.build_cf_mf_impact_map
_build_crop_catalog = _load_crop_catalog_helper()
annotate_cf_code = _load_annotate_cf_helper()
get_cropid_to_name_map = _load_crop_name_helper()
annotate_mf_codes = _load_annotate_mf_helper()


def _normalize_crop_ids(crop_ids: List[str] | None) -> List[str]:
	out: List[str] = []
	seen: Set[str] = set()
	for raw in crop_ids or []:
		crop_id = str(raw or "").strip().upper()
		if not crop_id or crop_id in seen:
			continue
		seen.add(crop_id)
		out.append(crop_id)
	return out


def _to_frontend_crop(crop_id: str, catalog: Dict[str, Dict[str, str]], cropid_to_name: Dict[str, str]) -> Dict[str, Any]:
	meta = catalog.get(crop_id, {})
	return {
		"id": crop_id,
		"name": cropid_to_name.get(crop_id, meta.get("crop_name") or crop_id),
		"family": meta.get("family") or "",
		"group": meta.get("functional_group") or "",
		"h": "",
		"rootD": meta.get("root_depth_class") or "",
		"mfp": [],
		"cfImprove": [],
		"desc": "",
	}


def analyze_weak_cf_support_and_recommendations(
	selected_crop_ids: List[str] | None,
	farm_cf_values: Dict[str, Any] | None,
) -> Dict[str, Any]:
	selected_ids = _normalize_crop_ids(selected_crop_ids)
	selected_set = set(selected_ids)

	cf_mf_impact_map = build_cf_mf_impact_map(CF_MF_IMPACT_MATRIX_PATH)
	normalized_cfs, unsupported_inputs = _normalize_farm_cf_values(
		farm_cf_values or {},
		cf_mf_impact_map,
		CF_FARM_FEATURES_PATH,
	)

	weak_cf_items = [
		(cf_code, status)
		for cf_code, status in (normalized_cfs or {}).items()
		if str(status or "").strip().lower() in WEAK_STATUSES
	]

	produced_by_cropid = get_produced_micro_features_by_cropid()
	cropid_to_name = get_cropid_to_name_map()
	crop_catalog = _build_crop_catalog()

	cf_analysis: List[Dict[str, Any]] = []
	crop_recommendation_map: Dict[str, Dict[str, Any]] = {}

	for full_cf_code, cf_status in weak_cf_items:
		improving_mfs = set(cf_mf_impact_map.get(full_cf_code, []) or [])

		selected_support: List[Dict[str, Any]] = []
		covered_mfs: Set[str] = set()

		for crop_id in selected_ids:
			matched = sorted(set(produced_by_cropid.get(crop_id, []) or []) & improving_mfs)
			if not matched:
				continue
			covered_mfs.update(matched)
			selected_support.append(
				{
					"crop_id": crop_id,
					"crop_name": cropid_to_name.get(crop_id, crop_id),
					"matching_mfs": annotate_mf_codes(matched),
				}
			)

		missing_mfs = sorted(improving_mfs - covered_mfs)

		cf_analysis.append(
			{
				"cf": annotate_cf_code(full_cf_code, CF_FARM_FEATURES_PATH),
				"status": cf_status,
				"improving_mfs": annotate_mf_codes(sorted(improving_mfs)),
				"selected_crops_helping": selected_support,
				"missing_mfs": annotate_mf_codes(missing_mfs),
			}
		)

		if not missing_mfs:
			continue

		missing_set = set(missing_mfs)
		for crop_id, produced_mfs in (produced_by_cropid or {}).items():
			if crop_id in selected_set:
				continue

			matched_missing = sorted(set(produced_mfs or []) & missing_set)
			if not matched_missing:
				continue

			entry = crop_recommendation_map.setdefault(
				crop_id,
				{
					"crop_id": crop_id,
					"crop_name": cropid_to_name.get(crop_id, crop_id),
					"family": (crop_catalog.get(crop_id) or {}).get("family") or "",
					"functional_group": (crop_catalog.get(crop_id) or {}).get("functional_group") or "",
					"root_depth_class": (crop_catalog.get(crop_id) or {}).get("root_depth_class") or "",
					"supports": [],
				},
			)

			cf_meta = annotate_cf_code(full_cf_code, CF_FARM_FEATURES_PATH)
			mf_meta = annotate_mf_codes(matched_missing)
			entry["supports"].append(
				{
					"cf": cf_meta,
					"status": cf_status,
					"matching_mfs": mf_meta,
					"reasons": [
						(
							f'Produces MF "{(mf or {}).get("mf_label") or (mf or {}).get("mf_code") or ""}", '
							f'which helps weak CF "{cf_meta.get("cf_label") or full_cf_code}"'
						)
						for mf in mf_meta
					],
				}
			)

	recommended_crops = sorted(
		crop_recommendation_map.values(),
		key=lambda item: (-len(item.get("supports") or []), item.get("crop_name") or item.get("crop_id") or ""),
	)

	return {
		"selected_crop_ids": selected_ids,
		"unsupported_inputs": unsupported_inputs,
		"weak_cfs": [annotate_cf_code(code, CF_FARM_FEATURES_PATH) for code, _ in weak_cf_items],
		"cf_analysis": cf_analysis,
		"recommended_crops": recommended_crops,
	}


def build_frontend_payload(
	selected_crop_ids: List[str] | None,
	farm_cf_values: Dict[str, Any] | None,
) -> Dict[str, Any]:
	result = analyze_weak_cf_support_and_recommendations(selected_crop_ids, farm_cf_values)

	cropid_to_name = get_cropid_to_name_map()
	crop_catalog = _build_crop_catalog()

	recommendations: List[Dict[str, Any]] = []
	for rec in result.get("recommended_crops", []) or []:
		crop_id = str(rec.get("crop_id") or "").strip().upper()
		if not crop_id:
			continue

		supports = rec.get("supports") or []
		all_reasons: List[str] = []
		all_mfp_codes: List[str] = []
		cf_codes: List[str] = []

		for support in supports:
			for reason in support.get("reasons") or []:
				if reason not in all_reasons:
					all_reasons.append(reason)
			for mf in support.get("matching_mfs") or []:
				mf_code = str((mf or {}).get("mf_code") or "").strip().upper()
				if mf_code and mf_code not in all_mfp_codes:
					all_mfp_codes.append(mf_code)
			cf_code = str(((support.get("cf") or {}).get("cf_code") or "")).strip().upper()
			if cf_code and cf_code not in cf_codes:
				cf_codes.append(cf_code)

		crop_payload = _to_frontend_crop(crop_id, crop_catalog, cropid_to_name)
		crop_payload["mfp"] = all_mfp_codes
		crop_payload["cfImprove"] = cf_codes

		recommendations.append(
			{
				"crop": crop_payload,
				"reasons": all_reasons,
			}
		)

	return {
		"selected_crop_ids": result.get("selected_crop_ids", []),
		"unsupported_inputs": result.get("unsupported_inputs", []),
		"weak_cfs": result.get("weak_cfs", []),
		"cf_analysis": result.get("cf_analysis", []),
		"recommended_crops": result.get("recommended_crops", []),
		"recommendations": recommendations,
	}


if __name__ == "__main__":
	import json

	sample_crop_ids = ["CRP0001", "CRP0015"]
	sample_farm_cfs = {
		"CF1": "Very Weak",
		"CF9": "Weak",
		"CF16": "Good",
	}
	print(json.dumps(build_frontend_payload(sample_crop_ids, sample_farm_cfs), indent=2))
