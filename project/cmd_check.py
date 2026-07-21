from enum import StrEnum
from typing import cast, Any, Self
import shared_state


class BotMode(StrEnum):
    msg_desc: str

    DOWN = ("down", "down")
    MAINTENANCE = ("maintenance", "under maintenance")
    NORMAL = ("normal", "in operation")
    UNKNOWN = ("unknown", "in an unknown state")

    def __new__(cls, value: str, msg_desc: str):
        # to make type checker stop complaining about type mismatch...
        obj: "BotMode" = str.__new__(cast(Any, cls), value)
        obj._value_ = value
        obj.msg_desc = msg_desc
        return obj

    @staticmethod
    def curr_stmt() -> str:
        return f"the bot is currently"

    @staticmethod
    def req_stmt(sign: bool) -> str:
        assertion = "must" if sign else "can not"
        return f"it {assertion} be"

    @classmethod
    def from_str(cls, mode_str: str) -> Self | None:
        try:
            return cls(mode_str)
        except ValueError:
            return None

    @staticmethod
    def get_bot_mode():
        app_state = shared_state.get_app_state()
        return {app_state.get("bot_mode", BotMode.UNKNOWN.value)}

    @staticmethod
    def curr_bot_mode() -> BotMode:
        app_state = shared_state.get_app_state()
        return BotMode.from_str(app_state.get("bot_mode")) or BotMode.UNKNOWN


class Role(StrEnum):
    msg_desc: str

    SUPER_ADMIN = ("super", "super admin")
    ADMIN = ("regular", "admin")
    USER = ("user", "user")

    def __new__(cls, value: str, msg_desc: str):
        # to make type checker stop complaining about type mismatch...
        obj: "Role" = str.__new__(cast(Any, cls), value)
        obj._value_ = value
        obj.msg_desc = msg_desc
        return obj

    @staticmethod
    def curr_stmt() -> str:
        return f"you have role(s) of:"

    @staticmethod
    def req_stmt(sign: bool) -> str:
        assertion = "must" if sign else "can not"
        return f"you {assertion} have a role of:"

    @staticmethod
    def get_user_roles(discord_id: int | str) -> set[str]:
        session = shared_state.get_session()
        user_roles = session.get(discord_id, "roles", [])
        return set(user_roles + [Role.USER.value])


class CmdValList:
    def __init__(self, vals: list[BotMode | Role], sign: bool = True):
        self.vals = vals
        self.sign = sign

    def _to_set(self) -> set[str]:
        return {val.value for val in self.vals}

    def check(self, current_state: set[str]) -> bool:
        require_state = self._to_set()
        if self.sign:
            return bool(require_state & current_state)
        else:
            return not bool(require_state & current_state)

    def join_current_state(self, current_state: set[str]) -> str:
        # the enum's class of the current_state will always have the same type as self.vals[0]
        enum_class = type(self.vals[0])
        # sort the enums corresponding to the set of strings that represent the current state
        current_state_sored = [enum for enum in enum_class if enum.value in current_state]

        # join the msg_desc of the enums
        if len(current_state_sored) == 1:
            return current_state_sored[0].msg_desc
        before_and = [enum.msg_desc for enum in current_state_sored[:-1]]
        return ", ".join(before_and) + " and " + current_state_sored[-1].msg_desc

    def join_required_state(self) -> str:
        # get the class of the list of enums stored in self.vals
        enum_class = type(self.vals[0])
        # sort the required state enums
        temp_required_state = [enum for enum in enum_class if enum in self.vals]

        # join the msg_desc of the required enums list
        if len(temp_required_state) == 1:
            return temp_required_state[0].msg_desc
        before_or = [enum.msg_desc for enum in temp_required_state[:-1]]
        return ", ".join(before_or) + " or " + temp_required_state[-1].msg_desc

    def format_error_message(self, current_state: set[str]):
        # the current_state will always have the same type as self.vals[0]
        enum_class = type(self.vals[0])
        err_msg_1 = f"{enum_class.curr_stmt()} {self.join_current_state(current_state)},"
        err_msg_2 = f"{enum_class.req_stmt(sign=self.sign)} {self.join_required_state()}"
        return f"❌ {err_msg_1} {err_msg_2} to execute this command."


class CmdCheck:
    def __init__(self, req_roles: CmdValList | None = None, req_bot_mode: CmdValList | None = None):
        self.req_roles: CmdValList | None = req_roles
        self.req_bot_mode: CmdValList | None = req_bot_mode

    def command_check(self, discord_id: int | str):
        user_roles = Role.get_user_roles(discord_id)
        bot_mode = BotMode.get_bot_mode()

        if self.req_roles and not self.req_roles.check(user_roles):
            err_msg = self.req_roles.format_error_message(user_roles)
            return False, err_msg

        if self.req_bot_mode and not self.req_bot_mode.check(bot_mode):
            err_msg = self.req_bot_mode.format_error_message(bot_mode)
            return False, err_msg

        return True, "✅ Command check passed."

cvl_at_least_admin = CmdValList([Role.ADMIN, Role.SUPER_ADMIN])
cvl_cannot_be_user = CmdValList([Role.USER], False)

cvl_not_down_or_maint = CmdValList([BotMode.MAINTENANCE, BotMode.DOWN], False)
cvl_in_operation = CmdValList([BotMode.NORMAL])
cvl_any_bot_mode = CmdValList([BotMode.NORMAL, BotMode.MAINTENANCE, BotMode.DOWN])

cc_bot_mode_normal = CmdCheck(req_bot_mode=cvl_in_operation)
cc_bot_mode_any = CmdCheck(req_bot_mode=cvl_any_bot_mode)

cc_player_add_bot_mode_normal = CmdCheck(req_bot_mode=cvl_not_down_or_maint)
cc_admin_bot_mode_at_least_admin = CmdCheck(req_roles=cvl_at_least_admin)


"""
current design does not allows for conditions check like
    if bot_mode is down
        is_authorized = False
        authorization_error = "the command is not allowed when the bot is down"
    elif bot_mod is maintenance
        if role is user
            is_authorized = False
            authorizatio_error = "the command is not allowed for users when the bot is under maintenance"

if cvl_at_least_admin.check(users_roles)




"""