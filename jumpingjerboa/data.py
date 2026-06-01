import polars as pl


def load_daily_data(input_file: str) -> pl.DataFrame:
    df = pl.read_parquet(input_file)
    df = df.with_columns([
        pl.col("date").str.to_date().alias("date"),
        pl.col("scraped_at").str.to_datetime(time_zone="UTC").alias("scraped_at"),
    ])
    df = df.sort(["date", "scraped_at"])
    daily = df.group_by("date").last().sort("date")
    daily = daily.with_columns([pl.col("date").dt.strftime("%a").alias("dow")])
    daily = daily.with_columns([
        (pl.col("amount") - pl.col("amount").shift(1)).alias("daily_usage")
    ])
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
