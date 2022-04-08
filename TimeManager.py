# Deals with time related function, e.g. returning formatted date strings
# Sorting, calendar functions, and selecting all dreams occuring in some time period
import flask, pytz, datetime, calendar

def formatted_date(dream):
    # Local time formatting
    local_time = pytz.utc.localize(datetime.datetime.fromtimestamp(dream['creation_time']), is_dst=None).astimezone(pytz.timezone("Africa/Ouagadougou")) # Doesn't actually seem to have a time zone
    formatted_date = local_time.strftime("%d/%m/%Y: %H:%M")
    
    return formatted_date

# Gets current time
def cur_utc_time():
    return calendar.timegm(datetime.datetime.utcnow().utctimetuple())

# Getting the time range for the specific month in computer format
def month_sec_range(month, year):
    start_time = datetime.datetime(year,month,1).replace(tzinfo=datetime.timezone.utc).timestamp()
    end_time = datetime.datetime(year,month,calendar.monthrange(year, month)[1],23,59,59).replace(tzinfo=datetime.timezone.utc).timestamp()
    
    return(start_time, end_time)

# Gets the day of the month
def month_day_getter(epoch):
    local_time = pytz.utc.localize(datetime.datetime.fromtimestamp(epoch), is_dst=None).astimezone(pytz.timezone("Africa/Ouagadougou"))
    day = local_time.strftime("%d")
    return day