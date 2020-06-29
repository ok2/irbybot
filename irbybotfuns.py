import asyncio, threading, time, re, os, pickle
import dateutil.parser
from discord import Embed
from googleapiclient.discovery import build
import googletrans

class GlobalObjects(object):
    def initialized(self):
        return True

try: config.initialized()
except: config = GlobalObjects()
try: runtime.initialized()
except: runtime = GlobalObjects()
try: discord.initialized()
except: discord = GlobalObjects()
try: twitch.initialized()
except: twitch = GlobalObjects()

def out(*args, **kw):
    return print(time.strftime('%m.%d %H:%M:%S', time.localtime()), *args, **kw)

def _google_search(search_term, **kwargs):
    service = build("customsearch", "v1", developerKey=config.google_api)
    res = service.cse().list(q=search_term, cx=config.google_seid, **kwargs).execute()
    return res['items']

def _get_notify_channel(user):
    for regex, channel, online_msg, offline_msg in config.notify_channels:
        if re.match(regex, user.login) or re.match(regex, user.display_name):
            return (_get_channel_name(channel), online_msg, offline_msg)
    return (_get_channel_name('test-channel'), config.notify_online, config.notify_offline)

def _get_channel_name(channel_name, retry = True, use_cache = True):
    if not use_cache:
        discord.channels = {o.name: o for o in discord.bot.get_all_channels()}
    try: discord_channels = discord.channels
    except: discord_channels = discord.channels = {o.name: o for o in discord.bot.get_all_channels()}
    if channel_name in discord_channels:
        return channel_name
    for current_name in discord_channels.keys():
        if channel_name.lower() in current_name.lower():
            return current_name
    if retry:
        return _get_channel_name(channel_name, retry = False, use_cache = False)
    return channel_name

async def _message(channel_name, message, cb = None, typing_delay = 3):
    channel_name = _get_channel_name(channel_name)
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
    try:
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
            if 'game' in states[user_id]:
                del states[user_id]['game']
            out('twitch.stream.offline: https://twitch.tv/%s' % user.login)
            channel, online_msg, offline_msg = _get_notify_channel(user)
            if offline_msg is not None:
                await _message(channel, offline_msg(url = 'https://twitch.tv/%s' % user.login, login = user.login))
        elif stream is not None:
            notify = False
            if states[user_id]['stream'] is None:
                notify = True
            if abs(time.monotonic() - states[user_id]['notified']) > config.notify_timeout:
                notify = True
            if 'game' in states[user_id] and states[user_id]['game'].id != stream.game_id:
                notify = True
            started_at = dateutil.parser.isoparse(stream.started_at).timestamp()
            if abs(time.time() - started_at) > config.notify_max_started:
                notify = False

            states[user_id]['stream'] = stream
            if stream.game_id not in games:
                games[stream.game_id] = twitch.helix.game(id = int(stream.game_id))
            states[user_id]['game'] = games[stream.game_id]

            if 'force_notify' in states[user_id]:
                notify = states[user_id]['force_notify']
                del states[user_id]['force_notify']
            if notify:
                embed = Embed(url = 'https://twitch.tv/%s' % user.login,
                              title = config.notify_title(name = user.display_name,
                                                          game = states[user_id]['game'].name),
                              description = states[user_id]['stream'].title)
                embed.set_author(name = user.display_name, url = embed.url, icon_url = user.profile_image_url)
                embed.set_image(url = states[user_id]['stream'].thumbnail_url.format(width = 800, height = 450))
                embed.set_thumbnail(url = states[user_id]['game'].box_art_url.format(width = 75, height = 100))
                states[user_id]['notified'] = time.monotonic()
                out('twitch.stream.online: %s' % embed.url)
                channel, online_msg, offline_msg = _get_notify_channel(user)
                await _message(channel, online_msg(url = embed.url, login = user.login),
                               cb = lambda m: ((m,), {'embed': embed}))
    except Exception as err:
        out('twitch.stream.alert error: %s' % repr(err))

def online_streams():
    return {x['user'].login: x for x in runtime.states.values() if x['stream'] is not None}

async def team_stream_alert():
        while not discord.ready:
            await asyncio.sleep(1)
        while config.notify_team_enabled:
            try:
                for user in twitch.v5.api.get('teams/%s' % config.notify_team_name)['users']:
                    try: await stream_alert(int(user['_id']))
                    except Exception as err:
                        out('team.notify.%s.%s error: %s' % (config.notify_team_name, user['display_name'], repr(err)))
                await asyncio.sleep(config.notify_check_interval)
            except Exception as err:
                out('twitch.team.stream.alert error: %s' % repr(err))
                twitch.reinit()
                await asyncio.sleep(5)

async def discord_message(message):
    if message.author.name not in config.discord_ignore_users:
        out('discord.%s.%s %s: %s' % (getattr(message.channel, 'name', '()'), message.author.name, repr(message.author.id), message.content))
    await discord.bot.process_commands(message)

async def twitch_message(message):
    if message.user not in config.twitch_ignore_users:
        out('twitch.%s.%s: %s' % (message.channel, message.user, message.text))

async def discord_ping(ctx):
    """Antwortet mit PONG"""
    if config.allowed_channels is not None and ctx.channel.name not in config.allowed_channels:
        out('discord.command.ping not allowed')
        return
    out('discord.command.ping')
    async with ctx.typing():
        await ctx.send('PONG', tts = True)

async def discord_streams(ctx):
    """Listet die aktuellen Online-Streams vom NextGen Team auf"""
    if config.allowed_channels is not None and ctx.channel.name not in config.allowed_channels:
        out('discord.command.streams not allowed')
        return
    out('discord.command.streams')
    async with ctx.typing():
        count = 0
        msg = []
        for user, data in sorted(online_streams().items(), key = lambda x: x[0]):
            msg.append('`%s` mit `%s` auf <https://twitch.tv/%s>' % (data['user'].display_name, data['game'].name, user))
            count += 1
        msg.append('Offen %d von %d Streams des Teams: <https://www.twitch.tv/team/%s>' % (count, len(runtime.states), config.notify_team_name))
        await ctx.send('\n'.join(msg))

async def discord_google(ctx):
    """Suche etwas im Internet"""
    if config.allowed_channels is not None and ctx.channel.name not in config.allowed_channels:
        out('discord.command.google not allowed')
        return
    out('discord.command.google: %s' % repr(ctx.message.content))
    try: query = re.split(r'\s+', ctx.message.content, 1)[1].strip()
    except Exception as err:
        out('discord.command.google error: %s' % repr(err))
        return
    async with ctx.typing():
        msg = []
        for res in _google_search(query):
            msg.append('`%s`: <%s>' % (res['title'], res['link']))
        await ctx.send("\n".join(msg))

async def discord_translate(ctx):
    """Übersetzer"""
    out('discord.command.translate: %s' % repr(ctx.message.content))
    async with ctx.typing():
        try:
            _, lang, text = re.split(r'\s+', ctx.message.content, 2)
            out('discord.command.translate: %s' % repr((lang, text)))
            translation = googletrans.Translator().translate(text, dest = lang.strip()).text
            await ctx.send(translation)
        except Exception as err:
            out('discord.command.translate error: %s' % repr(err))
            if 'invalid destination language' in repr(err):
                await ctx.send('Die Sprache `%s` ist mir leider nicht bekannt' % lang)
            else: await ctx.send('Ich kann das leider nicht übersetzen')

async def discord_commands(ctx):
    """Zeigt verfügbare Befehle"""
    if config.allowed_channels is not None and ctx.channel.name not in config.allowed_channels:
        out('discord.command.commands not allowed')
        return
    out('discord.command.commands')
    async with ctx.typing():
        mod_channel = _get_channel_name(config.mod_channel)
        msg = ["Folgende Befehle sind verfügbar:"]
        for cmd_name in sorted(discord.bot.all_commands.keys()):
            cmd_obj = discord.bot.all_commands[cmd_name]
            if cmd_obj.name != cmd_name: continue
            if cmd_obj.hidden: continue
            if cmd_name in config.admin_commands \
               and ctx.channel.name not in config.admin_channels:
                continue
            if ctx.channel.name in config.allowed_channels:
                if cmd_name in runtime.commands: pointer = '`<=`'
                else: pointer = '`=>`'
                msg.append("`% 14s` %s %s" % ('!%s' % cmd_name, pointer, cmd_obj.description))
        await ctx.send("\n".join(msg))

async def discord_print(ctx):
    if config.allowed_channels is not None and ctx.channel.name not in config.allowed_channels:
        out('discord.command.%s (print) not allowed' % ctx.command.name)
        return
    out('discord.command.%s (print)' % ctx.command.name)
    async with ctx.typing():
        _, msg = runtime.commands.get(ctx.command.name, ('', ''))
        if msg is not '':
            await ctx.send(msg)

def flush_commands():
    with open(config.commands_file + '.tmp', 'wb') as fd:
        pickle.dump(runtime.commands, fd)
    os.rename(config.commands_file + '.tmp', config.commands_file)

async def discord_ready():
    discord.ready = True
    print('Discord is ready!')

async def discord_resumed():
    print('Discord resumed!')

async def auto_roling():
    guild = discord.bot.get_guild(config.discord_guild)
    messages_cache = {}
    for channel_id, message_id, emoji_name, role_id in config.auto_roling:
        if (channel_id, message_id) not in messages_cache:
            channel = guild.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            messages_cache[(channel_id, message_id)] = message
        else: message = messages_cache[(channel_id, message_id)]
        role = guild.get_role(role_id)
        users_found = set()
        for reaction in message.reactions:
            if reaction.emoji != emoji_name:
                continue
            async for user in reaction.users():
                try: roles = user.roles
                except: continue
                role_found = False
                for currole in roles:
                    if currole.id == role_id:
                        role_found = True
                        break
                if not role_found:
                    print('discord.autorolling: %s' % 'add role %s on message %s.%d for user %s' % (role.name, channel.name, message_id, user.name))
                    await user.add_roles(role, reason = 'Auto rolling add on message %s.%s' % (channel_id, message_id))
                users_found.add(user.id)
        #for member in guild.members:
        #    if member.id in users_found:
        #        continue
        #    print('@@@ %s' % repr((role, 'Auto rolling remove role %s on message %s for user %s' % (role, message, member))))
        #    #await member.remove_roles(role, reason = 'Auto rolling remove on message %s.%s' % (channel_id, message_id))

async def discord_reaction(rtype, payload):
    try:
        print('reaction.%s: %s' % (rtype, payload))
        start_auto_roling = False
        for channel_id, message_id, _, _ in config.auto_roling:
            if channel_id == payload.channel_id and message_id == message_id:
                start_auto_roling = True
                break
        if start_auto_roling:
            await auto_roling()
    except Exception as err:
        out('discord.reactor error: %s' % (member.name, repr(err)))
    
async def discord_error(event, *args, **kwargs):
    print('DISCORD ERROR: %s' % repr((event, args, kwargs)))

async def discord_join(member):
    out('discord.join.%s' % member.name)
    try: await member.send(config.join_message)
    except Exception as err:
        out('discord.join.%s error: %s' % (member.name, repr(err)))

async def discord_left(member):
    out('discord.left.%s' % member.name)
    discord_members = {x.name: x for x in discord.bot.get_all_members()}
    for user in config.left_users:
        if user not in discord_members: continue
        try: await discord_members[user].send('%s %s' % (member.name, config.left_message))
        except Exception as err:
            out('discord.left.%s error for user %s: %s' % (member.name, user, repr(err)))

async def discord_setcommand(ctx):
    """Setzt ein Textbefehl"""
    out('discord.command.setcommand: %s' % repr((ctx.channel.name, ctx.author.name, ctx.message.content)))
    async with ctx.typing():
        mod_channel = _get_channel_name(config.mod_channel)
        if mod_channel != ctx.channel.name and ctx.channel.name not in config.admin_channels:
            await ctx.send('FEHLER: `!setcommand` ist in diesem Kanal nicht erlaubt.')
            return
        try:
            args, content = ctx.message.content.split('\n', 1)
            _, cmd_name, cmd_desc = re.split(r'\s+', args, 2)
            cmd_name, cmd_desc = cmd_name.strip().lower(), cmd_desc.strip()
            if cmd_name.startswith('!'): cmd_name = cmd_name[1:]
            if not re.match('^[a-z0-9_]+$', cmd_name):
                raise SyntaxError('Wrong command name: %s' % repr(cmd_name))
            if cmd_name in discord.bot.all_commands:
                if getattr(discord.bot.all_commands[cmd_name], 'not_overwritable', False):
                    raise SyntaxError('Failed to overwrite command: %s' % repr(cmd_name))
                discord.bot.remove_command(cmd_name)
            runtime.commands[cmd_name] = (cmd_desc, content)
            discord.bot.command(name = cmd_name, description = cmd_desc)(discord_print)
            flush_commands()
            await ctx.send('Befehl `!%s` erfolgreich gesetzt.' % cmd_name)
        except Exception as err:
            await ctx.send('FEHLER: Befehl ist ungültig, gültige Syntax ist:\n' \
                           '```\n!setcommand <name> <beschreibung>\n<inhalt>\n```\n' \
                           'Anmerkungen:\n' \
                           '- `<inhalt>` muss zwingend auf einer neuen Zeile stehen\n' \
                           '- Nur vorher gesetzte Befehle können überschrieben werden')
            raise err

async def discord_delcommand(ctx):
    """Löscht ein gesetztes Befehl"""
    out('discord.command.delcommand')
    async with ctx.typing():
        mod_channel = _get_channel_name(config.mod_channel)
        if mod_channel != ctx.channel.name and ctx.channel.name not in config.admin_channels:
            await ctx.send('FEHLER: `!delcommand` ist in diesem Kanal nicht erlaubt.')
            return
        try:
            _, cmd_name = re.split(r'\s+', ctx.message.content, 2)
            cmd_name = cmd_name.strip()
            if cmd_name.startswith('!'): cmd_name = cmd_name[1:]
            if cmd_name not in runtime.commands:
                await ctx.send('FEHLER: Befehl `!%s` ist nicht gesetzt.' % cmd_name)
            elif cmd_name in discord.bot.all_commands and \
                getattr(discord.bot.all_commands[cmd_name], 'not_overwritable', False):
                await ctx.send('FEHLER: Befehl `!%s` kann nicht gelöscht werden.' % cmd_name)
            else:
                discord.bot.remove_command(cmd_name)
                del runtime.commands[cmd_name]
                flush_commands()
                await ctx.send('Befehl `!%s` gelöscht!' % cmd_name)
        except Exception as err:
            await ctx.send('FEHLER: Befehl ist ungültig.')
            raise err

async def _reset_commands():
    for cmd_name in list(discord.bot.all_commands.keys()):
        discord.bot.remove_command(cmd_name)
    try:
        with open(config.commands_file, 'rb') as fd:
            runtime.commands = pickle.load(fd)
    except Exception as err:
        out("WARNING: failed to read file %s: %s" % (repr(config.commands_file), repr(err)))
    discord.bot.command(name = 'nextgen', description = discord_streams.__doc__)(discord_streams)
    discord.bot.command(name = 'ping',
                        description = discord_ping.__doc__,
                        aliases = ['hallo', 'servus', 'hi'])(discord_ping)
    discord.bot.command(name = 'commands',
                        description = discord_commands.__doc__,
                        aliases = ['help', 'hilfe', 'befehle', 'cmds', 'ls'])(discord_commands)
    discord.bot.command(name = 'setcommand',
                        aliases = ['set'],
                        description = discord_setcommand.__doc__)(discord_setcommand)
    discord.bot.command(name = 'delcommand',
                        aliases = ['del'],
                        description = discord_delcommand.__doc__)(discord_delcommand)
    discord.bot.command(name = 'suche',
                        aliases = ['google'],
                        hidden = True,
                        description = discord_google.__doc__)(discord_google)
    discord.bot.command(name = 'translate',
                        aliases = ['übersetze'],
                        hidden = True,
                        description = discord_translate.__doc__)(discord_translate)
    for cmd in discord.bot.all_commands.values():
        cmd.not_overwritable = True
    for cmd_name, cmd_data in runtime.commands.items():
        cmd_desc, _ = cmd_data
        discord.bot.command(name = cmd_name, description = cmd_desc)(discord_print)

def reset_commands():
    return asyncio.run_coroutine_threadsafe(_reset_commands(), runtime.loop).result(60)
