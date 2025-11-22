#!/usr/bin/env python3
"""
jumpingjerboa - Internet usage data analysis tool
"""
import argparse
import sys
import pathlib
import polars as pl
import datetime


def calculate_daily_diff(input_file: str, output_file: str = None, show_stats: bool = False, 
                        rolling_windows: list = None, project_days: int = 0):
    """
    Calculate the daily usage difference from the dataset.
    
    Implementation details:
    1. Read parquet file and convert dates/timestamps
    2. Group by date, taking the last (most recent) scrape per day
    3. Calculate daily_usage by taking difference from previous day
    4. Handle month resets (negative diffs mean counter reset to 0)
    5. Add rolling averages if requested using polars rolling_mean()
    6. Project future usage if requested by:
       - Taking the last rolling average value
       - Creating future date records
       - Accumulating usage day by day
       - Checking when cap would be exceeded
    
    Args:
        input_file: Path to the parquet file
        output_file: Optional path to save the results
        show_stats: Show statistics about the data
        rolling_windows: List of day windows for rolling averages (e.g., [7, 14, 30])
        project_days: Number of days to project into the future
    """
    # Read the parquet file
    df = pl.read_parquet(input_file)
    
    # Convert date and scraped_at to datetime if they aren't already
    df = df.with_columns([
        pl.col('date').str.to_date().alias('date'),
        pl.col('scraped_at').str.to_datetime(time_zone='UTC').alias('scraped_at')
    ])
    
    # Sort by date and scraped_at
    df = df.sort(['date', 'scraped_at'])
    
    # For each date, take the last scraped value (most recent for that day)
    daily_df = df.group_by('date').last().sort('date')
    
    # Add day of week
    daily_df = daily_df.with_columns([
        pl.col('date').dt.strftime('%a').alias('dow')
    ])
    
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
    
    # Add rolling averages if requested
    # Implementation: For each window size, use polars rolling_mean() which calculates
    # the mean over the specified number of preceding rows (including current row)
    if rolling_windows:
        for window in rolling_windows:
            daily_df = daily_df.with_columns([
                pl.col('daily_usage').rolling_mean(window_size=window, min_periods=1)
                .alias(f'rolling_{window}d')
            ])
    
    # Add month column for grouping
    daily_df = daily_df.with_columns([
        pl.col('date').dt.strftime('%Y-%m').alias('month')
    ])
    
    # Mark actual data as not projected
    daily_df = daily_df.with_columns([
        pl.lit(False).alias('is_projected')
    ])
    
    # Project future usage if requested
    # Implementation:
    # 1. Take the most recent rolling average (or regular daily average if no rolling window)
    # 2. Create future date records starting from day after last record
    # 3. For each future day, add the average to previous day's total
    # 4. Mark when we exceed the data cap
    projected_df = None
    if project_days > 0:
        # Get the last row to start projection from
        last_row = daily_df.row(-1, named=True)
        last_date = last_row['date']
        current_amount = last_row['amount']
        data_cap = last_row['total']
        
        # Determine which average to use for projection
        if rolling_windows:
            # Use the first (typically smallest) rolling window's most recent value
            projection_avg = last_row[f'rolling_{rolling_windows[0]}d']
        else:
            # Use overall average of daily_usage
            projection_avg = daily_df['daily_usage'].mean()
        
        # Create future dates
        future_dates = []
        future_amounts = []
        future_usages = []
        future_caps = []
        future_dows = []
        future_rolling = {window: [] for window in (rolling_windows or [])}
        
        running_amount = current_amount
        for i in range(1, project_days + 1):
            future_date = last_date + datetime.timedelta(days=i)
            running_amount += projection_avg
            
            future_dates.append(future_date)
            future_amounts.append(running_amount)
            future_usages.append(projection_avg)
            future_caps.append(data_cap)
            future_dows.append(future_date.strftime('%a'))
            
            # Add rolling averages (they'll all be the projection average)
            if rolling_windows:
                for window in rolling_windows:
                    future_rolling[window].append(projection_avg)
        
        # Create projection dataframe with same structure as daily_df
        proj_data = {
            'date': future_dates,
            'dow': future_dows,
            'amount': future_amounts,
            'daily_usage': future_usages,
            'total': future_caps,
            'is_projected': [True] * project_days,
            'month': [d.strftime('%Y-%m') for d in future_dates]
        }
        
        # Add rolling average columns to match daily_df
        if rolling_windows:
            for window in rolling_windows:
                proj_data[f'rolling_{window}d'] = future_rolling[window]
        
        projected_df = pl.DataFrame(proj_data)
    
    # Display results
    print("\n=== Daily Internet Usage ===\n")
    
    # Build header based on rolling windows
    header = f"{'Date':<12} {'DOW':<5} {'Total Usage':<12} {'Daily Usage':<12}"
    if rolling_windows:
        for window in rolling_windows:
            header += f" {f'Avg {window}d':<12}"
    header += f" {'% of Cap':<10}"
    
    print(header)
    print("-" * len(header))
    
    # Combine actual and projected data for display
    # Select only the columns we need for display to ensure schemas match
    display_cols = ['date', 'dow', 'amount', 'daily_usage', 'total', 'is_projected']
    if rolling_windows:
        for window in rolling_windows:
            display_cols.append(f'rolling_{window}d')
    
    display_df = daily_df.select(display_cols)
    if projected_df is not None:
        display_df = pl.concat([display_df, projected_df.select(display_cols)])
    
    for row in display_df.iter_rows(named=True):
        if row['daily_usage'] is not None:
            pct = (row['amount'] / row['total']) * 100
            date_str = row['date'].strftime('%Y-%m-%d')
            is_proj = row['is_projected']
            proj_marker = '*' if is_proj else ' '
            
            line = f"{date_str:<12} {row['dow']:<5} {row['amount']:>8.2f} GB   {row['daily_usage']:>8.2f} GB  "
            
            if rolling_windows:
                for window in rolling_windows:
                    avg_val = row[f'rolling_{window}d']
                    line += f" {avg_val:>8.2f} GB  "
            
            line += f" {pct:>6.2f}%{proj_marker}"
            print(line)
    
    # Show projection summary if we projected
    if projected_df is not None:
        print("\n* = Projected (estimated future usage)")
        last_projected = projected_df.row(-1, named=True)
        final_amount = last_projected['amount']
        data_cap = last_projected['total']
        
        print(f"\nProjection Summary (based on {projection_avg:.2f} GB/day average):")
        print(f"  Current usage: {current_amount:.2f} GB")
        print(f"  Projected usage in {project_days} days: {final_amount:.2f} GB")
        print(f"  Data cap: {data_cap} GB")
        
        if final_amount > data_cap:
            overage = final_amount - data_cap
            print(f"  ⚠️  WARNING: Projected to EXCEED cap by {overage:.2f} GB")
            
            # Find when we'll hit the cap
            for i, row in enumerate(projected_df.iter_rows(named=True)):
                if row['amount'] > data_cap:
                    days_until_cap = i + 1
                    cap_date = row['date'].strftime('%Y-%m-%d')
                    print(f"  📅 Estimated to hit cap on {cap_date} ({days_until_cap} days from now)")
                    break
        else:
            remaining = data_cap - final_amount
            print(f"  ✓ Projected to stay under cap with {remaining:.2f} GB remaining")
    
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
        
        # Rolling average stats if available
        if rolling_windows:
            print("\nRolling Average Statistics:")
            for window in rolling_windows:
                col_name = f'rolling_{window}d'
                latest_avg = daily_df[col_name][-1]
                print(f"  Last {window}-day average: {latest_avg:.2f} GB/day")
        
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
        output_df = daily_df.select(['date', 'dow', 'amount', 'daily_usage', 'total'])
        
        # Add rolling averages to output
        if rolling_windows:
            for window in rolling_windows:
                output_df = output_df.with_columns([
                    pl.col(f'rolling_{window}d')
                ])
        
        output_df = output_df.with_columns([
            pl.col('date').dt.strftime('%Y-%m-%d').alias('date')
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
    # Parse rolling windows
    rolling_windows = None
    if args.rolling:
        rolling_windows = []
        for r in args.rolling:
            # Support comma-separated values
            for val in r.split(','):
                rolling_windows.append(int(val.strip()))
    
    calculate_daily_diff(args.input, args.output, args.stats, rolling_windows, args.project)


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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jumpingjerboa diff data.parquet
  jumpingjerboa diff data.parquet --stats
  jumpingjerboa diff data.parquet -r 7 -r 14 -r 30
  jumpingjerboa diff data.parquet -r 7,14,30
  jumpingjerboa diff data.parquet -r 7 -p 10
  jumpingjerboa diff data.parquet -o report.csv
  jumpingjerboa summary data.parquet

Rolling Averages:
  Use -r/--rolling to add rolling average columns. You can specify multiple
  window sizes to see different trends:
    -r 7        7-day rolling average
    -r 7 -r 14  Both 7-day and 14-day rolling averages
    -r 7,14,30  Same as above but comma-separated

Projection:
  Use -p/--project to estimate future usage based on rolling averages:
    -p 10       Project 10 days into the future
  
  When projecting, the tool uses the most recent rolling average (if specified)
  or the overall average to estimate daily usage going forward. It will warn
  you if you're projected to exceed your data cap.
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Diff subcommand
    diff_parser = subparsers.add_parser(
        'diff',
        help='Calculate daily usage differences',
        description='Calculate daily internet usage from cumulative data in parquet format',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    diff_parser.add_argument(
        'input',
        metavar='PARQUET_FILE',
        help='Path to input parquet file containing usage data'
    )
    diff_parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Save results to FILE (supports .csv, .json, .parquet)'
    )
    diff_parser.add_argument(
        '-s', '--stats',
        action='store_true',
        help='Show detailed statistics (monthly averages, min/max, etc.)'
    )
    diff_parser.add_argument(
        '-r', '--rolling',
        action='append',
        metavar='DAYS',
        help='Add rolling average column for DAYS (can specify multiple times or comma-separated)'
    )
    diff_parser.add_argument(
        '-p', '--project',
        type=int,
        default=0,
        metavar='DAYS',
        help='Project usage DAYS into the future based on rolling average'
    )
    diff_parser.set_defaults(func=cmd_diff)
    
    # Summary subcommand
    summary_parser = subparsers.add_parser(
        'summary',
        help='Show dataset summary',
        description='Display quick overview of usage data'
    )
    summary_parser.add_argument(
        'input',
        metavar='PARQUET_FILE',
        help='Path to input parquet file containing usage data'
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
