import datetime

time = 123871623

local_dt = datetime.datetime.fromtimestamp(time)
iso_format_with_tz = local_dt.isoformat()
print(iso_format_with_tz)