from discord.ext import commands
from cogs.utils import context
from discord.ext import tasks
from collections import deque
from itertools import cycle
from enum import Enum
import configparser
import traceback
import datetime
import logging
import discord
import aiohttp
import json
import sys
import csv

log = logging.getLogger(__name__)

parser = configparser.ConfigParser()
parser.read('config.ini')
ACTIVITY_INTERVAL = parser.getint('default', 'activity-change-time-interval')

description = "A bot made in Python by ɃĦɃĦĐ#2224 for naz#6078 upon his requirements"
activities = []
initial_extensions = ['cogs.owner', 'cogs.errors', 'cogs.misc',
                      'cogs.bank', 'cogs.item']

with open("src/activities.csv", "r", encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=",")
    for rows in reader:
        for row in rows:
            activity = row
            activities.append(activity)
activities = cycle(activities)


class naz(commands.AutoShardedBot):

    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or(parser.get('default', 'prefix')),
                         description=description, owner_id=parser.getint('discord', 'owner-id'),
                         case_insensitive=False)
        super().remove_command("help")
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.uptime = datetime.datetime.utcnow()
        self._prev_events = deque(maxlen=10)
        self.cogsList = initial_extensions

        for color in Colors:
            if color.name.lower() == parser.get("embedColor", "embed-color").lower():
                self.color = color.value

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                log.error(f'Failed to load extension {extension}, {e}', file=sys.stderr)
                traceback.print_exc()

    @tasks.loop(seconds=ACTIVITY_INTERVAL)
    async def maintain_presence(self):
        current_activity = next(activities)
        await super().change_presence(activity=discord.Game(name=current_activity))

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()
        self.maintain_presence.start()

        print(f'Ready: {self.user} (ID: {self.user.id})')

    async def on_resumed(self):
        print('resumed...')

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)

        if ctx.command is None:
            return

        try:
            await self.invoke(ctx)
        except Exception as e:
            print(e)

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

    async def close(self):
        await super().close()
        await self.session.close()
        print('Sessions closed!')

    def run(self):
        try:
            super().run(parser.get('discord', 'token'), reconnect=True)
        finally:
            with open('logs/prev_events.log', 'w', encoding='utf-8') as fp:
                for data in self._prev_events:
                    try:
                        x = json.dumps(data, ensure_ascii=True, indent=4)
                    except Exception as e:
                        fp.write(f'{data}\n')
                        print(f'Data written in {fp} with Exception{e}')
                    else:
                        fp.write(f'{x}\n')

    @property
    def config(self):
        return __import__('config')


class Colors(Enum):
    black = 0x000000
    teal = discord.Color.teal()
    dark_teal = discord.Color.dark_teal()
    green = discord.Color.green()
    dark_green = discord.Color.dark_green()
    blue = discord.Color.blue()
    dark_blue = discord.Color.dark_blue()
    purple = discord.Color.purple()
    dark_purple = discord.Color.dark_purple()
    magenta = discord.Color.magenta()
    dark_magenta = discord.Color.dark_magenta()
    gold = discord.Color.gold()
    dark_gold = discord.Color.dark_gold()
    orange = discord.Color.orange()
    dark_orange = discord.Color.dark_orange()
    red = discord.Color.red()
    dark_red = discord.Color.dark_red()
    lighter_grey = discord.Color.lighter_grey()
    dark_grey = discord.Color.dark_grey()
    light_grey = discord.Color.light_grey()
    darker_grey = discord.Color.darker_grey()
    blurple = discord.Color.blurple()
    greyple = discord.Color.greyple()
