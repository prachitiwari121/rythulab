import frappe
from frappe import _
import csv
import re

# ---------------- FARMER REGISTER ---------------- #

@frappe.whitelist(allow_guest=True)
def register_farmer(
    full_name: str = None,
    email: str = None,
    phone: str = None,
    land_name: str = None,
    land_area: str = None,
    password: str = None
):
    required = {
        "full_name": full_name,
        "email":     email,
        "phone":     phone,
        "password":  password,
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        frappe.throw(_("Missing required fields: {0}").format(", ".join(missing)))

    email     = email.strip().lower()
    full_name = full_name.strip()
    phone     = phone.strip()

    land_name     = land_name.strip() if land_name else ""
    land_area_val = 0.0
    if land_area:
        try:
            land_area_val = float(land_area)
        except Exception:
            land_area_val = 0.0

    if not phone.isdigit() or len(phone) != 10:
        frappe.throw(_("Phone number must be exactly 10 digits."))

    if frappe.db.exists("User", email):
        frappe.throw(_("An account with this email already exists. Please login."))

    role_name = "Farmer Scientist"
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name
        }).insert(ignore_permissions=True)

    try:
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "enabled": 1,
            "new_password": password,
            "send_welcome_email": 0,
            "user_type": "Website User"
        })
        user.append("roles", {"role": role_name})
        user.insert(ignore_permissions=True)

    except frappe.ValidationError as e:
        frappe.throw(_("Unable to create user: {0}").format(str(e)))

    except Exception:
        frappe.log_error(
            title="User Creation Failed",
            message=frappe.get_traceback()
        )
        frappe.throw(_("Something went wrong while creating user."))

    if frappe.db.exists("DocType", "Farmer Profile"):
        meta    = frappe.get_meta("Farmer Profile")
        allowed = {df.fieldname for df in meta.fields}
        profile_data = {"doctype": "Farmer Profile"}
        if "user"      in allowed: profile_data["user"]      = user.name
        if "phone"     in allowed: profile_data["phone"]     = phone
        if "land_name" in allowed: profile_data["land_name"] = land_name
        if "land_area" in allowed: profile_data["land_area"] = land_area_val
        if not frappe.db.exists("Farmer Profile", {"user": user.name}):
            frappe.get_doc(profile_data).insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "ok": True,
        "message": "Farmer registered successfully",
        "user": user.name
    }


# ---------------- LOGIN REDIRECT ---------------- #

@frappe.whitelist()
def login_redirect():
    user = frappe.session.user

    if user == "Administrator":
        return "admin"

    if frappe.db.exists("Has Role", {
        "parent": user, "role": "System Manager", "parenttype": "User"
    }):
        return "admin"

    if frappe.db.exists("Has Role", {
        "parent": user, "role": "Farmer Scientist", "parenttype": "User"
    }):
        return "farmer"

    return "admin"


# ---------------- GET CROPS ---------------- #

@frappe.whitelist()
def get_crops():
    crops = frappe.get_all(
        "Crop",
        fields=[
            "name", "crop_name", "crop_type", "crop_image", "crop_symbol",
            "season", "min_spacing", "max_spacing",
            "row_spacing", "description", "water_needs", "growth_duration"
        ]
    )
    # Make sure image URL is absolute
    for crop in crops:
        if crop.get("crop_image") and not crop["crop_image"].startswith("http"):
            crop["crop_image"] = frappe.utils.get_url(crop["crop_image"])
    return crops


# ---------------- GET MY MODELS ---------------- #

@frappe.whitelist()
def get_my_models():
    user = frappe.session.user
    is_admin = "System Manager" in frappe.get_roles(user) or user == "Administrator"
    filters = {} if is_admin else {"farmer": user}
    models = frappe.get_all(
        "Crop Model",
        filters=filters,
        fields=[
            "name", "model_name", "version", "season", "date",
            "comment", "model_data", "main_crop_reason",
            "associated_crop_reason", "trap_crop_reason", "spacing_reason", "farmer"
        ],
        order_by="modified desc"
    )
    return models


# ---------------- SAVE CROP MODEL ---------------- #

@frappe.whitelist()
def save_crop_model(
    model_name: str = None,
    season: str = None,
    date: str = None,
    comment: str = None,
    version: str = None,
    model_data: str = None,
    main_crop_reason: str = None,
    associated_crop_reason: str = None,
    trap_crop_reason: str = None,
    spacing_reason: str = None,
    existing_name: str = None
):
    user = frappe.session.user

    if not model_name:
        frappe.throw(_("Model name is required."))
    if not season:
        frappe.throw(_("Season is required."))
    if not date:
        frappe.throw(_("Date is required."))

    version_int = int(version) if version else 1

    doc = frappe.get_doc({
        "doctype":                "Crop Model",
        "model_name":             model_name,
        "farmer":                 user,
        "version":                version_int,
        "season":                 season,
        "date":                   date,
        "comment":                comment or "",
        "model_data":             model_data or "{}",
        "main_crop_reason":       main_crop_reason or "",
        "associated_crop_reason": associated_crop_reason or "",
        "trap_crop_reason":       trap_crop_reason or "",
        "spacing_reason":         spacing_reason or "",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"ok": True, "name": doc.name}

@frappe.whitelist()
def delete_crop_model(model_name: str = None):
    if not model_name:
        frappe.throw("Model name required.")
    doc = frappe.get_doc("Crop Model", model_name)
    if doc.farmer != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw("Not authorized.")
    frappe.delete_doc("Crop Model", model_name, ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


# ---------------- PHASE 1 FEASIBLE CROPS ---------------- #

def _norm_crop_name(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _crop_id_from_name(name: str) -> str:
    clean = re.sub(r"\([^)]*\)", "", (name or "").strip().lower())
    clean = clean.replace("&", " and ").replace("/", " ")
    clean = re.sub(r"[^a-z0-9]+", "_", clean).strip("_")
    return clean or "crop"


def _to_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _extract_numeric_value(value, default=None):
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return default
    try:
        return float(match.group(0))
    except Exception:
        return default


def _get_cf_field(farm_cfs, key, field_name="val"):
    value = (farm_cfs or {}).get(key)
    if isinstance(value, dict):
        return value.get(field_name)
    return value


def _normalize_texture(value):
    text = (value or "").strip().lower().replace("-", " ")
    mapping = {
        "sandy loam": "SandyLoam",
        "sandy": "Sandy",
        "sand": "Sandy",
        "loam": "Loam",
        "loamy": "Loam",
        "clay loam": "ClayLoam",
        "red sandy loam": "SandyLoam",
    }
    return mapping.get(text, value)


def _normalize_drainage(value):
    text = (value or "").strip().lower()
    mapping = {
        "waterlogged": "Poor",
        "poor": "Poor",
        "moderate": "Moderate",
        "good": "Good",
        "well drained": "Excellent",
        "well-drained": "Excellent",
        "excellent": "Excellent",
    }
    return mapping.get(text, value)


def _normalize_irrigation(value):
    text = (value or "").strip().lower()
    mapping = {
        "none": "None",
        "occasional": "Protective",
        "seasonal": "Protective",
        "reliable": "Assured",
        "assured": "Assured",
        "frequent": "Frequent",
    }
    return mapping.get(text, value)


def _normalize_nitrogen_class(value):
    text = (value or "").strip().lower()
    mapping = {
        "very weak": "Low",
        "weak": "Low",
        "moderate": "Medium",
        "good": "High",
        "ideal": "High",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
    }
    return mapping.get(text, value)


def _normalize_frost_risk(value):
    numeric = _extract_numeric_value(value, default=None)
    if numeric is None:
        return value
    if numeric <= 0:
        return "None"
    if numeric <= 2:
        return "Low"
    if numeric <= 5:
        return "Medium"
    return "High"


def _normalize_drought_risk(water_slab, water_supply):
    slab = (water_slab or "").strip().lower()
    supply = (water_supply or "").strip().lower()
    if "copious" in supply:
        return "Low-Medium"
    if "controlled" in supply:
        return "Medium"
    mapping = {
        "very weak": "Very High",
        "weak": "High",
        "moderate": "Medium",
        "good": "Low",
        "ideal": "Low-Medium",
    }
    return mapping.get(slab)


def _normalize_flood_risk(water_supply, drainage):
    supply = (water_supply or "").strip().lower()
    drainage_text = (drainage or "").strip().lower()
    if "copious" in supply or drainage_text == "poor":
        return "High"
    if "controlled" in supply or drainage_text == "moderate":
        return "Medium"
    if drainage_text == "good":
        return "Low"
    return None


def _build_phase1_step6_farm_cfs(payload):
    farm_context = payload.get("farm_context") or {}
    farm_cfs = payload.get("farm_cfs") or {}
    resolved = {}

    ph_value = _extract_numeric_value(_get_cf_field(farm_cfs, "pH"), default=None)
    if ph_value is not None:
        resolved["CF5_pH"] = ph_value

    texture_value = _normalize_texture(_get_cf_field(farm_cfs, "TXT"))
    if texture_value:
        resolved["CF7_Texture"] = texture_value

    depth_value = _extract_numeric_value(_get_cf_field(farm_cfs, "ESD"), default=None)
    if depth_value is not None:
        resolved["CF8_Depth"] = depth_value

    drainage_value = _normalize_drainage(_get_cf_field(farm_cfs, "DR"))
    if drainage_value:
        resolved["CF11_Drainage"] = drainage_value

    groundwater_value = _extract_numeric_value(_get_cf_field(farm_cfs, "GW"), default=None)
    if groundwater_value is not None:
        resolved["CF13_GW"] = groundwater_value

    irrigation_value = _normalize_irrigation(_get_cf_field(farm_cfs, "IA"))
    if irrigation_value:
        resolved["CF14_Irrigation"] = irrigation_value

    heat_days_value = _extract_numeric_value(_get_cf_field(farm_cfs, "HSD"), default=None)
    if heat_days_value is not None:
        resolved["CF17_HeatDays"] = heat_days_value

    frost_risk_value = _normalize_frost_risk(_get_cf_field(farm_cfs, "FR"))
    if frost_risk_value:
        resolved["CF18_FrostRisk"] = frost_risk_value

    nitrogen_value = _normalize_nitrogen_class(_get_cf_field(farm_cfs, "N", "slab"))
    if nitrogen_value:
        resolved["CF4_N"] = nitrogen_value

    water_slab = _get_cf_field(farm_cfs, "W", "slab")
    water_value = _get_cf_field(farm_cfs, "W")
    if water_value:
        resolved["CF_Water"] = water_value

    water_supply = farm_context.get("water_supply") or farm_context.get("waterSupply")
    if water_supply:
        resolved["Water_Regime"] = water_supply

    drought_risk_value = _normalize_drought_risk(water_slab, water_supply)
    if drought_risk_value:
        resolved["CF25_DroughtRisk"] = drought_risk_value

    flood_risk_value = _normalize_flood_risk(water_supply, drainage_value)
    if flood_risk_value:
        resolved["CF24_FloodRisk"] = flood_risk_value

    rainfall_value = _extract_numeric_value(farm_context.get("rain"), default=None)
    if rainfall_value is not None:
        resolved["Rainfall_mm"] = rainfall_value

    min_temp = _extract_numeric_value(farm_context.get("minTemp"), default=None)
    max_temp = _extract_numeric_value(farm_context.get("maxTemp"), default=None)
    if min_temp is not None and max_temp is not None:
        resolved["TempC"] = round((min_temp + max_temp) / 2.0, 2)

    return resolved


def _build_phase1_step7_farm_cfs(payload):
    farm_cfs = payload.get("farm_cfs") or {}

    short_to_cf = {
        "N": "CF1",
        "P": "CF2",
        "K": "CF3",
        "SOC": "CF4",
        "PH": "CF5",
        "EC": "CF6",
        "TXT": "CF7",
        "ESD": "CF8",
        "WHC": "CF9",
        "BD": "CF10",
        "DR": "CF11",
        "ER": "CF12",
        "GW": "CF13",
        "IA": "CF14",
        "RR": "CF15",
        "TMP": "CF16",
        "HSD": "CF17",
        "FR": "CF18",
        "WS": "CF19",
        "BI": "CF20",
        "PP": "CF21",
        "EW": "CF22",
        "SLP": "CF23",
        "FDR": "CF24",
        "DDR": "CF25",
        "CA": "CF26",
    }

    resolved = {}
    for key, value in farm_cfs.items():
        key_text = str(key or "").strip()
        normalized_key = key_text.upper()

        cf_code = None
        if re.match(r"^CF\d+", normalized_key):
            cf_match = re.match(r"^(CF\d+)", normalized_key)
            cf_code = cf_match.group(1) if cf_match else None
        else:
            cf_code = short_to_cf.get(normalized_key)

        if not cf_code:
            continue

        if isinstance(value, dict):
            resolved[cf_code] = {
                "slab": value.get("slab"),
                "s": value.get("s"),
                "status": value.get("status"),
                "val": value.get("val"),
                "l": value.get("l"),
            }
        else:
            resolved[cf_code] = value

    return resolved

def _format_step6_check(entry):
    return {
        "k": entry.get("parameter"),
        "ok": bool(entry.get("passed")),
        "det": entry.get("message"),
        "sv": str(entry.get("severity") or "").lower() == "severe",
        "cf_codes": entry.get("cf_codes") or [],
        "cf_labels": entry.get("cf_labels") or [],
        "expected": entry.get("expected"),
        "actual_value": entry.get("actual_value"),
        "input_keys": entry.get("input_keys") or [],
    }


def _no_critical_parameters_result(crop):
    check_entry = {
        "k": "No Critical Parameters",
        "ok": True,
        "det": "No critical parameters defined for this crop.",
        "sv": False,
        "cf_codes": [],
        "cf_labels": [],
        "expected": "",
        "actual_value": "",
        "input_keys": [],
    }
    return {
        "crop": crop,
        "checks": [check_entry],
        "failed_checks": [],
        "passed_checks": [check_entry],
        "warnings": [],
        "all_passed": True,
        "failed_count": 0,
        "passed_count": 1,
    }


def _build_crop_type_map():
    crop_docs = frappe.get_all("Crop", fields=["crop_name", "crop_type"])
    by_norm = {}
    aliases = {
        "rice": "paddy rice",
        "paddy": "paddy rice",
        "jowar": "jowar sorghum",
        "sorghum": "jowar sorghum",
        "bengal gram": "chickpeas garbanzo beans cicer arietinum",
        "chilli": "chilli commercial",
        "chillies": "chilli commercial",
        "brinjal": "brinjal eggplant",
    }

    for doc in crop_docs:
        crop_name = doc.get("crop_name") or ""
        crop_type = doc.get("crop_type") or "Main Crop"
        norm_name = _norm_crop_name(crop_name)
        if norm_name:
            by_norm[norm_name] = crop_type

    for key, mapped in aliases.items():
        norm_target = _norm_crop_name(mapped)
        if norm_target in by_norm:
            by_norm[_norm_crop_name(key)] = by_norm[norm_target]

    return by_norm


def _build_cropid_map_from_sheet():
    cropid_map = {}
    crop_details_dir = frappe.get_app_path("rythulab", "sheets", "crop_details")

    candidate_names = [
        "0.list of all crops - sheet1.csv",
        "0.list_of_all_crops___sheet1.csv",
        "0_list_of_all_crops_sheet1.csv",
    ]

    list_path = None
    try:
        import os

        files = os.listdir(crop_details_dir)
        lower_to_real = {name.lower(): name for name in files}

        for candidate in candidate_names:
            if candidate in lower_to_real:
                list_path = os.path.join(crop_details_dir, lower_to_real[candidate])
                break

        if not list_path:
            for name in files:
                low = name.lower()
                if low.endswith(".csv") and "list" in low and "crop" in low and "sheet1" in low:
                    list_path = os.path.join(crop_details_dir, name)
                    break
    except Exception:
        list_path = None

    if not list_path:
        list_path = frappe.get_app_path(
            "rythulab",
            "sheets",
            "crop_details",
            "0.List of All crops - Sheet1.csv",
        )

    aliases = {
        "rice": "paddy rice",
        "paddy": "paddy rice",
        "jowar": "jowar sorghum",
        "sorghum": "jowar sorghum",
        "bengal gram": "chickpeas garbanzo beans cicer arietinum",
        "chilli": "chilli commercial",
        "chillies": "chilli commercial",
        "brinjal": "brinjal eggplant",
    }

    with open(list_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            crop_name = (row.get("Crop Name") or "").strip()
            crop_id = (row.get("CropID") or "").strip()
            if not crop_name or not crop_id:
                continue

            norm_name = _norm_crop_name(crop_name)
            if norm_name:
                cropid_map[norm_name] = crop_id

    for key, mapped in aliases.items():
        norm_target = _norm_crop_name(mapped)
        if norm_target in cropid_map:
            cropid_map[_norm_crop_name(key)] = cropid_map[norm_target]

    return cropid_map


@frappe.whitelist()
def get_feasible_crops(
    area: int = None,
    zone: str = None,
    season: str = None,
    soil: str = None,
    waterAvail: str = None,
    waterSupply: str = None,
    wind: str = None,
    minTemp: str = None,
    maxTemp: str = None,
    season_weight: str = None,
    water_weight: str = None,
    soil_weight: str = None,
    temperature_weight: str = None,
):
    from rythulab.phase_1_step_1 import get_suitable_crops_by_conditions
    from rythulab.phase_1_step_3 import get_crop_water_demand_min

    # Support JSON body as well as form/query params
    frappe.logger().info("Enter")
    payload = frappe.request.get_json(silent=True) or {}
    area = area or payload.get("area")
    zone = zone or payload.get("zone")
    season = season or payload.get("season")
    soil = soil or payload.get("soil")
    waterAvail = waterAvail or payload.get("waterAvail")
    waterSupply = waterSupply or payload.get("water_supply")
    wind = wind or payload.get("wind")
    minTemp = minTemp if minTemp is not None else payload.get("minTemp")
    maxTemp = maxTemp if maxTemp is not None else payload.get("maxTemp")
    season_weight = season_weight if season_weight is not None else payload.get("season_weight")
    water_weight = water_weight if water_weight is not None else payload.get("water_weight")
    soil_weight = soil_weight if soil_weight is not None else payload.get("soil_weight")
    temperature_weight = temperature_weight if temperature_weight is not None else payload.get("temperature_weight")

    missing = []
    if not zone:
        missing.append("zone")
    if not season:
        missing.append("season")
    if not soil:
        missing.append("soil")
    if not waterAvail:
        missing.append("waterAvail")
    if not waterSupply:
        missing.append("waterSupply")
    if missing:
        frappe.throw(_("Missing required fields: {0}").format(", ".join(missing)))

    min_temp_val = _to_float(minTemp, default=None)
    max_temp_val = _to_float(maxTemp, default=None)
    season_weight_val = _to_float(season_weight, default=1.0)
    water_weight_val = _to_float(water_weight, default=1.0)
    soil_weight_val = _to_float(soil_weight, default=1.0)
    temperature_weight_val = _to_float(temperature_weight, default=1.0)

    feasible = get_suitable_crops_by_conditions(
        soil_texture=soil,
        water_supply_regime=waterSupply,
        season=season,
        agro_climatic_zone=zone,
        season_weight=season_weight_val,
        water_weight=water_weight_val,
        soil_weight=soil_weight_val,
        min_temperature=min_temp_val,
        max_temperature=max_temp_val,
        temperature_weight=temperature_weight_val,
    )

    crop_type_map = _build_crop_type_map()
    cropid_map = _build_cropid_map_from_sheet()
    crops = []
    for item in feasible:
        crop_id = item.get("crop_id")
        crop_name = item.get("crop")
        weighted = float(item.get("weighted_score") or 0.0)
        sc = int(round(max(0.0, min(5.0, weighted)) * 20))
        season_score = float(item.get("season_score") or 0)
        water_score = float(item.get("water_score") or 0)
        soil_score = float(item.get("soil_score") or 0)
        temp_score = item.get("temperature_score")

        norm_name = _norm_crop_name(crop_name or "")
        crop_type = crop_type_map.get(norm_name, "Main Crop")
        if not crop_id:
            crop_id = cropid_map.get(norm_name) or _crop_id_from_name(crop_name)
        try:
            wr = get_crop_water_demand_min(crop_id)
        except Exception:
            wr = None

        crops.append({
            "id": crop_id,
            "cropid": crop_id,
            "name": crop_name,
            "type": crop_type,
            "wr": wr,
            "sc": sc,
            "sm": season_score > 0,
            "zm": season_score > 0,
            "wm": water_score > 0,
            "som": soil_score > 0,
            "tm": (temp_score is None) or (float(temp_score) > 0),
            "season_score": season_score,
            "water_score": water_score,
            "soil_score": soil_score,
            "temperature_score": temp_score,
            "weighted_score": weighted,
        })

    return {
        "ok": True,
        "farm_context": {
            "area": area,
            "zone": zone,
            "season": season,
            "soil": soil,
            "waterAvail": waterAvail,
            "wind": wind,
            "minTemp": min_temp_val,
            "maxTemp": max_temp_val,
        },
        "crops": crops,
    }


@frappe.whitelist()
def get_phase1_crops(**kwargs):
    # Backward-compatible alias for frontend code already calling this endpoint.
    return get_feasible_crops(**kwargs)


@frappe.whitelist()
def get_phase1_farm_feasibility(selected_crops=None, farm_cfs=None, farm_context=None):
    from rythulab.phase_1_step_6 import check_critical_parameters

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []
    farm_cfs = farm_cfs or payload.get("farm_cfs") or {}
    farm_context = farm_context or payload.get("farm_context") or {}

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)
    if isinstance(farm_cfs, str):
        farm_cfs = frappe.parse_json(farm_cfs)
    if isinstance(farm_context, str):
        farm_context = frappe.parse_json(farm_context)

    request_payload = {
        "selected_crops": selected_crops,
        "farm_cfs": farm_cfs,
        "farm_context": farm_context,
    }
    resolved_cfs = _build_phase1_step6_farm_cfs(request_payload)

    results = []
    for crop in selected_crops or []:
        crop_id = (crop.get("cropid") or crop.get("id") or "").strip()
        if not crop_id:
            continue

        try:
            analysis = check_critical_parameters(crop_id, resolved_cfs)
        except ValueError as exc:
            message = str(exc)
            if "has no critical parameters defined" in message:
                results.append(_no_critical_parameters_result(crop))
                continue
            raise

        results.append({
            "crop": crop,
            "checks": [_format_step6_check(entry) for entry in analysis.get("checks", [])],
            "failed_checks": analysis.get("failed_checks", []),
            "passed_checks": analysis.get("passed_checks", []),
            "warnings": analysis.get("warnings", []),
            "all_passed": analysis.get("all_passed", False),
            "failed_count": analysis.get("failed_count", 0),
            "passed_count": analysis.get("passed_count", 0),
        })

    return {
        "ok": True,
        "results": results,
        "resolved_cfs": resolved_cfs,
    }


@frappe.whitelist()
def get_phase1_resource_pressure(selected_crops=None, farm_cfs=None, farm_context=None):
    from rythulab.phase_1_step_7 import check_resource_pressure

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []
    farm_cfs = farm_cfs or payload.get("farm_cfs") or {}
    farm_context = farm_context or payload.get("farm_context") or {}

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)
    if isinstance(farm_cfs, str):
        farm_cfs = frappe.parse_json(farm_cfs)
    if isinstance(farm_context, str):
        farm_context = frappe.parse_json(farm_context)

    request_payload = {
        "selected_crops": selected_crops,
        "farm_cfs": farm_cfs,
        "farm_context": farm_context,
    }
    resolved_cfs = _build_phase1_step7_farm_cfs(request_payload)

    results = []
    warnings = []

    for crop in selected_crops or []:
        crop_id = (crop.get("cropid") or crop.get("id") or "").strip()
        if not crop_id:
            continue

        analysis = check_resource_pressure(crop_id, resolved_cfs)
        results.append({
            "crop": crop,
            "analysis": analysis,
        })

        for warning in analysis.get("warnings", []):
            warnings.append({
                "cn": analysis.get("crop_name") or crop.get("name") or crop_id,
                "t": "warn",
                "m": warning.get("message"),
                "cf_code": warning.get("cf_code"),
                "cf_label": warning.get("cf_label"),
            })

    return {
        "ok": True,
        "results": results,
        "warnings": warnings,
        "resolved_cfs": resolved_cfs,
    }


@frappe.whitelist()
def get_phase1_ecosystem_impact(selected_crops=None, farm_cfs=None, farm_context=None):
    from rythulab.phase_1_step_8 import check_produced_mf_deterioration_warning

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []
    farm_cfs = farm_cfs or payload.get("farm_cfs") or {}
    farm_context = farm_context or payload.get("farm_context") or {}

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)
    if isinstance(farm_cfs, str):
        farm_cfs = frappe.parse_json(farm_cfs)
    if isinstance(farm_context, str):
        farm_context = frappe.parse_json(farm_context)

    request_payload = {
        "selected_crops": selected_crops,
        "farm_cfs": farm_cfs,
        "farm_context": farm_context,
    }
    resolved_cfs = _build_phase1_step7_farm_cfs(request_payload)
    step8_farm_cfs = {}

    for cf_code, cf_value in (resolved_cfs or {}).items():
        if isinstance(cf_value, dict):
            slab_value = cf_value.get("slab")
            if slab_value not in (None, ""):
                step8_farm_cfs[cf_code] = slab_value
        elif cf_value not in (None, ""):
            step8_farm_cfs[cf_code] = cf_value

    results = []
    warnings = []

    for crop in selected_crops or []:
        crop_id = (crop.get("cropid") or crop.get("id") or "").strip()
        if not crop_id:
            continue

        analysis = check_produced_mf_deterioration_warning(crop_id, step8_farm_cfs)
        results.append({
            "crop": crop,
            "analysis": analysis,
        })

        for warning in analysis.get("warnings", []):
            warnings.append({
                "cn": analysis.get("crop_label") or crop.get("name") or crop_id,
                "t": "warn",
                "m": warning.get("message"),
                "cf_code": warning.get("cf_code"),
                "cf_label": warning.get("cf_label"),
                "mf_code": warning.get("mf_code"),
                "mf_label": warning.get("mf_label"),
            })

    return {
        "ok": True,
        "results": results,
        "warnings": warnings
    }


@frappe.whitelist()
def get_phase1_intercrop_competition(selected_crops=None):
    from rythulab.phase_1_step_9 import check_crop_competition

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)

    crop_ids = []
    crop_lookup = {}

    for crop in selected_crops or []:
        if not isinstance(crop, dict):
            continue

        crop_id = (crop.get("cropid") or crop.get("id") or "").strip().upper()
        if not crop_id:
            continue

        crop_ids.append(crop_id)
        crop_lookup[crop_id] = crop

    analysis_warnings = check_crop_competition(crop_ids)

    type_map = {
        "light_competition": "Light",
        "horizontal_canopy_competition": "Canopy",
        "ground_competition": "Ground",
        "root_competition": "Root",
        "temporal_competition": "Temporal",
        "resource_competition": "Resource",
        "pest_host_overlap": "Pest",
    }

    warnings = []
    for warning in analysis_warnings:
        crop_a_id = (warning.get("crop_a_id") or "").strip().upper()
        crop_b_id = (warning.get("crop_b_id") or "").strip().upper()

        crop_a = crop_lookup.get(crop_a_id, {})
        crop_b = crop_lookup.get(crop_b_id, {})

        crop_a_name = warning.get("crop_a_label") or crop_a.get("name") or crop_a_id
        crop_b_name = warning.get("crop_b_label") or crop_b.get("name") or crop_b_id

        warning_type = warning.get("warning_type")

        warnings.append({
            "a": crop_a_name,
            "b": crop_b_name,
            "t": type_map.get(warning_type, "Competition"),
            "m": warning.get("message"),
            "warning_type": warning_type,
            "crop_a_id": crop_a_id,
            "crop_b_id": crop_b_id,
        })

    return {
        "ok": True,
        "warnings": warnings,
        "results": analysis_warnings,
    }


@frappe.whitelist()
def get_phase1_microfeature_conflicts(selected_crops=None):
    from rythulab.phase_1_step_10 import check_microfeature_conflicts

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)

    crop_ids = []
    crop_lookup = {}

    for crop in selected_crops or []:
        if not isinstance(crop, dict):
            continue

        crop_id = (crop.get("cropid") or crop.get("id") or "").strip().upper()
        if not crop_id:
            continue

        crop_ids.append(crop_id)
        crop_lookup[crop_id] = crop

    analysis_conflicts = check_microfeature_conflicts(crop_ids)

    warnings = []
    for conflict in analysis_conflicts:
        crop_req_id = (conflict.get("crop_requiring_id") or "").strip().upper()
        crop_supp_id = (conflict.get("crop_suppressing_id") or "").strip().upper()

        warnings.append({
            "nc": conflict.get("crop_requiring_label") or crop_req_id,
            "sc": conflict.get("crop_suppressing_label") or crop_supp_id,
            "mf": conflict.get("mf_code"),
            "msg": conflict.get("message"),
            "mf_label": conflict.get("mf_label"),
        })

    return {
        "ok": True,
        "warnings": warnings,
        "results": analysis_conflicts,
    }


@frappe.whitelist()
def get_phase2_missing_mfs(selected_crops=None):
    from rythulab.phase_2_step_1 import find_missing_mfs_and_producers

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)

    crop_ids = []
    for crop in selected_crops or []:
        if not isinstance(crop, dict):
            continue
        crop_id = (crop.get("cropid") or crop.get("id") or "").strip().upper()
        if crop_id:
            crop_ids.append(crop_id)

    result = find_missing_mfs_and_producers(crop_ids)

    return {
        "ok": True,
        "missing_mfs": result.get("missing_mfs", []),
        "missing_mf_details": result.get("missing_mf_details", []),
        "recommended_crops": result.get("recommended_crops", []),
        "required_mfs": result.get("required_mfs", []),
        "available_mfs": result.get("available_mfs", []),
    }


@frappe.whitelist()
def get_phase2_cross_compatibility(selected_crops=None):
    from rythulab.phase_2_step_2 import find_cross_compatible_associate_crops

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)

    crop_ids = []
    for crop in selected_crops or []:
        if not isinstance(crop, dict):
            continue
        crop_id = (crop.get("cropid") or crop.get("id") or "").strip().upper()
        if crop_id:
            crop_ids.append(crop_id)

    result = find_cross_compatible_associate_crops(crop_ids)

    return {
        "ok": True,
        "selected_crop_ids": result.get("selected_crop_ids", []),
        "selected_produced_mfs": result.get("selected_produced_mfs", []),
        "selected_required_mfs": result.get("selected_required_mfs", []),
        "associated_crops": result.get("associated_crops", []),
    }


@frappe.whitelist()
def get_phase2_disease_mitigation(selected_crops=None):
    from rythulab.phase_2_step_3 import find_disease_mitigating_crops

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)

    crop_ids = []
    for crop in selected_crops or []:
        if isinstance(crop, dict):
            crop_id = (crop.get("cropid") or crop.get("id") or "").strip().upper()
        else:
            crop_id = str(crop or "").strip().upper()
        if crop_id:
            crop_ids.append(crop_id)

    result = find_disease_mitigating_crops(crop_ids)

    return {
        "ok": True,
        "selected_crop_ids": result.get("selected_crop_ids", []),
        "crop_disease_mitigations": result.get("crop_disease_mitigations", []),
    }


@frappe.whitelist()
def get_phase2_farm_context_support(farm_cfs=None):
    from rythulab.phase_2_step_4 import (
        CF_FARM_FEATURES_PATH,
        CF_MF_IMPACT_MATRIX_PATH,
        _normalize_farm_cf_values,
        analyze_weak_cf_mitigating_crops,
        build_cf_mf_impact_map,
    )
    from rythulab.sheets.cf_label_extract import annotate_cf_code
    from rythulab.sheets.mf_labels.mf_label_extract import annotate_mf_codes

    payload = frappe.request.get_json(silent=True) or {}
    farm_cfs = farm_cfs or payload.get("farm_cfs") or {}
    selected_crops = payload.get("selected_crops") or payload.get("main_crops") or payload.get("crops") or []

    if isinstance(farm_cfs, str):
        farm_cfs = frappe.parse_json(farm_cfs)
    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)

    selected_crop_ids = []
    for crop in selected_crops or []:
        if isinstance(crop, dict):
            crop_id = (crop.get("cropid") or crop.get("id") or "").strip().upper()
        else:
            crop_id = str(crop or "").strip().upper()
        if crop_id:
            selected_crop_ids.append(crop_id)

    if "CRP0001" in selected_crop_ids and isinstance(farm_cfs, dict):
        filtered_farm_cfs = {}
        for key, value in (farm_cfs or {}).items():
            normalized_key = str(key or "").strip().upper()
            if normalized_key == "CF11" or normalized_key.startswith("CF11_"):
                continue
            filtered_farm_cfs[key] = value
        farm_cfs = filtered_farm_cfs

    result = analyze_weak_cf_mitigating_crops(farm_cfs)

    farm_context_features = []
    try:
        cf_mf_impact_map = build_cf_mf_impact_map(CF_MF_IMPACT_MATRIX_PATH)
        normalized_farm_cfs, _ = _normalize_farm_cf_values(
            farm_cfs,
            cf_mf_impact_map,
            CF_FARM_FEATURES_PATH,
        )

        weak_codes = {
            str((cf_item or {}).get("cf_code") or "").strip().upper()
            for cf_item in (result.get("weak_cfs") or [])
            if isinstance(cf_item, dict)
        }

        for full_cf_code, status in normalized_farm_cfs.items():
            if str(full_cf_code).strip().upper() not in weak_codes:
                continue
            cf_meta = annotate_cf_code(full_cf_code, CF_FARM_FEATURES_PATH)
            farm_context_features.append(
                {
                    "cf": cf_meta,
                    "status": status,
                    "is_weak": str(full_cf_code).strip().upper() in weak_codes,
                    "improving_mfs": annotate_mf_codes(cf_mf_impact_map.get(full_cf_code, [])),
                }
            )
    except Exception:
        farm_context_features = []

    cropid_to_name = {}
    try:
        from rythulab.sheets.extraction_utils import get_cropid_to_name_map

        cropid_to_name = get_cropid_to_name_map()
    except Exception:
        cropid_to_name = {}

    recommended = []
    for rec in result.get("recommended_crops", []) or []:
        crop_id = str(rec.get("crop") or "").strip().upper()
        recommended.append(
            {
                "crop_id": crop_id,
                "crop_name": cropid_to_name.get(crop_id, crop_id),
                "supports": rec.get("supports", []),
            }
        )

    return {
        "ok": True,
        "weak_cfs": result.get("weak_cfs", []),
        "unsupported_inputs": result.get("unsupported_inputs", []),
        "farm_context_features": farm_context_features,
        "cf_analysis": result.get("cf_analysis", []),
        "recommended_crops": recommended,
    }


@frappe.whitelist()
def get_phase2_wind_barrier_crops(selected_crops=None):
    from rythulab.phase_2_step_5 import get_crops_producing_wind_barrier

    payload = frappe.request.get_json(silent=True) or {}
    selected_crops = selected_crops or payload.get("selected_crops") or payload.get("crops") or []

    if isinstance(selected_crops, str):
        selected_crops = frappe.parse_json(selected_crops)

    cropid_to_name = {}
    try:
        from rythulab.sheets.extraction_utils import get_cropid_to_name_map

        cropid_to_name = get_cropid_to_name_map()
    except Exception:
        cropid_to_name = {}

    recommended = []
    for rec in get_crops_producing_wind_barrier() or []:
        crop_id = str(rec.get("crop") or "").strip().upper()
        if not crop_id:
            continue
        recommended.append(
            {
                "crop_id": crop_id,
                "crop_name": cropid_to_name.get(crop_id, crop_id),
                "reason": rec.get("reason") or "Produces MF11 (Wind Barrier)",
            }
        )

    return {
        "ok": True,
        "recommended_crops": recommended,
    }


@frappe.whitelist()
def get_phase2_zone_pest_mitigation(agro_climatic_zone=None):
    from rythulab.phase_2_step_6 import find_zone_pest_mitigating_crops

    payload = frappe.request.get_json(silent=True) or {}
    zone = agro_climatic_zone or payload.get("agro_climatic_zone") or payload.get("zone")

    if not zone:
        return {
            "ok": False,
            "error": "Missing required field: agro_climatic_zone",
            "common_pests": [],
            "mitigating_mfs": [],
            "recommended_crops": [],
        }

    try:
        result = find_zone_pest_mitigating_crops(zone)
    except ValueError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "common_pests": [],
            "mitigating_mfs": [],
            "recommended_crops": [],
        }

    return {
        "ok": True,
        "agro_climatic_zone": result.get("agro_climatic_zone", zone),
        "common_pests": result.get("common_pests", []),
        "mitigating_mfs": result.get("mitigating_mfs", []),
        "recommended_crops": result.get("recommended_crops", []),
    }
