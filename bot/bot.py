import json
import os
import discord
from discord import app_commands
from discord.ext import commands

DATA_FILE = os.getenv("DATA_FILE", "data/output.json")
TOKEN = os.getenv("DISCORD_TOKEN")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)

class StatsBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self) -> None:
        await self.tree.sync()

bot = StatsBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="stats", description="Show captured stats")
async def stats(interaction: discord.Interaction):
    data = load_data()
    text = data.get("text", "No data available")
    await interaction.response.send_message(text, ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN environment variable not set")
    bot.run(TOKEN)
