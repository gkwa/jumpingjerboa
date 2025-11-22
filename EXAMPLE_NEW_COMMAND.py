"""
Example: Adding a new subcommand to jumpingjerboa

This shows how easy it is to extend the CLI with new functionality.
"""

# Example: Add a "predict" subcommand that estimates future usage
# Add this to main.py:

def cmd_predict(args):
    """Predict future usage based on historical averages"""
    import polars as pl
    
    df = pl.read_parquet(args.input)
    
    # Convert date to datetime if it isn't already
    df = df.with_columns([
        pl.col('date').str.to_date().alias('date')
    ])
    
    # Get daily averages
    daily_df = df.group_by('date').last().sort('date')
    daily_df = daily_df.with_columns([
        (pl.col('amount') - pl.col('amount').shift(1)).alias('daily_usage')
    ])
    
    # Handle month resets
    daily_df = daily_df.with_columns([
        pl.when(pl.col('daily_usage') < 0)
        .then(pl.col('amount'))
        .otherwise(pl.col('daily_usage'))
        .alias('daily_usage')
    ])
    
    # Calculate average
    avg_daily = daily_df['daily_usage'].mean()
    
    # Get current month progress
    latest = daily_df.row(-1, named=True)
    current_usage = latest['amount']
    days_in_month = 30  # simplified
    day_of_month = latest['date'].day
    days_remaining = days_in_month - day_of_month
    
    predicted_total = current_usage + (avg_daily * days_remaining)
    
    print(f"\n=== Usage Prediction ===\n")
    print(f"Current usage: {current_usage:.2f} GB")
    print(f"Average daily: {avg_daily:.2f} GB/day")
    print(f"Days remaining: {days_remaining}")
    print(f"Predicted total: {predicted_total:.2f} GB")
    print(f"Data cap: {latest['total']} GB")
    
    if predicted_total > latest['total']:
        print(f"⚠️  WARNING: Predicted to exceed cap by {predicted_total - latest['total']:.2f} GB")
    else:
        print(f"✓ Predicted to stay under cap")


# Then register it in main():
# predict_parser = subparsers.add_parser('predict', help='Predict end-of-month usage')
# predict_parser.add_argument('input', help='Path to parquet file')
# predict_parser.set_defaults(func=cmd_predict)

# Usage:
# python -m jumpingjerboa.main predict /path/to/astound.parquet
