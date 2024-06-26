import discord
import aiohttp
import asyncio
import json
import logging
import inflect
import time
from datetime import datetime
from discord import ButtonStyle
from discord.ui import Button, View

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


class WigleBot(discord.Client):
    def __init__(self, wigle_api_key) -> None:
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

    async def fetch_wigle_user_stats(self, username: str):
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
                    return {"success": False, "message": "User not found."}
                elif response.status != 200:
                    logging.error(f"Error fetching WiGLE user stats for {username}: {response.status}")
                    return {"success": False, "message": f"HTTP error {response.status}"}

                data = await response.json()
                if data.get("success") and "statistics" in data and "userName" in data["statistics"]:
                    if data["statistics"]["userName"].lower() == username.lower():
                        logging.info(f"Fetched WiGLE user stats for {username}")

                        # Change here: append a timestamp to the image URL to avoid caching
                        image_url = data.get("imageBadgeUrl", "")
                        if image_url:
                            image_url += f"?nocache={timestamp}"
                            data["imageBadgeUrl"] = image_url  # Update the URL in the data dictionary

                        return data
                    else:
                        return {"success": False, "message": "User not found."}
                else:
                    return {"success": False, "message": "Invalid data received or user not found."}
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE user stats for {username}: {e}")
            return {"success": False, "message": str(e)}

    async def fetch_wigle_group_rank(self):
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
                    return {"success": False, "message": f"HTTP error {response.status}"}

                data = await response.json()
                if data.get("success") and "groups" in data:
                    return data
                else:
                    return {"success": False, "message": "No group data available."}
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE group ranks: {e}")
            return {"success": False, "message": str(e)}

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

                    # No group with the specified name found
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

    async def fetch_wigle_alltime_rank(self):
        req = f"https://api.wigle.net/api/v2/stats/standings?sort=discovered&pagestart=0"
        headers = {
            "Authorization": f'Basic {config["wigle_api_key"]}',
            "Cache-Control": "no-cache",
        }
        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Error fetching WiGLE user ranks: {response.status}")
                    return {"success": False, "message": f"HTTP error {response.status}"}

                data = await response.json()
                if data.get("success") and "results" in data:
                    # Remove the user named "Anonymous" from the results
                    data["results"] = [result for result in data["results"] if result["userName"] != "anonymous"]
                    return data
                else:
                    return {"success": False, "message": "No rank data available."}
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE user ranks: {e}")
            return {"success": False, "message": str(e)}

    async def fetch_wigle_month_rank(self):
        req = f"https://api.wigle.net/api/v2/stats/standings?sort=monthcount&pagestart=0"
        headers = {
            "Authorization": f'Basic {config["wigle_api_key"]}',
            "Cache-Control": "no-cache",
        }
        try:
            async with self.session.get(req, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Error fetching WiGLE monthly ranking: {response.status}")
                    return {"success": False, "message": f"HTTP error {response.status}"}

                data = await response.json()
                if data.get("success") and "results" in data:
                    # Remove the user named "Anonymous" from the results
                    data["results"] = [result for result in data["results"] if result["userName"] != "anonymous"]
                    return data
                else:
                    return {"success": False, "message": "No rank data available."}
        except Exception as e:
            logging.error(f"Failed to fetch WiGLE monthly ranking: {e}")
            return {"success": False, "message": str(e)}


class UserRankView(discord.ui.View):
    def __init__(self, users, group):
        super().__init__(timeout=10)
        self.users = users
        self.group = group
        self.page = 0
        self.message = None  # Add this line to initialize the 'message' attribute
        self.update_button()

    def update_button(self):
        if len(self.users) == 0 or self.page >= len(self.users) // 10:
            self.previous_page.disabled = False
            self.next_page.disabled = True
        else:
            self.previous_page.disabled = self.page == 0
            self.next_page.disabled = False  # Always enable the "Next" button

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
            discovered_formatted = "{:,}".format(discovered)
            rankings += f"**{rank}:** {username} | **Total:** {discovered_formatted}\n"

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
            self.message = interaction.message  # Set the 'message' attribute when the view is sent
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True  # Disable all buttons
        await self.message.edit(view=self)  # Update the message with the new view


class GroupView(View):
    def __init__(self, groups):
        super().__init__(timeout=10)
        self.groups = groups
        self.page = 0
        self.message = None  # Add this line to initialize the 'message' attribute
        self.p = inflect.engine()  # Create an instance of the inflect library
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
            formatted_discovered = "{:,}".format(discovered)
            rank = self.p.ordinal(i)
            rankings += f"**{rank}:** {groupName} | **Total:** {formatted_discovered}\n"
        embed = discord.Embed(title="WiGLE Group Rankings", description=rankings, color=EMBED_COLOR_GROUP_RANK)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message is None:
            self.message = interaction.message  # Set the 'message' attribute when the view is sent
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True  # Disable all buttons
        await self.message.edit(view=self)  # Update the message with the new view


class AllTime(View):
    def __init__(self, results):
        super().__init__(timeout=10)
        self.results = results
        self.page = 0
        self.message = None  # Add this line to initialize the 'message' attribute
        self.p = inflect.engine()  # Create an instance of the inflect library
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
            formatted_discoveredWiFiGPS = "{:,}".format(discoveredWiFiGPS)
            rankings += f"**{rank}:** {userName} | **Total:** {formatted_discoveredWiFiGPS}\n"
        embed = discord.Embed(title="WiGLE All-Time User Rankings", description=rankings, color=EMBED_COLOR_GROUP_RANK)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message is None:
            self.message = interaction.message  # Set the 'message' attribute when the view is sent
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True  # Disable all buttons
        await self.message.edit(view=self)  # Update the message with the new view


class MonthRank(View):
    def __init__(self, results):
        super().__init__(timeout=10)
        self.results = results
        self.page = 0
        self.message = None  # Add this line to initialize the 'message' attribute
        self.p = inflect.engine()  # Create an instance of the inflect library
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
            rankings += f"**{rank}:** {userName} | **Total:** {eventMonthCount:,}\n"
        embed = discord.Embed(title="WiGLE Monthly User Rankings", description=rankings, color=EMBED_COLOR_GROUP_RANK)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message is None:
            self.message = interaction.message  # Set the 'message' attribute when the view is sent
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True  # Disable all buttons
        await self.message.edit(view=self)  # Update the message with the new view


class HelpView(View):
    def __init__(self):
        super().__init__(timeout=None)

        # Create the buttons
        self.add_item(Button(label="Kavitate", style=ButtonStyle.link, url="https://github.com/Kavitate"))
        self.add_item(Button(label="WiGLE", style=ButtonStyle.link, url="https://wigle.net"))
        self.add_item(Button(label="RocketGod", style=ButtonStyle.link, url="https://github.com/RocketGod-git"))


client = WigleBot(wigle_api_key=wigle_api_key)


@client.tree.command(name="user", description="Get stats for a WiGLE user.")
async def user(interaction: discord.Interaction, username: str):
    logging.info(f"Command 'user' invoked for username: {username}")

    await interaction.response.defer(ephemeral=False)

    try:
        # Fetch the user stats from the WiGLE API
        response = await client.fetch_wigle_user_stats(username)

        # Check if the API call was successful before trying to access the data
        if "success" in response and response["success"]:
            # Scrape all of the data
            username = response["user"]
            rank = response["rank"]
            monthRank = response["monthRank"]
            statistics = response["statistics"]
            prevRank = statistics["prevRank"]
            prevMonthRank = statistics["prevMonthRank"]
            eventMonthCount = statistics["eventMonthCount"]
            eventPrevMonthCount = statistics["eventPrevMonthCount"]
            discoveredWiFiGPS = statistics["discoveredWiFiGPS"]
            discoveredWiFiGPSPercent = statistics["discoveredWiFiGPSPercent"]
            discoveredWiFi = statistics["discoveredWiFi"]
            discoveredCellGPS = statistics["discoveredCellGPS"]
            discoveredCell = statistics["discoveredCell"]
            discoveredBtGPS = statistics["discoveredBtGPS"]
            discoveredBt = statistics["discoveredBt"]
            totalWiFiLocations = statistics["totalWiFiLocations"]
            last = statistics["last"]
            first = statistics["first"]
            image_url = response.get("imageBadgeUrl", "")

            # Extract and format 'last' and 'first' event dates (ignoring time)
            last_event_date_str, _ = last.split("-")
            first_event_date_str, _ = first.split("-")

            last_event_datetime = datetime.strptime(last_event_date_str, "%Y%m%d")
            first_event_datetime = datetime.strptime(first_event_date_str, "%Y%m%d")

            last_event_formatted = last_event_datetime.strftime("%B %d, %Y")
            first_event_formatted = first_event_datetime.strftime("%B %d, %Y")

            # Create an embed object for a nicely formatted Discord message
            embed = discord.Embed(title=f"WiGLE User Stats for '{username}'", color=0x1E90FF)

            # Add fields to embed
            embed.add_field(name="Username", value=username, inline=True)
            embed.add_field(name="Rank", value=format(rank, ","), inline=True)
            embed.add_field(name="Previous Rank", value=format(prevRank, ","), inline=True)
            embed.add_field(name="Monthly Rank", value=format(monthRank, ","), inline=True)
            embed.add_field(name="Last Month's Rank", value=format(prevMonthRank, ","), inline=True)
            embed.add_field(name="Events This Month", value=format(eventMonthCount, ","), inline=True)
            embed.add_field(name="Last Month's Events", value=format(eventPrevMonthCount, ","), inline=True)
            embed.add_field(name="Discovered WiFi GPS", value=format(discoveredWiFiGPS, ","), inline=True)
            embed.add_field(name="Discovered WiFi GPS Percent", value=format(discoveredWiFiGPSPercent, ","), inline=True)
            embed.add_field(name="Discovered WiFi", value=format(discoveredWiFi, ","), inline=True)
            embed.add_field(name="Discovered Cell GPS", value=format(discoveredCellGPS, ","), inline=True)
            embed.add_field(name="Discovered Cell", value=format(discoveredCell, ","), inline=True)
            embed.add_field(name="Discovered BT GPS", value=format(discoveredBtGPS, ","), inline=True)
            embed.add_field(name="Discovered BT", value=format(discoveredBt, ","), inline=True)
            embed.add_field(name="Total WiFi Locations", value=format(totalWiFiLocations, ","), inline=True)
            embed.add_field(name="Last Event", value=last_event_formatted, inline=True)
            embed.add_field(name="First Ever Event", value=first_event_formatted, inline=True)

            # Add image if available
            if image_url:
                embed.set_image(url=f"https://api.wigle.net{image_url}")

            # Send the embed as a follow-up to the interaction
            await interaction.followup.send(embed=embed)
        else:
            error_message = response.get("message", "Failed to fetch user stats.")
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

    if "success" in response and response["success"] is True:
        groups = response["groups"]
        view = GroupView(groups)
        await interaction.followup.send(embed=view.get_embed(), view=view)
    else:
        await interaction.followup.send("Failed to fetch group ranks: " + response.get("message", "Unknown error"))


@client.tree.command(name="userrank", description="Get user ranks for group.")
async def userrank(interaction: discord.Interaction, group: str):
    logging.info(f"Command 'userrank' invoked for group name: {group}")
    await interaction.response.defer(ephemeral=False)

    try:
        # Fetch the WiGLE group ID and URL
        response = await client.fetch_wigle_id(group)

        if "success" in response and response["success"] is True:
            url = response.get("url", None)

            if url is not None:
                # Fetch data from the URL
                group_data = await client.fetch_user_rank(url)

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
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        await interaction.followup.send(f"An error occurred: {e}")


@client.tree.command(name="alltime", description="Get WiGLE All-Time User Rankings.")
async def alltime(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    # Fetch the group ranks from the WiGLE API
    response = await client.fetch_wigle_alltime_rank()

    if "success" in response and response["success"] is True:
        results = response["results"]
        view = AllTime(results)
        await interaction.followup.send(embed=view.get_embed(), view=view)
    else:
        await interaction.followup.send("Failed to fetch user ranks: " + response.get("message", "Unknown error"))


@client.tree.command(name="monthly", description="Get WiGLE Monthly User Rankings.")
async def monthly(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    # Fetch the group ranks from the WiGLE API
    response = await client.fetch_wigle_month_rank()

    if "success" in response and response["success"] is True:
        results = response["results"]
        view = MonthRank(results)
        await interaction.followup.send(embed=view.get_embed(), view=view)
    else:
        await interaction.followup.send(
            "Failed to fetch monthly user rankings: " + response.get("message", "Unknown error")
        )


@client.tree.command(name="help", description="Displays help information for WiGLE Bot commands.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    help_text = ("**Command List**\n"
                 "`/user <username>` - Get stats for a WiGLE user.\n"
                 "`/grouprank` - Get WiGLE group rankings.\n"
                 "`/userrank` - Get WiGLE user rankings for a group.\n"
                 "`/alltime` - Get WiGLE All-Time user rankings.\n"
                 "`/monthly` - Get WiGLE monthly user rankings.\n"
                 "`/help` - Shows this help message.\n\n")

    color = 0x00FF00  # Bright Green

    embed = discord.Embed(title="WiGLE Bot Help",
                          description=help_text,
                          color=color)
    embed.set_footer(text="WiGLE Wardriving Bot by Kavitate & RocketGod")

    image_url = "https://i.imgur.com/90kBgvJ.png"
    embed.set_image(url=image_url)

    view = HelpView()
    await interaction.followup.send(embed=embed, view=view)


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
    
