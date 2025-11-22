# jumpingjerboa

Internet usage data analysis tool for tracking and analyzing daily bandwidth consumption.

## Installation
```bash
cd jumpingjerboa
pip install -e .
```

## Usage

### Calculate Daily Differences

Calculate how much data was used each day:
```bash
python -m jumpingjerboa.main diff /path/to/astound.parquet
```

With statistics:
```bash
python -m jumpingjerboa.main diff /path/to/astound.parquet --stats
```

Save results to a file:
```bash
python -m jumpingjerboa.main diff /path/to/astound.parquet -o output.csv
```

### View Summary

Get a quick overview of the dataset:
```bash
python -m jumpingjerboa.main summary /path/to/astound.parquet
```

## Subcommands

- `diff` - Calculate daily usage differences from cumulative data
- `summary` - Show dataset overview and current usage

## Features

- Handles monthly resets automatically (when usage counter goes back to 0)
- Takes the last scraped value for each day (most recent/accurate)
- Calculates daily usage from cumulative totals
- Provides monthly and overall statistics
- Exports to CSV, JSON, or Parquet formats
- Uses Polars for fast data processing
