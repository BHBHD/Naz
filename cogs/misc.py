from configparser import ConfigParser
from discord.ext import commands
from collections import Counter
from datetime import datetime
import platform
import asyncio
import discord
import logging

log = logging.getLogger(__name__)
parser = ConfigParser()
parser.read('config.ini')

ADMIN_ROLE = parser.getint('server', 'admin-role-id')


def chunks(a, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(a), n):
        yield a[i:i + n]


def command_helper(self, ctx, command):
    """ Displays a command and it's sub commands """

    try:
        cmd = [x for x in command.commands if not x.hidden]
        cmds_ = []
        for i in list(chunks(list(cmd), 6)):
            embed = discord.Embed(color=self.bot.color)
            embed.set_author(name=command.signature)
            embed.description = f"```{command.help}```"
            for x in i:
                embed.add_field(name=f'{ctx.prefix}{x.qualified_name} {x.signature}', value=f'```{x.help}```',
                                inline=False)
            cmds_.append(embed)

        for n, x in enumerate(cmds_):
            x.set_footer(text=f"Page {n + 1} of {len(cmds_)}")
        return cmds_
    except AttributeError:
        embed = discord.Embed(color=self.bot.color)
        embed.set_author(name=f'{ctx.prefix}{command.qualified_name} {command.signature}')
        embed.description = f"```{command.help}```"
        return [embed]


async def paginate(ctx, input_):
    """ Paginator """

    try:
        pages = await ctx.send(embed=input_[0])
    except (AttributeError, TypeError):
        return await ctx.send(embed=input_)

    if len(input_) == 1:
        return

    current = 0

    r = ['\U000023ee', '\U000025c0', '\U000025b6',
         '\U000023ed', '\U0001f522', '\U000023f9']
    for x in r:
        await pages.add_reaction(x)

    paging = True
    while paging:
        def check(r_, u_):
            return u_ == ctx.author and r_.message.id == pages.id and str(r_.emoji) in r

        done, pending = await asyncio.wait([ctx.bot.wait_for('reaction_add', check=check, timeout=120),
                                            ctx.bot.wait_for('reaction_remove', check=check, timeout=120)],
                                           return_when=asyncio.FIRST_COMPLETED)
        try:
            reaction, user = done.pop().result()
        except asyncio.TimeoutError:
            try:
                await pages.clear_reactions()
            except discord.Forbidden:
                await pages.delete()

            paging = False

        for future in pending:
            future.cancel()
        else:
            if str(reaction.emoji) == r[2]:
                current += 1
                if current == len(input_):
                    current = 0
                    try:
                        await pages.remove_reaction(r[2], ctx.author)
                    except discord.Forbidden:
                        pass
                    await pages.edit(embed=input_[current])

                await pages.edit(embed=input_[current])
            elif str(reaction.emoji) == r[1]:
                current -= 1
                if current == 0:
                    try:
                        await pages.remove_reaction(r[1], ctx.author)
                    except discord.Forbidden:
                        pass

                    await pages.edit(embed=input_[len(input_) - 1])

                await pages.edit(embed=input_[current])
            elif str(reaction.emoji) == r[0]:
                current = 0
                try:
                    await pages.remove_reaction(r[0], ctx.author)
                except discord.Forbidden:
                    pass

                await pages.edit(embed=input_[current])

            elif str(reaction.emoji) == r[3]:
                current = len(input_) - 1
                try:
                    await pages.remove_reaction(r[3], ctx.author)
                except discord.Forbidden:
                    pass

                await pages.edit(embed=input_[current])

            elif str(reaction.emoji) == r[4]:
                m = await ctx.send(f"What page you do want to go? 1-{len(input_)}")

                def pager(m_):
                    return m_.author == ctx.author and m_.channel == ctx.channel and int(m_.content) > 1 <= len(input_)

                try:
                    msg = int((await ctx.bot.wait_for('message', check=pager, timeout=60)).content)
                except asyncio.TimeoutError:
                    return await m.delete()
                current = msg - 1
                try:
                    await pages.remove_reaction(r[4], ctx.author)
                except discord.Forbidden:
                    pass

                await pages.edit(embed=input_[current])
            else:
                try:
                    await pages.clear_reactions()
                except discord.Forbidden:
                    await pages.delete()

                paging = False


class Misc(commands.Cog, name='Misc'):
    """Handle Miscellaneous commands which don't have any categories."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='bot', aliases=["botstatus", "info"])
    async def info_bot(self, ctx):
        """Give the bot's details like bot version, python version, creator and other details."""
        versioninfo = platform.sys.version_info
        major = versioninfo.major
        minor = versioninfo.minor
        micro = versioninfo.micro
        embed = discord.Embed(title='Bot Information', description='Created by ɃĦɃĦĐ#2224',
                              color=self.bot.color)

        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_footer(text=f'{self.bot.user.name}',
                         icon_url=self.bot.user.avatar_url)
        embed.add_field(name='**Total Guilds**', value=f'`{len(list(self.bot.guilds))}`', inline=True)
        embed.add_field(name='**Total Users**', value=f'`{len(list(self.bot.users))}`', inline=True)
        channel_types = Counter(isinstance(c, discord.TextChannel) for c in self.bot.get_all_channels())
        text = channel_types[True]
        embed.add_field(name='**Total Channels**', value=f'`{text}`', inline=True)
        embed.add_field(name='**Python Version**', value=f'`{major}.{minor}.{micro}`',
                        inline=True)
        embed.add_field(name='**Discord.py Version**', value=f'`{discord.__version__}`', inline=True)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
        log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Seen the bot stats and details!')

    @commands.command(name='package', aliases=["discord.py", "rapptz"])
    async def library(self, ctx):
        """Gives the depth of the API and Author of the API"""
        e = discord.Embed(title=f'{discord.__title__}', description="\u200b", color=self.bot.color)
        e.add_field(name="*Author:* ", value=f"{discord.__author__}")
        e.add_field(name="*Version:* ", value=f"{discord.__version__}")
        e.add_field(name=f"*{discord.__copyright__}:* ", value=f"{discord.__license__}")
        e.set_footer(text=f'{self.bot.user.name}', icon_url=self.bot.user.avatar_url)
        e.timestamp = datetime.utcnow()
        await ctx.send(embed=e)
        log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Seen the library copyrights!')

    @commands.command(name='user-commands', aliases=["user", "uc", "usercommands"])
    async def user_help(self, ctx, *, command=None):
        """Give all the user commands!\n
        Cooldown: null\n
        For Example:\n
        !user-commands bet\n
        !help bet
        """
        if command:
            thing = ctx.bot.get_command(command)
            if isinstance(thing, commands.Command):
                await paginate(ctx, command_helper(self, ctx, thing))
                return
            else:
                await ctx.send(f'Looks like "{command}" is not a command.')
                return

        embed = discord.Embed(color=self.bot.color)
        embed.set_footer(text='Type "!help <command>" for more information')
        embed.timestamp = datetime.utcnow()

        embed.description = f"*User-Commands:*"
        embed.add_field(name="*Bank:* ", value="`request`, `check`, `transfer`, "
                                               "`withdraw`, `deposit`, `terminate`, `authorize`",
                        inline=False)
        embed.add_field(name="*Account:* ", value="`account`", inline=False)
        embed.add_field(name="*Item:* ", value="`item`, `inventory`", inline=False)
        embed.add_field(name="*Trade:* ", value="`sell`, `buy`", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='admin-commands', aliases=["admin", "ac", "admincommands"])
    async def admin_help(self, ctx, *, command=None):
        """Give all the admin commands!\n
        Cooldown: null\n
        For Example:\n
        !admin-commands finish\n
        !help finish
        """
        if command:
            thing = ctx.bot.get_command(command)
            if isinstance(thing, commands.Command):
                await paginate(ctx, command_helper(self, ctx, thing))
                return
            else:
                await ctx.send(f'Looks like "{command}" is not a command.')
                return

        embed = discord.Embed(color=self.bot.color)
        embed.set_footer(text='Type "!help <command>" for more information')
        embed.timestamp = datetime.utcnow()

        embed.description = f"*Admin-Commands:*"
        embed.add_field(name="*Bank:* ", value="`check`, `balance`, `terminate`", inline=False)
        embed.add_field(name="*TaxType:* ", value="`new`, `edit`, `delete`, `list`", inline=False)
        embed.add_field(name="*ItemCategory:* ", value="`new`, `edit`, `delete`, `remove`, `add`, `list`", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='owner-commands', aliases=["owner"], hidden=True)
    @commands.is_owner()
    async def owner_help(self, ctx, *, command=None):
        """Give all the owner commands!\n
        Cooldown: null\n
        For Example:\n
        !<owner-commands|owner> [command]
        """
        if command:
            thing = ctx.bot.get_command(command)
            if isinstance(thing, commands.Command):
                await paginate(ctx, command_helper(self, ctx, thing))
                return
            else:
                await ctx.send(f'Looks like "{command}" is not a command.')
                return

        embed = discord.Embed(color=self.bot.color)
        embed.set_footer(text='Type "!help <command>" for more information')
        embed.timestamp = datetime.utcnow()

        embed.description = f"*Owner-Commands:*"
        embed.add_field(name="*Module:* ", value="`reload`, `unload`, `load`", inline=False)
        embed.add_field(name="*Bot:* ", value="`shutdown`, `restart`, `uptime`", inline=False)
        embed.add_field(name="*Presence:* ", value="`activity`, `cycle`, `cycle stop`", inline=False)
        embed.add_field(name="*Version Control:* ", value="`version`, `update`", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name='help', aliases=["commands"], hidden=True)
    async def help_help(self, ctx, *, command=None):
        """Tell the details of the command like there aliases, example and cooldown!\n
        For Example:\n
        !help help
        """
        if command:
            thing = ctx.bot.get_command(command)
            if isinstance(thing, commands.Command):
                await paginate(ctx, command_helper(self, ctx, thing))
                return
            else:
                await ctx.send(f'Looks like "{command}" is not a command.')
                return

        embed = discord.Embed(color=self.bot.color)
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        embed.timestamp = datetime.utcnow()

        embed.description = f"You cannot see the commands like this please use your' specific commands.\n" \
                            f"> {ctx.prefix}admin-commands\n" \
                            f"> {ctx.prefix}user-commands\n" \
                            f"> {ctx.prefix}owner-commands"

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Misc(bot))
    log.info("Misc Cog/Module Loaded Successfully!")
