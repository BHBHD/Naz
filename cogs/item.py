from .utils.formats import TabularData, plural
from configparser import ConfigParser
from discord.ext import commands
from datetime import datetime
from locale import currency
import asyncio
import logging
import discord
import sqlite3
import locale
import typing
import json
import io

parser = ConfigParser()
parser.read('config.ini')
ADMIN_ROLE = parser.getint('server', 'admin-role-id')
locale.setlocale(locale.LC_ALL, '')


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
        cur.execute(f"SELECT accountReg FROM accounts "
                    f"WHERE user_id = {ctx.author.id} OR authorize_id = {ctx.author.id}")
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
        cur = conn.cursor()

        # Fetch Item Category
        with open('src/itemC.json', encoding='utf-8') as f:
            data = json.load(f)

        iCList = ""
        onlyCList = []
        if len(data["iC"]) <= 0:
            e.description = "There is'nt any itemCategory! Please contact staff!"
            await ques.edit(embed=e)
            return
        for category in data["iC"]:
            iCList += f"{category}\n"
            onlyCList.append(category)

        # Check account details and balance
        e.description = 'Please type in the corresponding bank account name you wish to use to take funds from ' \
                        'to pay for item creation’s value.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        accountName = await self.wait_for(ctx, ques)

        if accountName == 'cancel':
            await self.item_cancel(ques)
            return

        cur.execute(f"SELECT accountBal, accountNo FROM accounts WHERE accountName = '{accountName}'")
        accountHolder = cur.fetchone()
        if accountHolder is None:
            e.color = discord.Color.red()
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
                        f'```\n{iCList}\n```\n' \
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
        for x in onlyCList:
            if itemCategorie.lower() == x.lower():
                if int(itemValue) >= accountHolder[0]:
                    e.title = 'Item Creation Error'
                    e.description = "Insufficient balance in your account and therefore your application has been " \
                                    "terminated. Please try again by using !item"
                    await ques.edit(embed=e)
                    return

                else:
                    confirm = await ctx.prompt(f"Are you sure that you wants to create an new **{itemName}**?")
                    if not confirm:
                        e.color = discord.Color.red()
                        e.title = 'Item Creation'
                        e.description = "Application has been terminated."
                        await ques.edit(embed=e)
                        return

                    cur.execute(
                        f"CREATE TABLE IF NOT EXISTS `{accountHolder[1]}`('itemName' TEXT, 'itemCategory' TEXT, "
                        f"'itemDescription' TEXT, 'itemValue' REAL, 'accountName' TEXT)")
                    conn.commit()
                    cur.execute(f"INSERT INTO `{accountHolder[1]}` (itemName, itemCategory, itemDescription, "
                                f"itemValue, accountName) VALUES ('{itemName}', '{itemCategorie}', "
                                f"'{itemDescription}', {itemValue}, '{accountName}')")
                    cur.execute(f"UPDATE accounts SET accountBal = {float(accountHolder[0]) - float(itemValue)} "
                                f"WHERE accountName = '{accountName}'")
                    cur.close()
                    conn.commit()
                    e.color = discord.Color.green()
                    e.title = f"Item Created!"
                    e.description = "Item Create Successfully with the following information!"
                    e.add_field(name="*Item Name:* ", value=f"***{itemName}***")
                    e.add_field(name="*Item Category:* ", value=f"***{itemCategorie}***")
                    e.add_field(name="*Item Description:* ", value=f"***{itemDescription}***")
                    e.add_field(name="*Item Value:* ", value=f"***{itemValue}***")
                    await ques.edit(embed=e)
                    return

        e.color = discord.Color.red()
        e.title = 'Item Creation Error'
        e.description = "This is not a valid category name and therefore your application has been " \
                        "terminated. Please try again by using !item"
        await ques.edit(embed=e)
        return

    async def item_edit(self, ctx, ques):
        e = discord.Embed(title='Item Edit!')
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        # Check account details and balance
        e.description = 'Please type in the corresponding bank account name which was linked to that item.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        accountName = await self.wait_for(ctx, ques)

        if accountName == 'cancel':
            await self.item_cancel(ques)
            return

        cur.execute(f"SELECT accountBal, accountNo FROM accounts WHERE accountName = '{accountName}'")
        accountHolder = cur.fetchone()
        if accountHolder is None:
            e.color = discord.Color.red()
            e.title = "Item Modification Error"
            e.description = "This is not a valid bank account name and therefore your application has been " \
                            "terminated. Please try again by using !item"
            await ques.edit(embed=e)
            return

        # Modification stats here
        e.description = 'Please enter the item name you wish to edit\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        itemName = await self.wait_for(ctx, ques)

        cur.execute(f"SELECT itemName FROM `{accountHolder[1]}` WHERE itemName = '{itemName}'")
        validItemName = cur.fetchone()
        if validItemName is None:
            e.color = discord.Color.red()
            e.title = "Item Modification Error"
            e.description = "This item is not registered to your account Please try again!"
            await ques.edit(embed=e)
            return

        e.description = 'Please enter an extensive description of this item. Make sure you cover all necessary ' \
                        'in-game details. \nType “cancel” to cancel this form'
        await ques.edit(embed=e)
        itemDescription = await self.wait_for(ctx, ques)

        cur.execute(f"UPDATE `{accountHolder[1]}` SET itemDescription = '{itemDescription}' "
                    f"WHERE itemName = '{itemName}'")
        cur.close()
        conn.commit()
        e.color = discord.Color.green()
        e.title = "Edit successful"
        e.description = "You have successfully edited your item’s description."
        await ques.edit(embed=e)

    async def item_show(self, ctx, ques):
        e = discord.Embed(title='Item Show!')
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        # Check account details and balance
        e.description = 'Please type in the corresponding bank account name which is linked to that item.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        accountName = await self.wait_for(ctx, ques)

        if accountName == 'cancel':
            await self.item_cancel(ques)
            return

        cur.execute(f"SELECT accountBal, accountNo FROM accounts WHERE accountName = '{accountName}'")
        accountHolder = cur.fetchone()
        if accountHolder is None:
            e.color = discord.Color.red()
            e.title = "Item Modification Error"
            e.description = "This is not a valid bank account name and therefore your application has been " \
                            "terminated. Please try again by using !item"
            await ques.edit(embed=e)
            return

        # Ask itemName
        e.description = 'Please enter the item name you wish to look up.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        itemName = await self.wait_for(ctx, ques)

        if accountName == 'cancel':
            await self.item_cancel(ques)
            return

        cur.execute(f"SELECT itemName, itemCategory, itemDescription, "
                    f"itemValue, accountName FROM `{accountHolder[1]}` WHERE itemName = '{itemName}'")
        validItemName = cur.fetchone()
        if validItemName is None:
            e.color = discord.Color.red()
            e.title = "Item Not Found"
            e.description = "This item is not registered to your account Please try again!"
            await ques.edit(embed=e)
            return

        e.color = discord.Color.green()
        e.title = f"{validItemName[4]}"
        e.description = ""
        e.add_field(name="*Item Name:* ", value=f"***{validItemName[0]}***")
        e.add_field(name="*Item Category:* ", value=f"***{validItemName[1]}***")
        e.add_field(name="*Item Description:* ", value=f"***{validItemName[2]}***")
        e.add_field(name="*Item Value:* ", value=f"***{validItemName[3]}***")
        await ques.edit(embed=e)
        return

    async def item_delete(self, ctx, ques):
        e = discord.Embed(title='Item Delete!')
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        # Check account details and balance
        e.description = 'Please type in the corresponding bank account name which is linked to that item.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        accountName = await self.wait_for(ctx, ques)

        if accountName == 'cancel':
            await self.item_cancel(ques)
            return

        cur.execute(f"SELECT accountBal, accountNo FROM accounts WHERE accountName = '{accountName}'")
        accountHolder = cur.fetchone()
        if accountHolder is None:
            e.color = discord.Color.red()
            e.title = "Item Deletion Error"
            e.description = "This is not a valid bank account name and therefore your application has been " \
                            "terminated. Please try again by using !item"
            await ques.edit(embed=e)
            return

        # Ask itemName
        e.description = 'Please enter the item name you wish to permanently remove from your inventory.\n' \
                        'Type “cancel” to cancel this form.'
        await ques.edit(embed=e)
        itemName = await self.wait_for(ctx, ques)

        if accountName == 'cancel':
            await self.item_cancel(ques)
            return

        cur.execute(f"SELECT itemName, itemCategory, itemDescription, "
                    f"itemValue, accountName FROM `{accountHolder[1]}` WHERE itemName = '{itemName}'")
        validItemName = cur.fetchone()
        if validItemName is None:
            e.color = discord.Color.red()
            e.title = "Item Not Found"
            e.description = "This item is not registered to your account Please try again!"
            await ques.edit(embed=e)
            return

        e.color = discord.Color.green()
        e.title = f"Item Delete!"
        e.description = f"You have selected **{itemName}**"
        await ques.edit(embed=e)
        confirm = await ctx.prompt("Are you sure you wish to permanently delete this item from your inventory? "
                                   "Its item value will not be reimbursed.")
        if not confirm:
            e.color = discord.Color.red()
            e.title = "Item Deletion Terminated!"
            await ques.edit(embed=e)
            return

        cur.execute(f"DELETE FROM `{accountHolder[1]}` WHERE itemName = '{itemName}'")
        cur.close()
        conn.commit()
        e.title = "Item Removed!"
        await ctx.send(embed=e)

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
        elif reply.lower() == 'edit':
            await self.item_edit(ctx, ques)
        elif reply.lower() == 'show':
            await self.item_show(ctx, ques)
        elif reply.lower() == 'delete':
            await self.item_delete(ctx, ques)
        else:
            e.description = "I did'nt recognize what your sayin'! \nPlease try again!"
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

    @commands.group(name='trade', case_insensitive=False, invoke_without_command=True)
    @commands.guild_only()
    @is_account_holder()
    async def trade_info(self, ctx):
        """Give the trade command info and there use."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @trade_info.command(name='sell')
    async def trade_sell(self, ctx, member: discord.Member, itemName, accountName, price: int):
        """Trade item to other server members"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        # Check buyer has any account or not.
        cur.execute(f"SELECT accountNo FROM accounts WHERE user_id = {ctx.author.id} OR authorize_id = {ctx.author.id}")
        valid = cur.fetchone()
        if valid is None:
            e.color = discord.Color.red()
            e.title = "Trade Failed"
            e.description = f"User **{member.name}** doesnt have any account of his own or authorized!"
            await ctx.send(embed=e)
            return

        # Check seller have that item in his account or not.
        cur.execute(f"SELECT accountNo FROM accounts WHERE user_id = {ctx.author.id} OR authorize_id = {ctx.author.id}")
        sellerAccounts = cur.fetchall()
        accountInNo = 0
        itemDetails = []
        for sellerAccount in sellerAccounts:
            try:
                cur.execute(f"SELECT itemName, itemCategory, itemDescription, itemValue, accountName "
                            f"FROM `{sellerAccount[0]}` WHERE itemName = '{itemName}'")
                itemDetails = cur.fetchone()
                if itemDetails is None:
                    e.color = discord.Color.red()
                    e.title = "Trade Failed"
                    e.description = "Item not found! Please try again!"
                    await ctx.send(embed=e)
                    return
                accountInNo = sellerAccount[0]
            except sqlite3.OperationalError:
                pass

        # Check is that trade is already exists of not.
        with open('src/trade.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        try:
            itemExists = data["trades"][f"{itemName}"]
            e.title = "Trade Failed"
            e.description = "This item is already on sale."
            await ctx.send(embed=e)
            return
        except KeyError:
            pass

        # Add item for trade.
        newTradeTemplate = {f"{itemName}": [accountInNo, ctx.author.id, member.id, f"{accountName}", price]}

        with open('src/trade.json', 'w', encoding='utf-8') as fp:
            data["trades"].update(newTradeTemplate)
            json.dump(data, fp, indent=2)

        # Publish the msg in the channel
        e.color = discord.Color.green()
        e.title = "Item up for Sale!"
        e.description = f"To buy this item use command:\n" \
                        f"`{ctx.prefix}trade buy {itemName} <accountNo>`"
        e.add_field(name="*Item Name:* ", value=f"***{itemDetails[0]}***")
        e.add_field(name="*Item Category:* ", value=f"***{itemDetails[1]}***")
        e.add_field(name="*Item Description:* ", value=f"***{itemDetails[2]}***")
        e.add_field(name="*Item Value:* ", value=f"***{currency(itemDetails[3], grouping=True)}***")
        await ctx.send(f"{member.mention}", embed=e)

    @trade_info.command(name='buy')
    async def trade_buy(self, ctx, itemName, accountName):
        """Buy any active item trades"""
        # Check buyer has any account or not.
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        # Check user have an valid account or not.
        cur.execute(f"SELECT accountNo, accountBal FROM accounts "
                    f"WHERE accountName = '{accountName}' AND "
                    f"(user_id = {ctx.author.id} OR authorize_id = {ctx.author.id})")
        valid = cur.fetchone()
        if valid is None:
            e.color = discord.Color.red()
            e.title = "Trade Failed"
            e.description = f"You doesnt have any account of your own or authorized!"
            await ctx.send(embed=e)
            return

        # Check if item is on sell or not.
        with open('src/trade.json', 'r', encoding='utf-8') as f:
            trade = json.load(f)
        try:
            itemExists = trade["trades"][f"{itemName}"]
        except KeyError:
            e.color = discord.Color.red()
            e.title = "Trade Failed"
            e.description = "This item is on sale."
            await ctx.send(embed=e)
            return

        if itemExists[2] != ctx.author.id:
            e.color = discord.Color.red()
            e.title = "Trade Failed"
            e.description = "Sorry, This item is not meant for you to buy!"
            await ctx.send(embed=e)
            return

        # Check if user have sufficient money to buy or not.
        if float(valid[1]) <= float(itemExists[4]):
            e.color = discord.Color.red()
            e.title = "Trade Failed"
            e.description = f"Sorry, You don't have sufficient balance on your account **{accountName}**"
            await ctx.send(embed=e)
            return

        # Delete item from sellers account.
        cur.execute(f"SELECT itemName, itemCategory, itemDescription, itemValue, accountName "
                    f"FROM `{itemExists[0]}` WHERE itemName = '{itemName}'")
        sellerItem = cur.fetchone()
        cur.execute(f"DELETE FROM `{itemExists[0]}` WHERE itemName = '{itemName}'")
        conn.commit()

        # Add item to buys account.
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS `{valid[0]}`('itemName' TEXT, 'itemCategory' TEXT, "
            f"'itemDescription' TEXT, 'itemValue' REAL, 'accountName' TEXT)")
        cur.execute(f"INSERT INTO `{valid[0]}` (itemName, itemCategory, itemDescription, "
                    f"itemValue, accountName) VALUES ('{sellerItem[0]}', '{sellerItem[1]}', "
                    f"'{sellerItem[2]}', {sellerItem[3]}, '{accountName}')")
        conn.commit()

        # Update buyer accountBal.
        cur.execute(f"SELECT accountBal FROM accounts WHERE accountNo = {itemExists[0]}")
        sellerAccount = cur.fetchone()
        cur.execute(f"UPDATE accounts SET accountBal = {float(valid[1]) - float(itemExists[4])} "
                    f"WHERE accountName = '{accountName}'")
        conn.commit()

        # Calculate Multiplier
        with open('src/itemC.json', encoding='utf-8') as f:
            data = json.load(f)
        multipliers = data["iC"][f"{sellerItem[1]}"]
        addMultiplier = 0
        for multiplier in multipliers:
            cur.execute(f"SELECT multiplier FROM taxType WHERE taxType = '{multiplier}'")
            addOne = cur.fetchone()
            addMultiplier += float(addOne[0])
        multiplier = float(itemExists[4]) * 1.0 - addMultiplier

        # Update seller accountBal.
        cur.execute(f"UPDATE accounts SET accountBal = {float(sellerAccount[0]) - multiplier} "
                    f"WHERE accountNo = {itemExists[0]}")
        conn.commit()

        with open('src/trade.json', 'w') as fp:
            del trade["trades"][f"{itemName}"]
            json.dump(trade, fp, indent=2)

        e.color = discord.Color.green()
        e.title = "Success"
        e.description = f"You successfully bought the item **{itemName}**"
        await ctx.send(embed=e)

    @commands.command(name='inventory')
    @commands.guild_only()
    @is_account_holder()
    async def my_inventory(self, ctx):
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        cur.execute(f"SELECT accountNo, accountName FROM accounts WHERE user_id = {ctx.author.id}")
        accounts = cur.fetchall()
        if len(accounts) <= 0:
            e.title = "Uh.. You do'nt have any bank account."
            await ctx.send(embed=e)
            return

        headers = ["ItemOwner", "ItemCategory", "ItemName", "ItemInfo", "ItemValue", "AccountName"]
        table = TabularData()
        table.set_columns(headers)

        full = []
        for account in accounts:
            try:
                cur.execute(f"SELECT itemName, itemCategory, itemDescription, itemValue, accountName "
                            f"FROM `{account[0]}`")
            except sqlite3.OperationalError:
                e.title = "Item List"
                e.description = "You don't have any item!"
                await ctx.send(embed=e)
                return
            items = cur.fetchall()
            for item in items:
                this = [f"{ctx.author.name}", f"{item[1]}", f"{item[0]}", f"{item[2]}",
                        f"{currency(item[3], grouping=True)}", f"{item[4]}"]
                full.append(this)

        if len(full) <= 0:
            e.title = "Uh.. You do'nt have any items."
            await ctx.send(embed=e)
            return

        table.add_rows(list(r for r in full))
        render = table.render()

        fmt = f'```\n{render}\n```\n*You got {plural(len(full)):item}*'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=discord.File(fp, 'items.txt'))
        else:
            await ctx.send(fmt)

        cur.close()

    @my_inventory.error
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

        with open('src/itemC.json', encoding='utf-8') as f:
            data = json.load(f)

        try:
            exists = data["iC"][f"{itemCategoryName}"]
        except KeyError:
            pass
        else:
            e.description = f"**{itemCategoryName}** already exists"
            await ctx.send(embed=e)
            return

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

        # cur.execute(f"INSERT INTO itemCategory (iCName, iCTaxType) VALUES ('{itemCategoryName}', '{iCTaxType}')")
        # cur.close()
        # conn.commit()
        newItemCategory = {f"{itemCategoryName}": [f"{iCTaxType}"]}
        with open('src/itemC.json', 'w', encoding='utf-8') as fp:
            data["iC"].update(newItemCategory)
            json.dump(data, fp, indent=2)

        e.title = "Item Category Creation Complete!"
        e.description = f"**{itemCategoryName}** added!"
        await ques.edit(embed=e)

    @iC.command(name='delete')
    async def iC_delete(self, ctx, *, itemCategoryName):
        """Creates a new item category called itemcategory_name"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        with open('src/itemC.json', encoding='utf-8') as f:
            data = json.load(f)

        try:
            valid = data["iC"][f"{itemCategoryName}"]
        except KeyError:
            e.title = 'Item Category Terminated!'
            e.description = f"**{itemCategoryName}** is not any itemCategory so far! Please try again!"
            await ctx.edit(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to remove itemCategory called "
                                   f"**{itemCategoryName}**")
        if not confirm:
            e.title = 'Item Category Terminated!'
            e.description = f"Removing of **{itemCategoryName}** Terminated at the end!"
            await ctx.edit(embed=e)
            return

        with open('src/itemC.json', 'w', encoding='utf-8') as fp:
            del data["iC"][f"{itemCategoryName}"]
            json.dump(data, fp, indent=2)

        e.title = "Item Category Delete Successfully!"
        await ctx.send(embed=e)

    @iC.command(name='add')
    async def iC_add(self, ctx, itemCategoryName, taxType):
        """This command will add any taxType to an existing ItemCategory!"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        with open('src/itemC.json', encoding='utf-8') as f:
            data = json.load(f)

        try:
            valid = data["iC"][f"{itemCategoryName}"]
        except KeyError:
            e.title = 'Item Category Terminated!'
            e.description = f"**{itemCategoryName}** is not any itemCategory so far! Please try again!"
            await ctx.edit(embed=e)
            return

        cur.execute(f"SELECT taxType FROM taxType WHERE taxType = '{taxType}'")
        validTaxType = cur.fetchone()
        if validTaxType is None:
            e.description = f"**{taxType}** is not a valid tax type! Please try again!"
            await ctx.send(embed=e)
            return

        taxTypes = data["iC"][f"{itemCategoryName}"]
        if taxType in taxTypes:
            e.description = f"**{taxType}** is already added to **{itemCategoryName}**"
            await ctx.send(embed=e)
            return

        with open('src/itemC.json', 'w', encoding='utf-8') as fp:
            data["iC"][f"{itemCategoryName}"].append(taxType)
            json.dump(data, fp, indent=2)
        e.title = "Success!"
        e.description = f"**{taxType}** added to **{itemCategoryName}**"
        await ctx.send(embed=e)

    @iC.command(name='remove')
    async def iC_remove(self, ctx, itemCategoryName, taxType):
        """This command will able to remove the existing tax types from any item."""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        with open('src/itemC.json', encoding='utf-8') as f:
            data = json.load(f)

        try:
            valid = data["iC"][f"{itemCategoryName}"]
        except KeyError:
            e.title = 'Item Category Terminated!'
            e.description = f"**{itemCategoryName}** is not any itemCategory so far! Please try again!"
            await ctx.edit(embed=e)
            return

        taxTypes = data["iC"][f"{itemCategoryName}"]
        if taxType not in taxTypes:
            e.description = f"**{taxType}** is not added to **{itemCategoryName}** yet!"
            await ctx.send(embed=e)
            return

        with open('src/itemC.json', 'w', encoding='utf-8') as fp:
            data["iC"][f"{itemCategoryName}"].remove(taxType)
            json.dump(data, fp, indent=2)
        e.title = "Success!"
        e.description = f"**{taxType}** removed from **{itemCategoryName}**"
        await ctx.send(embed=e)

    @iC.command(name='list')
    async def iC_list(self, ctx):
        """Give you the list of all the itemCategory and there taxTypes."""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        with open('src/itemC.json', encoding='utf-8') as f:
            data = json.load(f)

        msg = ""
        if len(data["iC"]) <= 0:
            e.title = "Item Category List!"
            e.description = "There arne't any category to see!"
            await ctx.send(embed=e)
            return
        for category in data["iC"]:
            taxTypes = data["iC"][category]
            taxes = ', '.join(taxTypes)
            msg += f"{category} - {taxes}\n"

        e.title = "Item Category List!"
        e.description = f"```{msg}```"
        await ctx.send(embed=e)

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
