from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from map_crop_ids_step1 import build_alias_map, load_crop_details_with_ids, resolve_canonical


BASE_DIR = Path(__file__).resolve().parent
MICRO_FEATURES_DIR = BASE_DIR / "Crop Micro Features"
CROP_DETAILS_DIR = BASE_DIR / "crop_details"

STANDARD_HEADER = [
    "CropID",
    "Crop",
    "Produces (MF List)",
    "Requires (MF List)",
    "Suppresses (MF List)",
]

SHEET_BY_SUBCATEGORY = {
    "Cereals": "AP-Crops-Micro-Features.xlsx - Cereals.csv",
    "Minor Millets": "AP-Crops-Micro-Features.xlsx - Cereals.csv",
    "Pulses": "AP-Crops-Micro-Features.xlsx - Pulses.csv",
    "Oilseeds": "AP-Crops-Micro-Features.xlsx - Oilseeds.csv",
    "Commercial": "AP-Crops-Micro-Features.xlsx - Commercial Crops.csv",
    "Fodder": "AP-Crops-Micro-Features.xlsx - Fodder.csv",
    "GLV": "AP-Crops-Micro-Features.xlsx - Vegetables.csv",
    "Creepers": "AP-Crops-Micro-Features.xlsx - Vegetables.csv",
    "Gourds": "AP-Crops-Micro-Features.xlsx - Vegetables.csv",
    "Melons": "AP-Crops-Micro-Features.xlsx - Vegetables.csv",
    "Solanaceae": "AP-Crops-Micro-Features.xlsx - Vegetables.csv",
    "Vegetables": "AP-Crops-Micro-Features.xlsx - Vegetables.csv",
    "Fruit Crops": "AP-Crops-Micro-Features.xlsx - Fruits.csv",
    "Plantation": "AP-Crops-Micro-Features.xlsx - Spices & Plantation.csv",
    "Spices": "AP-Crops-Micro-Features.xlsx - Spices & Plantation.csv",
    "Medicinal": "AP-Crops-Micro-Features.xlsx - Medicinal.csv",
    "Flowers": "AP-Crops-Micro-Features.xlsx - Flowers.csv",
    "Canopy Trees": "AP-Crops-Micro-Features.xlsx - Trees.csv",
    "Sub-Canopy": "AP-Crops-Micro-Features.xlsx - Trees.csv",
    "Pioneer": "AP-Crops-Micro-Features.xlsx - Trees.csv",
}

PROFILE_DEFINITIONS = {
    "wheat": (
        "MF3G, MF3L, MF13, MF16, MF24, MF25",
        "MF3G, MF13",
        "MF1, MF2, MF14",
    ),
    "dry_millet": (
        "MF3G, MF3L, MF10, MF13, MF15, MF16, MF19, MF20, MF24, MF25",
        "MF3G, MF3L, MF11, MF15",
        "MF1, MF2, MF6, MF8, MF9, MF14",
    ),
    "pulse_low": (
        "MF3G, MF16, MF17, MF19, MF20, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "pulse_shrub": (
        "MF1, MF3L, MF16, MF17, MF18, MF19, MF20, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3L, MF13",
        "MF2, MF12, MF14",
    ),
    "pulse_open": (
        "MF3G, MF16, MF17, MF19, MF20, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3G, MF11, MF13",
        "MF2, MF6, MF14",
    ),
    "mustard": (
        "MF3G, MF16, MF19, MF20, MF24, MF25",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "coconut_like": (
        "MF1, MF3U, MF4, MF6, MF8, MF11, MF14, MF17, MF19, MF20, MF24, MF25",
        "MF3U, MF13",
        "MF3G, MF10",
    ),
    "turmeric_like": (
        "MF8, MF9, MF17, MF24, MF25, MF26",
        "MF1, MF6, MF14",
        "MF3G, MF10, MF15",
    ),
    "garlic": (
        "MF3G, MF10, MF15, MF16, MF24, MF26",
        "MF3G, MF13",
        "MF2, MF9, MF14",
    ),
    "chilli": (
        "MF1, MF19",
        "MF3G, MF13",
        "MF2",
    ),
    "napier": (
        "MF2, MF3U, MF6, MF11, MF17, MF22, MF25",
        "MF3U, MF11",
        "MF3G, MF13, MF15",
    ),
    "fodder_legume": (
        "MF1, MF16, MF17, MF18, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3L, MF13",
        "MF2, MF14",
    ),
    "fodder_cover_legume": (
        "MF3G, MF17, MF18, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "leafy_green": (
        "MF3G, MF17, MF19, MF24",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "leafy_legume": (
        "MF3G, MF17, MF19, MF23, MF24, MF27, MF28, MF29",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "brassica": (
        "MF2, MF5, MF9, MF17, MF19",
        "MF3G, MF11",
        "MF13, MF15",
    ),
    "curry_leaf": (
        "MF1, MF6, MF14, MF17, MF19, MF20, MF24, MF25",
        "MF3L, MF13",
        "MF3G, MF10",
    ),
    "moringa": (
        "MF1, MF3U, MF13, MF16, MF19, MF20, MF24, MF25",
        "MF3U, MF13",
        "MF2, MF14",
    ),
    "cucurbit": (
        "MF1, MF17, MF18, MF19, MF20, MF25",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "root_veg": (
        "MF3G, MF16, MF19, MF24",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "fruit_tree_medium": (
        "MF1, MF3L, MF6, MF17, MF19, MF20, MF24, MF25",
        "MF3L, MF13",
        "MF3G, MF10",
    ),
    "areca": (
        "MF1, MF6, MF14, MF16, MF17, MF24, MF25",
        "MF1, MF14",
        "MF3G, MF10",
    ),
    "cocoa": (
        "MF1, MF4, MF6, MF14, MF17, MF19, MF20, MF24, MF25",
        "MF1, MF4, MF14",
        "MF3G, MF10, MF13",
    ),
    "coffee": (
        "MF1, MF6, MF14, MF17, MF19, MF20, MF24, MF25",
        "MF1, MF14",
        "MF3G, MF10, MF13",
    ),
    "tea": (
        "MF1, MF6, MF14, MF17, MF24, MF25",
        "MF1, MF14",
        "MF3G, MF10",
    ),
    "clove": (
        "MF1, MF6, MF14, MF17, MF19, MF20, MF24, MF25, MF26",
        "MF3L, MF14",
        "MF3G, MF10",
    ),
    "cardamom": (
        "MF1, MF4, MF14, MF17, MF19, MF24",
        "MF1, MF4, MF14",
        "MF3G, MF10, MF13",
    ),
    "ashwagandha": (
        "MF3G, MF10, MF15, MF16, MF19, MF24",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "tulsi": (
        "MF3G, MF13, MF19, MF20, MF24, MF26",
        "MF3G, MF13",
        "MF2, MF14",
    ),
    "neem": (
        "MF1, MF4, MF6, MF11, MF14, MF16, MF17, MF20, MF24, MF25, MF26",
        "MF3U, MF13",
        "MF3G, MF10",
    ),
    "vetiver": (
        "MF3G, MF10, MF16, MF21, MF25",
        "MF3G, MF13",
        "MF2, MF9, MF14",
    ),
    "flower_pollinator": (
        "MF3G, MF19, MF20, MF24",
        "MF3G, MF13",
        "MF2",
    ),
    "flower_trap": (
        "MF3G, MF19, MF20, MF21, MF24, MF26",
        "MF3G, MF13",
        "MF2, MF22",
    ),
    "lotus": (
        "MF9, MF14, MF19, MF20, MF24",
        "MF9, MF14",
        "MF10",
    ),
    "canopy_tree": (
        "MF1, MF2, MF4, MF6, MF8, MF11, MF14, MF16, MF17, MF24, MF25",
        "MF3U, MF13",
        "MF3G, MF10, MF15, MF19",
    ),
    "nfix_tree": (
        "MF1, MF4, MF6, MF11, MF14, MF16, MF17, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3U, MF13",
        "MF3G, MF10, MF15",
    ),
    "bamboo": (
        "MF1, MF2, MF11, MF16, MF17, MF24, MF25",
        "MF3U, MF13",
        "MF3G, MF10",
    ),
    "sesbania": (
        "MF1, MF6, MF16, MF17, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3L, MF13",
        "MF2, MF14",
    ),
    "calliandra": (
        "MF1, MF6, MF11, MF16, MF17, MF19, MF20, MF23, MF24, MF25, MF27, MF28, MF29",
        "MF3L, MF13",
        "MF2, MF14",
    ),
    "vitex": (
        "MF1, MF6, MF11, MF16, MF17, MF19, MF20, MF24, MF25",
        "MF3L, MF13",
        "MF2, MF14",
    ),
}

CROP_TO_PROFILE = {
    "Wheat": "wheat",
    "Foxtail Millet (Korralu)": "dry_millet",
    "Little Millet (Samalu)": "dry_millet",
    "Barnyard Millet (Udalu)": "dry_millet",
    "Proso Millet (Varigalu)": "dry_millet",
    "Kodo Millet (Paspalum scrobiculatum)": "dry_millet",
    "Browntop Millet (Urochloa ramosa / Brachiaria ramosa)": "dry_millet",
    "Cowpea": "pulse_shrub",
    "Broad Beans (Faba Beans) (Vicia faba)": "pulse_shrub",
    "Lentils (Lens culinaris)": "pulse_low",
    "Cluster Bean": "pulse_open",
    "Field Bean": "pulse_shrub",
    "Mustard": "mustard",
    "Oil Palm": "coconut_like",
    "Ginger": "turmeric_like",
    "Garlic": "garlic",
    "Chilli (Commercial)": "chilli",
    "Napier Grass": "napier",
    "Hedge Lucerne (Desmanthus)": "fodder_legume",
    "Stylosanthes": "fodder_cover_legume",
    "Spinach": "leafy_green",
    "Amaranth": "leafy_green",
    "Fenugreek": "leafy_legume",
    "Lettuce": "leafy_green",
    "Cabbage": "brassica",
    "Cauliflower": "brassica",
    "Curry leaf": "curry_leaf",
    "Gogu": "leafy_green",
    "Drumstick (Moringa)": "moringa",
    "Bitter Gourd": "cucurbit",
    "Snake Gourd": "cucurbit",
    "Bottle Gourd": "cucurbit",
    "Ridge Gourd": "cucurbit",
    "Pumpkin": "cucurbit",
    "Watermelon": "cucurbit",
    "Beetroot": "root_veg",
    "Radish": "root_veg",
    "Carrot": "root_veg",
    "Muskmelon": "cucurbit",
    "Jackfruit": "coconut_like",
    "Custard Apple": "fruit_tree_medium",
    "Pomegranate": "fruit_tree_medium",
    "Amla (Indian Gooseberry)": "fruit_tree_medium",
    "Areca Nut": "areca",
    "Cocoa": "cocoa",
    "Coffee": "coffee",
    "Tea": "tea",
    "cloves": "clove",
    "Cardamom": "cardamom",
    "Ashwagandha": "ashwagandha",
    "Tulsi (Holy Basil)": "tulsi",
    "Neem": "neem",
    "Vetiver": "vetiver",
    "Marigold(African/French)": "flower_trap",
    "Chrysanthemum": "flower_trap",
    "Rose": "flower_pollinator",
    "Crossandra (Kanakambaram)": "flower_pollinator",
    "Tuberose (Sugandhiraja)": "flower_pollinator",
    "Gaillardia (Blanket Flower)": "flower_pollinator",
    "Cock's Comb (Celosia)": "flower_pollinator",
    "China Aster": "flower_pollinator",
    "Lotus": "lotus",
    "Teak": "canopy_tree",
    "Pongamia (Kanuga)": "nfix_tree",
    "Indian Rosewood (Sheesham)": "nfix_tree",
    "Gliricidia": "nfix_tree",
    "Silver Oak (Grevillea)": "canopy_tree",
    "Bamboo": "bamboo",
    "Sesbania": "sesbania",
    "Calliandra": "calliandra",
    "Vitex (Lagundi)": "vitex",
}


def read_csv(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_csv(path: Path, rows: List[List[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def load_master_rows(list_path: Path) -> List[Dict[str, str]]:
    with list_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def ensure_header(rows: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
    if not rows:
        return STANDARD_HEADER[:], []

    header = rows[0][:]
    if "CropID" not in header:
        if "Crop" in header:
            crop_idx = header.index("Crop")
        elif "Crop Name" in header:
            crop_idx = header.index("Crop Name")
        else:
            crop_idx = 0
        header.insert(crop_idx, "CropID")
        data_rows = []
        for row in rows[1:]:
            updated = row[:]
            updated.insert(crop_idx, "")
            if len(updated) < len(header):
                updated.extend([""] * (len(header) - len(updated)))
            data_rows.append(updated)
        return header, data_rows

    data_rows = [row[:] for row in rows[1:]]
    for row in data_rows:
        if len(row) < len(header):
            row.extend([""] * (len(header) - len(row)))
    return header, data_rows


def build_present_canonical_set(
    micro_features_dir: Path,
    norm_to_canonical: Dict[str, str],
    alias_map: Dict[str, str],
) -> set[str]:
    present: set[str] = set()
    for csv_path in sorted(micro_features_dir.glob("*.csv")):
        rows = read_csv(csv_path)
        if not rows:
            continue
        header = rows[0]
        if "Crop" in header:
            crop_idx = header.index("Crop")
        elif "Crop Name" in header:
            crop_idx = header.index("Crop Name")
        else:
            continue

        for row in rows[1:]:
            if crop_idx >= len(row):
                continue
            crop_name = row[crop_idx].strip()
            if not crop_name:
                continue
            canonical_name = resolve_canonical(crop_name, norm_to_canonical, alias_map) or crop_name
            present.add(canonical_name)
    return present


def iter_missing_master_rows(
    master_rows: Iterable[Dict[str, str]],
    present_canonical: set[str],
) -> Iterable[Dict[str, str]]:
    seen_added: set[str] = set()
    for row in master_rows:
        crop_name = (row.get("Crop Name") or "").strip()
        if not crop_name or crop_name in present_canonical or crop_name in seen_added:
            continue
        seen_added.add(crop_name)
        yield row


def append_missing_entries(apply: bool) -> Dict[str, int]:
    canonical_to_id, norm_to_canonical, _ = load_crop_details_with_ids(CROP_DETAILS_DIR, apply=False)
    alias_map = build_alias_map(CROP_DETAILS_DIR, norm_to_canonical)
    alias_map.update(
        {
            "black pepper": "Pepper",
            "citrus": "Citrus (various)",
            "paddy rice": "Paddy/Rice",
            "jowar": "Jowar (Sorghum)",
            "bajra": "Bajra (Pearl Millet)",
            "ragi": "Ragi (Finger Millet)",
            "red gram": "Red Gram (Pigeon Pea)",
            "black gram": "Black Gram (Urad)",
            "green gram": "Green Gram (Moong)",
            "bengal gram": "Chickpeas (Garbanzo Beans) (Cicer arietinum)",
            "brinjal": "Brinjal (Eggplant)",
        }
    )

    master_rows = load_master_rows(CROP_DETAILS_DIR / "0.List of All crops - Sheet1.csv")
    present_canonical = build_present_canonical_set(MICRO_FEATURES_DIR, norm_to_canonical, alias_map)

    sheet_rows: Dict[str, Tuple[List[str], List[List[str]]]] = {}
    for sheet_name in set(SHEET_BY_SUBCATEGORY.values()):
        path = MICRO_FEATURES_DIR / sheet_name
        if path.exists():
            sheet_rows[sheet_name] = ensure_header(read_csv(path))
        else:
            sheet_rows[sheet_name] = (STANDARD_HEADER[:], [])

    additions: Dict[str, int] = {sheet_name: 0 for sheet_name in sheet_rows}

    for row in iter_missing_master_rows(master_rows, present_canonical):
        crop_name = (row.get("Crop Name") or "").strip()
        crop_id = (row.get("CropID") or canonical_to_id.get(crop_name) or "").strip()
        sub_category = (row.get("Sub-Category") or "").strip()
        profile_name = CROP_TO_PROFILE.get(crop_name)
        sheet_name = SHEET_BY_SUBCATEGORY.get(sub_category)

        if not profile_name:
            raise KeyError(f"No micro-feature profile configured for crop: {crop_name}")
        if not sheet_name:
            raise KeyError(f"No target sheet configured for sub-category: {sub_category}")

        produces, requires, suppresses = PROFILE_DEFINITIONS[profile_name]
        header, data_rows = sheet_rows[sheet_name]

        crop_idx = header.index("Crop") if "Crop" in header else header.index("Crop Name")
        cropid_idx = header.index("CropID")
        produces_idx = header.index("Produces (MF List)")
        requires_idx = header.index("Requires (MF List)")
        suppresses_idx = header.index("Suppresses (MF List)")

        new_row = [""] * len(header)
        new_row[cropid_idx] = crop_id
        new_row[crop_idx] = crop_name
        new_row[produces_idx] = produces
        new_row[requires_idx] = requires
        new_row[suppresses_idx] = suppresses
        data_rows.append(new_row)

        additions[sheet_name] += 1
        present_canonical.add(crop_name)

    if apply:
        for sheet_name, (header, data_rows) in sheet_rows.items():
            if additions[sheet_name] == 0 and not (MICRO_FEATURES_DIR / sheet_name).exists():
                continue
            write_csv(MICRO_FEATURES_DIR / sheet_name, [header, *data_rows])

    return {sheet_name: count for sheet_name, count in additions.items() if count}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate missing Crop Micro Features rows for canonical crops from crop_details."
    )
    parser.add_argument("--apply", action="store_true", help="Write the generated rows to CSV files")
    args = parser.parse_args()

    additions = append_missing_entries(apply=args.apply)
    total = sum(additions.values())
    for sheet_name, count in sorted(additions.items()):
        print(f"{sheet_name}: added={count}, mode={'apply' if args.apply else 'dry-run'}")
    print(f"total_added={total}")


if __name__ == "__main__":
    main()