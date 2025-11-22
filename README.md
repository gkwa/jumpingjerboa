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
jumpingjerboa diff /path/to/astound.parquet
```

With statistics:
```bash
jumpingjerboa diff /path/to/astound.parquet --stats
```

With rolling averages (7-day, 14-day, 30-day):
```bash
jumpingjerboa diff /path/to/astound.parquet -r 7 -r 14 -r 30
```

Project 10 days into the future:
```bash
jumpingjerboa diff /path/to/astound.parquet -r 7 -p 10
```

Save results to a file:
```bash
jumpingjerboa diff /path/to/astound.parquet -o output.csv
```

### View Summary

Get a quick overview of the dataset:
```bash
jumpingjerboa summary /path/to/astound.parquet
```

## Features

- **Daily usage calculation** - Converts cumulative data to daily usage amounts
- **Day of week display** - Shows Mon, Tue, Wed, etc. for each date
- **Rolling averages** - Calculate moving averages over specified windows (e.g., 7-day, 14-day, 30-day)
- **Usage projection** - Estimate future usage and predict when you'll hit your data cap
- **Month reset handling** - Automatically detects when usage counter goes back to 0
- **Smart sampling** - Takes the most recent scrape for each day (most accurate)
- **Statistics** - View daily, monthly, and overall usage patterns
- **Multiple output formats** - CSV, JSON, or Parquet
- **Fast processing** - Uses Polars for efficient data manipulation

## How Rolling Averages Work

Rolling averages smooth out daily fluctuations to show trends. The tool uses Polars' `rolling_mean()` function:

- A 7-day rolling average at day N = average of days N-6 through N
- This gives you a moving average that updates each day
- Helps identify if your usage is trending up or down

Example:
```bash
jumpingjerboa diff data.parquet -r 7 -r 30
```

This shows both 7-day and 30-day rolling averages, letting you see short-term and long-term trends.

## How Projection Works

Projection estimates future usage based on recent patterns:

1. Takes your most recent rolling average (or overall average if no rolling window specified)
2. Creates future date records for the specified number of days
3. For each future day, adds the average to the previous day's total
4. Checks when/if you'll exceed your data cap

Example:
```bash
jumpingjerboa diff data.parquet -r 7 -p 10
```

This projects 10 days forward using your 7-day rolling average, and warns you if you're on track to exceed your cap.

## Subcommands

- `diff` - Calculate daily usage differences from cumulative data
- `summary` - Show dataset overview and current usage
