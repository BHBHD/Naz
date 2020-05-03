from configparser import ConfigParser
from discord.ext import commands
from collections import Counter
import platform
import datetime
import discord
import logging

log = logging.getLogger(__name__)
parser = ConfigParser()
parser.read('config.ini')

ADMIN_ROLE = parser.getint('server', 'admin-role-id')


class Misc(commands.Cog, name='Misc'):
    """Handle Miscellaneous commands which don't have any categories."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="**Economy System Bot**",
                              description="List of commands:", color=self.bot.color)

        embed.add_field(name=f"{ctx.prefix}accounts",
                        value="Gives you the list of all of your accounts.", inline=False)
        embed.add_field(name=f"{ctx.prefix}item *account_name* create *item_name* *item_category* *item_info* "
                             f"*item_value*",
                        value="Creates an item to your account *account_name* called *item_name* of "
                              "category *item_category* and infomation *item_info* that costs $*item_value*",
                        inline=False)
        embed.add_field(name=f"{ctx.prefix}item *account_name* edit *item_name* *item_info*",
                        value="Changes the item information of *item_name* to *item_info*.", inline=False)
        embed.add_field(name=f"{ctx.prefix}item *account_name* show *item_name*",
                        value="Shows that *item_name* in the screen with all the details.", inline=False)
        embed.add_field(name=f"{ctx.prefix}item *account_name* delete *item_name*",
                        value="Deletes that *item_name* **permanently**.", inline=False)
        embed.add_field(name=f"{ctx.prefix}myitems",
                        value="Gives you the list of all the items you have in all accounts.", inline=False)
        embed.add_field(name=f"{ctx.prefix}trade *your_account_name* *item_name* *user_to* *price*",
                        value="Trades the item *item_name* from your account *your_account_name* "
                              "to *user_to* for $*price*. The user you are trading with recieves a message asking to "
                              "which account he wants the item to and the money to be deducted from.",
                        inline=False)

        admin_role = discord.utils.get(
            ctx.message.guild.roles, id=ADMIN_ROLE)
        if admin_role in ctx.message.author.roles:
            embed.add_field(
                name="{}bankadmin *user* *account_name* withdraw/deposit *ammount*",
                value="mode = withdraw -> withdraws that ammount to cash in that account for *user*.\n"
                      "mode = deposit -> deposits that ammount in that account for *user*",
                inline=False)
            embed.add_field(name=f"{ctx.prefix}bankadmin *user* *account_name* check",
                            value="Checks the ammount of money *user* have in that account", inline=False)
            embed.add_field(name=f"{ctx.prefix}bankadmin *user* *account_name* terminate",
                            value="Deletes that *user* account", inline=False)
            embed.add_field(name=f"{ctx.prefix}taxtype new *taxtype_name* *tax_value*",
                            value="Creates new tax *taxtype_name* with *tax_value*", inline=False)
            embed.add_field(name=f"{ctx.prefix}taxtype edit *taxtype_name* *tax_value*",
                            value="Changes *taxtype_name* tax to *tax_value*", inline=False)
            embed.add_field(name=f"{ctx.prefix}taxtype delete *taxtype_name*",
                            value="Removes *taxtype_name* from taxlist", inline=False)
            embed.add_field(name=f"{ctx.prefix}taxtypelist",
                            value="Lists all current taxes", inline=False)
            embed.add_field(name=f"{ctx.prefix}itemcategory new *itemcategory_name*",
                            value="Creates a new item category called *itemcategory_name*", inline=False)
            embed.add_field(name=f"{ctx.prefix}itemcategory delete *itemcategory_name*",
                            value="Deletes the item category called *itemcategory_name*", inline=False)
            embed.add_field(
                name=f"{ctx.prefix}itemcategory add/remove *itemcategory_name* *taxtype_name*",
                value="Adds or removes the taxtypr_name to/from *itemcategory_name*.", inline=False)
            embed.add_field(name=f"{ctx.prefix}itemcategorylist",
                            value="Lists all item categories.", inline=False)

        await ctx.send(embed=embed)

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
        embed.timestamp = datetime.datetime.utcnow()
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
        e.timestamp = datetime.datetime.utcnow()
        await ctx.send(embed=e)
        log.debug(f'User: {ctx.author} (ID: {ctx.author.id}) - Seen the library copyrights!')


def setup(bot):
    bot.add_cog(Misc(bot))
    log.info("Misc Cog/Module Loaded Successfully!")
