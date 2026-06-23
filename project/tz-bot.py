import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BOT_MODE = os.getenv("BOT_MODE", "debug")  # debug | production
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

if BOT_MODE == "debug" and not TEST_GUILD_ID:
    raise RuntimeError("Missing TEST_GUILD_ID for debug mode")


# --------------------------------------------------
# Timezone data (static list as requested)
# --------------------------------------------------

TZ_BY_REGION = {
    "Africa": [
        "Abidjan",
        "Accra",
        "Addis_Ababa",
        "Algiers",
        "Asmara",
        "Asmera",
        "Bamako",
        "Bangui",
        "Banjul",
        "Bissau",
        "Blantyre",
        "Brazzaville",
        "Bujumbura",
        "Cairo",
        "Casablanca",
        "Ceuta",
        "Conakry",
        "Dakar",
        "Dar_es_Salaam",
        "Djibouti",
        "Douala",
        "El_Aaiun",
        "Freetown",
        "Gaborone",
        "Harare",
        "Johannesburg",
        "Juba",
        "Kampala",
        "Khartoum",
        "Kigali",
        "Kinshasa",
        "Lagos",
        "Libreville",
        "Lome",
        "Luanda",
        "Lubumbashi",
        "Lusaka",
        "Malabo",
        "Maputo",
        "Maseru",
        "Mbabane",
        "Mogadishu",
        "Monrovia",
        "Nairobi",
        "Ndjamena",
        "Niamey",
        "Nouakchott",
        "Ouagadougou",
        "Porto-Novo",
        "Sao_Tome",
        "Timbuktu",
        "Tripoli",
        "Tunis",
        "Windhoek",
    ],
    "America": [
        "Adak",
        "Anchorage",
        "Anguilla",
        "Antigua",
        "Araguaina",
        "Argentina/Buenos_Aires",
        "Argentina/Catamarca",
        "Argentina/ComodRivadavia",
        "Argentina/Cordoba",
        "Argentina/Jujuy",
        "Argentina/La_Rioja",
        "Argentina/Mendoza",
        "Argentina/Rio_Gallegos",
        "Argentina/Salta",
        "Argentina/San_Juan",
        "Argentina/San_Luis",
        "Argentina/Tucuman",
        "Argentina/Ushuaia",
        "Aruba",
        "Asuncion",
        "Atikokan",
        "Atka",
        "Bahia",
        "Bahia_Banderas",
        "Barbados",
        "Belem",
        "Belize",
        "Blanc-Sablon",
        "Boa_Vista",
        "Bogota",
        "Boise",
        "Buenos_Aires",
        "Cambridge_Bay",
        "Campo_Grande",
        "Cancun",
        "Caracas",
        "Catamarca",
        "Cayenne",
        "Cayman",
        "Chicago",
        "Chihuahua",
        "Ciudad_Juarez",
        "Coral_Harbour",
        "Cordoba",
        "Costa_Rica",
        "Coyhaique",
        "Creston",
        "Cuiaba",
        "Curacao",
        "Danmarkshavn",
        "Dawson",
        "Dawson_Creek",
        "Denver",
        "Detroit",
        "Dominica",
        "Edmonton",
        "Eirunepe",
        "El_Salvador",
        "Ensenada",
        "Fort_Nelson",
        "Fort_Wayne",
        "Fortaleza",
        "Glace_Bay",
        "Godthab",
        "Goose_Bay",
        "Grand_Turk",
        "Grenada",
        "Guadeloupe",
        "Guatemala",
        "Guayaquil",
        "Guyana",
        "Halifax",
        "Havana",
        "Hermosillo",
        "Indiana/Indianapolis",
        "Indiana/Knox",
        "Indiana/Marengo",
        "Indiana/Petersburg",
        "Indiana/Tell_City",
        "Indiana/Vevay",
        "Indiana/Vincennes",
        "Indiana/Winamac",
        "Indianapolis",
        "Inuvik",
        "Iqaluit",
        "Jamaica",
        "Jujuy",
        "Juneau",
        "Kentucky/Louisville",
        "Kentucky/Monticello",
        "Knox_IN",
        "Kralendijk",
        "La_Paz",
        "Lima",
        "Los_Angeles",
        "Louisville",
        "Lower_Princes",
        "Maceio",
        "Managua",
        "Manaus",
        "Marigot",
        "Martinique",
        "Matamoros",
        "Mazatlan",
        "Mendoza",
        "Menominee",
        "Merida",
        "Metlakatla",
        "Mexico_City",
        "Miquelon",
        "Moncton",
        "Monterrey",
        "Montevideo",
        "Montreal",
        "Montserrat",
        "Nassau",
        "New_York",
        "Nipigon",
        "Nome",
        "Noronha",
        "North_Dakota/Beulah",
        "North_Dakota/Center",
        "North_Dakota/New_Salem",
        "Nuuk",
        "Ojinaga",
        "Panama",
        "Pangnirtung",
        "Paramaribo",
        "Phoenix",
        "Port-au-Prince",
        "Port_of_Spain",
        "Porto_Acre",
        "Porto_Velho",
        "Puerto_Rico",
        "Punta_Arenas",
        "Rainy_River",
        "Rankin_Inlet",
        "Recife",
        "Regina",
        "Resolute",
        "Rio_Branco",
        "Rosario",
        "Santa_Isabel",
        "Santarem",
        "Santiago",
        "Santo_Domingo",
        "Sao_Paulo",
        "Scoresbysund",
        "Shiprock",
        "Sitka",
        "St_Barthelemy",
        "St_Johns",
        "St_Kitts",
        "St_Lucia",
        "St_Thomas",
        "St_Vincent",
        "Swift_Current",
        "Tegucigalpa",
        "Thule",
        "Thunder_Bay",
        "Tijuana",
        "Toronto",
        "Tortola",
        "Vancouver",
        "Virgin",
        "Whitehorse",
        "Winnipeg",
        "Yakutat",
        "Yellowknife",
    ],
    "Asia": [
        "Aden",
        "Almaty",
        "Amman",
        "Anadyr",
        "Aqtau",
        "Aqtobe",
        "Ashgabat",
        "Ashkhabad",
        "Atyrau",
        "Baghdad",
        "Bahrain",
        "Baku",
        "Bangkok",
        "Barnaul",
        "Beirut",
        "Bishkek",
        "Brunei",
        "Calcutta",
        "Chita",
        "Choibalsan",
        "Chongqing",
        "Chungking",
        "Colombo",
        "Dacca",
        "Damascus",
        "Dhaka",
        "Dili",
        "Dubai",
        "Dushanbe",
        "Famagusta",
        "Gaza",
        "Harbin",
        "Hebron",
        "Ho_Chi_Minh",
        "Hong_Kong",
        "Hovd",
        "Irkutsk",
        "Istanbul",
        "Jakarta",
        "Jayapura",
        "Jerusalem",
        "Kabul",
        "Kamchatka",
        "Karachi",
        "Kashgar",
        "Kathmandu",
        "Katmandu",
        "Khandyga",
        "Kolkata",
        "Krasnoyarsk",
        "Kuala_Lumpur",
        "Kuching",
        "Kuwait",
        "Macao",
        "Macau",
        "Magadan",
        "Makassar",
        "Manila",
        "Muscat",
        "Nicosia",
        "Novokuznetsk",
        "Novosibirsk",
        "Omsk",
        "Oral",
        "Phnom_Penh",
        "Pontianak",
        "Pyongyang",
        "Qatar",
        "Qostanay",
        "Qyzylorda",
        "Rangoon",
        "Riyadh",
        "Saigon",
        "Sakhalin",
        "Samarkand",
        "Seoul",
        "Shanghai",
        "Singapore",
        "Srednekolymsk",
        "Taipei",
        "Tashkent",
        "Tbilisi",
        "Tehran",
        "Tel_Aviv",
        "Thimbu",
        "Thimphu",
        "Tokyo",
        "Tomsk",
        "Ujung_Pandang",
        "Ulaanbaatar",
        "Ulan_Bator",
        "Urumqi",
        "Ust-Nera",
        "Vientiane",
        "Vladivostok",
        "Yakutsk",
        "Yangon",
        "Yekaterinburg",
        "Yerevan",
    ],
    "Europe": [
        "Amsterdam",
        "Andorra",
        "Astrakhan",
        "Athens",
        "Belfast",
        "Belgrade",
        "Berlin",
        "Bratislava",
        "Brussels",
        "Bucharest",
        "Budapest",
        "Busingen",
        "Chisinau",
        "Copenhagen",
        "Dublin",
        "Gibraltar",
        "Guernsey",
        "Helsinki",
        "Isle_of_Man",
        "Istanbul",
        "Jersey",
        "Kaliningrad",
        "Kiev",
        "Kirov",
        "Kyiv",
        "Lisbon",
        "Ljubljana",
        "London",
        "Luxembourg",
        "Madrid",
        "Malta",
        "Mariehamn",
        "Minsk",
        "Monaco",
        "Moscow",
        "Nicosia",
        "Oslo",
        "Paris",
        "Podgorica",
        "Prague",
        "Riga",
        "Rome",
        "Samara",
        "San_Marino",
        "Sarajevo",
        "Saratov",
        "Simferopol",
        "Skopje",
        "Sofia",
        "Stockholm",
        "Tallinn",
        "Tirane",
        "Tiraspol",
        "Ulyanovsk",
        "Uzhgorod",
        "Vaduz",
        "Vatican",
        "Vienna",
        "Vilnius",
        "Volgograd",
        "Warsaw",
        "Zagreb",
        "Zaporozhye",
        "Zurich",
    ],
    "Australia": [
        "ACT",
        "Adelaide",
        "Brisbane",
        "Broken_Hill",
        "Canberra",
        "Currie",
        "Darwin",
        "Eucla",
        "Hobart",
        "LHI",
        "Lindeman",
        "Lord_Howe",
        "Melbourne",
        "NSW",
        "North",
        "Perth",
        "Queensland",
        "South",
        "Sydney",
        "Tasmania",
        "Victoria",
        "West",
        "Yancowinna",
    ],
    "Atlantic": [
        "Azores",
        "Bermuda",
        "Canary",
        "Cape_Verde",
        "Faeroe",
        "Faroe",
        "Jan_Mayen",
        "Madeira",
        "Reykjavik",
        "South_Georgia",
        "St_Helena",
        "Stanley",
    ],
    "Pacific": [
        "Apia",
        "Auckland",
        "Bougainville",
        "Chatham",
        "Chuuk",
        "Easter",
        "Efate",
        "Enderbury",
        "Fakaofo",
        "Fiji",
        "Funafuti",
        "Galapagos",
        "Gambier",
        "Guadalcanal",
        "Guam",
        "Honolulu",
        "Johnston",
        "Kanton",
        "Kiritimati",
        "Kosrae",
        "Kwajalein",
        "Majuro",
        "Marquesas",
        "Midway",
        "Nauru",
        "Niue",
        "Norfolk",
        "Noumea",
        "Pago_Pago",
        "Palau",
        "Pitcairn",
        "Pohnpei",
        "Ponape",
        "Port_Moresby",
        "Rarotonga",
        "Saipan",
        "Samoa",
        "Tahiti",
        "Tarawa",
        "Tongatapu",
        "Truk",
        "Wake",
        "Wallis",
        "Yap",
    ],
    "Indian": [
        "Antananarivo",
        "Chagos",
        "Christmas",
        "Cocos",
        "Comoro",
        "Kerguelen",
        "Mahe",
        "Maldives",
        "Mauritius",
        "Mayotte",
        "Reunion",
    ],
    "Antarctica": [
        "Casey",
        "Davis",
        "DumontDUrville",
        "Macquarie",
        "Mawson",
        "McMurdo",
        "Palmer",
        "Rothera",
        "South_Pole",
        "Syowa",
        "Troll",
        "Vostok",
    ],
    "Arctic": [
        "Longyearbyen",
    ],
}

REGION_CHOICES = [
    app_commands.Choice(name=r, value=r)
    for r in TZ_BY_REGION.keys()
]


# --------------------------------------------------
# In-memory storage (swap with DB later)
# --------------------------------------------------

user_timezones: dict[int, str] = {}



# --------------------------------------------------
# Autocomplete
# --------------------------------------------------

async def timezone_autocomplete(interaction: discord.Interaction, current: str):
    region = getattr(interaction.namespace, "region", None)

    if not region:
        return []

    locations = TZ_BY_REGION.get(region, [])

    return [
        app_commands.Choice(name=tz, value=tz)
        for tz in locations
        if current.lower() in tz.lower()
    ][:25]


PAGE_SIZE = 10


class TimezonePagerView(discord.ui.View):
    def __init__(self, region: str, page: int = 0):
        super().__init__(timeout=120)

        self.region = region
        self.page = page
        self.timezones = TZ_BY_REGION[region]

    def get_page(self):
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        return self.timezones[start:end]

    def build_content(self):
        items = self.get_page()

        text = f"**{self.region} (page {self.page + 1})**\n\n"
        text += "\n".join(f"• {tz}" for tz in items)

        return text

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1

        await interaction.response.edit_message(
            content=self.build_content(),
            view=self,
        )

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * PAGE_SIZE < len(self.timezones):
            self.page += 1

        await interaction.response.edit_message(
            content=self.build_content(),
            view=self,
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Closed.",
            view=None,
        )


class RegionButton(discord.ui.Button):
    def __init__(self, region: str):
        super().__init__(
            label=region,
            style=discord.ButtonStyle.primary
        )
        self.region = region

    async def callback(self, interaction: discord.Interaction):
        view = TimezonePagerView(self.region)

        await interaction.response.edit_message(
            content=view.build_content(),
            view=view,
        )

class RegionSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

        for region in TZ_BY_REGION.keys():
            self.add_item(RegionButton(region))


# --------------------------------------------------
# Command Group
# --------------------------------------------------

class Timezone(app_commands.Group):
    def __init__(self):
        super().__init__(name="timezone", description="Timezone tools")

    # /timezone browse
    @app_commands.command(name="browse", description="Browse available timezones by region")
    async def browse(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Select a region to browse:",
            view=RegionSelectView(),
            ephemeral=True,
        )

    # /timezone set
    @app_commands.command(name="set", description="Set your timezone")
    @app_commands.choices(region=REGION_CHOICES)
    @app_commands.autocomplete(location=timezone_autocomplete)
    async def set_timezone(self, interaction: discord.Interaction, region: str, location: str):

        if location not in TZ_BY_REGION.get(region, []):
            return await interaction.response.send_message(
                "Invalid timezone for selected region.",
                ephemeral=True,
            )

        user_timezones[interaction.user.id] = f"{region}/{location}"

        await interaction.response.send_message(
            f"✅ Set timezone to `{region}/{location}`",
            ephemeral=True,
        )

    # /timezone show
    @app_commands.command(name="show", description="Show timezone")
    async def show(self, interaction: discord.Interaction):
        tz = user_timezones.get(interaction.user.id)

        if not tz:
            return await interaction.response.send_message(
                "No timezone set.",
                ephemeral=True,
            )

        await interaction.response.send_message(f"Your timezone: `{tz}`", ephemeral=True)

    # /timezone remove
    @app_commands.command(name="remove", description="Remove timezone")
    async def remove(self, interaction: discord.Interaction):
        user_timezones.pop(interaction.user.id, None)

        await interaction.response.send_message("Timezone removed.", ephemeral=True)


# --------------------------------------------------
# Bot setup
# --------------------------------------------------

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await sync_commands()


# --------------------------------------------------
# Sync logic (DEBUG vs PRODUCTION)
# --------------------------------------------------

async def sync_commands():
    try:
        if BOT_MODE == "debug":
            guild = discord.Object(id=int(TEST_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)

            print(
                f"[DEBUG] Synced {len(synced)} commands to guild {TEST_GUILD_ID}"
            )

        else:
            synced = await bot.tree.sync()
            print(f"[PRODUCTION] Synced {len(synced)} global commands")

    except Exception as e:
        print(f"Command sync failed: {e}")


# --------------------------------------------------
# Register commands
# --------------------------------------------------

bot.tree.add_command(Timezone())


# --------------------------------------------------
# Run
# --------------------------------------------------

bot.run(TOKEN)
