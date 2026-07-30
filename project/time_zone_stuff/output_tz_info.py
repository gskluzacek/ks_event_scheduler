from typing import List, Dict, Optional, Any
import csv
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, available_timezones
from tznn import tznn


class TzDetail:
    """
    Represents detailed timezone information for a specific year,
    including DST transitions and offsets.
    """

    # Class-level tznn helper to avoid re-instantiation
    _tznn_helper = tznn()

    # List of regions considered non-legacy
    NON_LEGACY_REGIONS = [
        "Africa",
        "America",
        "Antarctica",
        "Arctic",
        "Asia",
        "Atlantic",
        "Australia",
        "Europe",
        "Indian",
        "Pacific",
    ]

    def __init__(self, tz_name: str, year: int) -> None:
        """
        Initializes the TzDetail object by calculating timezone information for the given year.

        :param tz_name: The name of the timezone (e.g., 'America/New_York').
        :param year: The year to analyze.
        """
        self.name: str = tz_name
        self.year: int = year
        self.tz: ZoneInfo = ZoneInfo(tz_name)

        # Initialize attributes
        self.observes_dst: bool = False
        self.standard_abbreviation: Optional[str] = None
        self.standard_utc_offset_hours: Optional[float] = None
        self.dst_abbreviation: Optional[str] = None
        self.dst_utc_offset_hours: Optional[float] = None
        self.dst_start: Optional[datetime] = None
        self.dst_end: Optional[datetime] = None

        # New attributes
        self.offset_delta: Optional[float] = None
        self.adjusted_dst_start: Optional[datetime] = None
        self.adjusted_dst_end: Optional[datetime] = None

        # Additional attributes
        parts = tz_name.split("/")
        self.parts_cnt = len(parts)
        self.part_1 = parts[0]
        self.remaining_parts_str = "/".join(parts[1:])
        self.remaining_parts = parts[1:]

        # Determine if it is a legacy timezone
        self.is_legacy: int = 1 if self.part_1 not in self.NON_LEGACY_REGIONS else 0

        # Perform analysis
        self._calculate_info()

    @staticmethod
    def offset_hours(dt: datetime) -> Optional[float]:
        """
        Returns the UTC offset of a datetime in hours.
        
        :param dt: The datetime object to calculate offset for.
        :return: Offset in hours or None if no offset is found.
        """
        offset = dt.utcoffset()
        if offset is None:
            return None
        return offset.total_seconds() / 3600

    def _find_transition(self, start_utc: datetime, end_utc: datetime) -> datetime:
        """
        Finds the approximate transition instant between start_utc and end_utc.
        Returns the local datetime after narrowing to second precision.

        :param start_utc: Start of the range in UTC.
        :param end_utc: End of the range in UTC.
        :return: The datetime of the transition in local time.
        """
        before_tz_info = start_utc.astimezone(self.tz)
        before_offset = before_tz_info.utcoffset()
        before_dst = before_tz_info.dst()

        low = start_utc
        high = end_utc

        while (high - low) > timedelta(seconds=1):
            mid = low + (high - low) / 2
            mid_tz_info = mid.astimezone(self.tz)

            if mid_tz_info.utcoffset() == before_offset and mid_tz_info.dst() == before_dst:
                low = mid
            else:
                high = mid

        # Return transition rounded to the nearest second
        transition = high.astimezone(self.tz)
        return transition.replace(microsecond=0)

    def _calculate_info(self) -> None:
        """
        Orchestrates the calculation of timezone details.
        """
        start_utc = datetime(self.year, 1, 1, tzinfo=timezone.utc)
        end_utc = datetime(self.year + 1, 1, 1, tzinfo=timezone.utc)

        # Detect transitions between standard and daylight time
        transitions = self._find_transitions(start_utc, end_utc)
        
        # Gather periodic samples to identify standard and daylight abbreviations/offsets
        samples = self._get_samples(start_utc, end_utc)

        # Process gathered data into final attributes
        self._process_samples(samples)
        self._process_transitions(transitions)

    def _find_transitions(self, start_utc: datetime, end_utc: datetime) -> List[Dict[str, Any]]:
        """
        Detects transitions in the timezone offset by sampling every 6 hours.

        :param start_utc: Start of the analysis period (UTC).
        :param end_utc: End of the analysis period (UTC).
        :return: List of transition details.
        """
        step = timedelta(hours=6)
        transitions: List[Dict[str, Any]] = []

        previous_utc = start_utc
        previous_local = previous_utc.astimezone(self.tz)
        previous_offset = previous_local.utcoffset()
        previous_dst = previous_local.dst()

        current_utc = start_utc + step

        while current_utc <= end_utc:
            current_local = current_utc.astimezone(self.tz)
            current_offset = current_local.utcoffset()
            current_dst = current_local.dst()

            # If offset or DST changed, narrow down the exact transition time
            if current_offset != previous_offset or current_dst != previous_dst:
                transition_local = self._find_transition(previous_utc, current_utc)

                transitions.append({
                    "datetime": transition_local,
                    "offset_before": previous_offset,
                    "offset_after": current_offset,
                    "dst_before": previous_dst,
                    "dst_after": current_local.dst(), # Will be re-evaluated at transition in _process_transitions
                })

            previous_utc = current_utc
            previous_offset = current_offset
            previous_dst = current_dst
            current_utc += step
        
        return transitions

    def _get_samples(self, start_utc: datetime, end_utc: datetime) -> List[Dict[str, Any]]:
        """
        Gathers representative samples of the timezone throughout the year.

        :param start_utc: Start of the analysis period (UTC).
        :param end_utc: End of the analysis period (UTC).
        :return: List of sample dictionaries.
        """
        samples: List[Dict[str, Any]] = []
        current_utc = start_utc

        while current_utc < end_utc:
            local = current_utc.astimezone(self.tz)

            samples.append({
                "datetime": local,
                "abbreviation": local.tzname(),
                "offset": local.utcoffset(),
                "dst": local.dst(),
            })

            # Sample every 15 days
            current_utc += timedelta(days=15)
        
        return samples

    def _format_abbreviation(self, abbreviation: Optional[str]) -> Optional[str]:
        """
        Formats the abbreviation using tznn as a fallback if the original is a numeric offset.

        :param abbreviation: The original abbreviation from zoneinfo.
        :return: Formatted abbreviation string.
        """
        if not abbreviation:
            return None

        # Check if the abbreviation represents a numeric offset (starts with + or -)
        if abbreviation.startswith("+") or abbreviation.startswith("-"):
            # Try to get a friendly name from tznn
            try:
                friendly_abbr = self._tznn_helper.get_abbr(self.name)
                abbreviation = f"{friendly_abbr} / {abbreviation}"
            except ValueError as e:
                error_msg = str(e)
                if not (error_msg.startswith("Invalid time zone name: ") and self.name in error_msg):
                    raise e

        return abbreviation

    def _process_samples(self, samples: List[Dict[str, Any]]) -> None:
        """
        Identifies standard and daylight time details from the gathered samples.

        :param samples: List of sample dictionaries.
        """
        standard_samples: List[Dict[str, Any]] = []
        daylight_samples: List[Dict[str, Any]] = []

        for sample in samples:
            # dst() returns timedelta(0) for standard time
            if sample["dst"] == timedelta(0):
                standard_samples.append(sample)
            elif sample["dst"] and sample["dst"] != timedelta(0):
                daylight_samples.append(sample)

        self.observes_dst = len(daylight_samples) > 0

        if not self.observes_dst:
            if standard_samples:
                # If no DST, just take the first standard sample
                self._apply_standard_sample(standard_samples[0])
            return

        # If DST is observed, we need to be careful about mid-year standard offset changes.
        # We'll try to find a pair of standard and daylight samples that have a typical offset difference.
        # Most common DST offset is 1 hour.
        
        best_standard = standard_samples[0] if standard_samples else None
        best_daylight = daylight_samples[0] if daylight_samples else None
        
        # If we have multiple standard offsets, try to find one that is NOT the same as daylight
        if len(standard_samples) > 1 and best_daylight:
            daylight_offset = self.offset_hours(best_daylight["datetime"])
            for s in standard_samples:
                if self.offset_hours(s["datetime"]) != daylight_offset:
                    best_standard = s
                    break
                    
        if best_standard:
            self._apply_standard_sample(best_standard)
        if best_daylight:
            self._apply_daylight_sample(best_daylight)

        # Calculate offset delta if DST is observed
        if self.observes_dst and self.standard_utc_offset_hours is not None and self.dst_utc_offset_hours is not None:
            self.offset_delta = abs(self.dst_utc_offset_hours - self.standard_utc_offset_hours)

    def _apply_standard_sample(self, sample: Dict[str, Any]) -> None:
        """Applies a standard time sample to attributes."""
        self.standard_abbreviation = self._format_abbreviation(sample["abbreviation"])
        self.standard_utc_offset_hours = self.offset_hours(sample["datetime"])

    def _apply_daylight_sample(self, sample: Dict[str, Any]) -> None:
        """Applies a daylight time sample to attributes."""
        self.dst_abbreviation = self._format_abbreviation(sample["abbreviation"])
        self.dst_utc_offset_hours = self.offset_hours(sample["datetime"])

    def _process_transitions(self, transitions: List[Dict[str, Any]]) -> None:
        """
        Identifies DST start and end moments from the detected transitions.

        :param transitions: List of transition details.
        """
        for transition in transitions:
            dt = transition["datetime"]
            # Check if this transition is into or out of DST
            # We check the dst() value at the exact transition and one second before
            is_dst_after = dt.dst() != timedelta(0)
            
            # To check before, we need a UTC time slightly before the transition
            # Transition datetime is already local (the 'high' value from binary search)
            # We convert it back to UTC to get a safe 'before' point.
            dt_utc = dt.astimezone(timezone.utc)
            is_dst_before = (dt_utc - timedelta(seconds=1)).astimezone(self.tz).dst() != timedelta(0)

            if is_dst_after and not is_dst_before:
                # Transition into DST - if multiple, we take the first one as start
                if self.dst_start is None:
                    self.dst_start = dt
            elif not is_dst_after and is_dst_before:
                # Transition out of DST - if multiple, we take the last one as end
                self.dst_end = dt

        # Calculate adjusted DST start and end
        if self.observes_dst and self.offset_delta is not None:
            delta = timedelta(hours=self.offset_delta)
            if self.dst_start:
                self.adjusted_dst_start = self.dst_start - delta
            if self.dst_end:
                self.adjusted_dst_end = self.dst_end + delta

    def to_dict(self, nbr: Optional[int] = None) -> Dict[str, Any]:
        """
        Returns the timezone information as a dictionary matching the previous implementation.

        :param nbr: Optional sequence number.
        """
        return {
            "nbr": nbr,
            "is_legacy": self.is_legacy,
            "name": self.name,
            "observes_dst": self.observes_dst,
            "standard_abbreviation": self.standard_abbreviation,
            "dst_abbreviation": self.dst_abbreviation,
            "standard_utc_offset_hours": self.standard_utc_offset_hours,
            "dst_utc_offset_hours": self.dst_utc_offset_hours,
            "offset_delta": self.offset_delta,
            "dst_start": self.dst_start,
            "dst_end": self.dst_end,
            "adjusted_dst_start": self.adjusted_dst_start,
            "adjusted_dst_end": self.adjusted_dst_end,
            "div_len": self.parts_cnt,
            "region": self.part_1,
            "loc_subloc": self.remaining_parts_str,
            "loc": self.remaining_parts[0] if len(self.remaining_parts) > 0 else None,
            "subloc": self.remaining_parts[1] if len(self.remaining_parts) > 1 else None,
        }

    @staticmethod
    def get_csv_headers() -> List[str]:
        """
        Returns the list of header names for CSV export.
        """
        return [
            "Nbr",
            "Legacy",
            "Name",
            "Observes DST",
            "STD Abbr",
            "DST Abbr",
            "STD UTC Offset",
            "DST UTC Offset",
            "Offset Delta",
            "Division Length",
            "Region",
            "Location / Sub-Location",
            "Location",
            "Sub-Location",
            "DST Start",
            "DST End",
            "Adjusted DST Start",
            "Adjusted DST End",
        ]

    def to_list(self, nbr: int) -> List[Any]:
        """
        Returns the timezone information as a list of values for CSV export.

        :param nbr: The sequence number for this record.
        """
        # Calculate location and sublocation
        loc = self.remaining_parts[0] if len(self.remaining_parts) > 0 else None
        subloc = self.remaining_parts[1] if len(self.remaining_parts) > 1 else None

        return [
            nbr,
            self.is_legacy,
            self.name,
            self.observes_dst,
            f"\t{self.standard_abbreviation}" if self.standard_abbreviation else None,
            f"\t{self.dst_abbreviation}" if self.dst_abbreviation else None,
            self.standard_utc_offset_hours,
            self.dst_utc_offset_hours,
            self.offset_delta,
            self.parts_cnt,
            self.part_1,  # Region
            self.remaining_parts_str,  # Location / Sub-Location
            loc,
            subloc,
            self.dst_start.isoformat() if self.dst_start else None,
            self.dst_end.isoformat() if self.dst_end else None,
            self.adjusted_dst_start.isoformat() if self.adjusted_dst_start else None,
            self.adjusted_dst_end.isoformat() if self.adjusted_dst_end else None,
        ]


def main() -> None:
    """
    Main entry point to demonstrate the usage of TzDetail class.
    Calculates timezone information for all available timezones and saves to CSV.
    """
    year = datetime.now().year
    output_file = "timezone_details.csv"

    print(f"Generating timezone details for {year} and saving to {output_file}...")

    try:
        with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(TzDetail.get_csv_headers())

            # Write data for each timezone
            for i, name in enumerate(sorted(available_timezones()), start=1):
                tz_detail = TzDetail(name, year)
                writer.writerow(tz_detail.to_list(i))
        
        print(f"Successfully saved timezone details to {output_file}")
    except Exception as e:
        print(f"An error occurred while writing to CSV: {e}")


# user local date + user local availability time + user timezone
if __name__ == "__main__":
    main()
