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
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --rolling-avg 14 --rolling-avg 30
```

Project 10 days into the future:
```bash
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --project 10
```

Project to end of current billing cycle (end of month):
```bash
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --billing-end eom
```

Project to a specific date (year inferred; next year if date already passed):
```bash
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --billing-end 3-31
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --billing-end 03-31
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --billing-end 2026-03-31
```

Show only last 4 days plus projection to end of month:
```bash
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --billing-end eom --last-days 4
```

Project with custom overage pricing ($10 per 50 GB block):
```bash
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --project 10 --overage-price 10.00 --overage-gb 50
```

Save results to a file:
```bash
jumpingjerboa diff /path/to/astound.parquet --output output.csv
```

### View Summary

Get a quick overview of the dataset:
```bash
jumpingjerboa summary /path/to/astound.parquet
```

## Features

- **Daily usage calculation** - Converts cumulative data to daily usage amounts
- **Day of week display** - Shows Mon, Tue, Wed, etc. for each date
- **Cap display** - Shows the data cap value (e.g., 400 GB) on each row
- **Rolling averages** - Calculate moving averages over specified windows (e.g., 7-day, 14-day, 30-day)
- **Usage projection** - Estimate future usage by days (`-p`) or billing cycle end (`--billing-end eom`, `--billing-end 3-31`, `--billing-end YYYY-MM-DD`)
- **Limited display** - Show only recent days while using all data for calculations
- **Overage cost calculation** - Calculate costs when usage exceeds data cap (rounded up to blocks)
- **Flexible pricing** - Customize overage pricing (default: $6.50 per 25 GB block)
- Target utilization - Flags a cycle projected to finish below --target-pct of the cap, with the daily pace that would spend the rest
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
jumpingjerboa diff data.parquet --rolling-avg 7 --rolling-avg 30
```

This shows both 7-day and 30-day rolling averages, letting you see short-term and long-term trends.

## How Projection Works

Projection estimates future usage based on recent patterns:

1. Takes your most recent rolling average (or overall average if no rolling window specified)
2. Creates future date records up to the projected date
3. For each future day, adds the average to the previous day's total
4. Calculates overage amounts and costs when cap is exceeded
5. Shows when you'll hit the cap and how much it will cost

Two ways to specify the projection horizon (mutually exclusive):

\`--project DAYS\` — project a fixed number of days forward:
```bash
jumpingjerboa diff data.parquet --rolling-avg 7 --project 10
```

`--billing-end DATE` — project to a specific end date, so the last row in the
table is always your billing cycle end and you can see at a glance whether
you'll be over quota:
```bash
jumpingjerboa diff data.parquet --rolling-avg 7 --billing-end eom       # end of current month
jumpingjerboa diff data.parquet --rolling-avg 7 --billing-end 3-31      # Mar 31, year inferred
jumpingjerboa diff data.parquet --rolling-avg 7 --billing-end 2026-03-31
```

Year inference for `MM-DD`: uses the current year, or next year if the date has already passed.

## Limiting Display

Use `--last-days` to focus on recent data:
```bash
jumpingjerboa diff data.parquet --last-days 7
```

This shows only the last 7 days in the output table. Important notes:

- **All data is still used** for statistics and rolling averages
- Only the display is limited to recent days
- Projected days are always shown (added after the limited actual days)
- File exports (via `-o`) contain all data, not just the limited display

This is useful when you have months of data but only want to see recent trends.

## Target Utilization

The cap is paid for whether or not it is used, so finishing a cycle far below it wastes money exactly as finishing above it does.

A month spent away from home leaves hundreds of gigabytes unspent, and nothing in a purely overage-driven report calls that out.

A cycle is on target when it lands between `--target-pct` of the cap and the cap itself, defaulting to 95 percent.

Below that floor the summary reports the shortfall instead of congratulating you for staying under:

```
Projection Summary (based on 2.62 GB/day average):
  Current usage: 7.86 GB
  Projected usage in 17 days: 52.40 GB
  Data cap: 400 GB
  Target: finish between 380.00 GB and 400 GB (95% of cap or better)
  Pace to land there: 21.89 - 23.07 GB/day for the remaining 17 days
     (pacing 2.62 GB/day -- 19.27 GB/day below the band)
  UNDER TARGET: finishing at 52.40 GB, 13.10% of the 400 GB cap
  Leaving 347.60 GB of paid allowance unused, against a 380.00 GB target
  At 2.62 GB/day the cap is 150 days off, on 2027-02-10
  Cost: $0.00
```

The pace band is the actionable part.

Its lower bound is the daily rate that reaches the target floor by the end of the cycle, and its upper bound is the rate that lands exactly on the cap.

Any pace inside the band spends the allowance without buying an overage block.

Set `--target-pct 0` to restore the old behaviour, where only exceeding the cap is worth reporting:

```bash
jumpingjerboa diff /path/to/astound.parquet --rolling-avg 7 --billing-end eom --target-pct 0
```

## Overage Pricing

The default overage pricing is **$6.50 per 25 GB block**. Overage is charged in **blocks**, rounded **UP** to the nearest block:

- **0.01 to 25.00 GB** over = 1 block = **$6.50**
- **25.01 to 50.00 GB** over = 2 blocks = **$13.00**
- **50.01 to 75.00 GB** over = 3 blocks = **$19.50**

If you go even 1 MB over your quota, you pay for a full block.

You can customize the pricing:
```bash
# Example: $10 per 50 GB block
jumpingjerboa diff data.parquet --project 10 --overage-price 10.00 --overage-gb 50

# Example: $5 per 10 GB block
jumpingjerboa diff data.parquet --project 10 --overage-price 5.00 --overage-gb 10
```

The tool will:
- Calculate overage amounts when usage exceeds your data cap
- Show costs in the daily usage table
- Display total projected costs in the projection summary
- Show when you'll hit the cap and the cost at that point
- Display the number of blocks being charged

## Subcommands

- `diff` - Calculate daily usage differences from cumulative data
- `summary` - Show dataset overview and current usage
