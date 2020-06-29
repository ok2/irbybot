#!/usr/bin/env python3

import asyncio, discord, logging, twitch
from discord.ext import commands as discord_cmd
from threading import Thread
from importlib import reload
import irbybotconfig as config
import irbybotfuns as env

logging.basicConfig(level = logging.DEBUG,
                    format = "%(asctime)s [%(levelname)s] %(message)s",
                    handlers = [logging.FileHandler('irbybot.log')])

config.configure(env)
env.runtime.loop = asyncio.new_event_loop()
env.runtime.commands = {}
env.discord.bot = discord_cmd.Bot(command_prefix = '!',
                                  case_insensitive = True,
                                  loop = env.runtime.loop)
env.discord.ready = False
def reinit_twitch():
    env.twitch.helix = twitch.Helix(client_id = config.TWITCH_CLIENT_ID,
                                    client_secret = config.TWITCH_CLIENT_SECRET,
                                    bearer_token = config.TWITCH_OAUTH.replace('oauth:', ''))
    env.twitch.v5    = twitch.v5.V5(client_id = config.TWITCH_CLIENT_ID,
                                    client_secret = config.TWITCH_CLIENT_SECRET)
    #env.twitch.chat  = twitch.Chat (channel = env.config.twitch_channel,
    #                                oauth = config.TWITCH_OAUTH,
    #                                nickname = env.config.twitch_nick,
    #                                helix = env.twitch.helix)
    #env.twitch.chat.subscribe(twitch_message)
    env.twitch.reinit = reinit_twitch

@env.discord.bot.event
async def on_ready():
    await env.discord_ready()

@env.discord.bot.event
async def on_error(event, *args, **kwargs):
    await env.discord_error(event, *args, **kwargs)

@env.discord.bot.event
async def on_message(message):
    await env.discord_message(message)

@env.discord.bot.event
async def on_raw_reaction_add(payload):
    await env.discord_reaction('add', payload)

@env.discord.bot.event
async def on_raw_reaction_remove(payload):
    await env.discord_reaction('remove', payload)

@env.discord.bot.event
async def on_raw_reaction_clear(payload):
    await env.discord_reaction('clear', payload)

@env.discord.bot.event
async def on_raw_reaction_clear_emoji(payload):
    await env.discord_reaction('clear_emoji', payload)

@env.discord.bot.event
async def on_member_join(member):
    await env.discord_join(member)

@env.discord.bot.event
async def on_member_remove(member):
    await env.discord_left(member)

def twitch_message(message):
    env.runtime.loop.create_task(env.twitch_message(message))

def discord_run():
    asyncio.set_event_loop(env.runtime.loop)
    asyncio.ensure_future(env.discord.bot.start(config.DISCORD_TOKEN),
                          loop = env.runtime.loop)
    env.runtime.loop.create_task(env.team_stream_alert())
    env.runtime.loop.create_task(env._reset_commands())
    env.runtime.loop.run_forever()

reinit_twitch()
env.discord.thread = Thread(target = discord_run)
env.discord.thread.start()
