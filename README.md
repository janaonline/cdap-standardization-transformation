# CDAP Agent - Python Orchestration Wrapper

A complete orchestration solution for the CDAP (Categorized Data Analytics Platform) pipeline. This wrapper automates the transformation and standardization workflow for PLFS (Periodic Labour Force Survey) data.

## What it does

The CDAP Agent is a wrapper that orchestrates a two-step data processing pipeline:

### Step 1: Transformation (PLFS Extracted → Raw Format)
- Takes a PDF-extracted Excel file (e.g., `Extracted_Data_2023.xlsx`)
- Uses `convert_plfs_industry_to_raw_dynamic.py` to parse industry-of-work tables
- Applies sub-indicator mappings from `Sub_Indicator_Mappings.xlsx`
- Produces intermediate raw-format dataset
- **Output**: `output/intermediate/transformed_raw_format.xlsx`

### Step 2: Standardization (Raw Format → Final CDAP)
- Reads the transformed raw format file
- Uses refactored `v36_cdap_pipeline_refactored.py` with dynamic file paths
- Applies taxonomy, metadata, geography, and indicator mappings
- Generates final CDAP-compliant output with standardized columns and codes
- Creates multiple output files for audit and downstream processing
- **Outputs**: 
  - `output/final/final_cdap_output.xlsx` (main)
  - `output/final/final_cdap_output.csv` (for compatibility)
  - `output/final/indicator_mapping_generated.xlsx`
  - `output/final/Indicators_list_updated.xlsx`
  - `output/final/Temporal_indicator_log_updated.xlsx`
  - `output/final/metadata_year_mapping_used.xlsx`

## File requirements

### Input Files (in root folder)
- **`Extracted_Data_2023.xlsx`** - PDF-extracted PLFS data (year must be in filename)
- **`Sub_Indicator_Mappings.xlsx`** - Industry section mappings

### Dependency Files (in root folder)
- **`Metadata.xlsx`** - Dataset-level metadata with Unique Dataset Identifiers
- **`Indicators_list.xlsx`** - Indicator master list
- **`LAT LONG.xlsx`** - Geography coordinate and code mappings
- **`Taxonomy_Mapping.xlsx`** - Sector/sub-sector taxonomy
- **`Temporal indicator log.xlsx`** - Temporal indicator definitions

### Script Files (in root folder)
- **`convert_plfs_industry_to_raw_dynamic.py`** - Transformation script
- **`v36_cdap_pipeline_refactored.py`** - Refactored standardization pipeline
- **`run_cdap_agent.py`** - Orchestration wrapper (this agent)
- **`config.json`** - Configuration file (created with default paths)

## How to run it

### Quick Start (using defaults)

```bash
python run_cdap_agent.py
```

This uses the default `config.json` with standard file names and paths.

### With custom config

```bash
python run_cdap_agent.py path/to/custom_config.json
```

### From PowerShell on Windows

```powershell
python run_cdap_agent.py
```

### What happens

1. **Validation**: Checks all required files exist
2. **Setup**: Creates output directories (`output/intermediate/`, `output/final/`)
3. **Step 1**: Runs transformation script, producing intermediate raw-format file
4. **Step 2**: Runs standardization pipeline on the intermediate output
5. **Success**: Displays final output location and file summary

## Configuration (config.json)

Edit `config.json` to customize file paths and output locations:

```json
{
  "input": {
    "extracted_data_file": "Extracted_Data_2023.xlsx",
    "sub_indicator_mapping_file": "Sub_Indicator_Mappings.xlsx"
  },
  "dependency_files": {
    "metadata_file": "Metadata.xlsx",
    "indicators_file": "Indicators_list.xlsx",
    "lat_long_file": "LAT LONG.xlsx",
    "taxonomy_file": "Taxonomy_Mapping.xlsx",
    "temporal_log_file": "Temporal indicator log.xlsx"
  },
  "scripts": {
    "transformation_script": "convert_plfs_industry_to_raw_dynamic.py",
    "standardization_script": "v36_cdap_pipeline_refactored.py"
  },
  "output": {
    "intermediate_output_dir": "output/intermediate",
    "final_output_dir": "output/final",
    "intermediate_output_file": "transformed_raw_format.xlsx",
    "final_output_file": "final_cdap_output.xlsx"
  }
}
```

### Key config sections

- **`input`**: Primary extracted data and mapping files
- **`dependency_files`**: All supporting reference files
- **`scripts`**: Python script file names
- **`output`**: Output directory and file name settings

## Expected outputs

### Folder structure after running

```
CDAP Agent/
├── (original files)
├── run_cdap_agent.py
├── config.json
├── v36_cdap_pipeline_refactored.py
│
└── output/
    ├── intermediate/
    │   └── transformed_raw_format.xlsx
    │
    └── final/
        ├── final_cdap_output.xlsx  (primary output)
        ├── final_cdap_output.csv
        ├── indicator_mapping_generated.xlsx
        ├── Indicators_list_updated.xlsx
        ├── Temporal_indicator_log_updated.xlsx
        └── metadata_year_mapping_used.xlsx
```

### Understanding the outputs

| File | Purpose |
|------|---------|
| **final_cdap_output.xlsx** | Main standardized CDAP dataset with all required columns and codes |
| **final_cdap_output.csv** | CSV version for compatibility and import to other tools |
| **indicator_mapping_generated.xlsx** | Mapping of raw indicators to CDAP taxonomy (Sector/Sub-sector) |
| **Indicators_list_updated.xlsx** | Updated master list with new indicator codes assigned |
| **Temporal_indicator_log_updated.xlsx** | Updated temporal definitions and linking codes |
| **metadata_year_mapping_used.xlsx** | Audit file showing which metadata years were used |

### Output columns (final_cdap_output.xlsx)

The final output includes:
- Geography: Geo-Level, Geo-cut, Geo-Name, Latitude/Longitude, LGD Codes
- Taxonomy: Super-Tag, Sector, Sub-Sector and their codes
- Data: Indicator, Sub-Indicator, Value, Unit
- Temporal: Indicator date, Temporal Indicator name and code, Time period
- Metadata: Unique Dataset Identifier, Keywords

## Troubleshooting

### Error: "Config file not found: config.json"
**Solution**: Make sure `config.json` exists in the same folder as `run_cdap_agent.py`. Copy the default template if missing.

### Error: "File not found: Extracted_Data_2023.xlsx"
**Solution**: 
- Check file exists in the root folder
- Verify spelling and case sensitivity
- Update `config.json` with correct path if file is named differently

### Error: "Could not find year in file name: [filename]"
**Solution**: The extracted data file name must contain a 4-digit year (e.g., `Extracted_Data_2020.xlsx`, `Data_2023.xlsx`). Rename the file to include the year.

### Error: "No PLFS industry-of-work table blocks found"
**Solution**: The transformation script looks for specific header text patterns. Verify:
- File contains PLFS tables with "percentage distribution" and "usually working"
- Tables structure matches expected format (industry codes A-U in columns)

### Error: "Missing required columns: [list of columns]"
**Solution**: Dependency files may have different column names. Check:
- Metadata.xlsx has "Unique Dataset Identifier"
- Indicators_list.xlsx has required indicator columns
- Taxonomy_Mapping.xlsx has sector/sub-sector columns
- LAT LONG.xlsx has geo-level, geo-name, latitude, longitude

### Error: "Permission denied" on output files
**Solution**: One of the output files is open in Excel. Close all Excel files and try again. The script will auto-generate timestamped filenames if this happens.

### No data in final output (0 rows)
**Solution**: 
- Verify transformation step produced data in `output/intermediate/`
- Check that indicator names match between raw and mapping data
- Ensure Metadata.xlsx contains valid Unique Dataset Identifiers

## How to extend for batch processing

The current setup processes a single extracted file. To process multiple files:

1. **Create a batch wrapper**: Write a loop that:
   - Modifies `config.json` for each input file
   - Calls `python run_cdap_agent.py`
   - Moves outputs to year-specific folders

Example batch script:

```python
import json
from pathlib import Path
from run_cdap_agent import CDAPAgent

years = [2020, 2021, 2022, 2023]

for year in years:
    config = {
        "input": {
            "extracted_data_file": f"Extracted_Data_{year}.xlsx",
            "sub_indicator_mapping_file": "Sub_Indicator_Mappings.xlsx"
        },
        # ... (rest of config)
    }
    
    with open("batch_config.json", "w") as f:
        json.dump(config, f)
    
    agent = CDAPAgent(config_file="batch_config.json")
    agent.run_full_pipeline()
    
    # Move outputs to year-specific folder
    year_folder = Path(f"output/{year}")
    year_folder.mkdir(exist_ok=True)
    # ... move files
```

2. **Adapt the orchestration script** to accept input file as a parameter:
   ```bash
   python run_cdap_agent.py config.json Extracted_Data_2023.xlsx
   ```

3. **Parallelize if needed**: Use Python's `multiprocessing` or `concurrent.futures` to run multiple years simultaneously.

## Technical notes

### Refactoring details

**v36_cdap_pipeline_refactored.py** is a minimal refactor of the original script:
- Extracted the main logic into `run_cdap_pipeline()` function
- Accepts file paths as parameters instead of hardcoded constants
- Preserves all original business logic and output structure
- Can be used standalone or called from orchestration wrapper
- Maintains backward compatibility with original output format

### Data flow

```
Extracted_Data_2023.xlsx (PDF-extracted)
        ↓ (Step 1: convert_plfs_industry_to_raw_dynamic.py)
        ↓
transformed_raw_format.xlsx (raw format with state, district, indicators)
        ↓ (Step 2: v36_cdap_pipeline_refactored.py)
        ↓ (with Metadata, Taxonomy, Lat-Long, Indicators, Temporal)
        ↓
final_cdap_output.xlsx (standardized CDAP format with all codes and mappings)
```

### Design decisions

1. **Config file over CLI args**: JSON config is easier to version control and review
2. **Separate intermediate outputs**: Keeps audit trail and allows step-by-step debugging
3. **Minimal refactoring**: Original business logic unchanged to reduce risk
4. **Subprocess calls**: Each step runs independently; easier to debug and extend

## Requirements

- Python 3.7+
- pandas
- openpyxl (for Excel I/O)

Install dependencies:
```bash
pip install pandas openpyxl
```

## Support and debugging

1. **Check logs**: Both scripts print detailed progress messages to console
2. **Review intermediate file**: Inspect `output/intermediate/transformed_raw_format.xlsx` to verify Step 1 output
3. **Validate inputs**: Manually check a few rows of each dependency file
4. **Year alignment**: Confirm extracted file name and Metadata years match the data

## Example command for your current setup

With the default configuration:

```bash
cd "d:\Saranya\CDAP Agent"
python run_cdap_agent.py
```

This will:
1. Read `Extracted_Data_2023.xlsx`
2. Transform to raw format in `output/intermediate/`
3. Standardize to final CDAP format in `output/final/`
4. Display summary of rows, indicators, and output files

---

**Version**: 1.0  
**Last Updated**: 2026-05-19  
**Author**: CDAP Orchestration Agent  
