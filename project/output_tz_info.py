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

        # Additional attributes
        parts = tz_name.split("/")
        self.parts_cnt = len(parts)
        self.part_1 = parts[0]
        self.remaining_parts_str = "/".join(parts[1:])
        self.remaining_parts = parts[1:]

        # Initialize tznn helper
        self._tznn_helper = tznn()

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
        before_offset = start_utc.astimezone(self.tz).utcoffset()

        low = start_utc
        high = end_utc

        while (high - low) > timedelta(seconds=1):
            mid = low + (high - low) / 2

            if mid.astimezone(self.tz).utcoffset() == before_offset:
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

        current_utc = start_utc + step

        while current_utc <= end_utc:
            current_local = current_utc.astimezone(self.tz)
            current_offset = current_local.utcoffset()

            # If offset changed, narrow down the exact transition time
            if current_offset != previous_offset:
                transition_local = self._find_transition(previous_utc, current_utc)

                transitions.append({
                    "datetime": transition_local,
                    "offset_before": previous_offset,
                    "offset_after": current_offset,
                })

            previous_utc = current_utc
            previous_offset = current_offset
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
        is_offset = abbreviation.startswith("+") or abbreviation.startswith("-")

        if is_offset:
            # Try to get a friendly name from tznn
            friendly_abbr = self._tznn_helper.get_abbr(self.name)
            if friendly_abbr:
                return f"{friendly_abbr} / {abbreviation}"

        return abbreviation

    def _process_samples(self, samples: List[Dict[str, Any]]) -> None:
        """
        Identifies standard and daylight time details from the gathered samples.

        :param samples: List of sample dictionaries.
        """
        standard_sample: Optional[Dict[str, Any]] = None
        daylight_sample: Optional[Dict[str, Any]] = None

        for sample in samples:
            # dst() returns timedelta(0) for standard time
            if sample["dst"] == timedelta(0):
                standard_sample = sample
            elif sample["dst"] and sample["dst"] != timedelta(0):
                daylight_sample = sample

        self.observes_dst = daylight_sample is not None

        if standard_sample:
            self.standard_abbreviation = self._format_abbreviation(standard_sample["abbreviation"])
            self.standard_utc_offset_hours = self.offset_hours(standard_sample["datetime"])

        if daylight_sample:
            self.dst_abbreviation = self._format_abbreviation(daylight_sample["abbreviation"])
            self.dst_utc_offset_hours = self.offset_hours(daylight_sample["datetime"])

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

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns the timezone information as a dictionary matching the previous implementation.
        """
        return {
            "name": self.name,
            "observes_dst": self.observes_dst,
            "standard_abbreviation": self.standard_abbreviation,
            "standard_utc_offset_hours": self.standard_utc_offset_hours,
            "dst_abbreviation": self.dst_abbreviation,
            "dst_utc_offset_hours": self.dst_utc_offset_hours,
            "dst_start": self.dst_start,
            "dst_end": self.dst_end,
            "div_len": self.parts_cnt,
            "region": self.name,
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
            "Name",
            "Observes DST",
            "STD Abbr",
            "STD UTC Offset",
            "DST Abbr",
            "DST UTC Offset",
            "DST Start",
            "DST End",
            "Division Length",
            "Region",
            "Location / Sub-Location",
            "Location",
            "Sub-Location",
        ]

    def to_list(self) -> List[Any]:
        """
        Returns the timezone information as a list of values for CSV export.
        """
        # Calculate location and sublocation
        loc = self.remaining_parts[0] if len(self.remaining_parts) > 0 else None
        subloc = self.remaining_parts[1] if len(self.remaining_parts) > 1 else None

        return [
            self.name,
            self.observes_dst,
            f"\t{self.standard_abbreviation}" if self.standard_abbreviation else None,
            self.standard_utc_offset_hours,
            f"\t{self.dst_abbreviation}" if self.dst_abbreviation else None,
            self.dst_utc_offset_hours,
            self.dst_start.isoformat() if self.dst_start else None,
            self.dst_end.isoformat() if self.dst_end else None,
            self.parts_cnt,
            self.name,  # Region
            self.remaining_parts_str,  # Location / Sub-Location
            loc,
            subloc,
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
            for name in sorted(available_timezones()):
                try:
                    tz_detail = TzDetail(name, year)
                    writer.writerow(tz_detail.to_list())
                except Exception as e:
                    print(f"Skipping {name} due to error: {e}")
        
        print(f"Successfully saved timezone details to {output_file}")
    except Exception as e:
        print(f"An error occurred while writing to CSV: {e}")



if __name__ == "__main__":
    main()
