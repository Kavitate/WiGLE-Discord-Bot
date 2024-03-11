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
logging.getLogger('discord.gateway').setLevel(logging.WARNING)


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


def format_number(number):
    return "{:,}".format(number)


class WigleCommandView(View):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        # Initialize buttons with their respective labels and unique custom_id
        self.add_item(Button(label="User Stats", style=ButtonStyle.blurple, custom_id="user_stats"))
        self.add_item(Button(label="Group Rank", style=ButtonStyle.blurple, custom_id="group_rank"))
        self.add_item(Button(label="All-Time Rankings", style=ButtonStyle.blurple, custom_id="alltime_rankings"))
        self.add_item(Button(label="Monthly Rankings", style=ButtonStyle.blurple, custom_id="monthly_rankings"))
        self.add_item(Button(label="User Rankings for Group", style=ButtonStyle.blurple, custom_id="user_rankings_for_group"))
        self.add_item(Button(label="Credits", style=ButtonStyle.blurple, custom_id="credits"))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    # Individual callback methods for each button
    async def user_stats_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = UserStatsModal(bot=self.bot)
        await interaction.response.send_modal(modal)

    async def group_rank_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.fetch_wigle_group_rank(interaction)

    async def alltime_rankings_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.fetch_wigle_alltime_rank(interaction)

    async def monthly_rankings_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.fetch_wigle_month_rank(interaction)

    async def user_rankings_for_group_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GroupNameModal(bot=self.bot)
        await interaction.response.send_modal(modal)

    async def credits_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.show_credits(interaction)

    # Handle button interactions
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id_to_callback = {
            "user_stats": self.user_stats_callback,
            "group_rank": self.group_rank_callback,
            "alltime_rankings": self.alltime_rankings_callback,
            "monthly_rankings": self.monthly_rankings_callback,
            "user_rankings_for_group": self.user_rankings_for_group_callback,
            "credits": self.credits_callback
        }

        button = discord.utils.get(self.children, custom_id=interaction.data['custom_id'])

        if button and button.custom_id in custom_id_to_callback:
            await custom_id_to_callback[button.custom_id](interaction, button)
            return True 
        return False  


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
        logging.info(f"Bot is in {len(self.guilds)} servers")
        self.session = aiohttp.ClientSession()

        for guild in self.guilds:
            owner = guild.owner  
            if owner is None:  
                try:
                    owner = await guild.fetch_member(guild.owner_id)  
                except discord.HTTPException:
                    owner = "Unable to fetch owner"  

            owner_name = owner if isinstance(owner, str) else f"{owner.name}#{owner.discriminator}"
            logging.info(f" - {guild.name} (Owner: {owner_name})")

    async def close(self):
        try:
            await super().close()
        finally:
            if self.session:
                await self.session.close()

    async def fetch_wigle_user_stats(self, interaction: discord.Interaction, username: str):
        user = interaction.user
        server = interaction.guild
        server_name = server.name if server else "Direct Message" 

        logging.info(f"{user} searched for '{username}' on {server_name}")

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
                if response.status == 403:  
                    response_text = await response.text()  
                    print(f"403 Forbidden error received. Response: {response_text}")  
                    logging.error(f"Error fetching WiGLE user stats for {username}: {response.status}, Response: {response_text}")
                    await interaction.followup.send(f"HTTP error {response.status}. Check the terminal for more details.")
                    return
                elif response.status != 200:
                    logging.error(f"Error fetching WiGLE user stats for {username}: {response.status}")
                    await interaction.followup.send(f"HTTP error {response.status}")
                    return

                data = await response.json()
                if data is None:
                    logging.error(f"Received no data for {username}")
                    await interaction.followup.send("Failed to retrieve data.")
                    return
                if data.get("success") and "statistics" in data and "userName" in data["statistics"]:
                    if data["statistics"]["userName"].lower() == username.lower():
                        embed = self.create_user_stats_embed(data, timestamp)
                        await interaction.edit_original_response(embed=embed, view=None)
                    else:
                        await interaction.followup.send("User not found.")
                else:
                    await interaction.followup.send("Invalid data received or user not found.")
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE user stats for {username}: {e}")
            await interaction.followup.send(str(e))

    def create_user_stats_embed(self, data, timestamp):
        username = data["statistics"]["userName"]
        rank = format_number(data["statistics"].get("rank", 0))
        monthRank = format_number(data["statistics"].get("monthRank", 0))
        prevRank = format_number(data["statistics"].get("prevRank", 0))
        prevMonthRank = format_number(data["statistics"].get("prevMonthRank", 0))
        eventMonthCount = format_number(data["statistics"].get("eventMonthCount", 0))
        eventPrevMonthCount = format_number(data["statistics"].get("eventPrevMonthCount", 0))
        discoveredWiFiGPS = format_number(data["statistics"].get("discoveredWiFiGPS", 0))
        discoveredWiFiGPSPercent = data["statistics"].get("discoveredWiFiGPSPercent")
        discoveredWiFi = format_number(data["statistics"].get("discoveredWiFi", 0))
        discoveredCellGPS = format_number(data["statistics"].get("discoveredCellGPS", 0))
        discoveredCell = format_number(data["statistics"].get("discoveredCell", 0))
        discoveredBtGPS = format_number(data["statistics"].get("discoveredBtGPS", 0))
        discoveredBt = format_number(data["statistics"].get("discoveredBt", 0))
        totalWiFiLocations = format_number(data["statistics"].get("totalWiFiLocations", 0))
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
            f"**All-Time Rank**: {rank}\n"
            f"**Previous All-Time Rank**: {prevRank}\n\n"
        )
        embed.add_field(name="📊 **Stats**", value=stats + "\n", inline=False)

        # Event Information
        event_info = (
            f"**Events This Month**: {eventMonthCount}\n"
            f"**Last Month's Events**: {eventPrevMonthCount}\n"
            f"**First Ever Event**: {first_event_formatted}\n"
            f"**Last Event**: {last_event_formatted}\n\n"
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
        user = interaction.user
        server = interaction.guild
        server_name = server.name if server else "Direct Message"

        logging.info(f"{user} accessed group rankings on {server_name}")

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
                    sent_message = await interaction.edit_original_response(embed=view.get_embed(), view=view)
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
        user = interaction.user
        server = interaction.guild
        server_name = server.name if server else "Direct Message"

        logging.info(f"{user} viewed all-time user rankings on {server_name}")

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
                    sent_message = await interaction.edit_original_response(embed=view.get_embed(), view=view)
                    view.message = sent_message
                else:
                    message = data.get("message", "No rank data available.")
                    await interaction.followup.send(message)
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE user ranks: {e}")
            await interaction.followup.send(str(e))

    async def fetch_wigle_month_rank(self, interaction: discord.Interaction):
        user = interaction.user
        server = interaction.guild
        server_name = server.name if server else "Direct Message"

        logging.info(f"{user} requested monthly user rankings on {server_name}")

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)

        req = f"https://api.wigle.net/api/v2/stats/standings?sort=monthcount&pagestart=0"
        headers = {
            "Authorization": f'Basic {config["wigle_api_key"]}',
            "Cache-Control": "no-cache",
        }

        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status == 403:
                    response_text = await response.text()  
                    print(f"403 Forbidden error received for monthly rankings. Response: {response_text}")  
                    logging.error(f"Error fetching WiGLE monthly ranking: {response.status}, Response: {response_text}")
                    await interaction.followup.send(f"HTTP error {response.status}. Check the terminal for more details.")
                    return
                elif response.status != 200:
                    logging.error(f"Error fetching WiGLE monthly ranking: {response.status}")
                    await interaction.followup.send(f"HTTP error {response.status}")
                    return

                data = await response.json()
                if data.get("success") and "results" in data:
                    data["results"] = [result for result in data["results"] if result["userName"] != "anonymous"]
                    view = MonthRank(data["results"])
                    await interaction.edit_original_response(embed=view.get_embed(), view=view)
                else:
                    message = data.get("message", "No rank data available.")
                    await interaction.followup.send(message)
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE monthly ranking: {e}")
            await interaction.followup.send(str(e))


    async def fetch_wigle_user_rank(self, interaction: discord.Interaction, group: str):
        user = interaction.user
        server = interaction.guild
        server_name = server.name if server else "Direct Message"

        logging.info(f"{user} checked user rankings for group '{group}' on {server_name}")

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
                    await interaction.edit_original_response(embed=view.embed, view=view)
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
        user = interaction.user
        server = interaction.guild
        server_name = server.name if server else "Direct Message"

        logging.info(f"{user} viewed credits on {server_name}")

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
        server_count = len(self.guilds)
        
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
            f"\nThis bot is used in {server_count} servers."
        )
        embed.add_field(name="", value=ascii_art, inline=False)

        view = HelpView()  
        await interaction.edit_original_response(embed=embed, view=view)


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
            discovered = format_number(user["discovered"]) 
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
            discovered = format_number(group["discovered"])  
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
            discoveredWiFiGPS = format_number(results["discoveredWiFiGPS"]) 
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
            eventMonthCount = format_number(results["eventMonthCount"]) 
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
