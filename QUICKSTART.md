# jumpingjerboa Quick Start Guide

## Installation
```bash
cd jumpingjerboa
pip install -e .
```

## Basic Usage

### 1. Calculate Daily Usage Differences

This is the main feature - it calculates how much data you used each day by finding the difference between consecutive days:
```bash
python -m jumpingjerboa.main diff /path/to/astound.parquet
```

**Example output:**
```
=== Daily Internet Usage ===

Date         Total Usage  Daily Usage  % of Cap  
--------------------------------------------------
2024-11-27     214.86 GB     153.61 GB    53.72%
2024-11-28     225.36 GB      10.50 GB    56.34%
2024-11-29     229.95 GB       4.59 GB    57.49%
```

### 2. View Statistics

Add `--stats` to see monthly averages and other statistics:
```bash
python -m jumpingjerboa.main diff /path/to/astound.parquet --stats
```

### 3. Export Results

Save the results to CSV, JSON, or Parquet:
```bash
# CSV format
python -m jumpingjerboa.main diff /path/to/astound.parquet -o results.csv

# JSON format
python -m jumpingjerboa.main diff /path/to/astound.parquet -o results.json

# Parquet format
python -m jumpingjerboa.main diff /path/to/astound.parquet -o results.parquet
```

### 4. Quick Summary

Get a quick overview without calculating differences:
```bash
python -m jumpingjerboa.main summary /path/to/astound.parquet
```

## How It Works

The tool:
1. Reads your parquet file containing cumulative usage data
2. Takes the last (most recent) scrape for each day
3. Calculates the difference between consecutive days
4. Handles month resets automatically (when usage goes back to 0)

## Adding New Subcommands

The tool uses argparse with subcommands, making it easy to extend:

1. Add a new function in `main.py`:
```python
   def cmd_yourcommand(args):
       # Your code here
       pass
```

2. Register it in the `main()` function:
```python
   new_parser = subparsers.add_parser('yourcommand', help='Description')
   new_parser.add_argument('arg1', help='Argument help')
   new_parser.set_defaults(func=cmd_yourcommand)
```

That's it! Your new command will be available as:
```bash
python -m jumpingjerboa.main yourcommand arg1
```
