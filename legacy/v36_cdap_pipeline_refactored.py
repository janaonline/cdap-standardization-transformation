import os
import re
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from google import genai
except Exception:
    genai = None

RAW_FILE = "sample_raw_dataset.xlsx"
TAXONOMY_FILE = "Taxonomy_Mapping.xlsx"
LATLONG_FILE = "LAT LONG.xlsx"
METADATA_FILE = "Metadata.xlsx"
INDICATOR_MASTER_FILE = "Indicators_list.xlsx"
TEMPORAL_LOG_FILE = "Temporal indicator log.xlsx"

OUTPUT_FINAL_XLSX = "final_cdap_output.xlsx"
OUTPUT_FINAL_CSV = "final_cdap_output.csv"
OUTPUT_INDICATOR_MASTER_XLSX = "Indicators_list_updated.xlsx"
OUTPUT_TEMPORAL_LOG_XLSX = "Temporal_indicator_log_updated.xlsx"
OUTPUT_MAPPING_XLSX = "indicator_mapping_generated.xlsx"
OUTPUT_METADATA_MAPPING_XLSX = "metadata_year_mapping_used.xlsx"

MODEL_NAME = "gemini-2.5-flash"
DEFAULT_NA_CODE = "NA99"

FINAL_COLUMNS = [
    "Unique Dataset Identifier",
    "Geo-Level",
    "Geo-cut",
    "Geo-Name",
    "Latitude for Geo-Name",
    "Longitude for Geo-Name",
    "LGD Code 1 (Primary LGD Code)",
    "Discontinued Geography Codes (Primary code)",
    "Secondary geo Code",
    "Tertiary geo Code",
    "Quaternary geo Code",
    "Quinary geo Code",
    "Super-Tag",
    "Super-tag code",
    "Sector",
    "Sector Code",
    "Sub-Sector",
    "Sub-Sector Code",
    "Dataset -Sector Mapping Code",
    "Indicator ",
    "Indicator Code",
    "Measurement Type of Indicator",
    "Indicator date",
    "Sub-Indicator ",
    "Sub-Indicator Code",
    "Dataset- Sector- Indicator Mapping Code",
    "Unit",
    "Value",
    "Keywords",
    "Temporal data ",
    "Temporal Indicator name",
    "Temporal Indicator linking Code",
    "Temporal time period ",
]

ALLOWED_MEASUREMENT_TYPES = [
    "Quantitative - Discrete",
    "Quantitative - Continuous",
    "Categorical - Nominal",
    "Categorical - Nominal-Text",
    "Categorical - Ordinal",
]

GEO_CUT_VALUE_COLUMNS = {
    "Rural": "rural_pct",
    "Urban": "urban_pct",
    "Total": "total_pct",
}


def clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "na"}:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_col_name(col: Any) -> str:
    text = str(col).strip().lower()
    text = text.replace("%", "pct")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_col_name(c) for c in df.columns]
    return df


def normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean_text(value).lower()).strip()


def safe_int(value: Any):
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        match = re.search(r"(19|20)\d{2}", text)
        return int(match.group(0)) if match else None


def clean_year_display(value: Any) -> str:
    """Return year as a clean 4-digit string. Example: 2022.0 -> 2022."""
    year = safe_int(value)
    return str(year) if year is not None else clean_text(value)


def read_raw_file(path: str) -> pd.DataFrame:
    df = normalize_columns(pd.read_excel(path))
    required = [
        "state", "state_lgd_code", "district", "district_lgd_name", "district_lgd_code",
        "indicator", "sub_indicator", "rural_pct", "urban_pct", "total_pct", "year", "unit"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Raw file missing required columns: {missing}\nAvailable columns: {list(df.columns)}")
    df["indicator"] = df["indicator"].map(clean_text)
    df["sub_indicator"] = df["sub_indicator"].map(clean_text)
    df["year"] = df["year"].map(clean_year_display)
    return df


def read_taxonomy(path: str) -> pd.DataFrame:
    df = normalize_columns(pd.read_excel(path))
    required = ["super_tag_code", "super_tag", "sector_code", "sector", "sub_sector_code", "sub_sector"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Taxonomy file missing required columns: {missing}\nAvailable columns: {list(df.columns)}")
    for col in required:
        df[col] = df[col].map(clean_text)
    return df


def read_latlong(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    header_row = None
    for idx, row in raw.iterrows():
        values = [normalize_key(x) for x in row.tolist()]
        if "geo level" in values and "geo name" in values:
            header_row = idx
            break
    if header_row is None:
        print("[WARN] Could not find lat-long header row. Latitude/longitude will be NA.")
        return pd.DataFrame()
    return normalize_columns(pd.read_excel(path, header=header_row))


def valid_uid(value: Any) -> bool:
    return bool(re.fullmatch(r"\d+_\d+_\d+_\d{4}", clean_text(value)))


def extract_year_from_uid(uid: str):
    uid = clean_text(uid)
    if valid_uid(uid):
        return int(uid[-4:])
    return None


def read_metadata(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        print("[WARN] Metadata file not found. Unique Dataset Identifier will be blank.")
        return pd.DataFrame()

    df = pd.read_excel(path)
    df = normalize_columns(df)

    if "unique_dataset_identifier" not in df.columns:
        raise ValueError(f"Metadata file must contain 'Unique Dataset Identifier'. Available columns: {list(df.columns)}")

    df = df.copy()
    df["unique_dataset_identifier"] = df["unique_dataset_identifier"].map(clean_text)
    df = df[df["unique_dataset_identifier"].map(valid_uid)].copy()

    if df.empty:
        raise ValueError("No valid Unique Dataset Identifier found in Metadata.xlsx. Expected format like 106_01_02_2020.")

    if "published_start_year" not in df.columns:
        df["published_start_year"] = ""
    if "published_end_year" not in df.columns:
        df["published_end_year"] = ""
    if "geographic_granularity" not in df.columns:
        df["geographic_granularity"] = ""

    df["uid_year"] = df["unique_dataset_identifier"].map(extract_year_from_uid)
    df["published_start_year_num"] = df["published_start_year"].map(safe_int)
    df["published_end_year_num"] = df["published_end_year"].map(safe_int)
    df["geo_level_from_metadata"] = df["geographic_granularity"].map(derive_default_geo_level_from_text)

    keep = [
        "unique_dataset_identifier",
        "uid_year",
        "published_start_year_num",
        "published_end_year_num",
        "geographic_granularity",
        "geo_level_from_metadata",
    ]
    return df[keep].drop_duplicates()


def derive_default_geo_level_from_text(text: Any) -> str:
    text = clean_text(text).lower()
    if "district" in text:
        return "District"
    if "state" in text:
        return "State"
    if "urban local government" in text or "ulg" in text:
        return "Urban local government (ULG)"
    return "State"


def build_metadata_lookup(metadata_df: pd.DataFrame) -> dict:
    if metadata_df.empty:
        return {"by_year": {}, "fallback_uid": "", "fallback_geo_level": "State", "table": metadata_df}

    by_year = {}
    for _, row in metadata_df.iterrows():
        uid = clean_text(row.get("unique_dataset_identifier", ""))
        uid_year = row.get("uid_year")
        start_year = row.get("published_start_year_num")
        end_year = row.get("published_end_year_num")
        geo_level = clean_text(row.get("geo_level_from_metadata", "")) or "State"

        candidate_years = set()
        for y in [uid_year, start_year, end_year]:
            if pd.notna(y) and y:
                candidate_years.add(int(y))

        if pd.notna(start_year) and pd.notna(end_year) and start_year and end_year:
            s, e = int(start_year), int(end_year)
            if 1900 <= s <= e <= 2100:
                candidate_years.update(range(s, e + 1))

        for year in candidate_years:
            by_year[year] = {"uid": uid, "geo_level": geo_level}

    first = metadata_df.iloc[0]
    return {
        "by_year": by_year,
        "fallback_uid": clean_text(first.get("unique_dataset_identifier", "")),
        "fallback_geo_level": clean_text(first.get("geo_level_from_metadata", "")) or "State",
        "table": metadata_df,
    }


def replace_uid_year(uid: str, year: int) -> str:
    uid = clean_text(uid)
    if valid_uid(uid) and 1900 <= int(year) <= 2100:
        return re.sub(r"\d{4}$", str(int(year)), uid)
    return uid


def complete_metadata_lookup_for_raw_years(metadata_lookup: dict, raw_df: pd.DataFrame) -> dict:
    """
    Metadata file may contain the dataset-series UID only once, for example 106_01_02_2018.
    If the raw file has Year values such as 2020-2025 and Metadata does not provide
    separate rows for those years, create year-wise UIDs by replacing the final year
    part of the fallback UID.
    """
    lookup = dict(metadata_lookup)
    by_year = dict(lookup.get("by_year", {}))
    fallback_uid = clean_text(lookup.get("fallback_uid", ""))
    fallback_geo_level = clean_text(lookup.get("fallback_geo_level", "")) or "State"

    raw_years = sorted({
        y for y in raw_df["year"].map(safe_int).dropna().astype(int).tolist()
        if 1900 <= y <= 2100
    })

    for year in raw_years:
        if year not in by_year:
            by_year[year] = {
                "uid": replace_uid_year(fallback_uid, year),
                "geo_level": fallback_geo_level,
                "source": "derived_from_raw_year",
            }

    lookup["by_year"] = by_year
    return lookup


def get_metadata_for_year(year_value: Any, metadata_lookup: dict) -> dict:
    year = safe_int(year_value)
    if year is not None and year in metadata_lookup["by_year"]:
        return metadata_lookup["by_year"][year]
    return {
        "uid": metadata_lookup.get("fallback_uid", ""),
        "geo_level": metadata_lookup.get("fallback_geo_level", "State"),
    }


def get_gemini_client():
    if genai is None:
        return None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def taxonomy_options_text(taxonomy_df: pd.DataFrame) -> str:
    rows = taxonomy_df[["super_tag", "sector", "sub_sector"]].drop_duplicates().to_dict("records")
    return "\n".join(
        f'- Super-Tag: {r["super_tag"]} | Sector: {r["sector"]} | Sub-Sector: {r["sub_sector"]}'
        for r in rows if clean_text(r.get("sub_sector", ""))
    )


def parse_json_response(text: str) -> dict:
    text = clean_text(text)
    text = re.sub(r"^```json|```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def fallback_keywords_from_indicator(indicator: str, sub_indicators: list[str]) -> str:
    """
    Generic fallback keywords only.
    Used when Gemini is unavailable or API key is invalid.
    This is intentionally NOT hardcoded to employment/labour keywords.
    """
    text = clean_text(f"{indicator} {' '.join(sub_indicators[:8])}")

    stop_words = {
        "total", "number", "percentage", "distribution", "with", "without", "from",
        "into", "purpose", "purposes", "indicator", "and", "the", "for", "of",
        "in", "by", "to", "as", "on", "rural", "urban"
    }

    tokens = [
        w.strip()
        for w in re.findall(r"[A-Za-z][A-Za-z0-9()/-]*", text)
        if len(w.strip()) > 2 and w.strip().lower() not in stop_words
    ]
    unique_tokens = list(dict.fromkeys(tokens))

    tags = []
    if clean_text(indicator):
        tags.append(clean_text(indicator))
    if len(unique_tokens) >= 2:
        tags.append(" ".join(unique_tokens[:2]))
    if len(unique_tokens) >= 3:
        tags.append(" ".join(unique_tokens[:3]))
    tags.extend(unique_tokens[:8])

    return ", ".join(dict.fromkeys([clean_text(tag) for tag in tags if clean_text(tag)]))


def fallback_classification(indicator: str, sub_indicators: list[str], taxonomy_df: pd.DataFrame) -> dict:
    """
    Fallback classification when Gemini is unavailable or fails.
    Keeps taxonomy fallback, but keywords are generated from the current indicator only.
    """
    tax = taxonomy_df.copy()
    tax["combined"] = (tax["sector"] + " " + tax["sub_sector"]).str.lower()
    match = tax[tax["combined"].str.contains("health|maternal|delivery|mortality|anaemia|sanitation|water|crime|women|safety|employment|livelihood|labour|labor|worker|work", regex=True, na=False)]
    if match.empty:
        match = tax[tax["sub_sector"].map(clean_text) != ""]
    row = match.iloc[0] if not match.empty else taxonomy_df.iloc[0]

    return {
        "measurement_type": "Quantitative - Continuous",
        "sub_sector": clean_text(row["sub_sector"]),
        "sector": clean_text(row["sector"]),
        "keywords": fallback_keywords_from_indicator(indicator, sub_indicators),
        "source": "fallback_current_indicator_generic",
    }


def llm_classify_indicator(indicator: str, sub_indicators: list[str], taxonomy_df: pd.DataFrame, client) -> dict:
    if client is None:
        return fallback_classification(indicator, sub_indicators, taxonomy_df)

    prompt = f"""
You are helping prepare a CDAP-compliant dataset.

The indicator text is already rephrased. Do NOT rephrase it.
The raw file already provides the unit. Do NOT decide unit.

Your task is only to choose:
1. Measurement Type of Indicator
2. One Sub-Sector from the taxonomy below
3. Search keywords

Indicator:
{indicator}

Sample sub-indicators:
{', '.join(sub_indicators[:12]) if sub_indicators else 'None'}

Allowed measurement types:
- Quantitative - Discrete
- Quantitative - Continuous
- Categorical - Nominal
- Categorical - Nominal-Text
- Categorical - Ordinal

Taxonomy options:
{taxonomy_options_text(taxonomy_df)}

Rules:
- Since this dataset contains percentage values, choose Quantitative - Continuous unless there is a stronger reason otherwise.
- Choose exactly one sub-sector that exists in the taxonomy list.
- Return JSON only.
- JSON keys: measurement_type, sub_sector, keywords
- Generate 8 to 12 comma-separated phrase-level search tags.
- Keywords must be specific to the current indicator and must not reuse unrelated dataset keywords.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.1},
        )
        result = parse_json_response(response.text)
        mt = clean_text(result.get("measurement_type", "Quantitative - Continuous"))
        if mt not in ALLOWED_MEASUREMENT_TYPES:
            mt = "Quantitative - Continuous"
        keywords = result.get("keywords", "")
        if isinstance(keywords, list):
            keywords = ", ".join(clean_text(x) for x in keywords if clean_text(x))
        return {
            "measurement_type": mt,
            "sub_sector": clean_text(result.get("sub_sector", "")),
            "keywords": clean_text(keywords),
            "source": "gemini",
        }
    except Exception as exc:
        print(f"[WARN] Gemini failed for indicator: {indicator}. Using fallback. Error: {exc}")
        return fallback_classification(indicator, sub_indicators, taxonomy_df)


def match_taxonomy_by_sub_sector(sub_sector: str, taxonomy_df: pd.DataFrame) -> dict:
    target = normalize_key(sub_sector)
    tax = taxonomy_df.copy()
    tax["sub_sector_key"] = tax["sub_sector"].map(normalize_key)
    exact = tax[tax["sub_sector_key"] == target]
    if exact.empty and target:
        exact = tax[tax["sub_sector_key"].str.contains(re.escape(target), na=False)]
    if exact.empty:
        exact = tax[tax["sub_sector"].map(clean_text) != ""]
    row = exact.iloc[0]
    return {
        "Super-Tag": clean_text(row.get("super_tag", "")),
        "Super-tag code": clean_text(row.get("super_tag_code", "")),
        "Sector": clean_text(row.get("sector", "")),
        "Sector Code": clean_text(row.get("sector_code", "")),
        "Sub-Sector": clean_text(row.get("sub_sector", "")),
        "Sub-Sector Code": clean_text(row.get("sub_sector_code", "")),
    }


def derive_geo_cut(indicator: str) -> str:
    text = clean_text(indicator).lower()
    if text.startswith("rural:"):
        return "Rural"
    if text.startswith("urban:"):
        return "Urban"
    if text.startswith("total:"):
        return "Total"
    return "Total"


def load_indicator_master(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=["indicator_code", "rephrased_indicator"])
    df = normalize_columns(pd.read_excel(path))
    if "indicator_code" not in df.columns:
        df["indicator_code"] = pd.NA
    if "rephrased_indicator" not in df.columns:
        indicator_cols = [c for c in df.columns if "indicator" in c and c != "indicator_code"]
        df["rephrased_indicator"] = df[indicator_cols[0]] if indicator_cols else ""
    df["indicator_code"] = pd.to_numeric(df["indicator_code"], errors="coerce").astype("Int64")
    df["rephrased_indicator"] = df["rephrased_indicator"].map(clean_text)
    return df


def assign_indicator_codes(unique_indicators: list[str], master_df: pd.DataFrame) -> dict:
    lookup = {}
    for _, row in master_df.iterrows():
        name = normalize_key(row.get("rephrased_indicator", ""))
        code = row.get("indicator_code")
        if name and pd.notna(code):
            lookup[name] = int(code)

    used_codes = set(pd.to_numeric(master_df.get("indicator_code", pd.Series(dtype="object")), errors="coerce").dropna().astype(int).tolist())
    next_code = (max(used_codes) + 1) if used_codes else 1

    assigned = {}
    for indicator in unique_indicators:
        key = normalize_key(indicator)
        if key in lookup:
            assigned[indicator] = lookup[key]
        else:
            while next_code in used_codes:
                next_code += 1
            assigned[indicator] = next_code
            used_codes.add(next_code)
            next_code += 1
    return assigned


def load_temporal_log(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=["temporal_indicator_name", "temporal_indicator_linking_code", "source"])
    df = normalize_columns(pd.read_excel(path))
    if "temporal_indicator_name" not in df.columns:
        df["temporal_indicator_name"] = ""
    if "temporal_indicator_linking_code" not in df.columns:
        df["temporal_indicator_linking_code"] = ""
    df["temporal_indicator_name"] = df["temporal_indicator_name"].map(clean_text)
    df["temporal_indicator_linking_code"] = df["temporal_indicator_linking_code"].map(clean_text)
    return df


def next_temporal_code(log_df: pd.DataFrame) -> int:
    max_num = 0
    if "temporal_indicator_linking_code" in log_df.columns:
        for value in log_df["temporal_indicator_linking_code"].dropna().tolist():
            match = re.fullmatch(r"T_(\d+)", clean_text(value))
            if match:
                max_num = max(max_num, int(match.group(1)))
    return max_num + 1


def assign_temporal_codes(unique_indicators: list[str], temporal_log_df: pd.DataFrame) -> dict:
    lookup = {}
    for _, row in temporal_log_df.iterrows():
        name_key = normalize_key(row.get("temporal_indicator_name", ""))
        code = clean_text(row.get("temporal_indicator_linking_code", ""))
        if name_key and re.fullmatch(r"T_\d+", code):
            lookup[name_key] = code

    next_num = next_temporal_code(temporal_log_df)
    assigned = {}
    used_codes = set(lookup.values())

    for indicator in unique_indicators:
        key = normalize_key(indicator)
        if key in lookup:
            assigned[indicator] = lookup[key]
        else:
            code = f"T_{next_num}"
            while code in used_codes:
                next_num += 1
                code = f"T_{next_num}"
            assigned[indicator] = code
            used_codes.add(code)
            next_num += 1
    return assigned


def build_mapping(raw_df: pd.DataFrame, taxonomy_df: pd.DataFrame, master_df: pd.DataFrame, temporal_log_df: pd.DataFrame) -> pd.DataFrame:
    unique_indicators = sorted(raw_df["indicator"].dropna().map(clean_text).unique().tolist())
    indicator_codes = assign_indicator_codes(unique_indicators, master_df)
    temporal_codes = assign_temporal_codes(unique_indicators, temporal_log_df)
    client = get_gemini_client()
    rows = []

    for i, indicator in enumerate(unique_indicators, start=1):
        subset = raw_df[raw_df["indicator"].map(clean_text) == indicator]
        sub_indicators = subset["sub_indicator"].dropna().map(clean_text).drop_duplicates().tolist()
        print(f"[{i}/{len(unique_indicators)}] Classifying: {indicator}")
        result = llm_classify_indicator(indicator, sub_indicators, taxonomy_df, client)
        tax = match_taxonomy_by_sub_sector(result.get("sub_sector", ""), taxonomy_df)
        rows.append({
            "Indicator": indicator,
            "Indicator Code": indicator_codes[indicator],
            "Temporal Indicator linking Code": temporal_codes[indicator],
            "Measurement Type of Indicator": result.get("measurement_type", "Quantitative - Continuous"),
            "Keywords": result.get("keywords", ""),
            "Classification Source": result.get("source", ""),
            **tax,
        })
        if client is not None:
            time.sleep(0.3)
    return pd.DataFrame(rows)


def update_indicator_master(master_df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    out = master_df.copy()
    if "indicator_code" not in out.columns:
        out["indicator_code"] = pd.NA
    if "rephrased_indicator" not in out.columns:
        out["rephrased_indicator"] = ""

    existing = set(out["rephrased_indicator"].map(normalize_key).tolist())
    new_rows = []
    for _, row in mapping_df.iterrows():
        name = clean_text(row["Indicator"])
        if normalize_key(name) not in existing:
            new_rows.append({
                "indicator_code": int(row["Indicator Code"]),
                "rephrased_indicator": name,
            })
            existing.add(normalize_key(name))

    if new_rows:
        out = pd.concat([out, pd.DataFrame(new_rows)], ignore_index=True)
    return out


def update_temporal_log(temporal_log_df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    out = temporal_log_df.copy()
    if "temporal_indicator_name" not in out.columns:
        out["temporal_indicator_name"] = ""
    if "temporal_indicator_linking_code" not in out.columns:
        out["temporal_indicator_linking_code"] = ""

    existing = set(out["temporal_indicator_name"].map(normalize_key).tolist())
    new_rows = []
    for _, row in mapping_df.iterrows():
        name = clean_text(row["Indicator"])
        if normalize_key(name) not in existing:
            new_rows.append({
                "temporal_indicator_name": name,
                "temporal_indicator_linking_code": clean_text(row["Temporal Indicator linking Code"]),
                "source": "generated_by_pipeline",
            })
            existing.add(normalize_key(name))

    if new_rows:
        out = pd.concat([out, pd.DataFrame(new_rows)], ignore_index=True)
    return out


def build_geo_lookup(latlong_df: pd.DataFrame) -> dict:
    lookup = {}
    if latlong_df.empty or "geo_name" not in latlong_df.columns:
        return lookup
    for _, row in latlong_df.iterrows():
        name = normalize_key(row.get("geo_name", ""))
        code = normalize_key(row.get("primary_lgd_code", ""))
        item = {
            "geo_level": clean_text(row.get("geo_level", "")),
            "geo_name": clean_text(row.get("geo_name", "")),
            "primary_lgd_code": clean_text(row.get("primary_lgd_code", "")),
            "latitude": clean_text(row.get("latitude", "")),
            "longitude": clean_text(row.get("longitude", "")),
        }
        if name:
            lookup[("name", name)] = item
        if code:
            lookup[("code", code)] = item
    return lookup


def clean_lgd_code_for_geo(value: Any) -> str:
    """Clean LGD code values only for geography code fields, e.g. 603.0 -> 603."""
    text = clean_text(value)
    if not text:
        return ""

    compact = text.replace(",", "").strip()
    try:
        num = float(compact)
        if num.is_integer():
            return str(int(num))
    except Exception:
        pass

    match = re.fullmatch(r"(\d+)\.0+", compact)
    if match:
        return match.group(1)

    return compact


def get_first_geo_value(raw_row: pd.Series, candidate_cols: list[str], *, is_code: bool = False) -> str:
    """Return the first non-empty value from possible geography columns."""
    for col in candidate_cols:
        if col in raw_row.index:
            value = raw_row.get(col, "")
            cleaned = clean_lgd_code_for_geo(value) if is_code else clean_text(value)
            if cleaned:
                return cleaned
    return ""


def has_any_geo_header(raw_row: pd.Series, candidate_cols: list[str]) -> bool:
    """Check whether any of the possible geography headers exists in the raw row."""
    return any(col in raw_row.index for col in candidate_cols)


def get_geo_details(raw_row: pd.Series, geo_lookup: dict, metadata_row: dict) -> dict:
    """
    Geography mapping logic.

    Senior-dev rule:
    - If ULG/ULB/Urban Local Government columns are present, only then use LAT LONG.xlsx.
    - If there are no ULG headers, never use LAT LONG.xlsx.
    - If District/District LGD Name + District LGD Code are present, treat as District-level.
      District wins even if State and State LGD Code are also present.
    - If district is blank/NA but State + State LGD Code are present, treat as State-level.
    - For State/District rows, latitude and longitude must be hardcoded as NA.
    """

    # ULG/ULB headers after normalize_columns(). Add more aliases here if a new raw file uses a new naming style.
    ulg_name_cols = [
        "ulg",
        "ulg_name",
        "ulb",
        "ulb_name",
        "urban_local_government",
        "urban_local_government_name",
        "urban_local_government_ulg",
        "urban_local_government_ulg_name",
        "urban_local_body",
        "urban_local_body_name",
    ]
    ulg_lgd_cols = [
        "ulg_lgd_code",
        "ulg_code",
        "ulb_lgd_code",
        "ulb_code",
        "urban_local_government_lgd_code",
        "urban_local_government_code",
        "urban_local_government_ulg_lgd_code",
        "urban_local_government_ulg_code",
        "urban_local_body_lgd_code",
        "urban_local_body_code",
    ]

    has_ulg_header = has_any_geo_header(raw_row, ulg_name_cols + ulg_lgd_cols)

    # District name can come from District or District LGD Name.
    district = get_first_geo_value(raw_row, ["district", "district_lgd_name"])
    district_lgd = get_first_geo_value(raw_row, ["district_lgd_code"], is_code=True)
    state = get_first_geo_value(raw_row, ["state", "state_lgd_name"])
    state_lgd = get_first_geo_value(raw_row, ["state_lgd_code"], is_code=True)

    # Only ULG files should use LAT LONG.xlsx.
    if has_ulg_header:
        ulg_name = get_first_geo_value(raw_row, ulg_name_cols)
        ulg_lgd = get_first_geo_value(raw_row, ulg_lgd_cols, is_code=True)

        geo_name = ulg_name or district or state
        lgd_code = ulg_lgd or district_lgd or state_lgd or DEFAULT_NA_CODE
        geo_level = "Urban local government (ULG)"

        matched = geo_lookup.get(("code", normalize_key(lgd_code))) or geo_lookup.get(("name", normalize_key(geo_name)))
        if matched:
            return {
                "Geo-Level": clean_text(matched.get("geo_level", "")) or geo_level,
                "Geo-Name": clean_text(matched.get("geo_name", "")) or geo_name,
                "LGD Code 1 (Primary LGD Code)": clean_lgd_code_for_geo(matched.get("primary_lgd_code", "")) or lgd_code,
                "Latitude for Geo-Name": clean_text(matched.get("latitude", "")) or "NA",
                "Longitude for Geo-Name": clean_text(matched.get("longitude", "")) or "NA",
            }

        return {
            "Geo-Level": geo_level,
            "Geo-Name": geo_name,
            "LGD Code 1 (Primary LGD Code)": lgd_code,
            "Latitude for Geo-Name": "NA",
            "Longitude for Geo-Name": "NA",
        }

    # No ULG header: District/State must NOT use LAT LONG.xlsx.
    # District wins whenever district name + district code are present.
    if district and district_lgd:
        return {
            "Geo-Level": "District",
            "Geo-Name": district,
            "LGD Code 1 (Primary LGD Code)": district_lgd,
            "Latitude for Geo-Name": "NA",
            "Longitude for Geo-Name": "NA",
        }

    # State-level fallback: only when district is unavailable.
    return {
        "Geo-Level": "State",
        "Geo-Name": state,
        "LGD Code 1 (Primary LGD Code)": state_lgd or DEFAULT_NA_CODE,
        "Latitude for Geo-Name": "NA",
        "Longitude for Geo-Name": "NA",
    }


def is_blank_sub_indicator(value: Any) -> bool:
    """Treat blank/NA/null sub-indicators as not available."""
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"na", "n/a", "nan", "none", "null", "-"}


def final_sub_indicator_value(value: Any) -> str:
    """Final CDAP output should show NA when sub-indicator is not available."""
    return "NA" if is_blank_sub_indicator(value) else clean_text(value)


def sub_indicator_code(indicator_code: int, sub_indicator: Any, code_map: dict) -> str:
    """
    Format: [Indicator Code]_[Sub-indicator Number].
    If sub-indicator is not available, use 99.
    Example: 1381_99
    """
    if is_blank_sub_indicator(sub_indicator):
        return f"{indicator_code}_99"

    key = (indicator_code, normalize_key(sub_indicator))
    if key not in code_map:
        count = sum(1 for existing in code_map if existing[0] == indicator_code) + 1
        code_map[key] = f"{indicator_code}_{count:02d}"
    return code_map[key]


def build_final(raw_df: pd.DataFrame, mapping_df: pd.DataFrame, latlong_df: pd.DataFrame, metadata_lookup: dict) -> pd.DataFrame:
    geo_lookup = build_geo_lookup(latlong_df)
    mapping_lookup = {clean_text(r["Indicator"]): r for _, r in mapping_df.iterrows()}
    rows = []
    sub_code_map = {}

    for _, raw_row in raw_df.iterrows():
        indicator = clean_text(raw_row.get("indicator", ""))
        if not indicator:
            continue

        raw_year = clean_year_display(raw_row.get("year", ""))
        metadata_row = get_metadata_for_year(raw_year, metadata_lookup)
        dataset_id = clean_text(metadata_row.get("uid", ""))

        # Final CDAP year fields should align with the UID year.
        # Example: UID 106_01_03_2023 -> Indicator date = 2023, Temporal time period = 2023.
        uid_year = extract_year_from_uid(dataset_id)
        year = str(uid_year) if uid_year is not None else raw_year

        geo_cut = derive_geo_cut(indicator)
        value_col = GEO_CUT_VALUE_COLUMNS.get(geo_cut, "total_pct")
        value = raw_row.get(value_col, "")
        try:
            if pd.notna(value) and clean_text(value) != "":
                value = round(float(value), 2)
            else:
                value = ""
        except Exception:
            value = clean_text(value)

        map_row = mapping_lookup[indicator]
        indicator_code = int(map_row["Indicator Code"])
        raw_sub_ind = raw_row.get("sub_indicator", "")
        sub_ind = final_sub_indicator_value(raw_sub_ind)
        sub_code = sub_indicator_code(indicator_code, raw_sub_ind, sub_code_map)
        geo = get_geo_details(raw_row, geo_lookup, metadata_row)

        sub_sector_code = clean_text(map_row.get("Sub-Sector Code", ""))
        dataset_sector_mapping_code = f"{dataset_id}_{sub_sector_code}" if dataset_id and sub_sector_code else ""
        ds_indicator_mapping_code = f"{dataset_id}_{sub_sector_code}_{sub_code}" if dataset_id and sub_sector_code and sub_code else ""

        row = {
            "Unique Dataset Identifier": dataset_id,
            **geo,
            "Geo-cut": geo_cut,
            "Discontinued Geography Codes (Primary code)": DEFAULT_NA_CODE,
            "Secondary geo Code": DEFAULT_NA_CODE,
            "Tertiary geo Code": DEFAULT_NA_CODE,
            "Quaternary geo Code": DEFAULT_NA_CODE,
            "Quinary geo Code": DEFAULT_NA_CODE,
            "Super-Tag": clean_text(map_row.get("Super-Tag", "")),
            "Super-tag code": clean_text(map_row.get("Super-tag code", "")),
            "Sector": clean_text(map_row.get("Sector", "")),
            "Sector Code": clean_text(map_row.get("Sector Code", "")),
            "Sub-Sector": clean_text(map_row.get("Sub-Sector", "")),
            "Sub-Sector Code": sub_sector_code,
            "Dataset -Sector Mapping Code": dataset_sector_mapping_code,
            "Indicator ": indicator,
            "Indicator Code": indicator_code,
            "Measurement Type of Indicator": clean_text(map_row.get("Measurement Type of Indicator", "Quantitative - Continuous")),
            "Indicator date": year,
            "Sub-Indicator ": sub_ind,
            "Sub-Indicator Code": sub_code,
            "Dataset- Sector- Indicator Mapping Code": ds_indicator_mapping_code,
            "Unit": clean_text(raw_row.get("unit", "")) or "Percentage",
            "Value": value,
            "Keywords": clean_text(map_row.get("Keywords", "")),
            "Temporal data ": "Yes",
            "Temporal Indicator name": indicator,
            "Temporal Indicator linking Code": clean_text(map_row.get("Temporal Indicator linking Code", "")),
            "Temporal time period ": year,
        }
        rows.append(row)

    final_df = pd.DataFrame(rows)
    for col in FINAL_COLUMNS:
        if col not in final_df.columns:
            final_df[col] = ""
    return final_df[FINAL_COLUMNS]



def safe_to_excel(df: pd.DataFrame, filename: str) -> str:
    try:
        df.to_excel(filename, index=False)
        return filename
    except PermissionError:
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{stem}_{timestamp}{suffix}"
        df.to_excel(new_filename, index=False)
        print(f"[WARN] {filename} is locked/open. Saved instead as {new_filename}")
        return new_filename


def safe_to_csv(df: pd.DataFrame, filename: str) -> str:
    try:
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        return filename
    except PermissionError:
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{stem}_{timestamp}{suffix}"
        df.to_csv(new_filename, index=False, encoding="utf-8-sig")
        print(f"[WARN] {filename} is locked/open. Saved instead as {new_filename}")
        return new_filename


def write_outputs(final_df: pd.DataFrame, mapping_df: pd.DataFrame, updated_master_df: pd.DataFrame, updated_temporal_log_df: pd.DataFrame, metadata_lookup: dict) -> None:
    safe_to_excel(final_df, OUTPUT_FINAL_XLSX)
    safe_to_csv(final_df, OUTPUT_FINAL_CSV)
    safe_to_excel(mapping_df, OUTPUT_MAPPING_XLSX)

    master_out = updated_master_df.copy()
    rename = {}
    if "indicator_code" in master_out.columns:
        rename["indicator_code"] = "Indicator_code"
    if "rephrased_indicator" in master_out.columns:
        rename["rephrased_indicator"] = "Rephrased Indicator"
    safe_to_excel(master_out.rename(columns=rename), OUTPUT_INDICATOR_MASTER_XLSX)

    temp_out = updated_temporal_log_df.copy()
    rename_temp = {}
    if "temporal_indicator_name" in temp_out.columns:
        rename_temp["temporal_indicator_name"] = "Temporal Indicator name"
    if "temporal_indicator_linking_code" in temp_out.columns:
        rename_temp["temporal_indicator_linking_code"] = "Temporal Indicator linking Code"
    safe_to_excel(temp_out.rename(columns=rename_temp), OUTPUT_TEMPORAL_LOG_XLSX)

    year_rows = []
    for year, item in sorted(metadata_lookup.get("by_year", {}).items()):
        year_rows.append({
            "Year": year,
            "Unique Dataset Identifier": item.get("uid", ""),
            "Geo-Level from Metadata": item.get("geo_level", ""),
        })
    safe_to_excel(pd.DataFrame(year_rows), OUTPUT_METADATA_MAPPING_XLSX)



def run_cdap_pipeline(
    raw_file: str,
    taxonomy_file: str,
    latlong_file: str,
    metadata_file: str,
    indicator_master_file: str,
    temporal_log_file: str,
    output_final_xlsx: str = "final_cdap_output.xlsx",
    output_final_csv: str = "final_cdap_output.csv",
    output_indicator_master_xlsx: str = "Indicators_list_updated.xlsx",
    output_temporal_log_xlsx: str = "Temporal_indicator_log_updated.xlsx",
    output_mapping_xlsx: str = "indicator_mapping_generated.xlsx",
    output_metadata_mapping_xlsx: str = "metadata_year_mapping_used.xlsx",
) -> dict:
    """Parameterized runner for the merged CDAP transformation-standardization system."""
    try:
        print("=" * 80)
        print("CDAP STANDARDIZATION PIPELINE - FIXED PARAMETERIZED VERSION")
        print("=" * 80)
        print("Reading inputs...")
        raw_df = read_raw_file(raw_file)
        taxonomy_df = read_taxonomy(taxonomy_file)
        latlong_df = read_latlong(latlong_file)
        metadata_df = read_metadata(metadata_file)
        metadata_lookup = build_metadata_lookup(metadata_df)
        metadata_lookup = complete_metadata_lookup_for_raw_years(metadata_lookup, raw_df)
        master_df = load_indicator_master(indicator_master_file)
        temporal_log_df = load_temporal_log(temporal_log_file)

        print(f"Raw rows: {len(raw_df)}")
        print(f"Taxonomy rows: {len(taxonomy_df)}")
        print(f"Unique indicators: {raw_df['indicator'].dropna().map(clean_text).nunique()}")

        mapping_df = build_mapping(raw_df, taxonomy_df, master_df, temporal_log_df)
        updated_master_df = update_indicator_master(master_df, mapping_df)
        updated_temporal_log_df = update_temporal_log(temporal_log_df, mapping_df)
        final_df = build_final(raw_df, mapping_df, latlong_df, metadata_lookup)

        uid_years = final_df["Unique Dataset Identifier"].astype(str).str.extract(r"(\d{4})$")[0]
        mismatch_count = (
            (uid_years != final_df["Indicator date"].astype(str))
            | (uid_years != final_df["Temporal time period "].astype(str))
        ).sum()
        print(f"Year mismatch count: {int(mismatch_count)}")

        out_final_xlsx = safe_to_excel(final_df, output_final_xlsx)
        out_final_csv = safe_to_csv(final_df, output_final_csv)
        out_mapping = safe_to_excel(mapping_df, output_mapping_xlsx)

        master_out = updated_master_df.copy()
        rename = {}
        if "indicator_code" in master_out.columns:
            rename["indicator_code"] = "Indicator_code"
        if "rephrased_indicator" in master_out.columns:
            rename["rephrased_indicator"] = "Rephrased Indicator"
        out_master = safe_to_excel(master_out.rename(columns=rename), output_indicator_master_xlsx)

        temp_out = updated_temporal_log_df.copy()
        rename_temp = {}
        if "temporal_indicator_name" in temp_out.columns:
            rename_temp["temporal_indicator_name"] = "Temporal Indicator name"
        if "temporal_indicator_linking_code" in temp_out.columns:
            rename_temp["temporal_indicator_linking_code"] = "Temporal Indicator linking Code"
        out_temporal = safe_to_excel(temp_out.rename(columns=rename_temp), output_temporal_log_xlsx)

        year_rows = []
        for year, item in sorted(metadata_lookup.get("by_year", {}).items()):
            year_rows.append({
                "Year": year,
                "Unique Dataset Identifier": item.get("uid", ""),
                "Geo-Level from Metadata": item.get("geo_level", ""),
            })
        out_metadata_mapping = safe_to_excel(pd.DataFrame(year_rows), output_metadata_mapping_xlsx)

        print("=" * 80)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print(f"Final XLSX: {out_final_xlsx}")
        print(f"Rows created: {len(final_df)}")
        print(f"Indicator codes assigned: {sorted(mapping_df['Indicator Code'].astype(int).unique().tolist())}")
        print(f"Temporal codes assigned: {sorted(mapping_df['Temporal Indicator linking Code'].unique().tolist(), key=lambda x: int(str(x).split('_')[1]))}")

        return {
            "success": True,
            "final_output": out_final_xlsx,
            "final_output_csv": out_final_csv,
            "intermediate_outputs": [out_mapping, out_master, out_temporal, out_metadata_mapping],
            "rows_created": len(final_df),
            "error": None,
        }
    except Exception as e:
        error_msg = f"Pipeline failed: {e}"
        print(f"[ERROR] {error_msg}")
        return {
            "success": False,
            "final_output": None,
            "final_output_csv": None,
            "intermediate_outputs": [],
            "rows_created": 0,
            "error": error_msg,
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 7:
        print(
            "Usage: python v36_cdap_pipeline_refactored_fixed.py <raw_file> <taxonomy> "
            "<latlong> <metadata> <indicator_master> <temporal_log> "
            "[final_xlsx] [final_csv] [indicator_master_xlsx] [temporal_log_xlsx] "
            "[mapping_xlsx] [metadata_mapping_xlsx]"
        )
        sys.exit(1)

    result = run_cdap_pipeline(
        raw_file=sys.argv[1],
        taxonomy_file=sys.argv[2],
        latlong_file=sys.argv[3],
        metadata_file=sys.argv[4],
        indicator_master_file=sys.argv[5],
        temporal_log_file=sys.argv[6],
        output_final_xlsx=sys.argv[7] if len(sys.argv) >= 8 else "final_cdap_output.xlsx",
        output_final_csv=sys.argv[8] if len(sys.argv) >= 9 else "final_cdap_output.csv",
        output_indicator_master_xlsx=sys.argv[9] if len(sys.argv) >= 10 else "Indicators_list_updated.xlsx",
        output_temporal_log_xlsx=sys.argv[10] if len(sys.argv) >= 11 else "Temporal_indicator_log_updated.xlsx",
        output_mapping_xlsx=sys.argv[11] if len(sys.argv) >= 12 else "indicator_mapping_generated.xlsx",
        output_metadata_mapping_xlsx=sys.argv[12] if len(sys.argv) >= 13 else "metadata_year_mapping_used.xlsx",
    )
    sys.exit(0 if result["success"] else 1)
