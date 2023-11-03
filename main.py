import discord
from discord.ext import commands
import requests
import inflect

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix = '!', intents=intents)

@client.event
async def on_ready():
    print('WiGLE stats are online.')

@client.command()
async def user(ctx, arg1):
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
  await ctx.message.delete()
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
      f"{image}"
  )
  return

@client.command()
async def grouprank(ctx):
    req = "https://api.wigle.net/api/v2/stats/group"
    response = requests.get(req, headers={'Authorization': 'Basic YOUR_WIGLE_API'}).json()

    # Scrape all of the data from the link
    groups = response['groups']

    # Initialize an empty string to store the rankings
    rankings = ""

    p = inflect.engine()
    for i, group in enumerate(groups[:40], 1):
        groupName = group['groupName']
        total = group['total']
        rank = p.ordinal(i)
        rankings += f"**{rank}:** {groupName} **Total:** {total}\n"

    # Reply back with the scraped data
    await ctx.message.delete()
    await ctx.send(f"## Group Rankings\n\n{rankings}")

@client.command()
async def userrank(ctx):
    req = "https://api.wigle.net/api/v2/group/groupMembers?groupid=YOUR_GROUP_ID_HERE"
    response = requests.get(req, headers={'Authorization': 'Basic YOUR_WIGLE_API'}).json()

    # Scrape all of the data from the link
    users = response['users']

    # Initialize an empty string to store the rankings
    rankings = ""

    p = inflect.engine()
    for i, user in enumerate(users[:50], 1):
        username = user['username']
        discovered = user['discovered']
        rank = p.ordinal(i)
        rankings += f"**{rank}:** {username} **Total:** {discovered}\n"

    # Reply back with the scraped data
    await ctx.message.delete()
    await ctx.send(f"## User Rankings\n\n{rankings}")

client.run("YOUR_DISCORD_BOT_TOKEN")
