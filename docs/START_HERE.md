# CDAP Agent - Start Here

The project has two stages:

Stage 1: Source file to intermediate raw dataset
Stage 2: Intermediate raw dataset to final CDAP output

If the input is already in intermediate format, Stage 1 is skipped.

## One Command

From the project root:

```bash
python run_cdap_agent.py
```

## Supported Input Scenarios

### Workflow A: Source/raw file

Put the source file here:

```text
input/source_data.xlsx
```

Then run:

```bash
python run_cdap_agent.py
```

The agent detects the source format, chooses a parser, writes the intermediate bridge file, validates it, and then creates the final CDAP output.

### Workflow B: Already intermediate-format file

Put the intermediate file here:

```text
input/intermediate_raw_dataset.xlsx
```

Then run:

```bash
python run_cdap_agent.py
```

If the file has the common intermediate columns, the agent skips Stage 1 and runs Stage 2 directly.

## Required Reference Files

These reusable reference files live in `input/`:

```text
input/metadata.xlsx
input/taxonomy_mapping.xlsx
input/indicators_list.xlsx
input/temporal_indicator_log.xlsx
input/lat_long.xlsx
```

For PLFS industry source conversion, this dataset-specific helper is also used:

```text
input/sub_indicator_mappings.xlsx
```

## Common Intermediate Format

Every parser must return these exact columns:

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

This is the golden bridge format consumed by Stage 2.

## Main Outputs

```text
output/intermediate/intermediate_raw_dataset.xlsx
output/final/final_cdap_output.xlsx
output/final/final_cdap_output.csv
output/reports/source_detection_report.xlsx
output/reports/intermediate_validation_report.xlsx
output/reports/final_validation_report.xlsx
output/reports/mapping_review_report.xlsx
```

`mapping_review_report.xlsx` is created when no parser is confident enough. The agent stops instead of guessing.

## Quick Checks

```bash
python validators/check_config.py
python validators/validate_syntax.py
python run_cdap_agent.py
```

The current PLFS industry source case should produce 6660 intermediate rows and 6660 final rows.
