# The idea for this bot was inspired by the WiGLE Bot Repo made by INIT6Source.
# More stats added by Kavitate
# Further fuckery and slash command modernization by RocketGod

import discord
import aiohttp
import asyncio
import json
import logging
import inflect
import time

# Constants for embed colors with 1990s BBS aesthetic FTW I'm an old ass RocketGod
EMBED_COLOR_USER = 0xFF00FF  # Magenta
EMBED_COLOR_GROUP_RANK = 0x0000FF  # Bright Red

logging.basicConfig(level=logging.DEBUG)

def load_config():
    try:
        with open('config.json', 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        logging.critical('The config.json file was not found.')
        raise
    except json.JSONDecodeError:
        logging.critical('config.json is not a valid JSON file.')
        raise
    except Exception as e:
        logging.critical(f'An unexpected error occurred while loading config.json: {e}')
        raise

config = load_config()

discord_bot_token = config['discord_bot_token']
wigle_api_key = config['wigle_api_key']
group_id = config['group_id']

class WigleBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.session = None

    async def on_ready(self):
        logging.info(f"Bot {self.user.name} is ready!")
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        await self.tree.sync()

    async def close(self):
        try:
            await super().close()
        finally:
            if self.session:
                await self.session.close()

    async def fetch_wigle_user_stats(self, username: str):
        timestamp = int(time.time())
        req = f"https://api.wigle.net/api/v2/stats/user?user={username}&nocache={timestamp}"
        headers = {
            'Authorization': f'Basic {config["wigle_api_key"]}',
            'Cache-Control': 'no-cache',  
        }
        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status == 404:
                    logging.info(f"WiGLE user {username} not found.")
                    return {'success': False, 'message': 'User not found.'}
                elif response.status != 200:
                    logging.error(f"Error fetching WiGLE user stats for {username}: {response.status}")
                    return {'success': False, 'message': f"HTTP error {response.status}"}
                logging.info(f"Fetched WiGLE user stats for {username}")
                return await response.json()
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE user stats for {username}: {e}")
            return {'success': False, 'message': str(e)}

    async def fetch_wigle_group_rank(self):
        timestamp = int(time.time())
        req = f"https://api.wigle.net/api/v2/stats/group?nocache={timestamp}"
        headers = {
            'Authorization': f'Basic {config["wigle_api_key"]}',
            'Cache-Control': 'no-cache',  
        }
        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status == 404:
                    logging.info("WiGLE group not found.")
                    return {'success': False, 'message': 'Group not found.'}
                elif response.status != 200:
                    logging.error(f"Error fetching WiGLE group ranks: {response.status}")
                    return {'success': False, 'message': f"HTTP error {response.status}"}
                return await response.json()
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE group ranks: {e}")
            return {'success': False, 'message': str(e)}

client = WigleBot()

@client.tree.command(name="user", description="Get stats for a WiGLE user.")
async def user(interaction: discord.Interaction, username: str):
    logging.info(f"Command 'user' invoked for username: {username}")

    await interaction.response.defer(ephemeral=False)

    try:
        # Fetch the user stats from the WiGLE API
        response = await client.fetch_wigle_user_stats(username)

        # Check if the API call was successful before trying to access the data
        if 'success' in response and response['success']:
            # Scrape all of the data
            username = response['user']
            rank = response['rank']
            monthRank = response['monthRank']
            statistics = response['statistics']
            prevRank = statistics['prevRank']
            prevMonthRank = statistics['prevMonthRank']
            eventMonthCount = statistics['eventMonthCount']
            eventPrevMonthCount = statistics['eventPrevMonthCount']
            discoveredWiFiGPS = statistics['discoveredWiFiGPS']
            discoveredWiFiGPSPercent = statistics['discoveredWiFiGPSPercent']
            discoveredWiFi = statistics['discoveredWiFi']
            discoveredCellGPS = statistics['discoveredCellGPS']
            discoveredCell = statistics['discoveredCell']
            discoveredBtGPS = statistics['discoveredBtGPS']
            discoveredBt = statistics['discoveredBt']
            totalWiFiLocations = statistics['totalWiFiLocations']
            last = statistics['last']
            first = statistics['first']
            image_url = response.get('imageBadgeUrl', '')

            # Create an embed object for a nicely formatted Discord message
            embed = discord.Embed(title=f"WiGLE User Stats for '{username}'", color=0x1E90FF)

            # Add fields to embed
            embed.add_field(name="Username", value=username, inline=True)
            embed.add_field(name="Rank", value=rank, inline=True)
            embed.add_field(name="Previous Rank", value=prevRank, inline=True)
            embed.add_field(name="Monthly Rank", value=monthRank, inline=True)
            embed.add_field(name="Last Month's Rank", value=prevMonthRank, inline=True)
            embed.add_field(name="Events This Month", value=eventMonthCount, inline=True)
            embed.add_field(name="Last Month's Events", value=eventPrevMonthCount, inline=True)
            embed.add_field(name="Discovered WiFi GPS", value=discoveredWiFiGPS, inline=True)
            embed.add_field(name="Discovered WiFi GPS Percent", value=discoveredWiFiGPSPercent, inline=True)
            embed.add_field(name="Discovered WiFi", value=discoveredWiFi, inline=True)
            embed.add_field(name="Discovered Cell GPS", value=discoveredCellGPS, inline=True)
            embed.add_field(name="Discovered Cell", value=discoveredCell, inline=True)
            embed.add_field(name="Discovered BT GPS", value=discoveredBtGPS, inline=True)
            embed.add_field(name="Discovered BT", value=discoveredBt, inline=True)
            embed.add_field(name="Total WiFi Locations", value=totalWiFiLocations, inline=True)
            embed.add_field(name="Last Event", value=last, inline=True)
            embed.add_field(name="First Ever Event", value=first, inline=True)

            # Add image if available
            if image_url:
                embed.set_image(url=f"https://wigle.net{image_url}")

            # Send the embed as a follow-up to the interaction
            await interaction.followup.send(embed=embed)
        else:
            error_message = response.get('message', 'Failed to fetch user stats.')
            logging.warning(f"WiGLE user stats fetch error for {username}: {error_message}")
            await interaction.followup.send(error_message)

    except KeyError as e:
        logging.error(f"A required key is missing in the response: {e}")
        await interaction.followup.send(f"Error: A required piece of information is missing: {e}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        await interaction.followup.send(f"An error occurred: {e}")

@client.tree.command(name="grouprank", description="Get WiGLE group rankings.")
async def grouprank(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    # Fetch the group ranks from the WiGLE API
    response = await client.fetch_wigle_group_rank()

    if 'success' in response and response['success'] is True:
        groups = response['groups']

        # Initialize an empty string to store the rankings
        rankings = ""

        # Use inflect to convert numbers to ordinals (1st, 2nd, 3rd, etc.)
        p = inflect.engine()
        for i, group in enumerate(groups[:40], 1):  # zzTop 40
            groupName = group['groupName']
            total = group['total']
            rank = p.ordinal(i)
            rankings += f"**{rank}:** {groupName} | **Total:** {total}\n"

        embed = discord.Embed(title="WiGLE Group Rankings", description=rankings, color=EMBED_COLOR_GROUP_RANK)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("Failed to retrieve group rankings. Please try again later.")

@client.tree.command(name="help", description="Displays help information for WigleBot commands.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    # Create a string that holds your help message text
    help_text = (
        "**Commands List**\n"
        "`/user <username>` - Get stats for a WiGLE user.\n"
        "`/grouprank` - Get WiGLE group rankings.\n"
        "`/help` - Shows this help message.\n\n"
    )

    color = 0x00FF00  # Bright Green

    embed = discord.Embed(title=":: WigleBot Help ::", description=help_text, color=color)
    embed.set_footer(text="WigleBot | Wardriving")

    ascii_art = (
        "```"
        "                    (         \n"
        " (  (        (      )\ )      \n"
        " )\))(   '(  )\ )  (()/( (    \n"
        "((_)()\ ) )\(()/(   /(_)))\   \n"
        "_(())\_)(|(_)/(_))_(_)) ((_)  \n"
        "\ \((_)/ /(_|_)) __| |  | __| \n"
        " \ \/\/ / | | | (_ | |__| _|  \n"
        "  \_/\_/  |_|  \___|____|___| \n"
        "                               \n"
        "```"
    )
    embed.add_field(name=":floppy_disk: RocketGod was here :floppy_disk:", value=ascii_art, inline=False)

    # Send the embed as a follow-up to the interaction
    await interaction.followup.send(embed=embed)


def run_discord_bot():
    try:
        client.run(config['discord_bot_token'])
    except Exception as e:
        logging.error(f"An error occurred while running the bot: {e}")
    finally:
        if client:
            asyncio.run(client.close())

if __name__ == "__main__":
    run_discord_bot()