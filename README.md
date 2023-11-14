<h1 align="center">:satellite: WiGLE Discord Bot :satellite:</h1>

<p align="center">
  <img src="https://i.imgur.com/CRKolzB.jpg">
</p>

This Discord bot is used to pull a user's stats from [WiGLE](https://wigle.net/) using WiGLE's API as shown below.

<p float="left">
  <img align="center" src="https://i.imgur.com/CA54inn.png" width="400" height="450"/>
  <img align="right" src="https://i.imgur.com/MT4ng6w.png" width="400" height="450"/>
</p>

<p float="left">
  <img align="center" src="https://i.imgur.com/0P2ourz.png" width="400" height="450"/>
  <img align="right" src="https://i.imgur.com/KyTYHpE.png" width="400" height="450"/>
</p>

## Variables
Prior to using the bot the following lines of code must be changed in the `config.json` file:
- Remove the `YOUR-TOKEN-HERE` text and replace it with your Discord Bot Token.
  - If you do not know how to create a Discord bot, instructions on how to do so can be found [here](https://discordpy.readthedocs.io/en/stable/discord.html)
- Replace `YOUR-ENCODED-FOR-USE-KEY-HERE` with your WiGLE API Key.
  - Your API key can be found [here](https://api.wigle.net/), select your account page in the lower right, then select "Show My Token".
  - The token you are looking for will be listed as the "Encoded for use".

You can change the amount of data shown on the group rank and user rank commands by changing the following variables:
- For `/grouprank` change line 231 from `40` to however many groups you want the bot to show.
- For `/userrank` change line 304 from `40` to however many users you want the bot to show.

:warning: Note that neither of these commands are designed to be split for Discord. If you enter a number that would produce an output over Discord's 2,000 character limit, it will not go through.

## Commands
Once the above lines have been updated run the bot using the following commands:
- `/user` followed by a username to get user stats. For example, `/user kavitate`.
- `/userrank` followed by a group name to get user rankings for that group. For example, `/userrank #wardriving`.
- `/grouprank` to show group rankings.
- `/help` to show a list of available bot commands.

# Credits
Further development of this bot is in collaboration with [RocketGod](https://github.com/RocketGod-git).

The idea for this bot was inspired by the [WiGLE Bot Repo](https://github.com/INIT6Source/WiGLE-bot) made by [INIT6Source](https://github.com/INIT6Source).
