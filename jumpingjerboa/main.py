#!/usr/bin/env python3
import argparse
import datetime
import sys

import polars as pl

import jumpingjerboa.data as jdata
import jumpingjerboa.display as jdisplay
import jumpingjerboa.projection as jprojection
import jumpingjerboa.summary as jsummary


def parse_billing_end(value: str) -> datetime.date:
    lower = value.lower().replace("_", "-")
    if lower in ("eom", "end-of-month"):
        today = datetime.date.today()
        first_next = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        return first_next - datetime.timedelta(days=1)
    if len(value) <= 5:
        today = datetime.date.today()
        month, day = (int(p) for p in value.split("-"))
        candidate = today.replace(month=month, day=day)
        if candidate < today:
            candidate = candidate.replace(year=today.year + 1)
        return candidate
    return datetime.date.fromisoformat(value)


def _save_output(
    daily_df: pl.DataFrame,
    rolling_windows: list[int] | None,
    output_file: str,
) -> None:
    output_df = daily_df.select(
        ["date", "dow", "amount", "daily_usage", "total", "overage_gb", "overage_cost"]
    )
    if rolling_windows:
        for w in rolling_windows:
            output_df = output_df.with_columns([pl.col(f"rolling_{w}d")])
    output_df = output_df.with_columns(
        [pl.col("date").dt.strftime("%Y-%m-%d").alias("date")]
    )
    if output_file.endswith(".csv"):
        output_df.write_csv(output_file)
    elif output_file.endswith(".parquet"):
        output_df.write_parquet(output_file)
    else:
        output_df.write_json(output_file)


def calculate_daily_diff(
    input_file: str,
    output_file: str | None = None,
    show_stats: bool = False,
    rolling_windows: list[int] | None = None,
    project_days: int = 0,
    overage_price: float = 6.50,
    overage_gb: float = 25.0,
    last_days: int | None = None,
    billing_end: datetime.date | None = None,
    target_pct: float = 95.0,
) -> pl.DataFrame:
    daily_df = jdata.load_daily_data(input_file)
    daily_df = jdata.add_overage_columns(daily_df, overage_gb, overage_price)
    if rolling_windows:
        daily_df = jdata.add_rolling_averages(daily_df, rolling_windows)

    if billing_end is not None:
        last_date = daily_df.row(-1, named=True)["date"]
        days_to_end = (billing_end - last_date).days
        if days_to_end > 0:
            project_days = days_to_end

    projected_df = None
    projection_avg = 0.0
    if project_days > 0:
        projected_df, projection_avg = jprojection.build_projection(
            daily_df, project_days, rolling_windows, overage_gb, overage_price
        )

    display_cols = [
        "date", "dow", "amount", "daily_usage", "total", "overage_cost", "is_projected",
    ]
    if rolling_windows:
        display_cols += [f"rolling_{w}d" for w in rolling_windows]

    display_df = daily_df.select(display_cols)
    if last_days is not None and last_days > 0:
        display_df = display_df.tail(last_days)
    if projected_df is not None:
        display_df = pl.concat([display_df, projected_df.select(display_cols)])

    jdisplay.print_table(display_df, rolling_windows, len(daily_df), last_days, overage_price, overage_gb)

    last_actual = daily_df.row(-1, named=True)
    current_amount = last_actual["amount"]
    data_cap = last_actual["total"]

    jdisplay.print_current_overage(current_amount, data_cap, last_actual["overage_cost"], overage_gb)

    if projected_df is not None:
        jsummary.print_projection_summary(
            current_amount, data_cap, project_days, projection_avg, projected_df, overage_gb, target_pct
        )
    elif billing_end is not None:
        jsummary.print_billing_period_summary(
            current_amount, data_cap, billing_end, last_actual["overage_cost"], overage_gb, target_pct
        )

    if show_stats:
        jdisplay.print_stats(daily_df, rolling_windows)

    if output_file:
        _save_output(daily_df, rolling_windows, output_file)

    return daily_df


def cmd_diff(args: argparse.Namespace) -> None:
    rolling_windows = None
    if args.rolling_avg:
        rolling_windows = [int(v.strip()) for r in args.rolling_avg for v in r.split(",")]

    billing_end = parse_billing_end(args.billing_end) if args.billing_end else None

    calculate_daily_diff(
        args.input,
        args.output,
        args.stats,
        rolling_windows,
        args.project,
        args.overage_price,
        args.overage_gb,
        args.last_days,
        billing_end,
        args.target_pct,
    )


def cmd_summary(args: argparse.Namespace) -> None:
    df = pl.read_parquet(args.input)
    df = df.with_columns([pl.col("date").str.to_date().alias("date")])
    daily_df = df.group_by("date").last().sort("date")

    print("\n=== Dataset Summary ===\n")
    print(f"Total records: {len(df)}")
    print(f"Unique dates: {len(daily_df)}")
    print(f"Date range: {daily_df['date'].min().strftime('%Y-%m-%d')} to {daily_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"Data cap: {df['total'][0]} GB")
    print(f"Current usage: {daily_df['amount'][-1]:.2f} GB")
    print(f"Remaining: {daily_df['total'][-1] - daily_df['amount'][-1]:.2f} GB")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="jumpingjerboa - Internet usage data analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jumpingjerboa diff data.parquet
  jumpingjerboa diff data.parquet --stats
  jumpingjerboa diff data.parquet --rolling-avg 7 --rolling-avg 14 --rolling-avg 30
  jumpingjerboa diff data.parquet --rolling-avg 7,14,30
  jumpingjerboa diff data.parquet --rolling-avg 7 --project 10
  jumpingjerboa diff data.parquet --rolling-avg 7 --project 10 --last-days 14
  jumpingjerboa diff data.parquet --rolling-avg 7 --project 10 --overage-price 10.00 --overage-gb 50
  jumpingjerboa diff data.parquet --output report.csv
  jumpingjerboa summary data.parquet

Rolling Averages:
  Use --rolling-avg to add rolling average columns. You can specify multiple
  window sizes to see different trends:
    --rolling-avg 7            7-day rolling average
    --rolling-avg 7,14,30      Multiple windows comma-separated

Projection:
  Use --project to estimate future usage based on rolling averages:
    --project 10       Project 10 days into the future

  Use --billing-end to project to a specific date (e.g. end of billing cycle):
    --billing-end eom           Project to end of current month
    --billing-end 03-31         Project to Mar 31 (year inferred; next year if past)
    --billing-end 2026-03-31    Project to a specific date

Limiting Output:
  Use --last-days to only display recent data:
    --last-days 7   Show only the last 7 days (plus projections)

Target Utilization:
  The cap is paid for whether or not it is used, so finishing far below it
  wastes money just as finishing above it does. A cycle is on target when it
  lands between --target-pct of the cap and the cap itself.
    --target-pct 95    Finishing below 95% of the cap is flagged (default)
    --target-pct 0     Only flag going over the cap

Overage Pricing:
  Default pricing is $6.50 per 25 GB block (rounded up to nearest block).
  Customize with --overage-price and --overage-gb.
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    diff_parser = subparsers.add_parser(
        "diff",
        help="Calculate daily usage differences",
        description="Calculate daily internet usage from cumulative data in parquet format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    diff_parser.add_argument("input", metavar="PARQUET_FILE", help="Path to input parquet file")
    diff_parser.add_argument("-o", "--output", metavar="FILE", help="Save results to FILE (.csv, .json, .parquet)")
    diff_parser.add_argument("-s", "--stats", action="store_true", help="Show detailed statistics")
    diff_parser.add_argument("-r", "--rolling-avg", action="append", metavar="DAYS", help="Rolling average window(s)")
    projection_group = diff_parser.add_mutually_exclusive_group()
    projection_group.add_argument("-p", "--project", type=int, default=0, metavar="DAYS", help="Project N days ahead")
    projection_group.add_argument("--billing-end", default=None, metavar="DATE", help="Project to billing end date (eom, MM-DD, YYYY-MM-DD)")
    diff_parser.add_argument("--last-days", type=int, default=None, metavar="N", help="Display last N days only")
    diff_parser.add_argument("--overage-price", type=float, default=6.50, metavar="DOLLARS", help="Price per overage block (default: $6.50)")
    diff_parser.add_argument("--target-pct", type=float, default=95.0, metavar="PCT", help="Lowest acceptable share of the cap to finish on (default: 95)")
    diff_parser.add_argument("--overage-gb", type=float, default=25.0, metavar="GB", help="GB per overage block (default: 25 GB)")
    diff_parser.set_defaults(func=cmd_diff)

    summary_parser = subparsers.add_parser("summary", help="Show dataset summary")
    summary_parser.add_argument("input", metavar="PARQUET_FILE", help="Path to input parquet file")
    summary_parser.set_defaults(func=cmd_summary)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
