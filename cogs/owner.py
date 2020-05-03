from sys import platform, exit as shutdown
from discord.ext import commands
from .utils import time
import platform
import logging
import discord
import os


log = logging.getLogger(__name__)
directory = os.path.dirname(os.path.realpath(__file__))


def restart():
    os.chdir(directory)
    python = "python" if platform == "win32" else "python3"
    cmd = os.popen(f"nohup {python} launcher.py &")
    cmd.close()


class Owner(commands.Cog, name='Owner'):
    """Owner-only commands that make the bot dynamic."""

    def __init__(self, bot):
        self.bot = bot

    def get_bot_uptime(self, *, brief=False):
        return time.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    @commands.command(hidden=True)
    async def load(self, ctx, *, module):
        """Loads a module."""
        try:
            self.bot.load_extension(module)
            log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Trying to Load -> {module}!')
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
            log.exception(f'User: {ctx.author} (ID: {ctx.author.id}) - Failed to Load -> {module}!')
        else:
            await ctx.send('\N{OK HAND SIGN}')
            log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Successfully Loaded -> {module}!')

    @commands.command(hidden=True)
    async def unload(self, ctx, *, module):
        """Unloads a module."""
        try:
            self.bot.unload_extension(module)
            log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Trying to Unload -> {module}!')
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
            log.exception(f'User: {ctx.author} (ID: {ctx.author.id}) - Failed to Unload -> {module}!')
        else:
            await ctx.send('\N{OK HAND SIGN}')
            log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Successfully Unloaded -> {module}!')

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    async def _reload(self, ctx, *, module):
        """Reloads a module."""
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
            log.exception(f'User: {ctx.author} (ID: {ctx.author.id}) - Failed to Reload -> {module}!')
        else:
            await ctx.send('\N{OK HAND SIGN}')
            log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Successfully Reloaded -> {module}!')

    @_reload.command(name='all')
    async def reload(self, ctx):
        """Reloads all module."""
        for ext in self.bot.cogsList:
            try:
                if hasattr(self, "bot"):
                    self.bot.reload_extension(ext)
                else:
                    self.bot.reload_extension(ext)
                log.info(f'User: {ctx.author} (ID: {ctx.author.id}) - Successfully to Reload all!')
            except Exception as e:
                log.error(f"ERROR: FAILED to load extension: {ext}")
                log.error(f"\t{e.__class__.__name__}: {e}\n")

    @commands.command(name='shutdown', aliases=["sd", "kill", "quit"], hidden=True)
    @commands.is_owner()
    async def shutdown_cmd(self, ctx):
        """Shuts the bot down."""
        e = discord.Embed(color=self.bot.color)
        log.warning(f'User: {ctx.author} (ID: {ctx.author.id}) - Shutdowns the {self.bot.user}!')
        e.title = "Goodbye!"
        await ctx.send(embed=e)
        await self.bot.logout()

    @commands.is_owner()
    @commands.command(name='restart', aliases=["reboot", "reset", "reignite"], hidden=True)
    async def restart_cmd(self, ctx):
        e = discord.Embed(color=self.bot.color)
        if platform != "win32":
            restart()
            e.title = "Restarting..."
            await ctx.send(embed=e)
            shutdown()
        else:
            e.title = "I cannot do this on Windows."
            await ctx.send(embed=e)

    @commands.command(name='activity', aliases=["botactivity", "presence"], hidden=True)
    @commands.is_owner()
    async def activity_bot(self, ctx):
        e = discord.Embed(color=self.bot.color)
        e.description = "```1 - Playing\n" \
                        "2 - Listening \n" \
                        "3 - Watching\n" \
                        "4 - Nothing (Empty)```"
        que = await ctx.send(embed=e)
        none = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author, timeout=30)
        e.title = "```Type a status activity that you want to show after playing ... ```"
        await que.edit(embed=e)
        await none.delete()
        activity = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author, timeout=30)
        await activity.delete()
        await self.bot.change_presence(activity=discord.Activity(type=none.content,
                                                                 name=activity.content),
                                       status=discord.Status.online)
        e.title = 'Success: Status changed!'
        await que.edit(embed=e)
        self.bot.maintain_presence.cancel()
        log.warning(f'User: {ctx.author} (ID: {ctx.author.id}) - Changed the bot status to {self.bot.activity}!')

    @commands.group(name='cycle', aliases=["botstatuscycle", "presencecycle"], hidden=True, invoke_without_command=True)
    @commands.is_owner()
    async def activity_cycle_bot(self, ctx):
        e = discord.Embed(color=self.bot.color)
        try:
            self.bot.maintain_presence.start()
            e.title = 'Starting..'
            await ctx.send(embed=e)
            log.warning(f'User: {ctx.author} (ID: {ctx.author.id}) - Starts the bot presence cycle!')
        except RuntimeError:
            e.title = 'Task is already running!'
            await ctx.send(embed=e)

    @activity_cycle_bot.command(name='stop', hidden=True)
    @commands.is_owner()
    async def activity_cycle_bot_stop(self, ctx):
        e = discord.Embed(color=self.bot.color)
        try:
            self.bot.maintain_presence.stop()
            e.title = 'Stopped!'
            await ctx.send(embed=e)
            log.warning(f'User: {ctx.author} (ID: {ctx.author.id}) - Stop the bot presence cycle!')
        except Exception as e:
            e.title = f'{str(e)}'
            await ctx.send(embed=e)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def uptime(self, ctx):
        """Tells you how long the bot has been up for."""
        e = discord.Embed(color=self.bot.color)
        e.title = 'Uptime'
        e.description = f'**{self.get_bot_uptime()}**'
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Owner(bot))
    log.info(f'Owner Cog/Module Loaded Successfully!')
