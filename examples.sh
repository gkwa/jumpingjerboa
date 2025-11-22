#!/bin/bash
# jumpingjerboa usage examples

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}jumpingjerboa Usage Examples${NC}\n"

# Check if data file is provided
if [ "$#" -eq 0 ]; then
    echo "Usage: ./examples.sh /path/to/astound.parquet"
    echo ""
    echo "This script demonstrates common usage patterns."
    exit 1
fi

DATA_FILE=$1

# Check if file exists
if [ ! -f "$DATA_FILE" ]; then
    echo "Error: File not found: $DATA_FILE"
    exit 1
fi

echo -e "${GREEN}1. Quick summary of dataset${NC}"
echo "Command: python -m jumpingjerboa.main summary $DATA_FILE"
python -m jumpingjerboa.main summary "$DATA_FILE"
echo ""

echo -e "${GREEN}2. Calculate daily usage differences${NC}"
echo "Command: python -m jumpingjerboa.main diff $DATA_FILE"
python -m jumpingjerboa.main diff "$DATA_FILE"
echo ""

echo -e "${GREEN}3. Show statistics${NC}"
echo "Command: python -m jumpingjerboa.main diff $DATA_FILE --stats"
python -m jumpingjerboa.main diff "$DATA_FILE" --stats
echo ""

echo -e "${GREEN}4. Export to CSV${NC}"
OUTPUT_FILE="/tmp/usage_report_$(date +%Y%m%d).csv"
echo "Command: python -m jumpingjerboa.main diff $DATA_FILE -o $OUTPUT_FILE"
python -m jumpingjerboa.main diff "$DATA_FILE" -o "$OUTPUT_FILE"
echo "Saved to: $OUTPUT_FILE"
echo ""

echo -e "${BLUE}Done! Check the files in /tmp/ for exported reports.${NC}"
