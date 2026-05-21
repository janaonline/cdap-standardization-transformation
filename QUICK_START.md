# CDAP Agent - Quick Reference

## ⚡ Quick Start

```bash
cd "d:\Saranya\CDAP Agent"
python run_cdap_agent.py
```

## 📋 Required Files (must be in root folder)

### Input Files
- ✓ `Extracted_Data_2023.xlsx` (year required in filename)
- ✓ `Sub_Indicator_Mappings.xlsx`

### Dependency Files  
- ✓ `Metadata.xlsx`
- ✓ `Indicators_list.xlsx`
- ✓ `LAT LONG.xlsx`
- ✓ `Taxonomy_Mapping.xlsx`
- ✓ `Temporal indicator log.xlsx`

### Scripts
- ✓ `convert_plfs_industry_to_raw_dynamic.py` (original, unchanged)
- ✓ `v36_cdap_pipeline_refactored.py` (NEW, refactored)
- ✓ `run_cdap_agent.py` (NEW, orchestrator)

### Configuration
- ✓ `config.json` (NEW, auto-created with defaults)

## 📁 Output Structure

```
output/
├── intermediate/
│   └── transformed_raw_format.xlsx         ← Step 1 output
│
└── final/
    ├── final_cdap_output.xlsx              ← MAIN OUTPUT ⭐
    ├── final_cdap_output.csv
    ├── indicator_mapping_generated.xlsx
    ├── Indicators_list_updated.xlsx
    ├── Temporal_indicator_log_updated.xlsx
    └── metadata_year_mapping_used.xlsx
```

## 🔍 Validation

Before running:
```bash
python check_config.py
```

## ⚙️ Configuration (config.json)

Edit to customize file paths:
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

## 🚀 Workflow

```
INPUT: Extracted_Data_2023.xlsx
   ↓
[Step 1] convert_plfs_industry_to_raw_dynamic.py
   ↓
INTERMEDIATE: output/intermediate/transformed_raw_format.xlsx
   ↓
[Step 2] v36_cdap_pipeline_refactored.py
   ↓
OUTPUT: output/final/final_cdap_output.xlsx ✓
```

## 🆘 Common Issues

| Problem | Solution |
|---------|----------|
| "Config file not found" | Run from folder with config.json, or specify path: `python run_cdap_agent.py config.json` |
| "File not found: Extracted_Data_2023.xlsx" | Check file name and location; edit config.json with correct path |
| "Could not find year in file name" | Rename file to include year, e.g. `Extracted_Data_2020.xlsx` |
| "Permission denied" on output | Close the output .xlsx file in Excel if open; script will auto-rename if needed |
| "No rows created" or empty output | Check intermediate file in `output/intermediate/`; verify data in input files |
| Python not found | Install Python 3.7+ from python.org; ensure in PATH or use full path: `C:\Python39\python.exe run_cdap_agent.py` |

## 📦 Dependencies

```bash
pip install pandas openpyxl
```

## 📊 Output File Descriptions

| File | Contents |
|------|----------|
| **final_cdap_output.xlsx** | Standardized CDAP dataset with all columns and codes (rows per indicator × geography × year) |
| **final_cdap_output.csv** | Same as above, CSV format for Excel/Power BI import |
| **indicator_mapping_generated.xlsx** | Mapping of raw indicators to Sector/Sub-sector codes |
| **Indicators_list_updated.xlsx** | Updated indicator master with new codes |
| **Temporal_indicator_log_updated.xlsx** | Updated temporal linking codes |
| **metadata_year_mapping_used.xlsx** | Audit file showing UID → Year mapping |

## 🔧 Edit Configuration

To use different files, edit config.json:

```json
"input": {
  "extracted_data_file": "Extracted_Data_2020.xlsx",  ← Change year
  ...
}
```

No Python code changes needed!

## 📝 Full Documentation

See `README.md` for complete guide including:
- Detailed workflow explanation
- File format requirements
- Troubleshooting guide
- How to extend for batch processing
- Technical architecture notes

## 📞 File Status Check

```bash
python check_config.py
```

Shows which files are present/missing before running pipeline.

---

**Your command to run**:
```bash
python run_cdap_agent.py
```

**Expected duration**: 2-5 minutes (depending on file size)  
**Output**: `output/final/final_cdap_output.xlsx`
