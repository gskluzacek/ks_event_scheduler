# --------------------------------------------------
# Player Class
# --------------------------------------------------

class KsPlayer:
    # todo: we can remove the `next_player_id` when we transition to using a database for player storage
    next_player_id: int = 1

    def __init__(self, discord_id: int, discord_name: str, discord_nickname: str, kingshot_id: int, kingshot_name: str,
                 town_center_lvl: str, power: float, kingdom: int = 1467, alliance: str = "UCF"):
        # todo: when we transition to using a database for plyaer storage, we will need to initialize self.player_id to None
        self.player_id: int = KsPlayer.get_next_id()
        self.discord_id: int = discord_id
        self.discord_name: str = discord_name
        self.discord_nickname: str = discord_nickname
        self.kingshot_id: int = kingshot_id
        self.kingshot_name: str = kingshot_name
        self.kingdom: int = kingdom
        self.alliance: str = alliance
        self.town_center_lvl: str = town_center_lvl
        self.power: float = power
        self.kingdom: int = kingdom
        self.alliance: str = alliance
        self.timezone: str = ""

    @classmethod
    def get_next_id(cls):
        player_id = cls.next_player_id
        cls.next_player_id += 1
        return player_id

    def save(self, player_store: dict[int, KsPlayer]):
        # todo: when we transition to using a database for plyaer storage, we will need to modify the `save` method
        player_store[self.player_id] = self

