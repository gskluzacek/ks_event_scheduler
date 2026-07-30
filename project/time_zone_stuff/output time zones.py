from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones


now = datetime.now()


class TzDtls:
    def __init__(self, name):
        self.name = name

        tz = ZoneInfo(name)
        offset = now.replace(tzinfo=tz).utcoffset()
        self.offset = offset.total_seconds() / 3600

        tz_parts = name.split("/")
        self.parts_cnt = len(tz_parts)
        self.split_parts_str = '\t'.join(tz_parts)
        self.part_1 = tz_parts[0]
        self.remainder = "/".join(tz_parts[1:])

    def details(self):
        return f"{self.parts_cnt}\t{self.name}\t{self.offset}\t{self.part_1}\t{self.remainder}\t{self.split_parts_str}"


def main():
    for name in sorted(available_timezones()):
        print(TzDtls(name).details())

if __name__ == "__main__":
    main()


# timezones = []
#
# for name in sorted(available_timezones()):
#     tz = ZoneInfo(name)
#     offset = now.replace(tzinfo=tz).utcoffset()
#     offset_hours = offset.total_seconds() / 3600
#
#     tz_parts = name.split("/")
#     tz_parts_cnt = len(tz_parts)
#     tz_parts_str = '\t'.join(tz_parts)
#     tz_part_1 = tz_parts[0]
#     tz_rest = "/".join(tz_parts[1:])
#
#
#     timezones.append((name, offset_hours))
#
# for name, offset_hours in timezones:
#     print(name, offset_hours)