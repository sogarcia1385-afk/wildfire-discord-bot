import discord
import asyncio
import os
import feedparser
import requests

TOKEN = os.getenv("DISCORD_TOKEN")  # For cloud hosting
CHECK_INTERVAL = 600  # 10 minutes
STATES = ["Oregon", "Washington"]

intents = discord.Intents.default()
client = discord.Client(intents=intents)

announced = set()

def state_match(text):
    for state in STATES:
        if state.lower() in text.lower():
            return True
    return False


async def fetch_inciweb():
    feed = feedparser.parse("https://inciweb.nwcg.gov/feeds/rss/incidents/")
    fires = []

    for entry in feed.entries:
        if state_match(entry.title):
            fires.append({
                "id": "InciWeb-" + entry.id,
                "title": entry.title,
                "link": entry.link,
                "source": "InciWeb"
            })

    return fires


async def fetch_nasa():
    url = "https://eonet.gsfc.nasa.gov/api/v3/events?category=wildfires&status=open"
    r = requests.get(url)
    data = r.json()

    fires = []
    for event in data["events"]:
        if state_match(event["title"]):
            fires.append({
                "id": "NASA-" + event["id"],
                "title": event["title"],
                "link": event["link"],
                "source": "NASA EONET"
            })

    return fires


async def check_fires():
    await client.wait_until_ready()
    channel = discord.utils.get(client.get_all_channels(), name="fire-alerts")

    while not client.is_closed():
        try:
            fires = []
            fires.extend(await fetch_inciweb())
            fires.extend(await fetch_nasa())

            for fire in fires:
                if fire["id"] not in announced:
                    announced.add(fire["id"])

                    embed = discord.Embed(
                        title="🔥 Wildfire Alert",
                        description=fire["title"],
                        color=0xFF4500
                    )
                    embed.add_field(name="Source", value=fire["source"], inline=False)
                    embed.add_field(name="More Info", value=fire["link"], inline=False)

                    await channel.send(embed=embed)

        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(CHECK_INTERVAL)


@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")
    client.loop.create_task(check_fires())

client.run(TOKEN)