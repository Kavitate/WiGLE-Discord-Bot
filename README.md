<h1 align="center"> WiGLE Discord Bot</h1>

This Discord bot is used to pull a user's stats from [WiGLE](https://wigle.net/) using WiGLE's API as shown below.

<p align="center">
  <img width="460" height="500" src="https://i.imgur.com/GRhofk1.png">
</p>

Prior to using the bot the following lines of code must be changed in the main.py file:
- Line 18: Remove the `YOUR_WIGLE_API` text and replace it with your WiGLE API key.
  - Your API key can be found [here](https://api.wigle.net/), select your account page in the lower right, then select "Show My Token".
  - The token you are looking for will be listed as the "Header Value".
- Line 64: Replace `YOUR_DISCORD_BOT_TOKEN` with the token for your Discord bot.
  - If you do not know how to create a Discord bot, instructions on how to do so can be found [here](https://discordpy.readthedocs.io/en/stable/discord.html)

# Credits
The idea for this bot was inspired by the [WiGLE Bot Repo](https://github.com/INIT6Source/WiGLE-bot) made by [INIT6Source](https://github.com/INIT6Source).
