#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Ensure the output directory exists and is writable
log "${BLUE}Creating output directory...${NC}"
mkdir -p /app/kometa
chmod -R 755 /app/kometa
ls -la /app/kometa/ || log "${YELLOW}Warning: /app/kometa/ does not exist${NC}"

# Function to get next cron run time
get_next_cron_time() {
    /usr/local/bin/python3 -c "
import datetime

def parse_cron_field(field, min_val, max_val):
    \"\"\"Parse a cron field and return a sorted list of valid values.\"\"\"
    values = set()
    
    for part in field.split(','):
        part = part.strip()
        
        # Handle step values (*/n or n-m/step)
        if '/' in part:
            range_part, step = part.split('/')
            step = int(step)
            
            if range_part == '*':
                start, end = min_val, max_val
            elif '-' in range_part:
                start, end = map(int, range_part.split('-'))
            else:
                start = int(range_part)
                end = max_val
            
            values.update(range(start, end + 1, step))
        
        # Handle ranges (n-m)
        elif '-' in part:
            start, end = map(int, part.split('-'))
            values.update(range(start, end + 1))
        
        # Handle wildcard (*)
        elif part == '*':
            values.update(range(min_val, max_val + 1))
        
        # Handle single number
        else:
            values.add(int(part))
    
    return sorted(list(values))

cron_expression = '$CRON'
parts = cron_expression.split()

if len(parts) != 5:
    print('Unable to parse cron expression')
    exit(0)

minute_field, hour_field, day_field, month_field, dow_field = parts

try:
    # Parse each field
    minutes = parse_cron_field(minute_field, 0, 59)
    hours = parse_cron_field(hour_field, 0, 23)
    days = parse_cron_field(day_field, 1, 31) if day_field != '*' else None
    months = parse_cron_field(month_field, 1, 12) if month_field != '*' else None
    dows = parse_cron_field(dow_field, 0, 6) if dow_field != '*' else None
    
    now = datetime.datetime.now()
    
    # Start searching from the next minute
    search_time = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    
    # Search for up to 366 days
    for _ in range(366 * 24 * 60):
        # Check month
        if months and search_time.month not in months:
            search_time = search_time.replace(day=1, hour=0, minute=0)
            search_time += datetime.timedelta(days=32)
            search_time = search_time.replace(day=1)
            continue
        
        # Check day of month
        if days and search_time.day not in days:
            search_time = search_time.replace(hour=0, minute=0)
            search_time += datetime.timedelta(days=1)
            continue
        
        # Check day of week (convert Python weekday to cron weekday)
        if dows:
            cron_dow = (search_time.weekday() + 1) % 7
            if cron_dow not in dows:
                search_time = search_time.replace(hour=0, minute=0)
                search_time += datetime.timedelta(days=1)
                continue
        
        # Check hour
        if search_time.hour not in hours:
            search_time = search_time.replace(minute=0)
            search_time += datetime.timedelta(hours=1)
            continue
        
        # Check minute
        if search_time.minute not in minutes:
            search_time += datetime.timedelta(minutes=1)
            continue
        
        # Found a valid time
        print(search_time.strftime('%Y-%m-%d %H:%M:%S'))
        exit(0)
    
    print('Unable to calculate next cron time within 366 days')

except (ValueError, IndexError) as e:
    print('Unable to reliably parse and calculate next cron expression')
"
}

# Create a wrapper script that includes the next schedule calculation
# We need to bake the CRON value in but escape other variables
cat > /app/run-tssk.sh << WRAPPER_EOF
#!/bin/bash

# Set timezone - use passed value or default to UTC
export TZ="${TZ:-UTC}"

# Ensure the output directory exists and is writable
mkdir -p /app/kometa
chmod -R 755 /app/kometa

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo -e "[\$(date '+%Y-%m-%d %H:%M:%S')] \$1"
}

# Function to get next cron run time
get_next_cron_time() {
    /usr/local/bin/python3 -c "
import datetime

def parse_cron_field(field, min_val, max_val):
    \"\"\"Parse a cron field and return a sorted list of valid values.\"\"\"
    values = set()
    
    for part in field.split(','):
        part = part.strip()
        
        # Handle step values (*/n or n-m/step)
        if '/' in part:
            range_part, step = part.split('/')
            step = int(step)
            
            if range_part == '*':
                start, end = min_val, max_val
            elif '-' in range_part:
                start, end = map(int, range_part.split('-'))
            else:
                start = int(range_part)
                end = max_val
            
            values.update(range(start, end + 1, step))
        
        # Handle ranges (n-m)
        elif '-' in part:
            start, end = map(int, part.split('-'))
            values.update(range(start, end + 1))
        
        # Handle wildcard (*)
        elif part == '*':
            values.update(range(min_val, max_val + 1))
        
        # Handle single number
        else:
            values.add(int(part))
    
    return sorted(list(values))

cron_expression = '${CRON}'
parts = cron_expression.split()

if len(parts) != 5:
    print('Unable to parse cron expression')
    exit(0)

minute_field, hour_field, day_field, month_field, dow_field = parts

try:
    # Parse each field
    minutes = parse_cron_field(minute_field, 0, 59)
    hours = parse_cron_field(hour_field, 0, 23)
    days = parse_cron_field(day_field, 1, 31) if day_field != '*' else None
    months = parse_cron_field(month_field, 1, 12) if month_field != '*' else None
    dows = parse_cron_field(dow_field, 0, 6) if dow_field != '*' else None
    
    now = datetime.datetime.now()
    
    # Start searching from the next minute
    search_time = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    
    # Search for up to 366 days
    for _ in range(366 * 24 * 60):
        # Check month
        if months and search_time.month not in months:
            search_time = search_time.replace(day=1, hour=0, minute=0)
            search_time += datetime.timedelta(days=32)
            search_time = search_time.replace(day=1)
            continue
        
        # Check day of month
        if days and search_time.day not in days:
            search_time = search_time.replace(hour=0, minute=0)
            search_time += datetime.timedelta(days=1)
            continue
        
        # Check day of week (convert Python weekday to cron weekday)
        if dows:
            cron_dow = (search_time.weekday() + 1) % 7
            if cron_dow not in dows:
                search_time = search_time.replace(hour=0, minute=0)
                search_time += datetime.timedelta(days=1)
                continue
        
        # Check hour
        if search_time.hour not in hours:
            search_time = search_time.replace(minute=0)
            search_time += datetime.timedelta(hours=1)
            continue
        
        # Check minute
        if search_time.minute not in minutes:
            search_time += datetime.timedelta(minutes=1)
            continue
        
        # Found a valid time
        print(search_time.strftime('%Y-%m-%d %H:%M:%S'))
        exit(0)
    
    print('Unable to calculate next cron time within 366 days')

except (ValueError, IndexError) as e:
    print('Unable to reliably parse and calculate next cron expression')
"
}

cd /app
export DOCKER=true PATH=/usr/local/bin:\$PATH
/usr/local/bin/python TSSK.py

# Calculate and display next run time
NEXT_RUN=\$(get_next_cron_time)
log "\${BLUE}Next execution scheduled for: \${NEXT_RUN}\${NC}"
WRAPPER_EOF

chmod +x /app/run-tssk.sh

log "${BLUE}TSSK is starting with the following cron schedule: ${CRON}${NC}"

# Get TZ for cron
CRON_TZ="${TZ:-UTC}"

# Setup cron job with proper PATH
cat > /etc/cron.d/tssk-cron << 'CRONEOF'
PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
SHELL=/bin/bash
CRONEOF

echo "TZ=${CRON_TZ}" >> /etc/cron.d/tssk-cron
echo "" >> /etc/cron.d/tssk-cron
echo "${CRON} root /bin/bash -c \"/app/run-tssk.sh >> /var/log/cron.log 2>&1\"" >> /etc/cron.d/tssk-cron

chmod 0644 /etc/cron.d/tssk-cron
crontab /etc/cron.d/tssk-cron

touch /var/log/cron.log

# Run once on startup using the wrapper script
log "${GREEN}Running TSSK on startup...${NC}"
log "${BLUE}Current directory: $(pwd)${NC}"
log "${BLUE}DOCKER env var: $DOCKER${NC}"
/app/run-tssk.sh 2>&1 | tee -a /var/log/cron.log

log "${GREEN}Startup run completed. Starting cron daemon...${NC}"
cron
tail -f /var/log/cron.log