# CDAP Agent - Quick Start

## Run

```bash
python run_cdap_agent.py
```

## Check Setup

```bash
python validators/check_config.py
python validators/validate_syntax.py
```

## Workflow A: Source/raw file

1. Put the source file here:

```text
input/source_data.xlsx
```

2. Put reference files here:

```text
input/metadata.xlsx
input/taxonomy_mapping.xlsx
input/indicators_list.xlsx
input/temporal_indicator_log.xlsx
input/lat_long.xlsx
```

For PLFS industry source files, also keep:

```text
input/sub_indicator_mappings.xlsx
```

3. Run:

```bash
python run_cdap_agent.py
```

4. Get:

```text
output/intermediate/intermediate_raw_dataset.xlsx
output/final/final_cdap_output.xlsx
output/final/final_cdap_output.csv
output/reports/source_detection_report.xlsx
output/reports/intermediate_validation_report.xlsx
output/reports/final_validation_report.xlsx
```

## Workflow B: Already intermediate-format file

1. Put the intermediate file here:

```text
input/intermediate_raw_dataset.xlsx
```

2. Run:

```bash
python run_cdap_agent.py
```

3. The agent skips Stage 1 and writes:

```text
output/final/final_cdap_output.xlsx
```

## Two Stages

Stage 1: Source file to intermediate raw dataset  
Stage 2: Intermediate raw dataset to final CDAP output

If the input is already in intermediate format, Stage 1 is skipped.

## Unknown Source Formats

If the source format is not recognized, the agent stops and writes:

```text
output/reports/mapping_review_report.xlsx
```

Use that report to decide which parser/profile to add next.
