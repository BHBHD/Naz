from discord.ext import commands
from datetime import datetime
import configparser
import traceback
import discord
import sys

config = configparser.ConfigParser()
config.read('config.ini')


class ErrorCog(commands.Cog, name='Error'):
    """ Error Handling """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        e = discord.Embed(color=discord.Color.red())
        e.timestamp = datetime.utcnow()
        e.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        try:
            if isinstance(error, commands.CommandNotFound):
                pass
            elif isinstance(error, commands.CommandOnCooldown):
                e.description = str(error)
                await ctx.send(embed=e)
            elif isinstance(error, commands.NoPrivateMessage):
                e.description = 'This command cannot be used in private messages.'
                await ctx.send(embed=e)
            elif isinstance(error, commands.DisabledCommand):
                e.description = 'Sorry. This command is disabled and cannot be used.'
                await ctx.send(embed=e)
            elif isinstance(error, commands.ArgumentParsingError):
                e.description = str(error)
                await ctx.send(embed=e)
            elif isinstance(error, commands.MissingRequiredArgument):
                e.description = str(error)
                await ctx.send(embed=e)
            elif isinstance(error, commands.CheckFailure):
                pass
            elif isinstance(error, RuntimeError):
                e.description = 'Sorry, There is a problem with RunTime! Please try again later.'
                await ctx.send(embed=e)
            elif isinstance(error, discord.Forbidden):
                e.description = 'Sorry, I cannot do this task since I don\'t have enough permissions to do this!'
                await ctx.send(embed=e)
            elif isinstance(error, commands.CommandInvokeError):
                original = error.original
                if not isinstance(original, discord.HTTPException):
                    print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
                    traceback.print_tb(original.__traceback__)
                    print(f'{original.__class__.__name__}: {original}', file=sys.stderr)
            else:
                e.title = f'Error in `{ctx.command}`'
                e.description = f'{ctx.command.qualified_name} {ctx.command.signature} \n{error}'
                await ctx.send(embed=e)
        except Exception as error:
            print(f'A error has occur : {error}')


def setup(bot):
    bot.add_cog(ErrorCog(bot))
