import datetime
import math

import polars as pl


def build_projection(
    daily_df: pl.DataFrame,
    project_days: int,
    rolling_windows: list[int] | None,
    block_gb: float,
    price: float,
) -> tuple[pl.DataFrame, float]:
    last_row = daily_df.row(-1, named=True)
    last_date = last_row["date"]
    current_amount = last_row["amount"]
    data_cap = last_row["total"]

    if rolling_windows:
        avg = last_row[f"rolling_{rolling_windows[0]}d"]
    else:
        avg = daily_df["daily_usage"].mean()

    dates, amounts, usages, caps, dows, overages, costs = [], [], [], [], [], [], []
    rolling: dict[int, list[float]] = {w: [] for w in (rolling_windows or [])}

    running = current_amount
    for i in range(1, project_days + 1):
        d = last_date + datetime.timedelta(days=i)
        running += avg
        ov = max(0.0, running - data_cap)
        cost = math.ceil(ov / block_gb) * price if ov > 0 else 0.0

        dates.append(d)
        amounts.append(running)
        usages.append(avg)
        caps.append(data_cap)
        dows.append(d.strftime("%a"))
        overages.append(ov)
        costs.append(cost)
        for w in (rolling_windows or []):
            rolling[w].append(avg)

    proj_data: dict = {
        "date": dates,
        "dow": dows,
        "amount": amounts,
        "daily_usage": usages,
        "total": caps,
        "overage_gb": overages,
        "overage_cost": costs,
        "is_projected": [True] * project_days,
        "month": [d.strftime("%Y-%m") for d in dates],
    }
    for w in (rolling_windows or []):
        proj_data[f"rolling_{w}d"] = rolling[w]

    return pl.DataFrame(proj_data), avg
