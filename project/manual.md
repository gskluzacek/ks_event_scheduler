# Bot Modes

## Normal

## Maintenance

## Down

* noraml users - cannot execute commands when the bot is down.
* admin - 
* super admin - only some commands are aviable to super admins
  * /admin set_bot_mode - change the bot mode to normal or maintenance
  * /admin get_bot_mode - get the current bot mode

# Command Groups & Command

## Account

### Activate
* account_id - optional

#### Access
* admin +
  * can access when the bot is in normal or maintenance mode
  * can set their active account to any account

#### Results
* sets the active account for the user
* if account_id is not provided, then the currently active account will be displayed


### Register
* tz_region     - required: the major geographic region. Used to select TZ Lodation.
* tz_location   - required: the specific location within the major geographic region. Used to select your Time Zone Name.
* discore_user  - optional:
* discord_id    - optional:
* account_name  - optional:

#### Access
* normal user
  * can only access when the bot is in normal mode
  * can only register an account for themselves
* admin +
  * can access when the bot is in normal or maintenance mode
  * can register an account for themselves or any user

#### Results
* register a new account for the specified parameters
* sets the active account for the user
  * normal user - will set their active account to the newly registered account
  * admin + - will set their active account to the newly registered account (for themselves or the specified user)


### Show
* account_id - optional

#### Access
* normal user
  * can only access when the bot is in normal mode
* admin +
  * can access when the bot is in normal or maintenance mode

#### Results
* all users can display their own account information or the accout information of other users.
* displays the account information for the specified account_id


### List
* no parameters

#### Access
* normal user
  * can only access when the bot is in normal mode
* admin +
  * can access when the bot is in normal or maintenance mode

#### Results
* any user can list all accounts
* lists all registered accounts

---

## Player

### Activate
* player_id - optional

#### Access
* normal user
  * can only access when the bot is in normal mode
* admin +
  * can access when the bot is in normal or maintenance mode
  * can set their active player to any player of **their active account**

#### Results
* sets the active player for the user
* if player_id is not provided, then the currently active player will be displayed


### Add
* kingshot_id - required: the KingShot ID of the player to **add to the active account**
* kinshot_name - required: the KingShot Name
* power - required: the power of the player (in Millions, e.g. 250.1M)
* town_center_level - required: the Town Center Level (1 to 20, TG1 to TG5 - needs more exact values)
* kingdom - optional: the kingdom of the player
* alliance - optional: the alliance of the player
* account_id - optional

#### Access
* normal user
  * can only access when the bot is in normal mode
* admin +
  * can access when the bot is in normal or maintenance mode

#### existing behavior
* must have an account to add a player
* if a noremal user, you can only add players to your own account
* if an admin +, you can add players to your own account, or to any other account by specifying the account_id


### Show

### List

