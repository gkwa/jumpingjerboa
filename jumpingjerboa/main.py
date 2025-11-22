#!/usr/bin/env python3
"""
jumpingjerboa - Internet usage data analysis tool
"""
import argparse
import sys
import pathlib
import polars as pl


def calculate_daily_diff(input_file: str, output_file: str = None, show_stats: bool = False):
    """
    Calculate the daily usage difference from the dataset.
    
    Args:
        input_file: Path to the parquet file
        output_file: Optional path to save the results
        show_stats: Show statistics about the data
    """
    # Read the parquet file
    df = pl.read_parquet(input_file)
    
    # Convert date and scraped_at to datetime if they aren't already
    df = df.with_columns([
        pl.col('date').str.to_date().alias('date'),
        pl.col('scraped_at').str.to_datetime().alias('scraped_at')
    ])
    
    # Sort by date and scraped_at
    df = df.sort(['date', 'scraped_at'])
    
    # For each date, take the last scraped value (most recent for that day)
    daily_df = df.group_by('date').last().sort('date')
    
    # Calculate the difference from previous day
    daily_df = daily_df.with_columns([
        (pl.col('amount') - pl.col('amount').shift(1)).alias('daily_usage')
    ])
    
    # Handle month resets (when usage goes back to 0 or negative diff)
    # When we see a negative diff, it means the month reset
    daily_df = daily_df.with_columns([
        pl.when(pl.col('daily_usage') < 0)
        .then(pl.col('amount'))
        .otherwise(pl.col('daily_usage'))
        .alias('daily_usage')
    ])
    
    # Add month column for grouping
    daily_df = daily_df.with_columns([
        pl.col('date').dt.strftime('%Y-%m').alias('month')
    ])
    
    # Display results
    print("\n=== Daily Internet Usage ===\n")
    print(f"{'Date':<12} {'Total Usage':<12} {'Daily Usage':<12} {'% of Cap':<10}")
    print("-" * 50)
    
    for row in daily_df.iter_rows(named=True):
        if row['daily_usage'] is not None:
            pct = (row['amount'] / row['total']) * 100
            date_str = row['date'].strftime('%Y-%m-%d')
            print(f"{date_str:<12} {row['amount']:>8.2f} GB   {row['daily_usage']:>8.2f} GB   {pct:>6.2f}%")
    
    if show_stats:
        print("\n=== Statistics ===\n")
        
        # Overall stats
        stats = daily_df.select([
            pl.col('daily_usage').mean().alias('mean'),
            pl.col('daily_usage').median().alias('median'),
            pl.col('daily_usage').max().alias('max'),
            pl.col('daily_usage').min().alias('min')
        ])
        
        print("Overall Statistics:")
        print(f"  Average daily usage: {stats['mean'][0]:.2f} GB")
        print(f"  Median daily usage: {stats['median'][0]:.2f} GB")
        print(f"  Max daily usage: {stats['max'][0]:.2f} GB")
        print(f"  Min daily usage: {stats['min'][0]:.2f} GB")
        
        # Monthly stats
        print("\nMonthly Statistics:")
        monthly_stats = daily_df.group_by('month').agg([
            pl.col('daily_usage').mean().alias('avg_daily'),
            pl.col('amount').max().alias('total'),
            pl.col('daily_usage').count().alias('days')
        ]).sort('month')
        
        for row in monthly_stats.iter_rows(named=True):
            print(f"  {row['month']}: {row['total']:.2f} GB total, {row['avg_daily']:.2f} GB/day avg, {row['days']:.0f} days tracked")
    
    # Save to file if requested
    if output_file:
        output_df = daily_df.select([
            pl.col('date').dt.strftime('%Y-%m-%d').alias('date'),
            'amount',
            'daily_usage',
            'total'
        ])
        
        if output_file.endswith('.csv'):
            output_df.write_csv(output_file)
        elif output_file.endswith('.parquet'):
            output_df.write_parquet(output_file)
        else:
            output_df.write_json(output_file)
        
        print(f"\n✓ Results saved to {output_file}")
    
    return daily_df


def cmd_diff(args):
    """Handle the diff subcommand"""
    calculate_daily_diff(args.input, args.output, args.stats)


def cmd_summary(args):
    """Handle the summary subcommand"""
    df = pl.read_parquet(args.input)
    
    # Convert date to datetime if it isn't already
    df = df.with_columns([
        pl.col('date').str.to_date().alias('date')
    ])
    
    # Get unique dates
    daily_df = df.group_by('date').last().sort('date')
    
    print("\n=== Dataset Summary ===\n")
    print(f"Total records: {len(df)}")
    print(f"Unique dates: {len(daily_df)}")
    print(f"Date range: {daily_df['date'].min().strftime('%Y-%m-%d')} to {daily_df['date'].max().strftime('%Y-%m-%d')}")
    print(f"Data cap: {df['total'][0]} GB")
    print(f"Current usage: {daily_df['amount'][-1]:.2f} GB")
    print(f"Remaining: {daily_df['total'][-1] - daily_df['amount'][-1]:.2f} GB")


def main():
    """Main entry point for jumpingjerboa CLI"""
    parser = argparse.ArgumentParser(
        description="jumpingjerboa - Internet usage data analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Diff subcommand
    diff_parser = subparsers.add_parser(
        'diff',
        help='Calculate daily usage differences'
    )
    diff_parser.add_argument(
        'input',
        help='Path to input parquet file'
    )
    diff_parser.add_argument(
        '-o', '--output',
        help='Path to output file (csv, json, or parquet)'
    )
    diff_parser.add_argument(
        '-s', '--stats',
        action='store_true',
        help='Show statistics'
    )
    diff_parser.set_defaults(func=cmd_diff)
    
    # Summary subcommand
    summary_parser = subparsers.add_parser(
        'summary',
        help='Show dataset summary'
    )
    summary_parser.add_argument(
        'input',
        help='Path to input parquet file'
    )
    summary_parser.set_defaults(func=cmd_summary)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute the subcommand
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
