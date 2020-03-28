import asyncio, threading, time
import dateutil.parser
from discord import Embed

class GlobalObjects(object):
    def initialized(self):
        return True

try: runtime.initialized()
except: runtime = GlobalObjects()
try: discord.initialized()
except: discord = GlobalObjects()
try: twitch.initialized()
except: twitch = GlobalObjects()

async def _message(channel_name, message, cb = None, typing_delay = 3):
    try: channel = discord.channels[channel_name]
    except:
        discord.channels = {o.name: o for o in discord.bot.get_all_channels()}
        channel = discord.channels[channel_name]
    async with channel.typing():
        await asyncio.sleep(typing_delay)
        if cb is not None:
            args, kw = cb(message)
        else: args, kw = (message,), {}
        await channel.send(*args, **kw)

def message(channel_name, message, cb = None):
    return asyncio.run_coroutine_threadsafe(
        _message(channel_name, message, cb),
        runtime.loop).result(60)

async def stream_alert(user_id):
    user_id = int(user_id)
    try: states = runtime.states
    except: runtime.states = states = {}
    try: games = runtime.games
    except: runtime.games = games = {}
    if user_id not in states:
        states[user_id] = { 'stream': None,
                            'notified': 0.0 }
    if 'user' not in states[user_id]:
        states[user_id]['user'] = twitch.helix.user(user_id)
    user = states[user_id]['user']
    try: stream = user.stream
    except: stream = None
    if (stream is None and states[user_id]['stream'] is not None):
        states[user_id]['stream'] = None
        states[user_id]['notified'] = 0.0
        if 'game' in states[user_id]:
            del states[user_id]['game']
        await _message(runtime.notify_channel,
                       'Bis zum nächsten mal Freunde, wir sehen uns unter: https://twitch.tv/%s' % user.login)
    elif stream is not None:
        notify = False
        if states[user_id]['stream'] is None: notify = True
        if abs(time.monotonic() - states[user_id]['notified']) > runtime.notify_timeout:
            notify = True
        if 'game' in states[user_id] and states[user_id]['game'].id != stream.game_id:
            notify = True
        states[user_id]['stream'] = stream
        if stream.game_id not in games:
            games[stream.game_id] = twitch.helix.game(id = int(stream.game_id))
        states[user_id]['game'] = games[stream.game_id]
        
        started_at = dateutil.parser.isoparse(stream.started_at).timestamp()
        if abs(time.time() - started_at) > runtime.notify_max_started:
            notify = False

        if 'force_notify' in states[user_id]:
            notify = states[user_id]['force_notify']
            del states[user_id]['force_notify']
        if notify:
            embed = Embed(url = 'https://twitch.tv/%s' % user.login,
                          title = '%s spielt %s' % (user.display_name, states[user_id]['game'].name),
                          description = states[user_id]['stream'].title)
            embed.set_author(name = user.display_name, url = embed.url, icon_url = user.profile_image_url)
            embed.set_image(url = states[user_id]['stream'].thumbnail_url.format(width = 1920, height = 1080))
            embed.set_thumbnail(url = states[user_id]['game'].box_art_url.format(width = 75, height = 100))
            states[user_id]['notified'] = time.monotonic()
            await _message(runtime.notify_channel,
                           'Hey Freunde ich bin jetzt am start, schaut doch mal vorbei unter: %s' % embed.url,
                           cb = lambda m: ((m,), {'embed': embed}))

def online_streams():
    return {x['user'].login: x for x in runtime.states.values() if x['stream'] is not None}

async def team_stream_alert():
    while not discord.ready:
        await asyncio.sleep(1)
    while runtime.notify_team_enabled:
        for user in twitch.v5.api.get('teams/%s' % runtime.notify_team_name)['users']:
            try: await stream_alert(int(user['_id']))
            except Exception as err:
                print('team.notify.%s.%s error: %s' % (runtime.notify_team_name, user['display_name'], repr(err)))
        await asyncio.sleep(runtime.notify_check_interval)

async def discord_message(message):
    print('discord.%s.%s: %s' % (message.channel.name, message.author.name, message.content))
    await discord.bot.process_commands(message)

async def discord_ping(ctx):
    print('discord.command.ping')
    await ctx.send('pong', tts = True)
    
async def twitch_message(message):
    print('twitch.%s.%s: %s' % (message.channel, message.user, message.text))
