from datetime import datetime, UTC
from zoneinfo import ZoneInfo


def utc_to_local(utc_str: str, tz_name: str) -> str:
    utc_dt = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    local_dt = utc_dt.astimezone(ZoneInfo(tz_name))
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")
