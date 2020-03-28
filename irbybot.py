#!/usr/bin/env python3

import asyncio, discord, logging, twitch
from discord.ext import commands as discord_cmd
from irbybotconfig import *
from threading import Thread
from importlib import reload
import irbybotfuns as env

logging.basicConfig(level = logging.DEBUG,
                    format = "%(asctime)s [%(levelname)s] %(message)s",
                    handlers = [logging.FileHandler('irbybot.log')])

configure(env)
env.runtime.loop = asyncio.new_event_loop()
env.discord.bot = discord_cmd.Bot(command_prefix = '!', loop = env.runtime.loop)
env.discord.ready = False
env.twitch.helix = twitch.Helix(client_id = TWITCH_CLIENT_ID,
                                client_secret = TWITCH_CLIENT_SECRET)
env.twitch.v5    = twitch.v5.V5(client_id = TWITCH_CLIENT_ID,
                                client_secret = TWITCH_CLIENT_SECRET)
env.twitch.chat  = twitch.Chat (channel = '#irbygames',
                                oauth = TWITCH_OAUTH,
                                nickname = 'IrbyBot',
                                helix = env.twitch.helix)

@env.discord.bot.event
async def on_ready():
    env.discord.ready = True
    print('Discord is ready!')

@env.discord.bot.event
async def on_message(message):
    await env.discord_message(message)

@env.discord.bot.command(name = 'ping')
async def discord_ping(ctx):
    await env.discord_ping(ctx)

def twitch_message(message):
    env.runtime.loop.create_task(env.twitch_message(message))

def discord_run():
    asyncio.set_event_loop(env.runtime.loop)
    asyncio.ensure_future(env.discord.bot.start(DISCORD_TOKEN),
                          loop = env.runtime.loop)
    env.runtime.loop.create_task(env.team_stream_alert())
    env.runtime.loop.run_forever()

env.twitch.chat.subscribe(twitch_message)
env.discord.thread = Thread(target = discord_run)
env.discord.thread.start()
