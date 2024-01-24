import aiohttp
import asyncio
import json
import logging
import inflect
import time
from datetime import datetime
import discord
from discord.ui import Select, Button, View
from discord import ButtonStyle
from discord.ext import commands

EMBED_COLOR_USER = 0xFF00FF  # Magenta
EMBED_COLOR_GROUP_RANK = 0x0000FF  # Bright Red

logging.basicConfig(level=logging.DEBUG)


def load_config():
    try:
        with open("config.json", "r") as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        logging.critical("The config.json file was not found.")
        raise
    except json.JSONDecodeError:
        logging.critical("config.json is not a valid JSON file.")
        raise
    except Exception as e:
        logging.critical(f"An unexpected error occurred while loading config.json: {e}")
        raise

config = load_config()


discord_bot_token = config["discord_bot_token"]
wigle_api_key = config["wigle_api_key"]


class WigleCommandView(View):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def interact(self, interaction: discord.Interaction, command_name: str):
        if command_name == "user":
            modal = UserStatsModal(bot=self.bot)
            await interaction.response.send_modal(modal)

        elif command_name == "userrank":
            modal = GroupNameModal(bot=self.bot)
            await interaction.response.send_modal(modal)

        elif command_name == "group":
            await self.bot.fetch_wigle_group_rank(interaction)

        elif command_name == "alltime":
            await self.bot.fetch_wigle_alltime_rank(interaction)

        elif command_name == "month":
            await self.bot.fetch_wigle_month_rank(interaction)

        elif command_name == "credits":
            await self.bot.show_credits(interaction)

    @discord.ui.select(
        placeholder="Choose a WiGLE command",
        options=[
            discord.SelectOption(label="User Stats", value="user"),
            discord.SelectOption(label="Group Rank", value="group"),
            discord.SelectOption(label="All-Time Rankings", value="alltime"),
            discord.SelectOption(label="Monthly Rankings", value="month"),
            discord.SelectOption(label="User Rankings for Group", value="userrank"),
            discord.SelectOption(label="Credits", value="credits")
        ],
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_value = select.values[0]  
        await self.interact(interaction, selected_value) 


class UserStatsModal(discord.ui.Modal):
    def __init__(self, bot):
        super().__init__(title="Enter WiGLE Username")
        self.bot = bot

        self.username = discord.ui.TextInput(label="Username", placeholder="Enter the WiGLE username here")
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction):
        username = self.username.value
        await self.bot.fetch_wigle_user_stats(interaction, username)

class GroupNameModal(discord.ui.Modal):
    def __init__(self, bot):
        super().__init__(title="Enter WiGLE Group Name")
        self.bot = bot

        self.group_name = discord.ui.TextInput(label="Group Name", placeholder="Enter the WiGLE group name here")
        self.add_item(self.group_name)

    async def on_submit(self, interaction: discord.Interaction):
        group_name = self.group_name.value
        await self.bot.fetch_wigle_user_rank(interaction, group_name)

class WigleBot(discord.Client):
    def __init__(self, wigle_api_key):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.session = None
        self.wigle_api_key = wigle_api_key

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

    async def fetch_wigle_user_stats(self, interaction: discord.Interaction, username: str):
        logging.info(f"Fetching WiGLE stats for username: {username}")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)

        timestamp = int(time.time())
        req = f"https://api.wigle.net/api/v2/stats/user?user={username}&nocache={timestamp}"
        headers = {
            "Authorization": f"Basic {self.wigle_api_key}",
            "Cache-Control": "no-cache",
        }

        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status == 404:
                    logging.info(f"WiGLE user {username} not found.")
                    await interaction.followup.send("User not found.")
                    return
                elif response.status != 200:
                    logging.error(f"Error fetching WiGLE user stats for {username}: {response.status}")
                    await interaction.followup.send(f"HTTP error {response.status}")
                    return

                data = await response.json()
                if data.get("success") and "statistics" in data and "userName" in data["statistics"]:
                    if data["statistics"]["userName"].lower() == username.lower():
                        logging.info(f"Fetched WiGLE user stats for {username}")
                        embed = self.create_user_stats_embed(data, timestamp)
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("User not found.")
                else:
                    await interaction.followup.send("Invalid data received or user not found.")
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE user stats for {username}: {e}")
            await interaction.followup.send(str(e))

    def create_user_stats_embed(self, data, timestamp):
        username = data["statistics"]["userName"]
        rank = data["statistics"].get("rank")
        monthRank = data["statistics"].get("monthRank")
        prevRank = data["statistics"].get("prevRank")
        prevMonthRank = data["statistics"].get("prevMonthRank")
        eventMonthCount = data["statistics"].get("eventMonthCount")
        eventPrevMonthCount = data["statistics"].get("eventPrevMonthCount")
        discoveredWiFiGPS = data["statistics"].get("discoveredWiFiGPS")
        discoveredWiFiGPSPercent = data["statistics"].get("discoveredWiFiGPSPercent")
        discoveredWiFi = data["statistics"].get("discoveredWiFi")
        discoveredCellGPS = data["statistics"].get("discoveredCellGPS")
        discoveredCell = data["statistics"].get("discoveredCell")
        discoveredBtGPS = data["statistics"].get("discoveredBtGPS")
        discoveredBt = data["statistics"].get("discoveredBt")
        totalWiFiLocations = data["statistics"].get("totalWiFiLocations")
        last = data["statistics"].get("last", "").split("-")[0]
        first = data["statistics"].get("first", "").split("-")[0]

        date_format = "%Y%m%d"  
        last_event_formatted = "Unknown"
        first_event_formatted = "Unknown"

        try:
            if last:
                last_event_datetime = datetime.strptime(last, date_format)
                last_event_formatted = last_event_datetime.strftime("%B %d, %Y")
        except ValueError:
            logging.warning(f"Date format error for 'last': {last}")

        try:
            if first:
                first_event_datetime = datetime.strptime(first, date_format)
                first_event_formatted = first_event_datetime.strftime("%B %d, %Y")
        except ValueError:
            logging.warning(f"Date format error for 'first': {first}")

        embed = discord.Embed(title=f"WiGLE User Stats for '{username}'", color=0x1E90FF)

        # Stats
        stats = (
            f"**Username**: {username}\n"
            f"**Monthly Rank**: {monthRank}\n"
            f"**Last Month's Rank**: {prevMonthRank}\n"            
            f"**Rank**: {rank}\n"
            f"**Previous Rank**: {prevRank}\n"
        )
        embed.add_field(name="📊 **Stats**", value=stats + "\n", inline=False)

        # Event Information
        event_info = (
            f"**Events This Month**: {eventMonthCount}\n"
            f"**Last Month's Events**: {eventPrevMonthCount}\n"
            f"**First Ever Event**: {first_event_formatted}\n"
            f"**Last Event**: {last_event_formatted}"
        )
        embed.add_field(name="📅 **Event Information**", value=event_info + "\n", inline=False)

        # Discovery Statistics
        discovery_stats = (
            f"**Discovered WiFi GPS**: {discoveredWiFiGPS}\n"
            f"**Discovered WiFi GPS Percent**: {discoveredWiFiGPSPercent}%\n"
            f"**Discovered WiFi**: {discoveredWiFi}\n"
            f"**Discovered Cell GPS**: {discoveredCellGPS}\n"
            f"**Discovered Cell**: {discoveredCell}\n"
            f"**Discovered BT GPS**: {discoveredBtGPS}\n"
            f"**Discovered BT**: {discoveredBt}\n"
            f"**Total WiFi Locations**: {totalWiFiLocations}"
        )
        embed.add_field(name="🔍 **Discovery Statistics**", value=discovery_stats, inline=False)

        # Image
        image_url = data.get("imageBadgeUrl", "")
        if image_url:
            image_url += f"?nocache={timestamp}"
            embed.set_image(url=f"https://api.wigle.net{image_url}")

        return embed

    async def fetch_wigle_group_rank(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
            
        timestamp = int(time.time())
        req = f"https://api.wigle.net/api/v2/stats/group?nocache={timestamp}"
        headers = {
            "Authorization": f'Basic {config["wigle_api_key"]}',
            "Cache-Control": "no-cache",
        }

        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Error fetching WiGLE group ranks: {response.status}")
                    await interaction.followup.send(f"HTTP error {response.status}")
                    return

                data = await response.json()
                if data.get("success") and "groups" in data:
                    groups = data["groups"]
                    view = GroupView(groups)
                    sent_message = await interaction.followup.send(embed=view.get_embed(), view=view)
                    view.message = sent_message
                    
                else:
                    message = data.get("message", "No group data available.")
                    await interaction.followup.send(message)
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE group ranks: {e}")
            await interaction.followup.send(str(e))

    async def fetch_wigle_id(self, group_name: str):
        timestamp = int(time.time())
        req = f"https://api.wigle.net/api/v2/stats/group?nocache={timestamp}"
        headers = {
            "Authorization": f"Basic {self.wigle_api_key}",
            "Cache-Control": "no-cache",
        }
        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Error fetching WiGLE group ID for '{group_name}': {response.status}")
                    return {"success": False, "message": f"HTTP error {response.status}"}

                data = await response.json()
                if "success" in data:
                    groups = data.get("groups", [])
                    for group in groups:
                        if group["groupName"] == group_name:
                            group_id = group["groupId"]
                            url = f"https://api.wigle.net/api/v2/group/groupMembers?groupid={group_id}"
                            return {"success": True, "groupId": group_id, "url": url}

                    return {"success": False, "message": f"No group named '{group_name}' found."}
                else:
                    logging.warning(f"WiGLE group ID fetch error for '{group_name}': {data['message']}")
                    return {"success": False, "message": data["message"]}
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE group ID for '{group_name}': {e}")
            return {"success": False, "message": str(e)}

    async def fetch_user_rank(self, url: str):
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Error fetching user rank from URL: {url}, HTTP error {response.status}")
                    return None

                data = await response.json()
                return data
        except Exception as e:
            logging.error(f"Failed to fetch user rank from URL: {url}, {e}")
            return None

    async def fetch_wigle_alltime_rank(self, interaction: discord.Interaction):
        logging.info("Fetching WiGLE all-time user ranks")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
            
        req = f"https://api.wigle.net/api/v2/stats/standings?sort=discovered&pagestart=0"
        headers = {
            "Authorization": f'Basic {config["wigle_api_key"]}',
            "Cache-Control": "no-cache",
        }

        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Error fetching WiGLE user ranks: {response.status}")
                    await interaction.followup.send(f"HTTP error {response.status}")
                    return

                data = await response.json()
                if data.get("success") and "results" in data:
                    data["results"] = [result for result in data["results"] if result["userName"] != "anonymous"]
                    view = AllTime(data["results"])
                    sent_message = await interaction.followup.send(embed=view.get_embed(), view=view)
                    view.message = sent_message
                else:
                    message = data.get("message", "No rank data available.")
                    await interaction.followup.send(message)
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE user ranks: {e}")
            await interaction.followup.send(str(e))

    async def fetch_wigle_month_rank(self, interaction: discord.Interaction):
        logging.info("Fetching WiGLE monthly user rankings")
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)

        req = f"https://api.wigle.net/api/v2/stats/standings?sort=monthcount&pagestart=0"
        headers = {
            "Authorization": f'Basic {config["wigle_api_key"]}',
            "Cache-Control": "no-cache",
        }

        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Error fetching WiGLE monthly ranking: {response.status}")
                    await interaction.followup.send(f"HTTP error {response.status}")
                    return

                data = await response.json()
                if data.get("success") and "results" in data:
                    data["results"] = [result for result in data["results"] if result["userName"] != "anonymous"]
                    view = MonthRank(data["results"])
                    await interaction.followup.send(embed=view.get_embed(), view=view)
                else:
                    message = data.get("message", "No rank data available.")
                    await interaction.followup.send(message)
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE monthly ranking: {e}")
            await interaction.followup.send(str(e))

    async def fetch_wigle_user_rank(self, interaction: discord.Interaction, group: str):
        logging.info(f"Fetching WiGLE user ranks for group: {group}")

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)

        response = await self.fetch_wigle_id(group)

        if "success" in response and response["success"] is True:
            url = response.get("url", None)

            if url is not None:
                group_data = await self.fetch_user_rank(url)

                if group_data:
                    users = group_data.get("users", [])
                    view = UserRankView(users, group)
                    await interaction.followup.send(embed=view.embed, view=view)
                else:
                    await interaction.followup.send("Failed to fetch group data from the URL.")
            else:
                logging.warning(f"Missing 'url' key in WiGLE API response for '{group}'")
                await interaction.followup.send("Invalid API response: missing 'url' key.")
        else:
            error_message = response.get("message", "Failed to fetch group ID.")
            logging.warning(f"WiGLE group ID fetch error for {group}: {error_message}")
            await interaction.followup.send(error_message)

    async def show_credits(self, interaction: discord.Interaction):
        logging.info("Displaying credits")

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)

        credits_text = (
            "WiGLE Bot developed by Kavitate & RocketGod\n\n"
            "This bot provides various functionalities to interact with the WiGLE API.\n"
            "For more information, visit the official WiGLE website."
        )

        color = 0x00FF00  # Bright Green
        embed = discord.Embed(title="Credits", description=credits_text, color=color)
        embed.set_footer(text="WiGLE Wardriving Bot by Kavitate & RocketGod")
        
        ascii_art = (
            "```"
            "                       (         \n"
            "    (  (        (      )\ )      \n"
            "    )\))(   '(  )\ )  (()/( (    \n"
            "   ((_)()\ ) )\(()/(   /(_)))\   \n"
            "   _(())\_)(|(_)/(_))_(_)) ((_)  \n"
            "   \ \((_)/ /(_|_)) __| |  | __| \n"
            "    \ \/\/ / | | | (_ | |__| _|  \n"
            "     \_/\_/  |_|  \___|____|___| \n"
            "   ```"
        )
        embed.add_field(name="", value=ascii_art, inline=False)

        view = HelpView()  
        await interaction.followup.send(embed=embed, view=view)


class UserRankView(discord.ui.View):
    def __init__(self, users, group):
        super().__init__(timeout=10)
        self.users = users
        self.group = group
        self.page = 0
        self.message = None  
        self.update_button()

    def update_button(self):
        if len(self.users) == 0 or self.page >= len(self.users) // 10:
            self.previous_page.disabled = False
            self.next_page.disabled = True
        else:
            self.previous_page.disabled = self.page == 0
            self.next_page.disabled = False  

        p = inflect.engine()
        filtered_users = [user for user in self.users if "L" not in user["status"]]
        start = self.page * 10
        end = start + 10
        users_on_page = filtered_users[start:end]

        rankings = ""
        for i, user in enumerate(users_on_page, start + 1):
            username = user["username"]
            discovered = user["discovered"]
            rank = p.ordinal(i)
            rankings += f"**{rank}:** {username} | **Total:** {discovered}\n"

        self.embed = discord.Embed(title=f"User Rankings for '{self.group}'", color=0x1E90FF, description=rankings)

    @discord.ui.button(label="< Back", style=discord.ButtonStyle.blurple)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            self.update_button()
            await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red)
    async def reset_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self.update_button()
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="Next >", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.users) // 10:
            self.page += 1
            self.update_button()
            await interaction.response.edit_message(embed=self.embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message is None:
            self.message = interaction.message  
        return True

    async def on_timeout(self):
        if self.message is not None:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)


class GroupView(View):
    def __init__(self, groups):
        super().__init__(timeout=10)
        self.groups = groups
        self.page = 0
        self.message = None  
        self.p = inflect.engine()  
        self.update_buttons()

    def update_buttons(self):
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page == len(self.groups) // 10 - 1

    @discord.ui.button(label="< Back", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next >", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        start = self.page * 10
        end = start + 10
        group_slice = self.groups[start:end]
        rankings = ""
        for i, group in enumerate(group_slice, start=start + 1):
            groupName = group["groupName"]
            discovered = group["discovered"]
            rank = self.p.ordinal(i)
            rankings += f"**{rank}:** {groupName} | **Total:** {discovered}\n"
        embed = discord.Embed(title="WiGLE Group Rankings", description=rankings, color=EMBED_COLOR_GROUP_RANK)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message is None:
            self.message = interaction.message  
        return True

    async def on_timeout(self):
        if self.message is not None:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)


class AllTime(View):
    def __init__(self, results):
        super().__init__(timeout=10)
        self.results = results
        self.page = 0
        self.message = None  
        self.p = inflect.engine()  
        self.update_buttons()

    def update_buttons(self):
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page == len(self.results) // 10 - 1

    @discord.ui.button(label="< Back", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next >", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        start = self.page * 10
        end = start + 10
        user_slice = self.results[start:end]
        rankings = ""
        for i, results in enumerate(user_slice, start=start + 1):
            userName = results["userName"]
            discoveredWiFiGPS = results["discoveredWiFiGPS"]
            rank = self.p.ordinal(i)
            rankings += f"**{rank}:** {userName} | **Total:** {discoveredWiFiGPS}\n"
        embed = discord.Embed(title="WiGLE All-Time User Rankings", description=rankings, color=EMBED_COLOR_GROUP_RANK)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message is None:
            self.message = interaction.message  
        return True

    async def on_timeout(self):
        if self.message is not None:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)


class MonthRank(View):
    def __init__(self, results):
        super().__init__(timeout=10)
        self.results = results
        self.page = 0
        self.message = None 
        self.p = inflect.engine() 
        self.update_buttons()

    def update_buttons(self):
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page == len(self.results) // 10 - 1

    @discord.ui.button(label="< Back", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next >", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        start = self.page * 10
        end = start + 10
        user_slice = self.results[start:end]
        rankings = ""
        for i, results in enumerate(user_slice, start=start + 1):
            userName = results["userName"]
            eventMonthCount = results["eventMonthCount"]
            rank = self.p.ordinal(i)
            rankings += f"**{rank}:** {userName} | **Total:** {eventMonthCount}\n"
        embed = discord.Embed(title="WiGLE Monthly User Rankings", description=rankings, color=EMBED_COLOR_GROUP_RANK)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message is None:
            self.message = interaction.message  
        return True

    async def on_timeout(self):
        if self.message is not None:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)


class HelpView(View):
    def __init__(self):
        super().__init__(timeout=None)

        # Create the buttons
        self.add_item(Button(label="Kavitate", style=ButtonStyle.link, url="https://github.com/Kavitate"))
        self.add_item(Button(label="WiGLE", style=ButtonStyle.link, url="https://wigle.net"))
        self.add_item(Button(label="RocketGod", style=ButtonStyle.link, url="https://github.com/RocketGod-git"))


client = WigleBot(wigle_api_key=wigle_api_key)


@client.tree.command(name="wigle", description="Access WiGLE information.")
async def wigle_command(interaction: discord.Interaction):
    view = WigleCommandView(bot=client)
    await interaction.response.send_message("Choose a WiGLE command!", view=view, ephemeral=False)


def run_discord_bot():
    try:
        client.run(config["discord_bot_token"])
    except Exception as e:
        logging.error(f"An error occurred while running the bot: {e}")
    finally:
        if client:
            asyncio.run(client.close())

if __name__ == "__main__":
    run_discord_bot()
