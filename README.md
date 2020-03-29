# Irby bot

This is a bot implemented explicitely for
[IrbyGames twitch channel](https://twitch.tv/irbygames).

# Installation

You need at least python 3.7 and virtualenv. Installation commands of the bot
are like follows:
```sh
$ git clone https://github.com/ok2/irbybot.git
$ cd irbybot
$ virtualenv -p $(which python3)
$ . bin/activate
(irbybot) $ pip install -r requirements.txt
(irbybot) $ cp irbybotconfig_template.py irbybotconfig.py
```

# Configuration

All configuration is done through `irbybotconfig.py`, please edit it and enter
required info.

# Running

The bot is supposed to run inside `ipython`, usually you start it with:
```sh
(irbybot) $ ipython3 -i irbybot.py
```

If you don't see the `irbybot` prefix, please activate the environment:
```sh
$ . bin/activate
(irbybot) $
```

After ipython was started, please wait for `Discord is ready!` message, it can
take some time:
```sh
(irbybot) $ ipython3 -i irbybot.py
Python 3.7.6 (default, Jan  2 2020, 11:29:14) 
Type 'copyright', 'credits' or 'license' for more information
IPython 7.13.0 -- An enhanced Interactive Python. Type '?' for help.

Discord is ready!
In [1]: 
```

After that, you will see the text messages from discord and twitch.
