
import re
import sys
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

OUTPUT_COLUMNS = [
    "State",
    "State LGD Code",
    "District",
    "District LGD name",
    "District LGD Code",
    "Indicator",
    "Sub indicator",
    "Rural %",
    "Urban %",
    "Total %",
    "Year",
    "Unit",
]

# Fallback mapping in case the mapping Excel is missing any industry section.
# U is included because some PLFS years have U, while some years do not.
DEFAULT_INDUSTRY_MAPPING = {
    "A": "Agriculture, forestry and fishing",
    "B": "Mining and quarrying",
    "C": "Manufacturing",
    "D": "Electricity, gas, steam and air conditioning supply",
    "E": "Water supply; sewerage, waste management and remediation activities",
    "F": "Construction",
    "G": "Wholesale and retail trade; repair of motor vehicles and motorcycles",
    "H": "Transportation and storage",
    "I": "Accommodation and Food service activities",
    "J": "Information and communication",
    "K": "Financial and insurance activities",
    "L": "Real estate activities",
    "M": "Professional, scientific and technical activities",
    "N": "Administrative and support service activities",
    "O": "Public administration and defence compulsory social security",
    "P": "Education",
    "Q": "Human health and social work activities",
    "R": "Arts, entertainment and recreation",
    "S": "Other service activities",
    "T": "Activities of hhds as employers, undiff goods services prod actvs of hhds for own use",
    "U": "Activities of extraterritorial organizations and bodies",
}

STATE_LGD_MAPPING = {
    "andhra pradesh": ("Andhra Pradesh", "28"),
    "arunachal pradesh": ("Arunachal Pradesh", "12"),
    "assam": ("Assam", "18"),
    "bihar": ("Bihar", "10"),
    "chhattisgarh": ("Chhattisgarh", "22"),
    "delhi": ("Delhi", "7"),
    "goa": ("Goa", "30"),
    "gujarat": ("Gujarat", "24"),
    "haryana": ("Haryana", "6"),
    "himachal pradesh": ("Himachal Pradesh", "2"),
    "jharkhand": ("Jharkhand", "20"),
    "karnataka": ("Karnataka", "29"),
    "kerala": ("Kerala", "32"),
    "madhya pradesh": ("Madhya Pradesh", "23"),
    "maharashtra": ("Maharashtra", "27"),
    "manipur": ("Manipur", "14"),
    "meghalaya": ("Meghalaya", "17"),
    "mizoram": ("Mizoram", "15"),
    "nagaland": ("Nagaland", "13"),
    "odisha": ("Odisha", "21"),
    "punjab": ("Punjab", "3"),
    "rajasthan": ("Rajasthan", "8"),
    "sikkim": ("Sikkim", "11"),
    "tamil nadu": ("Tamil Nadu", "33"),
    "telangana": ("Telangana", "36"),
    "tripura": ("Tripura", "16"),
    "uttarakhand": ("Uttarakhand", "5"),
    "uttar pradesh": ("Uttar Pradesh", "9"),
    "west bengal": ("West Bengal", "19"),
    "andaman & n. island": ("Andaman And Nicobar Islands", "35"),
    "andaman and n. island": ("Andaman And Nicobar Islands", "35"),
    "andaman and nicobar islands": ("Andaman And Nicobar Islands", "35"),
    "chandigarh": ("Chandigarh", "4"),
    "dadra & nagar haveli & daman & diu": ("The Dadra And Nagar Haveli And Daman And Diu", "38"),
    "dadra and nagar haveli and daman and diu": ("The Dadra And Nagar Haveli And Daman And Diu", "38"),
    "the dadra and nagar haveli and daman and diu": ("The Dadra And Nagar Haveli And Daman And Diu", "38"),
    "jammu & kashmir": ("Jammu And Kashmir", "1"),
    "jammu and kashmir": ("Jammu And Kashmir", "1"),
    "ladakh": ("Ladakh", "37"),
    "lakshadweep": ("Lakshadweep", "31"),
    "puducherry": ("Puducherry", "34"),
    "all india": ("all India", "1000"),
}


# ---------------------------------------------------------
# BASIC CLEANING FUNCTIONS
# ---------------------------------------------------------

def clean_text(value):
    """
    Cleans text values coming from Excel.
    Handles blank cells, line breaks, multiple spaces, and non-breaking spaces.
    """
    if pd.isna(value):
        return ""

    value = str(value)
    value = value.replace("\xa0", " ")
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_lookup_key(value):
    value = clean_text(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def state_name_and_lgd_code(state):
    key = normalize_lookup_key(state)
    return STATE_LGD_MAPPING.get(key, (clean_text(state), ""))


def extract_year_from_filename(file_path):
    """
    Extracts year from filename.
    Example:
    Extracted_Data_2023.xlsx -> 2023
    """
    filename = Path(file_path).name
    match = re.search(r"(20\d{2})", filename)

    if not match:
        raise ValueError(
            f"Could not find year in file name: {filename}. "
            "Please keep the year in the extracted data file name, for example: Extracted_Data_2023.xlsx"
        )

    return int(match.group(1))


def normalize_geo_cut(raw_geo_cut):
    """
    Converts PLFS geo-cut text into output format.
    rural -> Rural
    urban -> Urban
    rural+urban -> Total
    """
    raw_geo_cut = clean_text(raw_geo_cut).lower()

    if raw_geo_cut == "rural":
        return "Rural"
    if raw_geo_cut == "urban":
        return "Urban"
    if raw_geo_cut in ["rural+urban", "rural + urban"]:
        return "Total"

    raise ValueError(f"Unknown geo-cut found: {raw_geo_cut}")


def normalize_gender(raw_gender):
    """
    Converts PLFS gender/person text into indicator wording.
    male -> male
    female -> female
    persons -> person
    """
    raw_gender = clean_text(raw_gender).lower()

    if raw_gender == "male":
        return "male"
    if raw_gender == "female":
        return "female"
    if raw_gender in ["person", "persons"]:
        return "person"

    raise ValueError(f"Unknown gender/person category found: {raw_gender}")


def build_indicator(geo_cut, gender):
    """
    Builds the final standardized indicator name.
    """
    return (
        f"{geo_cut}: Percentage distribution of usually working {gender} "
        f"(principal activity status + subsidiary economic activity status) "
        f"by industry of work"
    )


# ---------------------------------------------------------
# MAPPING FILE LOGIC
# ---------------------------------------------------------

def load_industry_mapping(mapping_file):
    """
    Reads Sub_Indicator_Mappings.xlsx.

    Expected column:
    industry_section

    Example values:
    A_Agriculture, forestry and fishing
    U_Activities of extraterritorial organizations and bodies
    """
    mapping = DEFAULT_INDUSTRY_MAPPING.copy()
    mapping_file = Path(mapping_file)

    if not mapping_file.exists():
        raise FileNotFoundError(f"Sub-indicator mapping file not found: {mapping_file}")

    xl = pd.ExcelFile(mapping_file)
    mapping_df = None

    for sheet in xl.sheet_names:
        temp = pd.read_excel(mapping_file, sheet_name=sheet)
        temp.columns = [clean_text(c).lower() for c in temp.columns]

        if "industry_section" in temp.columns:
            mapping_df = temp
            break

    if mapping_df is None:
        raise ValueError(
            "No 'industry_section' column found in Sub_Indicator_Mappings.xlsx. "
            "Please make sure the first row/header is exactly: industry_section"
        )

    for value in mapping_df["industry_section"].dropna():
        value = clean_text(value)

        # Expected format: A_Agriculture, forestry and fishing
        match = re.match(r"^([A-U])_(.+)$", value)

        if match:
            code = match.group(1).strip()
            description = match.group(2).strip()
            mapping[code] = description

    return mapping


# ---------------------------------------------------------
# DYNAMIC TABLE DETECTION LOGIC
# ---------------------------------------------------------

def row_text(df, row_idx):
    """
    Combines all non-empty cells in a row into one searchable string.
    This helps when the table title is not strictly in column A.
    """
    values = [clean_text(v) for v in df.iloc[row_idx].tolist()]
    values = [v for v in values if v]
    return re.sub(r"\s+", " ", " ".join(values)).strip()


def block_text(df, start_row, end_row):
    """
    Combines a few nearby rows into one string.
    This helps when rural/male or urban/female is split into another row.
    """
    parts = []

    for row_idx in range(start_row, min(end_row, len(df))):
        text = row_text(df, row_idx)
        if text:
            parts.append(text)

    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def find_table_blocks(df):
    """
    Finds PLFS industry-of-work table blocks dynamically.

    This does not depend on the table number.
    So it works for:
    Table (16), Table (27), Table 27, etc.

    It searches for the actual meaning of the table:
    percentage distribution + usually working + industry of work
    """
    title_rows = []

    for idx in range(len(df)):
        text = row_text(df, idx).lower()

        if (
            "percentage distribution" in text
            and "usually working" in text
            and "industry of work" in text
        ):
            title_rows.append(idx)

    return title_rows


def parse_geo_cut_and_gender(df, title_row):
    """
    Extracts geo-cut and gender/person category from title row and nearby rows.

    Handles both cases:
    1. Same cell:
       Table ... rural male

    2. Split rows/cells:
       Table ...
       rural       male
    """
    text = block_text(df, title_row, title_row + 4).lower()

    match = re.search(
        r"(rural\+urban|rural|urban)\s+(male|female|persons|person)\b",
        text,
    )

    if not match:
        raise ValueError(
            f"Could not parse geo-cut and gender near row {title_row + 1}. "
            f"Text found: {text[:300]}"
        )

    geo_cut = normalize_geo_cut(match.group(1))
    gender = normalize_gender(match.group(2))

    return geo_cut, gender


def find_industry_code_row(df, title_row, industry_mapping):
    """
    Finds the row containing industry section codes A, B, C...U.

    Instead of assuming title_row + 4 or title_row + 2,
    this scans the next 15 rows and chooses the row with the highest count
    of valid industry codes.
    """
    valid_codes = set(industry_mapping.keys())
    best_row = None
    best_count = 0

    for row_idx in range(title_row + 1, min(title_row + 16, len(df))):
        values = [clean_text(v).upper() for v in df.iloc[row_idx].tolist()]
        count = sum(1 for v in values if v in valid_codes)

        if count > best_count:
            best_count = count
            best_row = row_idx

    if best_row is None or best_count < 5:
        raise ValueError(
            f"Could not find industry code row after title row {title_row + 1}. "
            "Expected a row containing industry codes such as A, B, C, D..."
        )

    return best_row


def build_column_mapping(df, industry_code_row, industry_mapping, include_all_column=False):
    """
    Builds a dictionary like:
    column index -> sub indicator name

    Example:
    col 1 -> Agriculture, forestry and fishing
    col 2 -> Mining and quarrying
    """
    column_mapping = {}

    for col_idx, code in enumerate(df.iloc[industry_code_row].tolist()):
        code = clean_text(code).upper()

        if not code:
            continue

        if code in industry_mapping:
            column_mapping[col_idx] = industry_mapping[code]

        elif include_all_column and code.lower() == "all":
            column_mapping[col_idx] = "All industry sections"

    if not column_mapping:
        raise ValueError(
            f"No industry columns mapped from row {industry_code_row + 1}. "
            "Please check if the industry codes A, B, C... are present."
        )

    return column_mapping


def find_state_column(df, data_start_row, first_industry_col):
    """
    Finds the column containing State/UT names.

    Usually it is the column immediately before the industry columns.
    But this function checks nearby columns and chooses the one that looks textual.
    """
    candidate_cols = list(range(0, max(first_industry_col, 1)))
    if not candidate_cols:
        return 0

    best_col = 0
    best_score = -1

    for col_idx in candidate_cols:
        score = 0

        for row_idx in range(data_start_row, min(data_start_row + 15, len(df))):
            value = clean_text(df.iloc[row_idx, col_idx])

            if not value:
                continue

            # State names are text, not pure numbers and not headers.
            if (
                not re.fullmatch(r"-?\d+(\.\d+)?", value)
                and not value.lower().startswith(("state", "note", "table", "("))
            ):
                score += 1

        if score > best_score:
            best_score = score
            best_col = col_idx

    return best_col


def is_valid_state_row(state_value):
    """
    Keeps actual State/UT rows and removes notes/header/blank rows.
    """
    state = clean_text(state_value)

    if not state:
        return False

    lower_state = state.lower()

    invalid_starts = [
        "table",
        "note:",
        "descriptions",
        "section",
        "state",
        "(",
    ]

    if any(lower_state.startswith(x) for x in invalid_starts):
        return False

    # Exclude serial number rows like -1, -2, etc.
    if re.fullmatch(r"-?\d+(\.\d+)?", state):
        return False

    return True


def get_next_title_row(title_rows, current_title_row, total_rows):
    """
    Finds where the current table block should end.
    """
    later_titles = [row for row in title_rows if row > current_title_row]
    return min(later_titles) if later_titles else total_rows


def find_data_start_row(df, industry_code_row, state_col, column_mapping, block_end_row):
    """
    Finds first data row after the industry code row.

    It skips serial rows like (-1, -2...) and starts from the first valid State/UT row
    that has at least one numeric value under industry columns.
    """
    for row_idx in range(industry_code_row + 1, min(industry_code_row + 10, block_end_row)):
        state = clean_text(df.iloc[row_idx, state_col])

        if not is_valid_state_row(state):
            continue

        has_numeric_value = False

        for col_idx in column_mapping.keys():
            value = df.iloc[row_idx, col_idx]
            if pd.notna(value):
                try:
                    float(value)
                    has_numeric_value = True
                    break
                except Exception:
                    pass

        if has_numeric_value:
            return row_idx

    # Fallback: assume data starts two rows after industry code row
    return industry_code_row + 2


# ---------------------------------------------------------
# MAIN CONVERSION LOGIC
# ---------------------------------------------------------

def convert_plfs_to_raw_format(
    extracted_data_file,
    sub_indicator_mapping_file="Sub_Indicator_Mappings.xlsx",
    output_file=None,
    sheet_name=0,
    include_all_column=False,
):
    """
    Converts PLFS PDF-extracted Excel table into raw dataset format.

    Required input files:
    1. Extracted_Data_YYYY.xlsx
    2. Sub_Indicator_Mappings.xlsx
    """

    extracted_data_file = Path(extracted_data_file)

    if not extracted_data_file.exists():
        raise FileNotFoundError(f"Extracted PLFS data file not found: {extracted_data_file}")

    year = extract_year_from_filename(extracted_data_file)

    if output_file is None:
        output_file = f"PLFS_{year}_industry_of_work_raw_format.xlsx"

    output_file = Path(output_file)

    industry_mapping = load_industry_mapping(sub_indicator_mapping_file)

    df = pd.read_excel(extracted_data_file, sheet_name=sheet_name, header=None)

    output_rows = []
    title_rows = find_table_blocks(df)

    if not title_rows:
        raise ValueError(
            "No PLFS industry-of-work table blocks found in the extracted data file. "
            "The script searches for rows containing: 'percentage distribution', "
            "'usually working', and 'industry of work'."
        )

    print(f"Found {len(title_rows)} table blocks.")

    for block_number, title_row in enumerate(title_rows, start=1):
        block_end_row = get_next_title_row(title_rows, title_row, len(df))

        try:
            geo_cut, gender = parse_geo_cut_and_gender(df, title_row)
            indicator = build_indicator(geo_cut, gender)

            industry_code_row = find_industry_code_row(df, title_row, industry_mapping)
            column_mapping = build_column_mapping(
                df=df,
                industry_code_row=industry_code_row,
                industry_mapping=industry_mapping,
                include_all_column=include_all_column,
            )

            first_industry_col = min(column_mapping.keys())
            state_col = find_state_column(
                df=df,
                data_start_row=industry_code_row + 1,
                first_industry_col=first_industry_col,
            )

            data_start_row = find_data_start_row(
                df=df,
                industry_code_row=industry_code_row,
                state_col=state_col,
                column_mapping=column_mapping,
                block_end_row=block_end_row,
            )

            block_rows_created = 0

            for row_idx in range(data_start_row, block_end_row):
                raw_state = clean_text(df.iloc[row_idx, state_col])
                state, state_lgd_code = state_name_and_lgd_code(raw_state)
                lower_state = state.lower()

                if lower_state.startswith("note:"):
                    break

                if lower_state.startswith("descriptions of industry sections"):
                    break

                if not is_valid_state_row(state):
                    continue

                for col_idx, sub_indicator in column_mapping.items():
                    value = df.iloc[row_idx, col_idx]

                    # Keep 0 values, skip only actual blank cells.
                    if pd.isna(value):
                        continue

                    rural_value = ""
                    urban_value = ""
                    total_value = ""

                    if geo_cut == "Rural":
                        rural_value = value
                    elif geo_cut == "Urban":
                        urban_value = value
                    elif geo_cut == "Total":
                        total_value = value

                    output_rows.append({
                        "State": state,
                        "State LGD Code": state_lgd_code,
                        "District": "NA",
                        "District LGD name": "NA",
                        "District LGD Code": "NA",
                        "Indicator": indicator,
                        "Sub indicator": sub_indicator,
                        "Rural %": rural_value,
                        "Urban %": urban_value,
                        "Total %": total_value,
                        "Year": year,
                        "Unit": "Percentage",
                    })

                    block_rows_created += 1

            print(
                f"Block {block_number}: {geo_cut} {gender} | "
                f"industry columns: {len(column_mapping)} | rows created: {block_rows_created}"
            )

        except Exception as exc:
            print(f"Warning: Skipped block {block_number} at Excel row {title_row + 1}. Reason: {exc}")

    output_df = pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS)
    validate_output(output_df)
    output_df.to_excel(output_file, index=False)

    print("\nConversion completed successfully.")
    print(f"Input extracted data file: {extracted_data_file}")
    print(f"Input mapping file: {sub_indicator_mapping_file}")
    print(f"Output file: {output_file}")
    print(f"Rows created: {len(output_df)}")
    print(f"Unique indicators: {output_df['Indicator'].nunique()}")
    print(f"Unique sub indicators: {output_df['Sub indicator'].nunique()}")
    print(f"Year used: {year}")

    return output_df


# ---------------------------------------------------------
# VALIDATION LOGIC
# ---------------------------------------------------------

def validate_output(output_df):
    """
    Basic checks to ensure output is in expected raw format.
    """
    missing_columns = [col for col in OUTPUT_COLUMNS if col not in output_df.columns]

    if missing_columns:
        raise ValueError(f"Missing output columns: {missing_columns}")

    if output_df.empty:
        raise ValueError("Output is empty. No rows were created.")

    expected_indicator_count = 9
    actual_indicator_count = output_df["Indicator"].nunique()

    if actual_indicator_count != expected_indicator_count:
        print(
            f"Warning: Expected {expected_indicator_count} indicators, "
            f"but found {actual_indicator_count}."
        )

    actual_sub_indicator_count = output_df["Sub indicator"].nunique()

    if actual_sub_indicator_count not in [20, 21]:
        print(
            f"Warning: Expected either 20 or 21 sub indicators depending on whether U is present, "
            f"but found {actual_sub_indicator_count}."
        )

    for prefix in ["Rural:", "Urban:", "Total:"]:
        count = output_df["Indicator"].astype(str).str.startswith(prefix).sum()

        if count == 0:
            print(f"Warning: No rows found for indicator prefix: {prefix}")

    required_non_blank_columns = [
        "State",
        "District",
        "District LGD name",
        "District LGD Code",
        "Indicator",
        "Sub indicator",
        "Year",
        "Unit",
    ]

    for col in required_non_blank_columns:
        blank_count = output_df[col].isna().sum() + (
            output_df[col].astype(str).str.strip() == ""
        ).sum()

        if blank_count > 0:
            print(f"Warning: Column '{col}' has {blank_count} blank values.")


# ---------------------------------------------------------
# RUN SCRIPT
# ---------------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) < 2:
        raise ValueError(
            "Please provide the extracted data file name. "
            "Example: python convert_plfs_industry_to_raw_dynamic.py Extracted_Data_2023.xlsx "
            "[Sub_Indicator_Mappings.xlsx] [output.xlsx]"
        )

    EXTRACTED_DATA_FILE = sys.argv[1]
    SUB_INDICATOR_MAPPING_FILE = sys.argv[2] if len(sys.argv) >= 3 else "Sub_Indicator_Mappings.xlsx"

    YEAR = extract_year_from_filename(EXTRACTED_DATA_FILE)
    OUTPUT_FILE = sys.argv[3] if len(sys.argv) >= 4 else f"PLFS_{YEAR}_industry_of_work_raw_format.xlsx"

    convert_plfs_to_raw_format(
        extracted_data_file=EXTRACTED_DATA_FILE,
        sub_indicator_mapping_file=SUB_INDICATOR_MAPPING_FILE,
        output_file=OUTPUT_FILE,
        sheet_name=0,
        include_all_column=False,
    )
