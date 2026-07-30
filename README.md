# ks_event_scheduler

given a list of ks players, their timezone and preferred time slots, determines the best time for ks events

# project development files

* The project's development files (i.e., code files) are located in the top level of `project` directory.
* the project directory also contains other subdirectories. However, these subdirectories are not part of 
the active project development files.

# usage

there are 2 types of users: admin and normal users. 
* normal users can only add / edit their own information and view various details.
* while admins can perform adminstrative tasks, add / edit their own information as well as 
add / edit other users information.

the flow for a normal user is as follows:
1. a discord user joins the discord server where the bot is running.
2. the user then registers an account with the bot.
3. the user then can add 1 or more players to their account.
4. for each of the user's player, the user can add 1 or more time slots for that player.

# data model

the followint tables exist in the database:
* accounts - an account has 1 or more players.
* players - a player belongs to 1 account.
* events - this table contains the details of each event.
* avails - this table contains the availability of each player for each event.
