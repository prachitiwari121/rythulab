"""
Phase 2 Step 7 – Trap Crop + Pest-MF Companion Recommender

Given a list of CropIDs, this module:
  1. Checks the Trap CSV and returns recommended trap crops (by CropID) with reason.
  2. From the crop detail sheets, finds all High-severity pests for those crops.
  3. From the pest master, finds the MFs that REDUCE risk for those pests.
  4. From the Crop Micro Features sheets, finds which crops PRODUCE those MFs.
  5. Returns companion crop recommendations with reasons.
"""

import csv
import re
import pathlib
from collections import defaultdict

try:
    from rythulab.phase_1_step_1 import load_step1_results
except ModuleNotFoundError:
    import sys
    sys.path.append(str(pathlib.Path(__file__).parent))
    from phase_1_step_1 import load_step1_results

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = pathlib.Path(__file__).parent
SHEETS = BASE / "sheets"

TRAP_CSV       = SHEETS / "Trap" / "AP_Crops_Pests_Diseases_NF - AP_Crops_Pests_Diseases_NF.csv"
PEST_MASTER    = SHEETS / "Pests" / "AP_Disease_CF_MF_Triggers_filled - AP_Pest_CF_MF_Triggers.csv"
CROP_DETAILS   = SHEETS / "crop_details"
CROP_MF_DIR    = SHEETS / "Crop Micro Features"
MF_LEGEND_CSV  = SHEETS / "mf_labels" / "AP-Crops-Micro-Features.xlsx - MF Legend.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_mf_codes(cell: str) -> list[str]:
    """Extract MF codes like MF1, MF3G, MF14 from a free-text cell."""
    return re.findall(r"MF\d+[A-Z]?", cell)


def _clean_trap_crop_name(value: str) -> str:
    return re.sub(r"\s*\([^()]*\)\s*$", "", str(value or "").strip())


def load_trap_map() -> dict[str, dict]:
    """
    Returns {crop_id: {"crop": name, "trap_crops": [{"crop": name, "crop_id": id}]}}
    A crop may have multiple trap crops (split by /).
    """
    trap_map: dict[str, dict] = {}
    with open(TRAP_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid  = row["CropID"].strip()
            name = row["Crop"].strip()
            tc_names = [_clean_trap_crop_name(t) for t in row["TrapCrop"].split("/") if t.strip()]
            tc_ids   = [t.strip() for t in row["TrapCropID"].split("/") if t.strip()]
            trap_crops = [
                {"crop": n, "crop_id": i}
                for n, i in zip(tc_names, tc_ids)
                if n and i
            ]
            trap_map[cid] = {"crop": name, "trap_crops": trap_crops}
    return trap_map


def load_pest_master() -> dict[str, dict]:
    """
    Returns {pest_id: {"name": str, "mf_reduces_risk": [mf_code, ...]}}
    """
    pest_map: dict[str, dict] = {}
    with open(PEST_MASTER, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid  = row["PestID"].strip()
            name = row["Pest"].strip()
            mf_reduces = _parse_mf_codes(row.get("MF Produced → Reduces Risk (-)", ""))
            pest_map[pid] = {"name": name, "mf_reduces_risk": mf_reduces}
    return pest_map


def load_crop_high_pests() -> dict[str, list[str]]:
    """
    Scans all crop detail CSVs.
    Returns {crop_id: [pest_id, ...]} for pests with High severity only.
    """
    crop_pests: dict[str, list[str]] = defaultdict(list)
    for csv_file in sorted(CROP_DETAILS.glob("*.csv")):
        with open(csv_file, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        # Find header rows
        id_row = name_row = pest_row = None
        for i, row in enumerate(rows):
            if row and row[0].strip() == "CropID":
                id_row = (i, row)
            if row and "Major Pests" in row[0]:
                pest_row = (i, row)
        if not id_row or not pest_row:
            continue
        crop_ids = id_row[1]
        pest_cells = pest_row[1]
        for col in range(1, min(len(crop_ids), len(pest_cells))):
            cid = crop_ids[col].strip()
            if not cid:
                continue
            # Each cell: "PEST0001 (High), PEST0002 (Medium), ..."
            for entry in pest_cells[col].split(","):
                entry = entry.strip()
                m = re.match(r"(PEST\d+)\s*\((\w+)\)", entry)
                if m and m.group(2).lower() == "high":
                    crop_pests[cid].append(m.group(1))
    return dict(crop_pests)


def load_mf_name_map() -> dict[str, str]:
    """Returns {mf_code: feature_name}"""
    mf_names: dict[str, str] = {}
    with open(MF_LEGEND_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["MF Code"].strip()
            name = row["Feature Name"].strip()
            mf_names[code] = name
    return mf_names


def load_mf_producers() -> dict[str, list[dict]]:
    """
    Scans all Crop Micro Feature sheets.
    Returns {mf_code: [{"crop_id": str, "crop": str}, ...]}
    """
    mf_producers: dict[str, list[dict]] = defaultdict(list)
    for csv_file in sorted(CROP_MF_DIR.glob("*.csv")):
        with open(csv_file, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid  = row.get("CropID", "").strip()
                name = row.get("Crop", "").strip()
                produces_cell = row.get("Produces (MF List)", "")
                for mf in _parse_mf_codes(produces_cell):
                    mf_producers[mf].append({"crop_id": cid, "crop": name})
    return dict(mf_producers)


# ── Main API ──────────────────────────────────────────────────────────────────

def recommend(crop_ids: list[str]) -> dict:
    """
    Given a list of CropIDs, returns a structured recommendation dict:
    {
      "trap_crops": [
        {
          "for_crop_id": str,
          "for_crop": str,
          "trap_crops": [{"crop": str, "crop_id": str}],
          "reason": str
        }, ...
      ],
      "companion_crops_via_mf": [
        {
          "for_crop_id": str,
          "for_crop": str,
          "high_severity_pests": [{"pest_id": str, "pest_name": str}],
          "mitigating_mfs": [{"mf_code": str, "mf_name": str, "mitigates_pests": [pest_id]}],
          "companion_crops": [
            {
              "crop_id": str,
              "crop": str,
              "produces_mfs": [str],
              "mitigates_pests": [str],
              "reason": str
            }, ...
          ]
        }, ...
      ]
    }
    """
    crop_ids = [str(crop_id or "").strip().upper() for crop_id in crop_ids or [] if str(crop_id or "").strip()]

    trap_map      = load_trap_map()
    pest_master   = load_pest_master()
    crop_pests    = load_crop_high_pests()
    mf_names      = load_mf_name_map()
    mf_producers  = load_mf_producers()
    step1_scores  = load_step1_results()

    # ── 1. Trap crop recommendations ─────────────────────────────────────────
    trap_results = []
    for cid in crop_ids:
        if cid not in trap_map:
            continue
        entry = trap_map[cid]
        trap_crops_filtered = [
            {**tc, "step1_score": step1_scores.get(tc.get("crop_id"))}
            for tc in entry["trap_crops"]
            if not step1_scores or tc.get("crop_id") in step1_scores
        ]
        if not trap_crops_filtered:
            continue
        tc_names = ", ".join(tc["crop"] for tc in trap_crops_filtered)
        trap_results.append({
            "for_crop_id": cid,
            "for_crop": entry["crop"],
            "trap_crops": trap_crops_filtered,
            "reason": (
                f"{entry['crop']} is susceptible to pests that are diverted by "
                f"{tc_names} when grown as border/intercrop rows, reducing direct "
                f"pest pressure on the main crop."
            ),
        })

    # ── 2. Companion crops via MF mitigation ─────────────────────────────────
    companion_results = []

    for cid in crop_ids:
        high_pests = crop_pests.get(cid, [])
        if not high_pests:
            continue

        crop_name = trap_map.get(cid, {}).get("crop") or cid

        # Collect MFs that reduce risk for each high-severity pest
        # mf_code -> [pest_ids that it mitigates]
        mf_pest_map: dict[str, list[str]] = defaultdict(list)
        for pid in high_pests:
            if pid not in pest_master:
                continue
            for mf in pest_master[pid]["mf_reduces_risk"]:
                mf_pest_map[mf].append(pid)

        if not mf_pest_map:
            continue

        mitigating_mfs = [
            {
                "mf_code": mf,
                "mf_name": mf_names.get(mf, mf),
                "mitigates_pests": pids,
            }
            for mf, pids in sorted(mf_pest_map.items())
        ]

        # For each MF, find producers; aggregate by companion crop
        # companion_id -> {crop, produces_mfs: set, mitigates_pests: set}
        companions: dict[str, dict] = {}
        for mf, pids in mf_pest_map.items():
            for producer in mf_producers.get(mf, []):
                comp_id = producer["crop_id"]
                if comp_id == cid or not comp_id:
                    continue  # skip self
                if step1_scores and comp_id not in step1_scores:
                    continue
                if comp_id not in companions:
                    companions[comp_id] = {
                        "crop_id": comp_id,
                        "crop": producer["crop"],
                        "produces_mfs": set(),
                        "mitigates_pests": set(),
                    }
                companions[comp_id]["produces_mfs"].add(mf)
                companions[comp_id]["mitigates_pests"].update(pids)

        # Build sorted companion list (most MFs first)
        companion_list = []
        for comp in sorted(
            companions.values(),
            key=lambda c: (-len(c["produces_mfs"]), c["crop_id"]),
        ):
            mf_labels = sorted(comp["produces_mfs"])
            pest_labels = sorted(comp["mitigates_pests"])
            pest_names = [
                pest_master[p]["name"]
                for p in pest_labels
                if p in pest_master
            ]
            mf_descs = [
                mf_names.get(m, m) for m in mf_labels
            ]
            companion_list.append({
                "crop_id": comp["crop_id"],
                "crop": comp["crop"],
                "step1_score": step1_scores.get(comp["crop_id"]),
                "produces_mfs": mf_labels,
                "mitigates_pests": pest_labels,
                "reason": (
                    f"{comp['crop']} produces {', '.join(mf_descs)}, "
                    f"which reduce risk from: {', '.join(pest_names)}."
                ),
            })

        companion_results.append({
            "for_crop_id": cid,
            "for_crop": crop_name,
            "high_severity_pests": [
                {"pest_id": p, "pest_name": pest_master.get(p, {}).get("name", p)}
                for p in high_pests
                if p in pest_master
            ],
            "mitigating_mfs": mitigating_mfs,
            "companion_crops": companion_list,
        })

    return {
        "trap_crops": trap_results,
        "companion_crops_via_mf": companion_results,
    }


def build_frontend_payload(crop_ids: list[str]) -> dict:
    """Flatten the recommendation output into frontend-friendly card data."""
    result = recommend(crop_ids)

    recommended_trap_crops: dict[str, dict] = {}
    for item in result["trap_crops"]:
        for trap_crop in item.get("trap_crops", []):
            trap_crop_id = str(trap_crop.get("crop_id") or "").strip().upper()
            if not trap_crop_id:
                continue
            existing = recommended_trap_crops.setdefault(
                trap_crop_id,
                {
                    "crop_id": trap_crop_id,
                    "crop_name": trap_crop.get("crop", trap_crop_id),
                    "step1_score": trap_crop.get("step1_score"),
                    "reasons": [],
                    "supports_crop_ids": [],
                    "supports_crops": [],
                },
            )
            support_crop_id = item.get("for_crop_id")
            support_crop_name = item.get("for_crop")
            if support_crop_id and support_crop_id not in existing["supports_crop_ids"]:
                existing["supports_crop_ids"].append(support_crop_id)
            if support_crop_name and support_crop_name not in existing["supports_crops"]:
                existing["supports_crops"].append(support_crop_name)
            reason = (
                f"Recommended for {support_crop_name} as a trap crop to divert key pests."
            )
            if reason not in existing["reasons"]:
                existing["reasons"].append(reason)

    recommended_companion_crops: dict[str, dict] = {}
    for item in result["companion_crops_via_mf"]:
        for companion in item.get("companion_crops", []):
            companion_id = str(companion.get("crop_id") or "").strip().upper()
            if not companion_id:
                continue
            existing = recommended_companion_crops.setdefault(
                companion_id,
                {
                    "crop_id": companion_id,
                    "crop_name": companion.get("crop", companion_id),
                    "step1_score": companion.get("step1_score"),
                    "produces_mfs": [],
                    "mitigates_pests": [],
                    "supports_crop_ids": [],
                    "supports_crops": [],
                    "reasons": [],
                },
            )
            for mf_code in companion.get("produces_mfs", []):
                if mf_code not in existing["produces_mfs"]:
                    existing["produces_mfs"].append(mf_code)
            for pest_id in companion.get("mitigates_pests", []):
                if pest_id not in existing["mitigates_pests"]:
                    existing["mitigates_pests"].append(pest_id)
            support_crop_id = item.get("for_crop_id")
            support_crop_name = item.get("for_crop")
            if support_crop_id and support_crop_id not in existing["supports_crop_ids"]:
                existing["supports_crop_ids"].append(support_crop_id)
            if support_crop_name and support_crop_name not in existing["supports_crops"]:
                existing["supports_crops"].append(support_crop_name)
            reason = companion.get("reason")
            if reason and reason not in existing["reasons"]:
                existing["reasons"].append(reason)

    recommended_trap_crops_sorted = sorted(
        recommended_trap_crops.values(),
        key=lambda item: (item["crop_name"], item["crop_id"]),
    )
    recommended_companion_crops_sorted = sorted(
        recommended_companion_crops.values(),
        key=lambda item: (-len(item["produces_mfs"]), item["crop_name"], item["crop_id"]),
    )

    trap_list = [
        {
            "crop": {
                "id": item["crop_id"],
                "name": item["crop_name"],
                "mfp": ["trap_pest"],
                "type": "Trap",
                "family": "",
                "desc": "",
                "border": True,
                "trap": True,
                "step1_score": item.get("step1_score"),
            },
            "reasons": item.get("reasons", []),
        }
        for item in recommended_trap_crops_sorted
    ]

    associate_list = [
        {
            "crop": {
                "id": item["crop_id"],
                "name": item["crop_name"],
                "mfp": item.get("produces_mfs", []),
                "type": "Associate",
                "family": "",
                "desc": "",
                "border": False,
                "trap": False,
                "step1_score": item.get("step1_score"),
            },
            "reasons": item.get("reasons", []),
        }
        for item in recommended_companion_crops_sorted
    ]

    return {
        "trap_crops": result["trap_crops"],
        "companion_crops_via_mf": result["companion_crops_via_mf"],
        "recommended_trap_crops": recommended_trap_crops_sorted,
        "recommended_companion_crops": recommended_companion_crops_sorted,
        "trapList": trap_list,
        "associateList": associate_list,
    }


# ── CLI demo ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    sample_ids = ["CRP0001", "CRP0002", "CRP0029"]  # Paddy, Maize, Cotton
    result = build_frontend_payload(sample_ids)
    print(json.dumps(result, indent=2, ensure_ascii=False))
