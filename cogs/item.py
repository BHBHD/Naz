from configparser import ConfigParser
from discord.ext import commands
from datetime import datetime
from locale import currency
import asyncio
import logging
import discord
import sqlite3
import locale

parser = ConfigParser()
parser.read('config.ini')
ADMIN_ROLE = parser.getint('server', 'admin-role-id')


conn = sqlite3.connect('src/naz.db')
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS itemCategory ('iCName' TEXT, 'iCTaxType' TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS taxType ('taxType' TEXT, 'multiplier' REAL)")
cursor.close()
conn.commit()

log = logging.getLogger(__name__)


def is_account_holder():
    def predicate(ctx):
        if ctx.guild is None:
            return False
        cur = conn.cursor()
        cur.execute(f"SELECT accountReg FROM accounts WHERE user_id = {ctx.author.id}")
        accountReg = cur.fetchone()
        if accountReg is not None:
            if accountReg[0] == 'True':
                return True
        return False
    return commands.check(predicate)


class Item(commands.Cog, name='Items'):
    """"""

    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        conn.close()

    async def wait_for(self, ctx, ques):
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()

        try:
            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author, timeout=60.0)
            await msg.delete()
            return msg.content
        except asyncio.TimeoutError:
            e.title = "Timeout!"
            e.description = "You took too long to fill in an entry. Please try again by using `!item`!"
            await ques.edit(embed=e)
            return None

    async def item_cancel(self, ques):
        e = discord.Embed(title='Item Menu!')
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        e.description = "Talk to ya later :wink:"
        await ques.edit(embed=e)
        return

    async def item_create(self, ctx, ques):
        e = discord.Embed(title='Item Create!')
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        iCList = ""
        onlyCList = []
        cur = conn.cursor()
        cur.execute(f"SELECT iCName FROM itemCategory")
        iC = cur.fetchall()

        if len(iC) <= 0:
            iCList = "There is'nt any itemCategory! Please contact staff!"

        for category in iC:
            iCList += f"{category[0]}\n"
            onlyCList.append(category[0])

        e.description = 'Please type in the corresponding bank account name you wish to use to take funds from ' \
                        'to pay for item creation’s value.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        accountName = await self.wait_for(ctx, ques)

        if accountName == 'cancel':
            await self.item_cancel(ques)
            return

        cur.execute(f"SELECT accountBal FROM accounts WHERE accountName = '{accountName}'")
        accountHolder = cur.fetchone()
        if accountHolder is None:
            e.title = "Item Creation Error"
            e.description = "This is not a valid bank account name and therefore your application has been " \
                            "terminated. Please try again by using !item"
            await ques.edit(embed=e)
            return

        # Item creation starts here!
        e.description = 'Please enter the item name you wish to create.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        itemName = await self.wait_for(ctx, ques)

        if itemName == 'cancel':
            await self.item_cancel(ques)
            return

        e.title = 'Item Category!'
        e.description = f'Please select one of the following categories this item belongs to:\n' \
                        f'```{iCList}```\n' \
                        f'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        itemCategorie = await self.wait_for(ctx, ques)

        if itemCategorie == 'cancel':
            await self.item_cancel(ques)
            return

        e.title = 'Item Description!'
        e.description = 'Please enter an extensive description of this item. Make sure you cover all necessary ' \
                        'in-game details.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        itemDescription = await self.wait_for(ctx, ques)

        if itemDescription == 'cancel':
            await self.item_cancel(ques)
            return

        e.title = 'Item Value'
        e.description = 'Please enter the exact value of this item. Please note that your stated bank account will ' \
                        'need to have sufficient funds, or else this form will be terminated.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        itemValue = await self.wait_for(ctx, ques)

        if itemValue == 'cancel':
            await self.item_cancel(ques)
            return

        # Check details
        if itemCategorie in onlyCList:
            e.title = 'Item Creation Error'
            e.description = "This is not a valid category name and therefore your application has been " \
                            "terminated. Please try again by using !item"
            await ques.edit(embed=e)
            return

        if int(itemValue) >= accountHolder[0]:
            e.title = 'Item Creation Error'
            e.description = "Insufficient balance in your account and therefore your application has been " \
                            "terminated. Please try again by using !item"
            await ques.edit(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to create an new **{itemName}**?")
        if not confirm:
            e.title = 'Item Creation'
            e.description = "Application has been terminated."
            await ques.edit(embed=e)
            return

    @commands.command(name='item')
    @commands.guild_only()
    @is_account_holder()
    async def item_menu(self, ctx):
        """Give you the menu to choice from and give me abilities to do various jobs."""
        e = discord.Embed(title='Item Menu!')
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        e.description = "Welcome to your item hub. " \
                        "Please type one of the following modes to proceed with this form:\n" \
                        "`create`/`edit`/`show`/`delete` or `cancel` to exit!"
        ques = await ctx.send(embed=e)
        reply = await self.wait_for(ctx, ques)

        if reply.lower() == 'cancel':
            await self.item_cancel(ques)
        elif reply.lower() == 'create':
            await self.item_create(ctx, ques)
        else:
            e.description = "I did'nt recognize that your sayin'! \nPlease try again!"
            await ques.edit(embed=e)

    @item_menu.error
    async def item_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            e = discord.Embed(color=self.bot.color)
            e.timestamp = datetime.utcnow()
            e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            e.description = "Only, account holders can have these commands!\n" \
                            f"`{ctx.prefix}request <accountType>` - For open an new account!"
            await ctx.send(embed=e)

    @commands.group(name='itemcategory', aliases=["iC"], case_insensitive=False, invoke_without_command=True)
    @commands.guild_only()
    @commands.has_role(ADMIN_ROLE)
    async def iC(self, ctx):
        """Handle all the itemCategory admin commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @iC.command(name='new')
    async def iC_new(self, ctx, *, itemCategoryName):
        """Creates a new item category called itemcategory_name"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        e.title = "Item Category Creation"
        e.description = f"Please give a taxType of item **{itemCategoryName}**\n" \
                        f"Type 'cancel' for Terminate!"
        ques = await ctx.send(embed=e)
        iCTaxType = await self.wait_for(ctx, ques)

        if iCTaxType == 'cancel':
            e.title = 'Item Category Terminated!'
            e.description = f"Creation of **{itemCategoryName}** Terminated at the end!"
            await ques.edit(embed=e)
            return
        cur = conn.cursor()

        cur.execute(f"SELECT taxType, multiplier FROM taxType WHERE taxType = '{iCTaxType}'")
        valid = cur.fetchone()
        if valid is None:
            e.title = 'Item Category Terminated!'
            e.description = f"**{iCTaxType}** is not any taxType so far! Please try again!"
            await ques.edit(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to add new itemcategory called "
                                   f"**{itemCategoryName}** with **{iCTaxType}** TaxType?")
        if not confirm:
            e.title = 'Item Category Terminated!'
            e.description = f"Creation of **{itemCategoryName}** Terminated at the end!"
            await ques.edit(embed=e)
            return

        cur.execute(f"INSERT INTO itemCategory (iCName, iCTaxType) VALUES ('{itemCategoryName}', '{iCTaxType}')")
        cur.close()
        conn.commit()

    @iC.command(name='remove', aliases=["delete"])
    async def iC_delete(self, ctx, *, itemCategoryName):
        """Creates a new item category called itemcategory_name"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        e.title = "Item Category Delete!"
        e.description = f"Please give a taxType of item **{itemCategoryName}**\n" \
                        f"Type 'cancel' for Terminate!"
        ques = await ctx.send(embed=e)
        iCTaxType = await self.wait_for(ctx, ques)

        if iCTaxType == 'cancel':
            e.title = 'Item Category Terminated!'
            e.description = f"Creation of **{itemCategoryName}** Terminated at the end!"
            await ques.edit(embed=e)
            return
        cur = conn.cursor()

        cur.execute(f"SELECT taxType, multiplier FROM taxType WHERE taxType = '{iCTaxType}'")
        valid = cur.fetchone()
        if valid is None:
            e.title = 'Item Category Terminated!'
            e.description = f"**{iCTaxType}** is not any taxType so far! Please try again!"
            await ques.edit(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to remove itemcategory called "
                                   f"**{itemCategoryName}**")
        if not confirm:
            e.title = 'Item Category Terminated!'
            e.description = f"Creation of **{itemCategoryName}** Terminated at the end!"
            await ques.edit(embed=e)
            return

        cur.execute(f"INSERT INTO itemCategory (iCName, iCTaxType) VALUES ('{itemCategoryName}', '{iCTaxType}')")
        cur.close()
        conn.commit()

    @commands.group(name='taxtype', aliases=["tt"], invoke_without_command=True, case_insensitive=False)
    @commands.guild_only()
    @commands.has_role(ADMIN_ROLE)
    async def taxType(self, ctx):
        """Handle all the itemCategory admin commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @taxType.command(name='new')
    async def taxType_add(self, ctx, taxTypeName, taxTypeValu: float):
        """Create a new taxtype"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        cur = conn.cursor()
        cur.execute(f"SELECT taxType FROM taxType WHERE taxType = '{taxTypeName}'")
        taxType = cur.fetchone()
        if taxType is not None:
            e.title = "TaxType Creation Failed!"
            e.description = f"Sorry, **{taxTypeName}** is a already a registered taxtype!"
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to add new taxType called "
                                   f"**{taxTypeName}** with **{taxTypeValu}** multiplier?")
        if not confirm:
            e.title = 'TaxType Creation Terminated!'
            e.description = f"Creation of **{taxTypeName}** Terminated at the end!"
            await ctx.send(embed=e)
            return

        cur.execute(f"INSERT INTO taxType (taxType, multiplier) VALUES ('{taxTypeName}', {taxTypeValu})")
        cur.close()
        conn.commit()
        e.title = "TaxType Created!"
        e.description = f"**{taxTypeName}** added for **{taxTypeValu}**"
        await ctx.send(embed=e)

    @taxType.command(name='remove')
    async def taxType_remove(self, ctx, taxTypeName):
        """Remove any taxtype"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        cur = conn.cursor()
        cur.execute(f"SELECT taxType, multiplier FROM taxType WHERE taxType = '{taxTypeName}'")
        taxType = cur.fetchone()
        if taxType is None:
            e.title = "TaxType Remove Failed!"
            e.description = f"Sorry, **{taxTypeName}** is not any taxtype registered!"
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to remove taxType called "
                                   f"**{taxTypeName}** with **{taxType[1]}** multiplier?")
        if not confirm:
            e.title = 'TaxType Remove Terminated!'
            e.description = f"Removing of **{taxTypeName}** Terminated at the end!"
            await ctx.send(embed=e)
            return

        cur.execute(f"DELETE FROM taxType WHERE taxType = '{taxTypeName}'")
        cur.close()
        conn.commit()
        e.title = "TaxType Removed!"
        e.description = f"**{taxTypeName}** removed successfully!"
        await ctx.send(embed=e)

    @taxType.command(name='edit')
    async def taxType_edit(self, ctx, taxTypeName, taxTypeNewValue: float):
        """Modification taxtype"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        cur = conn.cursor()
        cur.execute(f"SELECT taxType FROM taxType WHERE taxType = '{taxTypeName}'")
        taxType = cur.fetchone()
        if taxType is None:
            e.title = "TaxType Edit Failed!"
            e.description = f"Sorry, **{taxTypeName}** is not a registered taxtype!"
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to edit taxType called "
                                   f"**{taxTypeName}** with new multiplier **{taxTypeNewValue}**?")
        if not confirm:
            e.title = 'TaxType Edit Terminated!'
            e.description = f"Modification of **{taxTypeName}** Terminated at the end!"
            await ctx.send(embed=e)
            return

        cur.execute(f"UPDATE taxType SET multiplier = {taxTypeNewValue} WHERE taxType = '{taxTypeName}'")
        cur.close()
        conn.commit()
        e.title = "TaxType Edit"
        e.description = f"**{taxTypeName}** updated to **{taxTypeNewValue}** multiplier"
        await ctx.send(embed=e)

    @taxType.command(name='list')
    async def taxType_list(self, ctx):
        """Give you the list for all the taxTypes"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        e.title = "TaxType List!"
        cur = conn.cursor()
        cur.execute(f"SELECT taxType, multiplier FROM taxType")
        taxTypeS = cur.fetchall()
        if len(taxTypeS) == 0:
            e.description = "I did'nt found any taxType! Please start adding."
            await ctx.send(embed=e)
            return
        msg = ""
        index = 1
        for taxType in taxTypeS:
            msg += f'{index}. {taxType[0]} - {taxType[1]}\n'
            index += 1
        e.add_field(name='**TaxTypes:**', value=f"```{msg}```")
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Item(bot))

