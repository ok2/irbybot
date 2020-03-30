DISCORD_TOKEN = 'XXXX'
TWITCH_CLIENT_ID = 'XXX'
TWITCH_CLIENT_SECRET = 'XXX'
TWITCH_OAUTH = 'XXX'

def configure(env):
    env.config.notify_timeout = 60 * 60
    env.config.notify_max_started = 10 * 60
    env.config.notify_channels = ((r'myuser', 'mychannel'),
                                   (r'.*', 'otherchannel'))
    env.config.notify_team_name = 'xxx'
    env.config.notify_team_enabled = True
    env.config.notify_check_interval = 60
    env.config.twitch_channel = '#mychannel'
    env.config.twitch_nick = 'Mynick'
    env.config.notify_online = lambda **k: \
        'Hey Freunde ich bin jetzt am start, schaut doch mal vorbei unter %s @everyone' % k['url']
    env.config.notify_title = lambda **k: \
        '%s spielt %s' % (k['name'], k['game'])
    env.config.notify_offline = None
    env.config.mod_channel = 'test-channel'
    env.config.commands_file = '/home/xxx/commands.dump'
    env.config.join_message = '''Hallöchen mein Freund'''
    env.config.left_message = '''hat den Server verlassen.'''
    env.config.left_users = ['myuser']
