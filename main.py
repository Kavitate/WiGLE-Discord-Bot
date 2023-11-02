import discord
from discord.ext import commands
import json
import requests

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix = '!', intents=intents)

@client.event
async def on_ready():
    print('WiGLE-bot is online.')

@client.command()
async def wigle(ctx, arg1):
  req = "https://api.wigle.net/api/v2/stats/user?user={}".format(arg1)
  response = requests.get(req, headers={'Authorization': 'Basic YOUR_WIGLE_API'}).json()

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
  image = ("https://wigle.net"+(response['imageBadgeUrl']))

  # Reply back with the scraped data
  await ctx.send(
      f"**Username:** {username}\n"
      f"**Rank:** {rank}\n"
      f"**Previous Rank:** {prevRank}\n"
      f"**Monthly Rank:** {monthRank}\n"
      f"**Last Month's Rank:** {prevMonthRank}\n"
      f"**Events This Month:** {eventMonthCount}\n"
      f"**Last Month's Events:** {eventPrevMonthCount}\n"
      f"**Discovered WiFi GPS:** {discoveredWiFiGPS}\n"
      f"**Discovered WiFi GPS Percent:** {discoveredWiFiGPSPercent}\n"
      f"**Discovered WiFi:** {discoveredWiFi}\n"
      f"**Discovered Cell GPS:** {discoveredCellGPS}\n"
      f"**Discovered Cell:** {discoveredCell}\n"
      f"**Discovered BT GPS:** {discoveredBtGPS}\n"
      f"**Discovered BT:** {discoveredBt}\n"
      f"**Total WiFi Locations:** {totalWiFiLocations}\n"
      f"**Last Event:** {last}\n"
      f"**First Ever Event:** {first}\n"
      f"{image}\n"
  )
  return

client.run("YOUR_DISCORD_BOT_TOKEN")
