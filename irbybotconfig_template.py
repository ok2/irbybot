DISCORD_TOKEN = 'XXXX'
TWITCH_CLIENT_ID = 'XXX'
TWITCH_CLIENT_SECRET = 'XXX'
TWITCH_OAUTH = 'XXX'

def configure(env):
    env.runtime.notify_timeout = 60 * 60
    env.runtime.notify_max_started = 10 * 60
    env.runtime.notify_channel = 'xxx'
    env.runtime.notify_team_name = 'xxx'
    env.runtime.notify_team_enabled = True
    env.runtime.notify_check_interval = 60

