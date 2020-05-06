import collections
import discord
from discord.ext import commands
import asyncio
import random

bot = commands.Bot(command_prefix='!')
token_file = "token.txt"

with open(token_file) as f:
    TOKEN = f.read()

accounts_data = {"id" : [], "account type" : [], "account name" : [], "account registered" : [], "account registered id" : [], "balance": [], "items": [], "item category": [], "item info": [], "item value": []}
item_types = {}
tax_types = {}


def in_nested_list(my_list, item):
    if item in my_list:
        return True
    else:
        return any(in_nested_list(sublist, item) for sublist in my_list if isinstance(sublist, list))


def ids(ids):
    global accounts_data
    if ids not in accounts_data["id"]:
        accounts_data["id"].append(ids)                     # user_id
        accounts_data["account type"].append([])            # accountType
        accounts_data["account name"].append([])            # accountName
        accounts_data["account registered"].append([])      # accountReg
        accounts_data["account registered id"].append([])   # accountNo
        accounts_data["balance"].append([])                 # accountBal
        accounts_data["items"].append([])                   #
        accounts_data["item category"].append([])
        accounts_data["item info"].append([])
        accounts_data["item value"].append([])


@bot.command()
async def item(ctx, account_name=None, mode=None, item_name=None, item_type=None, item_info=None, item_value=None):
    global accounts_data
    global item_types
    me = ctx.message.author

    # ERROR HANDLER
    try:
        index_me = accounts_data["id"].index(me.id)
        index_in_me = accounts_data["account name"][index_me].index(
            account_name)
    except ValueError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid Account name."))
        return 0
    if accounts_data["account registered"][index_me][index_in_me] == False:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="Your account **'{}'** hasn't been accepted yet".format(account_name)))
        return 0
    if mode != "create" and mode != "edit" and mode != "show" and mode != "delete":
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid action."))
        return 0
    if mode == "create" or mode == "edit":
        if item_name not in accounts_data["items"][index_me][index_in_me] and mode == "edit":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That item does not exist in your account."))
            return 0
        if item_name == None and mode == "create":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to give a name to the item."))
            return 0
        if in_nested_list(accounts_data["items"], item_name) and mode == "create":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That item already exists."))
            return 0
        if item_type == None and mode == "edit":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to update the item information to something."))
            return 0
        if item_type not in item_types.keys() and mode == "create":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That item type does not exist."))
            return 0
        if item_info == None and mode == "create":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce the item information."))
            return 0
        if mode == "create":
            try:
                item_value = float(item_value)
                if item_value <= 0:
                    raise ValueError
            except ValueError:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid price for the item."))
                return 0
            except TypeError:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid price for the item."))
                return 0
    if mode == "show" or mode == "delete":
        if item_name == None:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need type the name of the item you want to {}.".format(mode)))
            return 0
        if item_name not in accounts_data["items"][index_me][index_in_me]:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That item does not exist in your account."))
            return 0

    # ACTUAL PROGRAM
    if mode == "create":
        if accounts_data["balance"][index_me][index_in_me] >= item_value:
            accounts_data["balance"][index_me][index_in_me] -= item_value
            accounts_data["items"][index_me][index_in_me].append(item_name)
            accounts_data["item category"][index_me][index_in_me].append(
                item_type)
            accounts_data["item value"][index_me][index_in_me].append(
                item_value)
            accounts_data["item info"][index_me][index_in_me].append(item_info)
            await ctx.send(embed=discord.Embed(title="**New item**", description="You just obtained a **'{}'** for {}$.".format(item_name, item_value)))
            return 0
        else:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You don't have enough money to get that item."))
            return 0
    index_in_in_me = accounts_data["items"][index_me][index_in_me].index(
        item_name)
    if mode == "edit":
        accounts_data["item info"][index_me][index_in_me][index_in_in_me] = item_type
        await ctx.send(embed=discord.Embed(title="**Item changed**", description="You just changed an item info."))
        return 0
    if mode == "show":
        embed = discord.Embed(title="**Item data**",
                              description="Item information.")
        embed.add_field(name="Item name", value=item_name)
        embed.add_field(name="Item category",
                        value=accounts_data["item category"][index_me][index_in_me][index_in_in_me])
        embed.add_field(name="Item description",
                        value=accounts_data["item info"][index_me][index_in_me][index_in_in_me])
        embed.add_field(name="Item value", value="$"+str(
            accounts_data["item value"][index_me][index_in_me][index_in_in_me]))
        await ctx.send(embed=embed)
        return 0
    if mode == "delete":
        await ctx.send(embed=discord.Embed(title="**Deleted item**", description="You just deleted **'{}'** for you account **'{}'**.".format(item_name, account_name)))
        del accounts_data["items"][index_me][index_in_me][index_in_in_me]
        del accounts_data["item category"][index_me][index_in_me][index_in_in_me]
        del accounts_data["item info"][index_me][index_in_me][index_in_in_me]
        del accounts_data["item value"][index_me][index_in_me][index_in_in_me]


@bot.command()
async def myitems(ctx):
    try:
        index_in = accounts_data["id"].index(ctx.message.author.id)
        if accounts_data["account name"][index_in] == []:
            raise ValueError
    except ValueError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You have no accounts."))
        return 0
    total = []
    accoun = ""
    for i in accounts_data["items"][index_in]:
        total += i
        indexxxxx = accounts_data["items"][index_in].index(i)
        j = accounts_data["account name"][index_in][indexxxxx]
        for k in range(len(i)):
            accoun += j
            accoun += "\n"
    if total == []:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You have no items."))
        return
    embed = discord.Embed(title="**Items details**",
                          description="Detail of {} items.".format(len(total)))
    embed.add_field(name="Item name", value="\n".join(total))
    total = []
    for i in accounts_data["item category"][index_in]:
        total += i
    embed.add_field(name="Item type", value="\n".join(total))
    total = []
    for i in accounts_data["item info"][index_in]:
        total += i
    embed.add_field(name="Item description", value="\n".join(total))
    total = []
    for i in accounts_data["item value"][index_in]:
        total += ["$" + str(j) for j in i]
    embed.add_field(name="Item value", value="\n".join(total))
    embed.add_field(name="Account", value=accoun)
    await ctx.send(embed=embed)


# ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS
# ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS
# ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS
# ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS    ADMIN COMMANDS

@bot.command()
async def bankadmin(ctx, user=None, account_name=None, mode=None, ammount=None):
    global accounts_data
    admin_role = discord.utils.get(
        ctx.message.guild.roles, id=699281003893489695)
    if admin_role in ctx.message.author.roles:
        try:
            me = bot.get_user(int(user[3:-1]))
        except ValueError:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to tag a valid user."))
            return 0
        except TypeError:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to tag a valid user."))
            return 0

        # ERROR HANDLER
        try:
            index_me = accounts_data["id"].index(me.id)
            index_in_me = accounts_data["account name"][index_me].index(
                account_name)
        except ValueError:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid Account name."))
            return 0
        except AttributeError:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to tag a valid user."))
            return 0
        if accounts_data["account registered"][index_me][index_in_me] == False:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="{} account **'{}'** hasn't been accepted yet".format(me.mention, account_name)))
            return 0
        if mode != "check" and mode != "withdraw" and mode != "deposit" and mode != "terminate":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid action."))
            return 0
        if mode == "deposit" or mode == "withdraw":
            try:
                ammount = float(ammount)
                if ammount <= 0.0:
                    raise ValueError
            except ValueError:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid ammount you are going to *{}* into {}'s account **'{}'**.".format(mode, me.mention, account_name)))
                return 0
            except TypeError:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid ammount you are going to *{}* into {}'s account **'{}'**.".format(mode, me.mention, account_name)))
                return 0
        # ACUAL PROGRAM

        if mode == "check":
            await ctx.send(embed=discord.Embed(title="**Account Balance**", description="{}'s account **'{}'** has ${}".format(me.mention, account_name, accounts_data["balance"][index_me][index_in_me])))
            return 0
        if mode == "terminate":
            await ctx.send(embed=discord.Embed(title="**Account Termination**", description="{}'s account **'{}'** has been terminated".format(me.mention, account_name)))
            del accounts_data["account type"][index_me][index_in_me]
            del accounts_data["account name"][index_me][index_in_me]
            del accounts_data["account registered"][index_me][index_in_me]
            del accounts_data["account registered id"][index_me][index_in_me]
            del accounts_data["balance"][index_me][index_in_me]
            del accounts_data["items"][index_me][index_in_me]
            del accounts_data["item category"][index_me][index_in_me]
            del accounts_data["item value"][index_me][index_in_me]
            del accounts_data["item info"][index_me][index_in_me]
            return 0
        if mode == "withdraw":
            if accounts_data["balance"][index_me][index_in_me] >= ammount:
                await ctx.send(embed=discord.Embed(title="**Account Withdraw**", description="You withdrew ${} from {}'s account **'{}'**.".format(ammount, me.mention, account_name)))
                accounts_data["balance"][index_me][index_in_me] -= ammount
            else:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="{}'s account **'{}'** does not have enought funds to withdraw {}$.".format(me.mention, account_name, ammount)))
        if mode == "deposit":
            await ctx.send(embed=discord.Embed(title="**Account Deposit**", description="You deposited ${} to {}'s account **'{}'**.".format(ammount, me.mention, account_name)))
            accounts_data["balance"][index_me][index_in_me] += ammount
    else:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You don't have permission to use that command!"))


@bot.command()
async def taxtype(ctx, mode=None, name=None, data=None):
    global tax_types
    admin_role = discord.utils.get(
        ctx.message.guild.roles, id=699281003893489695)
    if admin_role in ctx.message.author.roles:
        if mode == None:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to select a mode."))
            return 0
        if mode != "new" and mode != "edit" and mode != "delete":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That mode does not exist."))
            return 0
        if mode == "new" and name in tax_types.keys():
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That tax type already exists."))
            return 0
        if name not in tax_types.keys() and mode != "new":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That tax type does not exist."))
            return 0
        if data == None and mode != "delete":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="The tax value need to be numerical."))
            return 0

        if mode == "new" or mode == "edit":
            try:
                if float(data) > 1.0 or float(data) <= 0.0:
                    raise ValueError
                tax_types[name] = float(data)
                await ctx.send(embed=discord.Embed(title="**New/Edited tax type**", description="You added or edited the tax **'{}'** to **{}**.".format(name, data)))
                return 0
            except ValueError:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="The tax value need to be numerical lower or equal than 1 and higher than 0."))
                return 0
        if mode == "delete":
            await ctx.send(embed=discord.Embed(title="**Tax type deleted**", description="You deleted the tax type **'{}'**.".format(name)))
            del tax_types[name]
            return 0
    else:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You don't have permission to use that command!"))


@bot.command()
async def itemcategory(ctx, mode=None, name=None, data=None):
    global item_types
    global tax_types
    admin_role = discord.utils.get(
        ctx.message.guild.roles, id=699281003893489695)
    if admin_role in ctx.message.author.roles:
        if mode == None:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to select a mode."))
            return 0
        if mode != "new" and mode != "delete" and mode != "add" and mode != "remove":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That mode does not exist."))
            return 0
        if mode == "new" and name in item_types.keys():
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That item type already exists."))
            return 0
        if name not in item_types.keys() and mode != "new":
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="That item type does not exist."))
            return 0
        if name == None:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce the name of the item type."))
            return 0
        if mode == "add":
            if data == None:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to atribute a tax to an item category."))
                return 0
            if data not in tax_types.keys():
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to atribute an existing tax to the item category."))
                return 0
            if data in item_types[name]:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="That item already has that tax type."))
                return 0
        if mode == "remove":
            if data == None:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to remove a tax to an item category."))
                return 0
            if data not in item_types[name]:
                await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to remove an existing tax on the selected item category."))
                return 0

        if mode == "new":
            item_types[name] = []
            await ctx.send(embed=discord.Embed(title="**New item category created**", description="You created the item category **'{}'**.".format(name)))
            return 0
        if mode == "delete":
            del item_types[name]
            await ctx.send(embed=discord.Embed(title="**Item category deleted**", description="You deleted the item category **'{}'**.".format(name)))
            return 0
        if mode == "add":
            item_types[name].append(data)
            await ctx.send(embed=discord.Embed(title="**Tax type added to item type**", description="You added the tax type **'{}'** to the item category **'{}'**.".format(data, name)))
            return 0
        if mode == "remove":
            item_types[name].remove(data)
            await ctx.send(embed=discord.Embed(title="**Tax type removed on item type**", description="You removed the tax type **'{}'** from the item category **'{}'**.".format(data, name)))
            return 0
    else:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You don't have permission to use that command!"))


@bot.command()
async def taxtypelist(ctx):
    global tax_types
    admin_role = discord.utils.get(
        ctx.message.guild.roles, id=699281003893489695)
    if admin_role in ctx.message.author.roles:
        if tax_types == {}:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="There are no tax types."))
            return 0
        embed = discord.Embed(title="**Tax types list**",
                              description="List of {} tax types".format(len(tax_types.keys())))
        embed.add_field(name="Tax type name",
                        value="\n".join(tax_types.keys()))
        embed.add_field(name="Tax value", value="\n".join(
            [str(tax_types[j]) for j in tax_types.keys()]))
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You don't have permission to use that command!"))


@bot.command()
async def itemcategorylist(ctx):
    global item_types
    admin_role = discord.utils.get(
        ctx.message.guild.roles, id=699281003893489695)
    if admin_role in ctx.message.author.roles:
        if item_types == {}:
            await ctx.send(embed=discord.Embed(title="**ERROR**", description="There are no item categories."))
            return 0
        embed = discord.Embed(title="**Item category list**",
                              description="List of {} item categories".format(len(item_types.keys())))
        embed.add_field(name="Item category name",
                        value="\n".join(item_types.keys()))
        l = [item_types[i] for i in item_types.keys()]
        total = ""
        for i in l:
            total += "[" + ", ".join(["'" + j + "'" for j in i]) + "]"
            total += "\n"
        embed.add_field(name="Item category taxes", value=total)
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You don't have permission to use that command!"))


@bot.command()
async def trade(ctx, account_name=None, item_name=None, item_to_from=None, ammount=None):
    global accounts_data
    me = ctx.message.author

    # ERROR HANDLER
    try:
        index_me = accounts_data["id"].index(me.id)
        index_in_me = accounts_data["account name"][index_me].index(
            account_name)
    except ValueError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You need to introduce a valid Account name."))
        return 0
    if accounts_data["account registered"][index_me][index_in_me] == False:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="Your account **'{}'** hasn't been accepted yet".format(account_name)))
        return 0
    try:
        index_in_in_me = accounts_data["items"][index_me][index_in_me].index(
            item_name)
    except ValueError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="You don't have that item in your account **'{}'**.".format(account_name)))
        return 0
    try:
        index_other = accounts_data["id"].index(int(item_to_from[3:-1]))
    except ValueError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="That user does not exist."))
        return 0
    except TypeError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="That user does not exist."))
        return 0
    try:
        ammount = float(ammount)
        if ammount <= 0:
            raise ValueError
    except ValueError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="The ammount you are selling for need to be numerical and > 0."))
        return 0
    except TypeError:
        await ctx.send(embed=discord.Embed(title="**ERROR**", description="The ammount you are selling for need to be numerical and > 0."))
        return 0

    item_to_from_obj = bot.get_user(int(item_to_from[3:-1]))

    await ctx.send(embed=discord.Embed(title="**New Trade**", description="You are selling **'{}'** to {} for ${}".format(item_name, item_to_from_obj.mention, ammount)))
    await item_to_from_obj.send(embed=discord.Embed(title="**New Trade**", description="{} is selling to you **'{}'** for ${} type the bank account you want the item to be transfered to accept the trade and *'deny'* to deny the trade you have 1 hour".format(item_to_from_obj.mention, item_name, ammount)))

    def check_msg(m):
        return item_to_from_obj == m.author and type(m.channel) == discord.DMChannel
    try:
        msg_t = await bot.wait_for('message', check=check_msg, timeout=3600.0)
    except asyncio.TimeoutError:
        await item_to_from_obj.send(embed=discord.Embed(title="**Trade**", description="You took to long to respond to the trade. It is ***CANCELED***"))
        return 0
    if msg_t.content == "deny":
        await item_to_from_obj.send(embed=discord.Embed(title="**Trade denied**", description="The trade as been ***CANCELED***"))
        return 0
    else:
        try:
            index_in_other = accounts_data["account name"][index_other].index(
                msg_t.content)
        except ValueError:
            await item_to_from_obj.send(embed=discord.Embed(title="**ERROR**", description="None of your accounts have that name. The trade has been ***CANCELED***."))
            return 0
        if accounts_data["account registered"][index_other][index_in_other] == False:
            await item_to_from_obj.send(embed=discord.Embed(title="**ERROR**", description="Your account **'{}'** hasn't been accepted yet".format(msg_t.content)))
            return 0
        if accounts_data["balance"][index_other][index_in_other] < ammount:
            await item_to_from_obj.send(embed=discord.Embed(title="**ERROR**", description="Your account **'{}'** does not have enought money for the trade ***CANCELED***".format(msg_t.content)))
            return 0
        else:
            await item_to_from_obj.send(embed=discord.Embed(title="**Trade Accepted**", description="You just bought {} for ${} from {}".format(item_name, ammount, item_to_from_obj.mention)))
            accounts_data["balance"][index_other][index_in_other] -= ammount
            for i in item_types[accounts_data["item category"][index_me][index_in_me][index_in_in_me]]:
                ammount *= tax_types[i]
            accounts_data["balance"][index_me][index_in_me] += ammount
            accounts_data["items"][index_other][index_in_other].append(
                accounts_data["items"][index_me][index_in_me][index_in_in_me])
            accounts_data["item category"][index_other][index_in_other].append(
                accounts_data["item category"][index_me][index_in_me][index_in_in_me])
            accounts_data["item info"][index_other][index_in_other].append(
                accounts_data["item info"][index_me][index_in_me][index_in_in_me])
            accounts_data["item value"][index_other][index_in_other].append(
                accounts_data["item value"][index_me][index_in_me][index_in_in_me])
            accounts_data["items"][index_me][index_in_me].pop(index_in_in_me)
            accounts_data["item category"][index_me][index_in_me].pop(
                index_in_in_me)
            accounts_data["item info"][index_me][index_in_me].pop(
                index_in_in_me)
            accounts_data["item value"][index_me][index_in_me].pop(
                index_in_in_me)


async def nice():
    while(True):
        print(accounts_data)
        print(item_types)
        print(tax_types)
        await asyncio.sleep(60.0)


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------------')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("[{}help] Stonks".format(bot.command_prefix)))
    await nice()


bot.run(TOKEN)
