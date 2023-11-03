<h1 align="center"> WiGLE Discord Bot</h1>

<p align="center">
  <img src="https://i.imgur.com/CRKolzB.jpg">
</p>

This Discord bot is used to pull a user's stats from [WiGLE](https://wigle.net/) using WiGLE's API as shown below.

<p float="left">
  <img src="https://i.imgur.com/NMJ8IRX.png" width="275" height="400"/>
  <img src="https://i.imgur.com/wWNkkHu.png" width="275" height="400"/> 
  <img src="https://i.imgur.com/lm32cxi.png" width="275" height="400"/>
</p>

## Variables
Prior to using the bot the following lines of code must be changed in the main.py file:
- Line 18, 68, and 90: Remove the `YOUR_WIGLE_API` text and replace it with your WiGLE API key.
  - Your API key can be found [here](https://api.wigle.net/), select your account page in the lower right, then select "Show My Token".
  - The token you are looking for will be listed as the "Header Value".
- Line 89: Replace `YOUR_GROUP_ID_HERE` with your group ID.
  - Your group ID can be found by logging into wigle.net, going [here](https://api.wigle.net/api/v2/stats/group), finding your group name within the list, and copying the `groupId`.
- Line 109: Replace `YOUR_DISCORD_BOT_TOKEN` with the token for your Discord bot.
  - If you do not know how to create a Discord bot, instructions on how to do so can be found [here](https://discordpy.readthedocs.io/en/stable/discord.html)

You can change the amount of data shown on the group rank and user rank commands by changing the following variables:
- For `!grouprank` change line 77 from `40` to however many groups you want the bot to show.
- For `!userrank` change line 99 from `50` to however many users you want the bot to show.

## Commands
Once the above lines have been updated run the bot using the following commands:
- `!user` followed by a username to get user stats. For example, `!user kavitate`.
- `!grouprank` to show group rankings.
- `!userrank` to show the user ranks within your group.

# Credits
The idea for this bot was inspired by the [WiGLE Bot Repo](https://github.com/INIT6Source/WiGLE-bot) made by [INIT6Source](https://github.com/INIT6Source).
