import polars as pl


def _to_usage_dates(daily: pl.DataFrame) -> pl.DataFrame:
    """Relabel each reading with the day whose bytes it actually counts.

    Astound posts the meter once a day, around 8am local, and the figure does
    not move again until the next morning's post.

    A reading taken on day D therefore covers usage through the end of day
    D-1, so its date is shifted back one day.

    A reading of exactly zero that follows a larger one was taken on the first
    day of a new billing cycle, and is dropped rather than shifted: the
    counter resets before the final day of the previous cycle is ever
    published, leaving that day unknowable.

    A reset reading that is not zero was taken later in the new cycle, so the
    day it shifts onto still belongs to that cycle and the row is kept.
    """
    resets = pl.col("amount") < pl.col("amount").shift(1)
    opens_cycle = (resets & (pl.col("amount") == 0)).fill_null(False)
    daily = daily.filter(~opens_cycle)
    return daily.with_columns(pl.col("date") - pl.duration(days=1))


def load_daily_data(input_file: str) -> pl.DataFrame:
    df = pl.read_parquet(input_file)
    df = df.with_columns([
        pl.col("date").str.to_date().alias("date"),
        pl.col("scraped_at").str.to_datetime(time_zone="UTC").alias("scraped_at"),
    ])
    df = df.sort(["date", "scraped_at"])
    daily = df.group_by("date").last().sort("date")
    daily = _to_usage_dates(daily)
    daily = daily.with_columns([pl.col("date").dt.strftime("%a").alias("dow")])
    daily = daily.with_columns([
        (pl.col("amount") - pl.col("amount").shift(1)).alias("daily_usage")
    ])
    # A negative delta means the previous row sat in the prior billing cycle,
    # so the cumulative amount is itself the first kept day's usage.
    daily = daily.with_columns([
        pl.when(pl.col("daily_usage") < 0)
        .then(pl.col("amount"))
        .otherwise(pl.col("daily_usage"))
        .alias("daily_usage")
    ])
    daily = daily.with_columns([pl.col("date").dt.strftime("%Y-%m").alias("month")])
    return daily.with_columns([pl.lit(False).alias("is_projected")])


def add_overage_columns(df: pl.DataFrame, block_gb: float, price: float) -> pl.DataFrame:
    df = df.with_columns([
        pl.when(pl.col("amount") > pl.col("total"))
        .then(pl.col("amount") - pl.col("total"))
        .otherwise(0.0)
        .alias("overage_gb")
    ])
    return df.with_columns([
        pl.when(pl.col("overage_gb") > 0)
        .then((pl.col("overage_gb") / block_gb).ceil() * price)
        .otherwise(0.0)
        .alias("overage_cost")
    ])


def add_rolling_averages(df: pl.DataFrame, windows: list[int]) -> pl.DataFrame:
    for window in windows:
        df = df.with_columns([
            pl.col("daily_usage")
            .rolling_mean(window_size=window, min_periods=1)
            .alias(f"rolling_{window}d")
        ])
    return df
