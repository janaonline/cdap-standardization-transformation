# CDAP Agent

CDAP Agent is a generic, production-style Python data-processing agent for preparing government datasets for CDAP.

The project has two stages:

Stage 1: Source file to intermediate raw dataset  
Stage 2: Intermediate raw dataset to final CDAP output

If the input is already in intermediate format, Stage 1 is skipped.

## Project Structure

```text
CDAP_AGENT/
├── run_cdap_agent.py
├── config.json
├── requirements.txt
├── input/
├── output/
│   ├── intermediate/
│   ├── final/
│   └── reports/
├── converters/
├── standardization/
├── validators/
├── utils/
├── legacy/
├── docs/
└── tests/
```

`legacy/` preserves the known-good PLFS converter and CDAP standardizer. New production modules wrap that logic instead of rewriting CDAP business rules.

## Input Scenarios

### Scenario 1: Source/raw file

Use this when the source could be a PDF-extracted PLFS workbook, NCRB-style district sections, a state-level table, a multi-sheet year workbook, wide year columns, NDAP-like tidy data, or another future government Excel/CSV format.

```text
input/source_data.xlsx
        -> detect format
        -> convert to intermediate raw dataset
        -> validate intermediate
        -> standardize to final CDAP output
        -> validate final output
```

### Scenario 2: Already intermediate-format file

Use this when you already have a file with the bridge schema.

```text
input/intermediate_raw_dataset.xlsx
        -> skip source conversion
        -> validate intermediate
        -> standardize to final CDAP output
        -> validate final output
```

If both source and intermediate files exist, `config.json` controls whether the intermediate file is preferred.

## Files to Put in input/

Dataset-specific files:

```text
input/source_data.xlsx
input/intermediate_raw_dataset.xlsx
input/sub_indicator_mappings.xlsx
```

Reusable reference files:

```text
input/metadata.xlsx
input/taxonomy_mapping.xlsx
input/indicators_list.xlsx
input/temporal_indicator_log.xlsx
input/lat_long.xlsx
```

`sub_indicator_mappings.xlsx` is currently required for the PLFS industry parser.

## How to Run

```bash
python run_cdap_agent.py
```

Useful checks:

```bash
python validators/check_config.py
python validators/validate_syntax.py
```

## Configuration

`config.json` is intentionally generic:

```json
{
  "mode": "auto",
  "input": {
    "source_file": "input/source_data.xlsx",
    "intermediate_file": "input/intermediate_raw_dataset.xlsx",
    "metadata_file": "input/metadata.xlsx",
    "taxonomy_file": "input/taxonomy_mapping.xlsx",
    "indicators_file": "input/indicators_list.xlsx",
    "temporal_log_file": "input/temporal_indicator_log.xlsx",
    "lat_long_file": "input/lat_long.xlsx",
    "sub_indicator_mapping_file": "input/sub_indicator_mappings.xlsx"
  }
}
```

Modes:

- `auto`: choose a valid intermediate file first when configured to prefer it, otherwise use the source file.
- `source`: force source-file conversion.
- `intermediate`: force intermediate-file processing.

## Input Type Detection

`validators/input_type_detector.py` classifies a candidate input as:

- `INTERMEDIATE_FORMAT`
- `SOURCE_FORMAT`
- `UNKNOWN`

Intermediate format is detected by normalized column matching. For example, `Rural %`, `Rural pct`, `rural_pct`, and `Rural Percentage` all map to `Rural %`.

## Source Format Detection

`converters/format_detector.py` inspects the file extension, sheet names, sampled rows, possible headers, geography columns, year labels, PLFS block text, government section headings, and tidy/wide table clues.

It returns:

```python
{
    "detected_format": "plfs_industry",
    "confidence": 0.95,
    "reason": "...",
    "candidate_parser": "converters.plfs_industry_parser",
    "detected_sheets": [],
    "possible_years": [],
    "possible_geo_columns": [],
    "possible_indicator_columns": []
}
```

The report is written to:

```text
output/reports/source_detection_report.xlsx
```

## Unknown Formats

When no parser reaches the configured confidence threshold, the agent writes:

```text
output/reports/mapping_review_report.xlsx
```

That report includes detected sheets, sample rows, possible geography/year/indicator columns, and the reason no parser was selected. The run stops so the pipeline does not continue with a wrong assumption.

## Parsers

Parser modules live in `converters/`. Each parser must return the common intermediate schema:

```text
State
State LGD Code
District
District LGD name
District LGD Code
Indicator
Sub indicator
Rural %
Urban %
Total %
Year
Unit
```

Current parser entrypoints:

- `plfs_industry_parser.py`
- `plfs_block_parser.py`
- `ncrb_district_section_parser.py`
- `flat_state_table_parser.py`
- `wide_year_columns_parser.py`
- `multi_sheet_year_parser.py`
- `ndap_tidy_parser.py`

The PLFS industry parser wraps the preserved legacy logic and adds generic year detection so `input/source_data.xlsx` can be used without requiring the year in the filename.

## Year Detection

`utils/year_utils.py` supports:

- `2021`
- `2022`
- `2017-18`
- `2017-2022`
- `Financial Year 2019`
- `Till March '22`
- `Upto 2017`
- sheet names like `2015`
- year columns like `2021`

The priority is configurable in `config.json`. Filename is the last fallback. False source-layout years such as `NIC 2008` are ignored for PLFS industry detection.

## Validation Reports

Intermediate validation writes:

```text
output/reports/intermediate_validation_report.xlsx
```

It checks required columns, blank state/indicator/year/unit values, value availability, row count, duplicates, missing geography code summaries, empty columns, and non-numeric values.

Final validation writes:

```text
output/reports/final_validation_report.xlsx
```

It checks required CDAP columns, critical nonblank fields, UID/year alignment, NA99 rule summaries, row-count comparison, and empty columns. Existing taxonomy blanks are reported as warnings so validation does not change the preserved business logic.

## Outputs

Main files:

```text
output/intermediate/intermediate_raw_dataset.xlsx
output/final/final_cdap_output.xlsx
output/final/final_cdap_output.csv
```

Audit and support files:

```text
output/final/indicator_mapping_generated.xlsx
output/final/Indicators_list_updated.xlsx
output/final/Temporal_indicator_log_updated.xlsx
output/final/metadata_year_mapping_used.xlsx
output/reports/source_detection_report.xlsx
output/reports/intermediate_validation_report.xlsx
output/reports/final_validation_report.xlsx
output/reports/mapping_review_report.xlsx
```

## Adding a New Parser

1. Add a module in `converters/`, for example `new_format_parser.py`.
2. Implement a `parse(source_file, output_file, **kwargs) -> dict` function.
3. Return an Excel file with the common intermediate schema.
4. Add a detector rule in `converters/format_detector.py`.
5. Register the parser in `PARSER_MODULES` inside `converters/source_to_intermediate_converter.py`.
6. Add focused tests under `tests/`.
7. Run `python validators/validate_syntax.py` and `python run_cdap_agent.py`.

## Current Backward Compatibility

The current PLFS industry source case is still supported through:

```text
input/source_data.xlsx
input/sub_indicator_mappings.xlsx
legacy/convert_plfs_industry_to_raw_dynamic.py
legacy/v36_cdap_pipeline_refactored.py
```

The smoke test should produce 6660 rows in the intermediate file and 6660 rows in the final output.
