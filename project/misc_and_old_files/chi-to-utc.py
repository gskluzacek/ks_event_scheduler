from datetime import datetime, timezone
# from zoneinfo import ZoneInfo
from dateutil import tz


def chicago_time_to_utc(local_dt: datetime) -> datetime | None:
    """
    Convert an America/Chicago local datetime to UTC.

    Rules:
    - If local_dt is naive, treat it as America/Chicago time.
    - If local_dt is already America/Chicago-aware, leave it as-is.
    - If local_dt is timezone-aware but not America/Chicago, raise ValueError.
    - Raise ValueError if the local Chicago time does not exist.
    """
    chicago_tz = tz.gettz("America/Chicago")

    if chicago_tz is None:
        raise RuntimeError("Could not load America/Chicago timezone")

    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(tzinfo=chicago_tz)
    elif local_dt.tzinfo != chicago_tz:
        raise ValueError(
            f"Expected America/Chicago datetime, got timezone: {local_dt.tzinfo}"
        )

    if not tz.datetime_exists(local_dt):
        print(f"non-existent datetime: {local_dt}")
        # return None

    return local_dt.astimezone(timezone.utc)

def utc_to_chicago_time(utc_dt: datetime) -> datetime:
    """
    Convert a UTC datetime to America/Chicago time.

    Rules:
    - utc_dt must be timezone-aware.
    - utc_dt must be in UTC.
    - Returns a timezone-aware America/Chicago datetime.
    """
    chicago_tz = tz.gettz("America/Chicago")

    if chicago_tz is None:
        raise RuntimeError("Could not load America/Chicago timezone")

    if utc_dt.tzinfo is None:
        raise ValueError("utc_dt must be timezone-aware and in UTC")

    if utc_dt.utcoffset() != timezone.utc.utcoffset(utc_dt):
        raise ValueError(f"Expected UTC datetime, got timezone: {utc_dt.tzinfo}")

    return utc_dt.astimezone(chicago_tz)


def main2():
    utc_dt = datetime(2027, 3, 13, 7, 59, tzinfo=timezone.utc)
    chicago_dt = utc_to_chicago_time(utc_dt)
    print(f"{utc_dt}\n{chicago_dt}\n")

    utc_dt = datetime(2027, 3, 13, 8, 0, tzinfo=timezone.utc)
    chicago_dt = utc_to_chicago_time(utc_dt)
    print(f"{utc_dt}\n{chicago_dt}\n")

    # -------------
    utc_dt = datetime(2027, 3, 14, 7, 59, tzinfo=timezone.utc)
    chicago_dt = utc_to_chicago_time(utc_dt)
    print(f"{utc_dt}\n{chicago_dt}\n")

    utc_dt = datetime(2027, 3, 14, 8, 0, tzinfo=timezone.utc)
    chicago_dt = utc_to_chicago_time(utc_dt)
    print(f"{utc_dt}\n{chicago_dt}\n")

    # -------------
    utc_dt = datetime(2027, 3, 15, 7, 0, tzinfo=timezone.utc)
    chicago_dt = utc_to_chicago_time(utc_dt)
    print(f"{utc_dt}\n{chicago_dt}\n")

    utc_dt = datetime(2027, 3, 15, 7, 59, tzinfo=timezone.utc)
    chicago_dt = utc_to_chicago_time(utc_dt)
    print(f"{utc_dt}\n{chicago_dt}\n")

    utc_dt = datetime(2027, 3, 15, 8, 0, tzinfo=timezone.utc)
    chicago_dt = utc_to_chicago_time(utc_dt)
    print(f"{utc_dt}\n{chicago_dt}\n")


def main():
    chicago_tz = tz.gettz("America/Chicago")

    local_chicago_dt = datetime(2027, 3, 13, 1, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 13, 1, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 13, 1, 0, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 13, 1, 59, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 13, 2, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 13, 2, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 13, 3, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 13, 3, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    print("-------------\n")

    local_chicago_dt = datetime(2027, 3, 14, 1, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 14, 1, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 14, 1, 0, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 14, 1, 59, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 14, 2, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 14, 2, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 14, 3, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 14, 3, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    print("-------------\n")

    local_chicago_dt = datetime(2027, 3, 15, 1, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 15, 1, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 15, 1, 0, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 15, 1, 59, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 15, 2, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 15, 2, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 15, 3, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 3, 15, 3, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    print("==================\n")

    local_chicago_dt = datetime(2027, 11, 6, 1, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 6, 1, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 6, 1, 0, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 6, 1, 59, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 6, 2, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 6, 2, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 6, 3, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 6, 3, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    print("-------------\n")

    local_chicago_dt = datetime(2027, 11, 7, 1, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 7, 1, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 7, 1, 0, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 7, 1, 59, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 7, 2, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 7, 2, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 7, 3, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 7, 3, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    print("-------------\n")

    local_chicago_dt = datetime(2027, 11, 8, 1, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 8, 1, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 8, 1, 0, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 8, 1, 59, tzinfo=chicago_tz, fold=1)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 8, 2, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 8, 2, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 8, 3, 00, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    local_chicago_dt = datetime(2027, 11, 8, 3, 59, tzinfo=chicago_tz)
    utc_dt = chicago_time_to_utc(local_chicago_dt)
    print(f"{local_chicago_dt}\n{utc_dt}\n")

    print("-------------\n")



if __name__ == "__main__":
    #
    # there are 2 use cases that we need to be aware of...
    #
    # 1) on the date that DST begins
    #    when DST begins, there is a time period where the time is non-existant. For example for america/chicago
    #    the DST transition for 2027 is March 14th at 2:00 am, and the time is adusted forwards by 1 hours.
    #    this results in times from 2:00 am to 2:59 am do not exist because we go from 1:59 am to 3:00 am.
    #
    #    if the player has availability which occurs within the transition time / utc offset change amount
    #    it will result in the non-existent times not being available for the user.
    #
    #    we MAY NEED (???) logic that breaks a users availibility into 2 parts if any part of the time slot falls
    #    in the transition period. for examkple, if user has stated that their availability is from
    #    11:00 pm to 4:00 am america/chicago, then we may need to break this time slot into 2 time slots of:
    #    11:00 pm to 2:00 am america/chicago and 3:00 am to 4:00 am america/chicago. problem is 2:00 is still a
    #    non-existent time and 1:59 am is 1 minute short...
    #
    # 2) on the date that DST ends
    #    when DST ends, there is a time period for the amount of time of the change in the UTS offset that
    #    repeats. For example for america/chicago the DST transition for 2027 is November 7th at 2:00 am,
    #    the time is adjusted backwards by 1 hour. This results in the time going from 1:59 am to 1:00 am.
    #
    #    in python there is the `fold` paramter of the datetime object, that is used to indicate if the time
    #    is in the first instance (fold = 0) of the repeated time or the second instance (fold = 1) of the
    #    repeated time.
    #

    #
    # I have 2 events to scheule, Event-A and Event-B. Both events happen on the same day UTC. Additonally,
    # the events occur every other day (i.e, the 1st, 3rd, 5th, etc.).
    #
    # People can only attend either Event-A or Event-B. Once the optimal times for both events are determined,
    # users will select which event they want to participate in. Once a person selects which event they will
    # participate in, they are not likely to switch to the other event.
    #
    # I want to consider start times of every 30 minutes. The event lasts 60 minutes. this will give event times (in UTC) of:
    # * 0:00 to 1:00
    # * 0:30 to 1:30
    # * 1:00 to 2:00
    # * 1:30 to 2:30
    # * 2:00 to 3:00
    # * 2:30 to 3:30
    # * 3:00 to 4:00
    # * 3:30 to 4:30
    # * 4:00 to 5:00
    # * 4:30 to 5:30
    # * 5:00 to 6:00
    # * 5:30 to 6:30
    # * 6:00 to 7:00
    # * 6:30 to 7:30
    # * 7:00 to 8:00
    # * 7:30 to 8:30
    # etc...
    #
    # lets assume a user in the america/chicago time zone has availability from 2:00 to 3:00 am.
    #
    # on March 13th, 2027 he could participate in events with times of 8:00 UTC
    # but on March 15th, 2027 he could participate in events with a start time of 7:00 UTC
    # however on March 14, 2027 he would not be able to participat in any event
    #

    #
    # PERHAPS to avoid the issue of invalid/non-existent times and ambiguous times (both due to DST)
    # we should use the concept of a block of time, which would be defined as a starting time plus
    # a duration. Time Blocks would always be in UTC time. e.g., starting time of 7:15 UTC with a
    # duration of 15 minutes.
    #
    # The duration would always be set to the start time increment. So if we are considering event start
    # times of every 15 minutes, then the Time Block Duration would also be 15 minutes.
    #
    # when calculating the optimal event scheduled times, convert the user's local time slots to
    # UTC Time Blocks. then compare the time blocks for the proposed event UTC Time Blocks to the UTC Time Blocks
    # that the user is available. For the user to be albe to participate, the must have all the Event's Proposed
    # UTC Time Blocks markded as Availible.
    #
    
    main()
