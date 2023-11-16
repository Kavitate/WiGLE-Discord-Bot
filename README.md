<h1 align="center">:satellite: WiGLE Discord Bot :satellite:</h1>

<p align="center">
  <img src="https://i.imgur.com/CRKolzB.jpg">
</p>

This Discord bot is used to pull a user's stats from [WiGLE](https://wigle.net/) using WiGLE's API as shown below.

<p float="left">
  <img align="center" src="https://i.imgur.com/BB17I72.png" width="350" height="400"/>
  <img align="right" src="https://i.imgur.com/RB42Vmb.png" width="350" height="400"/>
</p>

<p float="left">
  <img align="center" src="https://i.imgur.com/2fxu3Cu.png" width="350" height="400"/>
  <img align="right" src="https://i.imgur.com/c3Yg2zb.png" width="350" height="400"/>
</p>

## Variables
Prior to using the bot the following lines of code must be changed in the `config.json` file:
- Remove the `YOUR-TOKEN-HERE` text and replace it with your Discord Bot Token.
  - If you do not know how to create a Discord bot, instructions on how to do so can be found [here](https://discordpy.readthedocs.io/en/stable/discord.html)
- Replace `YOUR-ENCODED-FOR-USE-KEY-HERE` with your WiGLE API Key.
  - Your API key can be found [here](https://api.wigle.net/), select your account page in the lower right, then select "Show My Token".
  - The token you are looking for will be listed as the "Encoded for use".

## Commands
Once the above lines have been updated run the bot using the following commands:
- `/user` followed by a username to get user stats. For example, `/user kavitate`.
- `/userrank` followed by a group name to get user rankings for that group. For example, `/userrank #wardriving`.
- `/grouprank` to show group rankings.
- `/help` to show a list of available bot commands.

# Credits
Further development of this bot is in collaboration with [RocketGod](https://github.com/RocketGod-git).

The idea for this bot was inspired by the [WiGLE Bot Repo](https://github.com/INIT6Source/WiGLE-bot) made by [INIT6Source](https://github.com/INIT6Source).
