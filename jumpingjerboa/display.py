import datetime
import math

import polars as pl


def print_table(
    display_df: pl.DataFrame,
    rolling_windows: list[int] | None,
    total_days: int,
    last_days: int | None,
    overage_price: float,
    overage_gb: float,
) -> None:
    print("\n=== Daily Internet Usage ===\n")
    header = f"{'Date':<12} {'DOW':<5} {'Total Usage':<12} {'Daily Usage':<12}"
    if rolling_windows:
        for w in rolling_windows:
            header += f" {f'Avg {w}d':<12}"
    header += f" {'Cap':<8} {'% of Cap':<10} {'Overage Cost':<13}"
    print(header)
    print("-" * len(header))

    prev_cost = 0.0
    for row in display_df.iter_rows(named=True):
        if row["daily_usage"] is None:
            continue
        pct = (row["amount"] / row["total"]) * 100
        marker = "*" if row["is_projected"] else " "
        line = f"{row['date'].strftime('%Y-%m-%d'):<12} {row['dow']:<5} {row['amount']:>8.2f} GB   {row['daily_usage']:>8.2f} GB  "
        if rolling_windows:
            for w in rolling_windows:
                line += f" {row[f'rolling_{w}d']:>8.2f} GB  "
        line += f" {row['total']:>4.0f} GB  {pct:>6.2f}%  "
        cost = row["overage_cost"]
        cost_str = f"${cost:>6.2f}" if cost > prev_cost else ""
        prev_cost = cost
        line += f"{cost_str:<11}{marker}"
        print(line)

    if last_days is not None and last_days > 0 and total_days > last_days:
        print(f"\nShowing last {last_days} days (out of {total_days} total days)")
    print(f"\nOverage Pricing: ${overage_price:.2f} per {overage_gb:.0f} GB block (rounded up)")


def print_current_overage(
    current_amount: float,
    data_cap: float,
    overage_cost: float,
    block_gb: float,
) -> None:
    if current_amount <= data_cap:
        return
    overage = current_amount - data_cap
    blocks = math.ceil(overage / block_gb)
    print(f"\nCurrent overage: {overage:.2f} GB ({blocks} block{'s' if blocks != 1 else ''}) = ${overage_cost:.2f}")


def _print_cap_result(
    final_amount: float,
    data_cap: float,
    final_cost: float,
    block_gb: float,
    projected_df: pl.DataFrame | None,
) -> None:
    if final_amount > data_cap:
        overage = final_amount - data_cap
        blocks = math.ceil(overage / block_gb)
        print(f"  EXCEEDED cap by {overage:.2f} GB")
        print(f"  Overage blocks: {blocks} x {block_gb:.0f} GB = {blocks * block_gb:.0f} GB charged")
        print(f"  Cost: ${final_cost:.2f}")
        if projected_df is not None:
            for i, row in enumerate(projected_df.iter_rows(named=True)):
                if row["amount"] > data_cap:
                    ov = row["overage_gb"]
                    blks = math.ceil(ov / block_gb)
                    print(f"  Estimated to hit cap on {row['date'].strftime('%Y-%m-%d')} ({i + 1} days from now)")
                    print(f"     At that point: {ov:.2f} GB over = {blks} blocks = ${row['overage_cost']:.2f}")
                    break
    else:
        remaining = data_cap - final_amount
        print(f"  Stayed under cap with {remaining:.2f} GB remaining")
        print("  Cost: $0.00")


def print_projection_summary(
    current_amount: float,
    data_cap: float,
    project_days: int,
    projection_avg: float,
    projected_df: pl.DataFrame,
    block_gb: float,
) -> None:
    last = projected_df.row(-1, named=True)
    final_amount = last["amount"]
    final_cost = last["overage_cost"]

    print("\n* = Projected (estimated future usage)")
    print(f"\nProjection Summary (based on {projection_avg:.2f} GB/day average):")
    print(f"  Current usage: {current_amount:.2f} GB")
    print(f"  Projected usage in {project_days} days: {final_amount:.2f} GB")
    print(f"  Data cap: {data_cap:.0f} GB")

    budget = max(0.0, (data_cap - current_amount) / project_days)
    if budget > 0:
        diff = projection_avg - budget
        direction = "over" if diff > 0 else "under"
        print(f"  To stay under cap: budget {budget:.2f} GB/day for the remaining {project_days} days")
        print(f"     (pacing {projection_avg:.2f} GB/day -- {abs(diff):.2f} GB/day {direction} budget)")
    else:
        print(f"  No daily budget left: already at or over the {data_cap:.0f} GB cap")

    _print_cap_result(final_amount, data_cap, final_cost, block_gb, projected_df)


def print_billing_period_summary(
    current_amount: float,
    data_cap: float,
    billing_end: datetime.date,
    final_cost: float,
    block_gb: float,
) -> None:
    print(f"\nBilling Period Summary (ended {billing_end.strftime('%Y-%m-%d')}):")
    print(f"  Final usage: {current_amount:.2f} GB")
    print(f"  Data cap: {data_cap:.0f} GB")
    _print_cap_result(current_amount, data_cap, final_cost, block_gb, None)


def print_stats(daily_df: pl.DataFrame, rolling_windows: list[int] | None) -> None:
    print("\n=== Statistics ===\n")
    stats = daily_df.select([
        pl.col("daily_usage").mean().alias("mean"),
        pl.col("daily_usage").median().alias("median"),
        pl.col("daily_usage").max().alias("max"),
        pl.col("daily_usage").min().alias("min"),
    ])
    print("Overall Statistics:")
    print(f"  Average daily usage: {stats['mean'][0]:.2f} GB")
    print(f"  Median daily usage: {stats['median'][0]:.2f} GB")
    print(f"  Max daily usage: {stats['max'][0]:.2f} GB")
    print(f"  Min daily usage: {stats['min'][0]:.2f} GB")

    if rolling_windows:
        print("\nRolling Average Statistics:")
        for w in rolling_windows:
            print(f"  Last {w}-day average: {daily_df[f'rolling_{w}d'][-1]:.2f} GB/day")

    print("\nMonthly Statistics:")
    monthly = (
        daily_df.group_by("month")
        .agg([
            pl.col("daily_usage").mean().alias("avg_daily"),
            pl.col("amount").max().alias("total"),
            pl.col("daily_usage").count().alias("days"),
            pl.col("overage_cost").max().alias("max_cost"),
        ])
        .sort("month")
    )
    for row in monthly.iter_rows(named=True):
        cost_info = f", ${row['max_cost']:.2f} max overage" if row["max_cost"] > 0 else ""
        print(f"  {row['month']}: {row['total']:.2f} GB total, {row['avg_daily']:.2f} GB/day avg, {row['days']:.0f} days tracked{cost_info}")
