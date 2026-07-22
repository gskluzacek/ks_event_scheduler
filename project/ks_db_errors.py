class AcctCreateError(Exception):
    pass


class DupAcctAccountNameError(AcctCreateError):
    pass


class DupAcctDiscordIdError(AcctCreateError):
    pass


class PlayerCreateError(Exception):
    pass


class DupPlayerKingshotIdError(PlayerCreateError):
    pass


class DupPlayerKingshotNameError(PlayerCreateError):
    pass
