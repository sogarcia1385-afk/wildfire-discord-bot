import discord
import asyncio
import os
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")

CHECK_INTERVAL = 600
COUNTIES = ["klickitat","skamania","hood river","wasco","sherman","gilliam"]
AGENCIES = ["odf","us forest","usfs","dnr","us forest service"]
WILD_KEYWORDS = ["fire","wildfire","brush","timber"]
EXCLUDE_KEYWORDS = ["prescribed","rx","training","pile"]

announced = set()

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# --------------- HELPER FUNCTIONS ------------------

def is_valid_incident(text):
    txt = text.lower()
    # Must contain wildcard keywords
    if not any(w in txt for w in WILD_KEYWORDS):
        return False
    # Exclude trash
    if any(x in txt for x in EXCLUDE_KEYWORDS):
        return False
    # Must contain county
    if not any(c in txt for c in COUNTIES):
        return False
    # Must contain agency
    if not any(a in txt for a in AGENCIES):
        return False
    return True

# ------------ InciWeb Monitor ----------

async def fetch_inciweb():
    fires = []
    feed = feedparser.parse("https://inciweb.nwcg.gov/feeds/rss/incidents/")
    for entry in feed.entries:
        title = entry.title or ""
        if is_valid_incident(title):
            fires.append({
                "id": "INCIWEB-"+entry.id,
                "title": entry.title,
                "link": entry.link,
                "source": "InciWeb"
            })
    return fires

# ------------ Wildwebe Monitor ----------

async def fetch_wildwebe():
    fires = []
    try:
        url = "https://www.wildwebe.net/incidents?dc_Name=WACCC"
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        table = soup.find("table")
        if not table:
            return fires

        rows = table.find_all("tr")

        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            incident = cols[0].get_text(strip=True)
            agency = cols[1].get_text(strip=True)
            location = cols[2].get_text(strip=True)
            timestamp = cols[4].get_text(strip=True)

            full_text = f"{incident} {agency} {location}"

            if is_valid_incident(full_text):
                incident_id = "WILDWEBE-"+incident.replace(" ","_")
                fires.append({
                    "id": incident_id,
                    "title": f"{incident} ({agency}, {location})",
                    "link": url,
                    "source": "Wildwebe"
                })

    except Exception as e:
        print("Wildwebe Error:", e)

    return fires

# ------------ MAIN CHECK LOOP -------------

async def check_fires():
    await client.wait_until_ready()
    channel = discord.utils.get(client.get_all_channels(), name="fire-alerts")

    while not client.is_closed():
        try:
            all_fires = []
            all_fires.extend(await fetch_inciweb())
            all_fires.extend(await fetch_wildwebe())

            for fire in all_fires:
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
            print("Main Loop Error:", e)

        await asyncio.sleep(CHECK_INTERVAL)

@client.event
async def on_ready():
    print(f"Bot logged in as {client.user}")
    client.loop.create_task(check_fires())

client.run(TOKEN)