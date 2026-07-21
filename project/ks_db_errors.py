class AcctCreateError(Exception):
    pass


class DupAcctAccountNameError(AcctCreateError):
    pass


class DupAcctDiscordIdError(AcctCreateError):
    pass
