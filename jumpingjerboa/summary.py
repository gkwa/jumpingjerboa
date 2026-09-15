"""Verdict printed under the usage table once the cycle is projected out."""

import datetime
import math

import polars as pl

import jumpingjerboa.utilization as jutil


def _print_overage(
    verdict: jutil.Verdict,
    final_cost: float,
    block_gb: float,
    projected_df: pl.DataFrame | None,
) -> None:
    overage = verdict.final_amount - verdict.cap
    blocks = math.ceil(overage / block_gb)
    print(f"  EXCEEDED cap by {overage:.2f} GB")
    print(f"  Overage blocks: {blocks} x {block_gb:.0f} GB = {blocks * block_gb:.0f} GB charged")
    print(f"  Cost: ${final_cost:.2f}")
    if projected_df is None:
        return
    for i, row in enumerate(projected_df.iter_rows(named=True)):
        if row["amount"] <= verdict.cap:
            continue
        ov = row["overage_gb"]
        blks = math.ceil(ov / block_gb)
        print(f"  Estimated to hit cap on {row['date'].strftime('%Y-%m-%d')} ({i + 1} days from now)")
        print(f"     At that point: {ov:.2f} GB over = {blks} blocks = ${row['overage_cost']:.2f}")
        return


def _print_under_target(
    verdict: jutil.Verdict,
    current_amount: float,
    avg: float | None,
    last_date: datetime.date | None,
) -> None:
    print(f"  UNDER TARGET: finishing at {verdict.final_amount:.2f} GB, {verdict.pct_of_cap:.2f}% of the {verdict.cap:.0f} GB cap")
    print(f"  Leaving {verdict.unused_gb:.2f} GB of paid allowance unused, against a {verdict.target_gb:.2f} GB target")
    days = jutil.days_to_cap(current_amount, verdict.cap, avg) if avg else None
    if days is not None and last_date is not None:
        reached = last_date + datetime.timedelta(days=days)
        print(f"  At {avg:.2f} GB/day the cap is {days} days off, on {reached.strftime('%Y-%m-%d')}")
    print("  Cost: $0.00")


def _print_on_target(verdict: jutil.Verdict) -> None:
    print(f"  ON TARGET: finishing at {verdict.final_amount:.2f} GB, {verdict.pct_of_cap:.2f}% of the {verdict.cap:.0f} GB cap")
    print(f"  Headroom left: {verdict.unused_gb:.2f} GB")
    print("  Cost: $0.00")


def _print_verdict(
    verdict: jutil.Verdict,
    current_amount: float,
    final_cost: float,
    block_gb: float,
    projected_df: pl.DataFrame | None,
    avg: float | None,
    last_date: datetime.date | None,
) -> None:
    if verdict.is_over:
        _print_overage(verdict, final_cost, block_gb, projected_df)
        return
    if verdict.is_under_target:
        _print_under_target(verdict, current_amount, avg, last_date)
        return
    _print_on_target(verdict)


def _print_pace_band(
    current_amount: float,
    verdict: jutil.Verdict,
    project_days: int,
    projection_avg: float,
) -> None:
    band = jutil.pace_band(current_amount, verdict.cap, verdict.target_pct, project_days)
    if band is None or band[1] <= 0:
        print(f"  No headroom left: already at or over the {verdict.cap:.0f} GB cap")
        return

    low, high = band
    print(f"  Target: finish between {verdict.target_gb:.2f} GB and {verdict.cap:.0f} GB ({verdict.target_pct:.0f}% of cap or better)")
    if low < high:
        print(f"  Pace to land there: {low:.2f} - {high:.2f} GB/day for the remaining {project_days} days")
    else:
        print(f"  Pace to land there: {high:.2f} GB/day for the remaining {project_days} days")

    if projection_avg > high:
        print(f"     (pacing {projection_avg:.2f} GB/day -- {projection_avg - high:.2f} GB/day above the band)")
    elif projection_avg < low:
        print(f"     (pacing {projection_avg:.2f} GB/day -- {low - projection_avg:.2f} GB/day below the band)")
    else:
        print(f"     (pacing {projection_avg:.2f} GB/day -- inside the band)")


def print_projection_summary(
    current_amount: float,
    data_cap: float,
    project_days: int,
    projection_avg: float,
    projected_df: pl.DataFrame,
    block_gb: float,
    target_pct: float,
) -> None:
    last = projected_df.row(-1, named=True)
    first_projected = projected_df.row(0, named=True)["date"]
    last_date = first_projected - datetime.timedelta(days=1)
    verdict = jutil.Verdict(last["amount"], data_cap, target_pct)

    print("\n* = Projected (estimated future usage)")
    print(f"\nProjection Summary (based on {projection_avg:.2f} GB/day average):")
    print(f"  Current usage: {current_amount:.2f} GB")
    print(f"  Projected usage in {project_days} days: {verdict.final_amount:.2f} GB")
    print(f"  Data cap: {data_cap:.0f} GB")

    _print_pace_band(current_amount, verdict, project_days, projection_avg)
    _print_verdict(
        verdict,
        current_amount,
        last["overage_cost"],
        block_gb,
        projected_df,
        projection_avg,
        last_date,
    )


def print_billing_period_summary(
    current_amount: float,
    data_cap: float,
    billing_end: datetime.date,
    final_cost: float,
    block_gb: float,
    target_pct: float,
) -> None:
    verdict = jutil.Verdict(current_amount, data_cap, target_pct)
    print(f"\nBilling Period Summary (ended {billing_end.strftime('%Y-%m-%d')}):")
    print(f"  Final usage: {current_amount:.2f} GB")
    print(f"  Data cap: {data_cap:.0f} GB")
    _print_verdict(verdict, current_amount, final_cost, block_gb, None, None, None)
