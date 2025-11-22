# jumpingjerboa - Project Overview

## What This Tool Does

`jumpingjerboa` analyzes your internet usage data from parquet files. It takes cumulative usage measurements (scraped multiple times per day) and calculates:

- **Daily usage differences** - How much data you used each day
- **Monthly statistics** - Average daily usage per month
- **Usage predictions** - (can be added as shown in EXAMPLE_NEW_COMMAND.py)

## Key Features

✓ **Handles month resets** - Automatically detects when usage counter goes back to 0  
✓ **Smart sampling** - Takes the most recent scrape for each day  
✓ **Extensible CLI** - Easy to add new subcommands using argparse  
✓ **Multiple output formats** - CSV, JSON, or Parquet  
✓ **Statistics** - View daily, monthly, and overall usage patterns  
✓ **Fast processing** - Uses Polars for efficient data manipulation  

## Project Structure
```
jumpingjerboa/
├── jumpingjerboa/           # Main package
│   ├── __init__.py          # Package initialization
│   └── main.py              # CLI implementation with subcommands
├── pyproject.toml           # Project metadata and dependencies
├── README.md                # Full documentation
├── QUICKSTART.md            # Quick start guide
├── EXAMPLE_NEW_COMMAND.py   # Example of adding commands
├── test_install.py          # Installation test script
└── .python-version          # Python version requirement (3.12)
```

## Available Subcommands

### `diff` - Calculate Daily Differences
The main command that calculates daily usage from cumulative totals.
```bash
python -m jumpingjerboa.main diff input.parquet [--stats] [-o output.csv]
```

### `summary` - Dataset Overview
Quick summary of the dataset including date range and current usage.
```bash
python -m jumpingjerboa.main summary input.parquet
```

## Installation & Testing
```bash
# 1. Install dependencies
pip install -e .

# 2. Run tests
python test_install.py

# 3. Try it with your data
python -m jumpingjerboa.main diff /path/to/astound.parquet --stats
```

## Example Output
```
=== Daily Internet Usage ===

Date         Total Usage  Daily Usage  % of Cap  
--------------------------------------------------
2024-11-27     214.86 GB     153.61 GB    53.72%
2024-11-28     225.36 GB      10.50 GB    56.34%
2024-11-29     229.95 GB       4.59 GB    57.49%
2024-11-30     234.35 GB       4.40 GB    58.59%
2024-12-01       0.00 GB       0.00 GB     0.00%  ← Month reset!
2024-12-02      16.77 GB      16.77 GB     4.19%
2024-12-03      23.50 GB       6.73 GB     5.88%

=== Statistics ===

Overall Statistics:
  Average daily usage: 24.12 GB
  Median daily usage: 8.42 GB
  Max daily usage: 153.61 GB

Monthly Statistics:
  2024-11: 234.35 GB total, 43.28 GB/day avg, 4 days tracked
  2024-12: 43.94 GB total, 8.79 GB/day avg, 5 days tracked
```

## Architecture Highlights

### Why argparse subcommands?

The tool uses argparse's subparser functionality, which provides:

1. **Clean organization** - Each command is a separate function
2. **Easy extensibility** - Add new commands without touching existing ones
3. **Built-in help** - Automatic `--help` for each subcommand
4. **Scalability** - Can grow to dozens of commands without becoming messy

### Why Polars?

Polars is used instead of Pandas because it:
- Is faster for data processing
- Has a more expressive API with method chaining
- Uses lazy evaluation for efficiency
- Has better memory management

### How month resets are handled
```python
# When daily_usage is negative, it means the month reset
# Replace with the current amount (which is the actual daily usage)
daily_df = daily_df.with_columns([
    pl.when(pl.col('daily_usage') < 0)
    .then(pl.col('amount'))
    .otherwise(pl.col('daily_usage'))
    .alias('daily_usage')
])
```

### Data processing pipeline

1. **Load** parquet file with polars
2. **Sort** by date and scraped_at timestamp
3. **Group** by date, taking last (most recent) scrape
4. **Calculate** differences between consecutive days using shift()
5. **Handle** month resets (negative diffs)
6. **Output** results in requested format

## Dependencies

- **polars** - Fast data manipulation and analysis

## Future Enhancement Ideas

- Add `predict` subcommand (see EXAMPLE_NEW_COMMAND.py)
- Add `graph` subcommand using plotly
- Add `alert` subcommand for usage warnings
- Add `compare` subcommand for month-over-month comparison
- Add `export-report` for PDF summaries

## License

Add your license here.

## Contributing

To add a new subcommand:

1. Define command function: `def cmd_newcommand(args):`
2. Register in main(): `subparsers.add_parser('newcommand', ...)`
3. Set handler: `new_parser.set_defaults(func=cmd_newcommand)`

See EXAMPLE_NEW_COMMAND.py for a complete example.
