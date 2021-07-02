import discord
import os

client = discord.Client()

TOKEN = os.getenv('DISCORD_TOKEN')

@client.event
async def on_message(m):
    print(m)


client.run(TOKEN)
