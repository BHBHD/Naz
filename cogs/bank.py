from .utils.formats import TabularData, plural
from configparser import ConfigParser
from discord.ext import commands
from datetime import datetime
from locale import currency
from random import randint
import sqlite3
import asyncio
import discord
import locale
import re
import io

conn = sqlite3.connect('src/naz.db')
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS accounts ('user_id' INT, 'accountType' TEXT, 'accountName' TEXT, "
               "'accountReg' TEXT, 'accountNo' INT, 'accountBal' INT, 'authorize_id' INT, 'staffEmbedID' INT)")
cursor.close()
conn.commit()

parser = ConfigParser()
parser.read('config.ini')
patten = re.compile(r"^[A-Za-z0-9_]*$")
accountTypeList = ["business", "personal", "nonprofit", "trust"]
locale.setlocale(locale.LC_ALL, '')

ADMIN_ROLE = parser.getint('server', 'admin-role-id')
REQUEST_CHANNEL_ID = parser.getint('server', 'request-channel-id')
REQUEST_PENDING_CHANNEL_ID = parser.getint('server', 'request-pending-channel-id')
REPORT_CHANNEL_ID = parser.getint('server', 'report-channel-id')

staff_reactions = ('✅', '❎')


def is_request_channel():
    def predicate(ctx):
        if ctx.guild is None:
            return False
        if ctx.channel.id == REQUEST_CHANNEL_ID:
            return True
        for x in ctx.author.roles:
            if x.id == ADMIN_ROLE:
                return True
        return False
    return commands.check(predicate)


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
            if ctx.author.guild_permissions.administrator:
                return True
        return False
    return commands.check(predicate)


class Bank(commands.Cog, name='Bank'):
    """"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='request')
    @commands.guild_only()
    @is_request_channel()
    async def requests(self, ctx, accountType: str = None):
        """Requests a bank account"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        if accountType.lower() in accountTypeList:
            e.title = "**Request Form:**"
            e.description = f"You have successfully requested a **{accountType}** banking account.\n" \
                            f"Please fill in your unique preferred banking account name below.\n" \
                            f"Type down its name (you have **1** hour)."
            ask = await ctx.author.send(embed=e)
        else:
            e.title = "**Request**"
            e.description = f"You need to say the type of account you want correctly\n" \
                            f"(`business`, `personal`, `nonprofit` or `trust`). Not *{accountType}*!"
            await ctx.send(embed=e)
            return

        def check_msg(m):
            return ctx.message.author == m.author and type(m.channel) == discord.DMChannel

        try:
            msg_t = await self.bot.wait_for('message', check=check_msg, timeout=3600.0)
        except asyncio.TimeoutError:
            e.title = "**Request Form:**",
            e.description = f"You took too long to answer to the request. " \
                            f"You need to request again through {ctx.author.mention}."
            await ask.edit(embed=e)
            return

        if not patten.match(msg_t.content):
            e.title = "**Request Form:**",
            e.description = f"Well you cannot use special character or <spaces>. Only `_`'s are allowed in banking" \
                            f"account name `e.g. Barack_Obama_Personal_Account`" \
                            f"You need to request again through {ctx.author.mention}."
            await ask.edit(embed=e)
            return

        cur.execute(f"SELECT user_id FROM accounts WHERE accountReg = '{msg_t.content}'")
        accountReg = cur.fetchone()
        if accountReg is not None:
            e.title = "**Request Form**"
            e.description = f"Unfortunately, That bank account name is already being used by another client.\n" \
                            f"You need to request again through {ctx.author.mention}."
            await ask.edit(embed=e)
            return

        e.title = "**Request Form**"
        e.description = "Thank you for your banking account application. " \
                        "Your entry has been taken under revision by the staff team. " \
                        "You will be notified by Direct Message when your application has been processed."
        await ask.edit(embed=e)

        accountNo = int(str(ctx.message.author.id) + str(randint(0, 1000000)))
        request_receive_channel = self.bot.get_channel(REQUEST_PENDING_CHANNEL_ID)

        e.title = "**New Request**"
        e.description = f"A new application awaits to be processed. " \
                        f"Please process by clicking on one of the submitted emojis."
        e.add_field(name=f"Account Holder: ", value=ctx.author.mention)
        e.add_field(name=f"Account Type: ", value=f"**{accountType}**")
        e.add_field(name=f"Account Name: ", value=f"**{msg_t.content}**")
        e.add_field(name=f"Account Number: ", value=f"**{accountNo}**")
        rrc = await request_receive_channel.send(embed=e)
        for x in staff_reactions:
            await rrc.add_reaction(x)

        cur.execute(f"INSERT INTO accounts (user_id, accountType, accountName, accountReg, accountNo, accountBal, "
                    f"staffEmbedID) VALUES ({ctx.author.id}, '{accountType}', '{msg_t.content}', 'False', "
                    f"{accountNo}, 0.0, {rrc.id})")
        cur.close()
        conn.commit()

    @commands.group(name='bank')
    @commands.guild_only()
    @is_account_holder()
    async def banks(self, ctx):
        """Handle all the banking commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @banks.error
    async def banks_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            e = discord.Embed(color=self.bot.color)
            e.timestamp = datetime.utcnow()
            e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
            e.description = "Only, account holders can have these commands!\n" \
                            f"`{ctx.prefix}request <accountType>` - For open an new account!"
            await ctx.send(embed=e)

    @banks.command(name='check')
    async def bank_check(self, ctx, accountNameOrNo):
        """Checks the amount of money you have in that account"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)} AND "
                        f"(user_id = {ctx.author.id} OR authorize_id = {ctx.author.id})")
        elif ctx.author.guild_permissions.administrator:
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}'")
        else:
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}' AND "
                        f"(user_id = {ctx.author.id} OR authorize_id = {ctx.author.id})")
        account = cur.fetchone()
        cur.close()

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Balance**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you or not Found!"
            await ctx.send(embed=e)
            return

        e.title = "**Account Balance**"
        e.description = f"Your account **'{account[1]}'** has {currency(account[0], grouping=True )}"
        await ctx.send(embed=e)

    @banks.command(name='transfer')
    async def bank_transfer(self, ctx, accountNameOrNo, amount: float, payeeAccountNameOrNo):
        """Transfers amount to another account holder"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)} AND "
                        f"(user_id = {ctx.author.id} OR authorize_id = {ctx.author.id})")
        else:
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}' AND "
                        f"(user_id = {ctx.author.id} OR authorize_id = {ctx.author.id})")
        userAccount = cur.fetchone()

        if userAccount is None:
            e.color = discord.Colour.red()
            e.title = "**Account Transaction**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you!"
            await ctx.send(embed=e)
            return

        if float(amount) > float(userAccount[0]):
            e.title = "**Account Transaction**"
            e.description = f"Your account **'{userAccount[1]}'** does not have enough funds to transfer " \
                            f"{currency(amount, grouping=True)}\n"
            await ctx.send(embed=e)
            return

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountBal, user_id, accountName FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)}")
        else:
            cur.execute(f"SELECT accountBal, user_id, accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}'")
        payeeAccount = cur.fetchone()

        if payeeAccount is None:
            e.title = "**Account Transaction**"
            e.description = f"**{payeeAccountNameOrNo}** is not an account."
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you want to transfer "
                                   f"**{currency(amount, grouping=True)}** to **{payeeAccount[2]}**?")
        if not confirm:
            e.title = "**Account Transaction**"
            e.description = f"Aborted!"
            await ctx.send(embed=e)
            return

        payeeAccountUser = ctx.guild.get_member(int(payeeAccount[1]))

        cur.execute(f"UPDATE accounts SET accountBal = {userAccount[0] - amount} "
                    f"WHERE accountName = '{userAccount[1]}'")
        cur.execute(f"UPDATE accounts SET accountBal = {payeeAccount[0] + amount} "
                    f"WHERE accountName = '{payeeAccount[2]}'")
        cur.close()
        conn.commit()

        e.color = discord.Color.green()
        e.title = "**Account Transaction**"
        e.description = f"Your account **'{accountNameOrNo}'** transferred {currency(amount, grouping=True)} " \
                        f"to {payeeAccountUser.mention}'s **'{payeeAccount[2]}'** banking account."
        await ctx.send(embed=e)

    @banks.command(name='withdraw')
    async def bank_withdraw(self, ctx, accountNameOrNo, amount):
        """Withdraws that amount to cash in that account."""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        report_channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        cur = conn.cursor()

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)} AND user_id = {ctx.author.id}")
        else:
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}' AND user_id = {ctx.author.id}")
        account = cur.fetchone()
        cur.close()

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Withdraw**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you!"
            await ctx.send(embed=e)
            return

        if amount > account[0]:
            e.title = "**Account Withdraw**"
            e.description = f"Your account **'{account[1]}'** does not have enough funds to withdraw " \
                            f"{currency(amount, grouping=True)}."
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you want to withdraw "
                                   f"**{currency(amount, grouping=True)}**?")
        if not confirm:
            e.title = "**Account Withdraw**"
            e.description = f"Aborted!"
            await ctx.send(embed=e)
            return

        cur.execute(f"UPDATE accounts SET accountBal = {account[0] - amount} WHERE accountName = '{account[1]}'")
        handCash = amount

        e.color = discord.Color.green()
        e.title = "**Account Withdraw**",
        e.description = f"You withdrew {currency(amount, grouping=True)} from your account **'{account[1]}'**."
        await ctx.send(embed=e)

        if amount >= 10000:
            e.color = discord.Color.red()
            e.title = "**ALERT**"
            e.description = f"{ctx.author.mention}'s account **'{account[1]}'** " \
                            f"withdrew **{currency(amount, grouping=True)}**."
            await report_channel.send(embed=e)

    @banks.command(name='deposit')
    async def bank_deposit(self, ctx, accountNameOrNo, amount):
        """Deposits that amount in that account"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        report_channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        cur = conn.cursor()
        handCash = 0

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)} AND "
                        f"(user_id = {ctx.author.id} OR authorize_id = {ctx.author.id})")
        else:
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}' AND "
                        f"(user_id = {ctx.author.id} OR authorize_id = {ctx.author.id})")
        account = cur.fetchone()
        cur.close()

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Deposit**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you!"
            await ctx.send(embed=e)
            return

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Deposit**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you!"
            await ctx.send(embed=e)
            return

        if amount > handCash:
            e.title = "**Account Deposit**"
            e.description = f"Your hand balance does not have enough funds to deposit " \
                            f"{currency(amount, grouping=True)}."
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you want to deposit "
                                   f"**{currency(amount, grouping=True)}**?")
        if not confirm:
            e.title = "**Account Deposit**"
            e.description = f"Aborted!"
            await ctx.send(embed=e)
            return

        cur.execute(f"UPDATE accounts SET accountBal = {account[0] + amount} WHERE accountName = '{account[1]}'")

        e.color = discord.Color.green()
        e.title = "**Account Deposit**",
        e.description = f"You deposited {currency(amount, grouping=True)} from your account **'{account[1]}'**."
        await ctx.send(embed=e)

        if amount >= 10000:
            e.color = discord.Color.red()
            e.title = "**ALERT**"
            e.description = f"{ctx.author.mention}'s account **'{account[1]}'** " \
                            f"deposited **{currency(amount, grouping=True)}**."
            await report_channel.send(embed=e)

    @banks.command(name='terminate')
    async def bank_terminate(self, ctx, accountNameOrNo):
        """Deletes that account"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountName FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)} AND user_id = {ctx.author.id}")
        elif ctx.author.guild_permissions.administrator:
            cur.execute(f"SELECT accountBal, accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}'")
        else:
            cur.execute(f"SELECT accountName FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}' AND user_id = {ctx.author.id}")
        account = cur.fetchone()

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Termination**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you or not Found!"
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to terminate **'{account[0]}'**")
        if not confirm:
            e.title = "**Account Termination**"
            e.description = f"Aborted!"
            await ctx.send(embed=e)
            return

        try:
            cur.execute(f"DELETE FROM accounts WHERE accountName = {account[0]}")
            e.color = discord.Color.green()
            e.title = "**Account Termination**"
            e.description = f"Your account **'{account[0]}'** has been terminated"
            await ctx.send(embed=e)
        except sqlite3.OperationalError:
            e.color = discord.Color.red()
            e.title = "**Account Termination**"
            e.description = "Failed! Please contact staff for further assessment!"
            await ctx.send(embed=e)

    @banks.command(name='balance')
    async def bank_balance(self, ctx, accountName, action, amount: float):
        """Only admin command for adding/subtracting/set balance of any account!"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        if not ctx.author.guild_permissions.administrator:
            e.title = "Permissions Error!"
            e.description = "You don't have admin permission to use this command! :D"
            return

        cur.execute(f"SELECT accountBal, accountName FROM accounts "
                    f"WHERE accountName = '{accountName}'")
        account = cur.fetchone()

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Balance**"
            e.description = f"Account **'{accountName}'** not Found!"
            await ctx.send(embed=e)
            return

        if action == '+':
            cur.execute(f"UPDATE accounts SET accountBal = {float(account[0]) + amount} "
                        f"WHERE accountName = '{accountName}'")
            conn.commit()
        elif action == '-':
            cur.execute(f"UPDATE accounts SET accountBal = {float(account[0]) - amount} "
                        f"WHERE accountName = '{accountName}'")
            conn.commit()
        elif action.lower() == 'set':
            cur.execute(f"UPDATE accounts SET accountBal = {amount} WHERE accountName = '{accountName}'")
            conn.commit()
        else:
            e.description = 'Unknown operation, try `+`, `-` or `set`.'
            await ctx.send(embed=e)
            return

        e.title = "**Account Balance**"
        e.description = f"Done!"
        await ctx.send(embed=e)

    @banks.group(name='authorize')
    async def authorization(self, ctx):
        """Authorize other discord member to use some of your bank account commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @authorization.command(name='add')
    async def authorization_add(self, ctx, accountNameOrNo, user: discord.Member):
        """Add authorization to an person."""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountName, authorize_id, accountType FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)} AND user_id = {ctx.author.id}")
        else:
            cur.execute(f"SELECT accountName, authorize_id, accountType FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}' AND user_id = {ctx.author.id}")
        account = cur.fetchone()

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Authorization**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you!"
            await ctx.send(embed=e)
            return

        if account[1] is not None:
            authorizeUser = ctx.guild.get_member(account[1])
            e.color = discord.Colour.red()
            e.title = "**Account Authorization**"
            e.description = f"Your account is already authorized by {authorizeUser.mention}"
            await ctx.send(embed=e)
            return

        if account[2] == 'personal':
            e.color = discord.Colour.red()
            e.title = "**Account Authorization**"
            e.description = f"Account **'{accountNameOrNo}'** is **{account[2]}**, which can't be use to authorize!"
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to give authorization to {user.mention}?")
        if not confirm:
            e.title = "**Account Authorization**"
            e.description = f"Aborted!"
            await ctx.send(embed=e)
            return

        if account[1] is None:
            cur.execute(f"UPDATE accounts SET authorize_id = {user.id} WHERE accountName = '{account[0]}'")
            conn.commit()

            e.color = discord.Colour.green()
            e.title = "**Account Authorization**"
            e.description = f"{user.mention} authorized successfully!"
            await ctx.send(embed=e)
        cur.close()

    @authorization.command(name='remove')
    async def authorization_remove(self, ctx, accountNameOrNo, user: discord.Member):
        """Add authorization to an person."""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()

        if accountNameOrNo.isdigit():
            cur.execute(f"SELECT accountName, authorize_id, accountType FROM accounts "
                        f"WHERE accountNo = {int(accountNameOrNo)} AND user_id = {ctx.author.id}")
        else:
            cur.execute(f"SELECT accountName, authorize_id, accountType FROM accounts "
                        f"WHERE accountName = '{str(accountNameOrNo)}' AND user_id = {ctx.author.id}")
        account = cur.fetchone()

        if account is None:
            e.color = discord.Colour.red()
            e.title = "**Account Authorization**"
            e.description = f"Account **'{accountNameOrNo}'** does'nt belongs to you!"
            await ctx.send(embed=e)
            return

        if account[1] is None:
            e.color = discord.Colour.red()
            e.title = "**Account Authorization**"
            e.description = f"No one is authorized, Therefore no-one to remove!"
            await ctx.send(embed=e)
            return

        if account[2] != 'personal':
            e.color = discord.Colour.red()
            e.title = "**Account Authorization**"
            e.description = f"Account **'{accountNameOrNo}'** is **{account[2]}**, which can't be use to authorize!"
            await ctx.send(embed=e)
            return

        confirm = await ctx.prompt(f"Are you sure that you wants to revoke authorization from {user.mention}?")
        if not confirm:
            e.title = "**Account Authorization**"
            e.description = f"Aborted!"
            await ctx.send(embed=e)
            return

        if account[1] is None:
            cur.execute(f"UPDATE accounts SET authorize_id = {None} WHERE accountName = '{account[0]}'")
            conn.commit()

            e.color = discord.Colour.green()
            e.title = "**Account Authorization**"
            e.description = f"{user.mention} authorized successfully!"
            await ctx.send(embed=e)
        cur.close()

    # ACCOUNT
    @commands.command(name='account', aliases=["accounts"])
    @commands.guild_only()
    async def accounts(self, ctx):
        """Give the account view on a tabular form"""
        e = discord.Embed(color=self.bot.color)
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        cur = conn.cursor()
        cur.execute(f"SELECT accountType, accountName, authorize_id, accountBal FROM accounts "
                    f"WHERE user_id = {ctx.author.id}")
        accounts = cur.fetchall()

        if len(accounts) <= 0:
            e.title = "*Accounts*"
            e.description = "Accounts not found!"
            await ctx.send(embed=e)
            return

        headers = ["ClientName", "AccountType", "AccountName", "ClientType", "Balance"]
        table = TabularData()
        table.set_columns(headers)
        full = []
        for r in accounts:
            this = [f"{ctx.author.name}", f"{r[0]}", f"{r[1]}",
                    f"{'owner' if r[2] is None else 'authorized'}", f"{currency(r[3], grouping=True)}"]
            full.append(this)
            # print(this)

        table.add_rows(list(r for r in full))
        # print(list(r for r in accounts))
        render = table.render()

        fmt = f'```\n{render}\n```\n*You got {plural(len(accounts)):account}*'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
        else:
            await ctx.send(fmt)

        cur.close()

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_reaction_add(self, reaction):
        """This event will call on reaction of a emoji in REQUEST_PENDING_CHANNEL_ID"""
        if reaction.user_id == self.bot.user.id:
            return

        if reaction.channel_id != REQUEST_PENDING_CHANNEL_ID:
            return

        guild = self.bot.get_guild(reaction.guild_id)
        react_user = guild.get_member(reaction.user_id)
        react_channel = guild.get_channel(reaction.channel_id)
        react_msg = await react_channel.fetch_message(reaction.message_id)
        request_role = discord.utils.get(guild.roles, id=ADMIN_ROLE)

        cur = conn.cursor()
        cur.execute(f"SELECT accountReg, accountType, accountName, accountNo, user_id FROM accounts "
                    f"WHERE staffEmbedID = {reaction.message_id}")
        request = cur.fetchone()

        if request is None:
            return

        if request[0] != 'False':
            return

        if request_role not in react_user.roles:
            await react_msg.remove_reaction(reaction.emoji, react_user)
            return

        react = str(reaction.emoji)
        appUser = guild.get_member(request[4])
        requestChannel = guild.get_channel(REQUEST_PENDING_CHANNEL_ID)

        e = discord.Embed()
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        # TODO: EDIT THE REQUEST STATE AFTER ACTION!
        # accountReg, accountType, accountName, accountNo, user_id
        if react == staff_reactions[0]:
            cur.execute(f"UPDATE accounts SET accountReg = 'True' WHERE staffEmbedID = {reaction.message_id}")
            conn.commit()

            e.color = discord.Color.green()
            e.title = "**Request State**"
            e.description = f"{appUser.mention}'s **{request[1]}** banking account called **'{request[2]}'** with " \
                            f"account number **{int(request[3])}** has been approved."
            await requestChannel.send(embed=e)
            await appUser.send(embed=e)
        elif react == staff_reactions[1]:
            cur.execute(f"DELETE FROM accounts WHERE staffEmbedID = {reaction.message_id}")
            conn.commit()

            e.color = discord.Color.red()
            e.title = "**Request State**"
            e.description = f"{appUser.mention}'s **{request[1]}** banking account called **'{request[2]}'** with " \
                            f"account number **{int(request[3])}** has been denied."
            await requestChannel.send(embed=e)
            await appUser.send(embed=e)
        self.bot._prev_events.append("on_raw_reaction_add")


def setup(bot):
    bot.add_cog(Bank(bot))
