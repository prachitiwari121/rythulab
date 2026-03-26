"""
Assign CropIDs to step1/new sheets from the master crop list.
- Adds CropID as the first column.
- Rows in the sheet that match a master crop get its ID.
- Rows that don't match any master crop get '' (no ID).
- Master crops not in a sheet are appended with 'T' values.
"""

import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(BASE, "..", "crop_details", "0.List of All crops - Sheet1.csv")
SHEETS_DIR = os.path.join(BASE, "new")

# ─── Load master crop list ─────────────────────────────────────────────────────
with open(MASTER_CSV, newline="", encoding="utf-8-sig") as f:
    master_rows = list(csv.DictReader(f))

# master_list: [{crop_id, crop_name}, ...]
master_list = [{"crop_id": r["CropID"], "crop_name": r["Crop Name"]} for r in master_rows]

# ─── Name → CropID mapping (many-to-one, first match wins) ────────────────────
# Keys are normalised lower-stripped strings.
# For each alias, we point to a CropID.

NAME_ALIASES: dict[str, str] = {
    # Cereals
    "paddy/rice":                               "CRP0001",
    "paddy":                                    "CRP0001",
    "rice":                                     "CRP0001",
    "maize":                                    "CRP0002",
    "maize (fodder)":                           "CRP0002",
    "jowar (sorghum)":                          "CRP0003",
    "jowar":                                    "CRP0003",
    "fodder sorghum (jowar)":                   "CRP0003",
    "fodder sorghum (late sown)":               "CRP0003",
    "bajra (pearl millet)":                     "CRP0004",
    "bajra":                                    "CRP0004",
    "fodder bajra (pearl millet)":              "CRP0004",
    "fodder bajra (late sown)":                 "CRP0004",
    "napier–bajra hybrid":                      "CRP0004",
    "ragi (finger millet)":                     "CRP0005",
    "ragi":                                     "CRP0005",
    "wheat":                                    "CRP0006",
    # Minor millets
    "foxtail millet (korralu)":                 "CRP0007",
    "foxtail millet":                           "CRP0007",
    "little millet (samalu)":                   "CRP0008",
    "barnyard millet (udalu)":                  "CRP0009",
    "proso millet (varigalu)":                  "CRP0010",
    "kodo millet (paspalum scrobiculatum)":     "CRP0011",
    "browntop millet (urochloa ramosa / brachiaria ramosa)": "CRP0012",
    # Pulses
    "red gram (pigeon pea)":                    "CRP0013",
    "redgram":                                  "CRP0013",
    "red gram":                                 "CRP0013",
    "black gram (urad)":                        "CRP0014",
    "blackgram":                                "CRP0014",
    "black gram":                               "CRP0014",
    "green gram (moong)":                       "CRP0015",
    "greengram":                                "CRP0015",
    "green gram":                               "CRP0015",
    "horse gram":                               "CRP0016",
    "cowpea":                                   "CRP0017",
    "cowpea (fodder)":                          "CRP0017",
    "cowpea (fodder residual)":                 "CRP0017",
    "broad beans (faba beans) (vicia faba)":    "CRP0018",
    "chickpeas (garbanzo beans) (cicer arietinum)": "CRP0019",
    "bengal gram":                              "CRP0019",
    "bengalgram":                               "CRP0019",
    "lentils (lens culinaris)":                 "CRP0020",
    "cluster bean":                             "CRP0021",
    "cluster beans":                            "CRP0021",
    "guar (clusterbean fodder)":                "CRP0021",
    "field bean":                               "CRP0022",
    # Oilseeds
    "groundnut":                                "CRP0023",
    "sunflower":                                "CRP0024",
    "castor":                                   "CRP0025",
    "mustard":                                  "CRP0026",
    "oil palm":                                 "CRP0027",
    "sesame":                                   "CRP0028",
    # Commercial
    "cotton":                                   "CRP0029",
    "cotton (late)":                            "CRP0029",
    "sugarcane":                                "CRP0030",
    "turmeric":                                 "CRP0031",
    "turmeric (late)":                          "CRP0031",
    "ginger":                                   "CRP0032",
    "garlic":                                   "CRP0033",
    "chilli (commercial)":                      "CRP0034",
    # Fodder
    "napier grass":                             "CRP0035",
    "hybrid napier (perennial cuts)":           "CRP0035",
    "hedge lucerne (desmanthus)":               "CRP0036",
    "stylosanthes":                             "CRP0037",
    "stylo (stylo hamata)":                     "CRP0037",
    # GLV
    "spinach":                                  "CRP0038",
    "amaranth":                                 "CRP0039",
    "green amaranth":                           "CRP0039",
    "fenugreek":                                "CRP0040",
    "fenugreek leaves":                         "CRP0040",
    "lettuce":                                  "CRP0041",
    "cabbage":                                  "CRP0042",
    "cauliflower":                              "CRP0043",
    "coriander":                                "CRP0044",
    "curry leaf":                               "CRP0045",
    "curry leaves":                             "CRP0045",
    "gogu":                                     "CRP0046",
    "drumstick (moringa)":                      "CRP0047",
    "moringa":                                  "CRP0047",
    # Creepers / Gourds
    "bitter gourd":                             "CRP0048",
    "snake gourd":                              "CRP0049",
    "bottle gourd":                             "CRP0050",
    "ridge gourd":                              "CRP0051",
    "pumpkin":                                  "CRP0052",
    "watermelon":                               "CRP0053",
    "beetroot":                                 "CRP0054",
    "radish":                                   "CRP0055",
    "carrot":                                   "CRP0056",
    "muskmelon":                                "CRP0057",
    # Solanaceae / Vegetables
    "tomato":                                   "CRP0058",
    "brinjal (eggplant)":                       "CRP0059",
    "brinjal":                                  "CRP0059",
    "chilli":                                   "CRP0060",
    "chillies":                                 "CRP0060",
    "potato":                                   "CRP0061",
    "okra":                                     "CRP0062",
    "onion":                                    "CRP0063",
    "elephant yam":                             "CRP0064",
    # Fruit crops
    "mango":                                    "CRP0065",
    "citrus (various)":                         "CRP0066",
    "citrus":                                   "CRP0066",
    "lemon":                                    "CRP0066",
    "guava":                                    "CRP0067",
    "papaya":                                   "CRP0068",
    "coconut":                                  "CRP0069",
    "cashew":                                   "CRP0070",
    "banana":                                   "CRP0071",
    "jackfruit":                                "CRP0072",
    "custard apple":                            "CRP0073",
    "pomegranate":                              "CRP0074",
    "amla (indian gooseberry)":                 "CRP0075",
    "amla":                                     "CRP0075",
    # Plantation
    "areca nut":                                "CRP0076",
    "arecanut":                                 "CRP0076",
    "cocoa":                                    "CRP0077",
    "coffee":                                   "CRP0078",
    "coffee (arabica)":                         "CRP0078",
    "coffee (robusta)":                         "CRP0078",
    "tea":                                      "CRP0079",
    # Spices
    "pepper":                                   "CRP0080",
    "black pepper":                             "CRP0080",
    "cloves":                                   "CRP0081",
    "betel leaf":                               "CRP0082",
    "betel vine":                               "CRP0082",
    "cardamom":                                 "CRP0083",
    # Medicinal
    "ashwagandha":                              "CRP0084",
    "tulsi (holy basil)":                       "CRP0085",
    "tulsi (basil)":                            "CRP0085",
    "neem":                                     "CRP0086",
    "vetiver":                                  "CRP0087",
    "vetiver (perennial grass)":                "CRP0087",
    # Flowers
    "marigold(african/french)":                 "CRP0088",
    "marigold":                                 "CRP0088",
    "chrysanthemum":                            "CRP0089",
    "rose":                                     "CRP0090",
    "crossandra (kanakambaram)":                "CRP0091",
    "crossandra":                               "CRP0091",
    "tuberose (sugandhiraja)":                  "CRP0092",
    "tuberose":                                 "CRP0092",
    "gaillardia (blanket flower)":              "CRP0093",
    "cock's comb (celosia)":                    "CRP0094",
    "china aster":                              "CRP0095",
    "aster":                                    "CRP0095",
    "lotus":                                    "CRP0096",
    # Canopy Trees
    "teak":                                     "CRP0097",
    "pongamia (kanuga)":                        "CRP0099",
    "tamarind":                                 "CRP0100",
    "indian rosewood (sheesham)":               "CRP0101",
    # Sub-Canopy
    "gliricidia":                               "CRP0102",
    "silver oak (grevillea)":                   "CRP0103",
    "silver oak":                               "CRP0103",
    "bamboo":                                   "CRP0104",
    "banmboo":                                  "CRP0104",   # typo in perennial
    "sesbania":                                 "CRP0105",
    "sesbania (can be perennial depending on species)": "CRP0105",
    # Pioneer
    "calliandra":                               "CRP0106",
    "vitex (lagundi)":                          "CRP0107",
}

def normalise(name: str) -> str:
    return name.strip().lower()

def lookup_id(crop_name: str) -> str:
    return NAME_ALIASES.get(normalise(crop_name), "")

# ─── Process each sheet ────────────────────────────────────────────────────────
unmatched_report: dict[str, list[str]] = {}

for fname in sorted(os.listdir(SHEETS_DIR)):
    if not fname.endswith(".csv"):
        continue
    path = os.path.join(SHEETS_DIR, fname)
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        continue

    header = rows[0]          # e.g. ['Crop', 'North Coastal', ...]
    feature_cols = header[1:] # everything after 'Crop'
    n_features = len(feature_cols)
    t_values = ["T"] * n_features

    # Build: crop_name → data row (excluding the first 'Crop' cell)
    sheet_crops: dict[str, list[str]] = {}
    for row in rows[1:]:
        if not row:
            continue
        name = row[0].strip()
        data = row[1:] if len(row) > 1 else t_values
        # pad to feature cols length
        while len(data) < n_features:
            data.append("T")
        sheet_crops[name] = data

    # ── Assign IDs and build output rows ──────────────────────────────────────
    out_rows = [["CropID"] + header]  # new header

    unmatched: list[str] = []
    seen_ids: set[str] = set()

    for crop_name, data in sheet_crops.items():
        cid = lookup_id(crop_name)
        if not cid:
            unmatched.append(crop_name)
        else:
            seen_ids.add(cid)
        out_rows.append([cid, crop_name] + data[:n_features])

    # ── Append master crops missing from this sheet ────────────────────────────
    added = 0
    for m in master_list:
        if m["crop_id"] not in seen_ids:
            out_rows.append([m["crop_id"], m["crop_name"]] + t_values)
            added += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(out_rows)

    unmatched_report[fname] = unmatched
    print(f"✓ {fname}")
    print(f"  {len(sheet_crops)} original crops → {len(out_rows)-1} total rows (+{added} added from master)")
    if unmatched:
        print(f"  ⚠ {len(unmatched)} unmatched (no CropID assigned):")
        for u in unmatched:
            print(f"      - {u}")
    print()

print("Done.")
