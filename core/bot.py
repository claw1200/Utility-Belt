from os import environ, getenv
from traceback import format_exception
import discord
from aiohttp import ClientSession
from discord.ext import commands
from tortoise import Tortoise
from .context import Context
from .models import BotModel, UserModel

class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            allowed_mentions=discord.AllowedMentions.none(),
            auto_sync_commands=False,
            chunk_guilds_at_startup=False,
            help_command=None,
            intents=discord.Intents(
                members=True,
                messages=True,
                message_content=False,
                guilds=True,
            ),
            owner_ids=[512609720885051425],
        )
        self.cache: dict[str, dict] = {"example_list": {}}

    def get_emojis(self, emoji: str) -> discord.Emoji:
        return getenv(emoji)

    async def setup_tortoise(self) -> None:
        await Tortoise.init(
            db_url="sqlite://data/database.db", modules={"models": ["core.models"]}
        )
        await Tortoise.generate_schemas()

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        await self.setup_tortoise()
        return await super().start(token, reconnect=reconnect)

    async def close(self) -> None:
        await Tortoise.close_connections()
        return await super().close()

    async def get_application_context(
        self, interaction: discord.Interaction
    ) -> Context:
        return Context(self, interaction)

    @property
    def http_session(self) -> ClientSession:
        return self.http._HTTPClient__session  # type: ignore # it exists

    async def on_ready(self) -> None:   
        self.errors_webhook = (
            discord.Webhook.from_url(
                webhook_url,
                session=self.http_session,
                bot_token=self.http.token,
            )
            if (webhook_url := getenv("ERRORS_WEBHOOK"))
            else None
        )
        # get the bot data from the database
        bot_data = await BotModel.get_bot_presence()
        if bot_data and bot_data['presence']:
            activity = discord.CustomActivity(
                name=bot_data['presence']['presence_text']
            )
            await self.change_presence(activity=activity)
            print (f"Presence updated to watching {bot_data['presence']['presence_text']}")


        print(self.user, "is ready")

    async def on_application_command_error(self, ctx: Context, error: Exception):
        if isinstance(error, discord.ApplicationCommandInvokeError):
            if isinstance((error := error.original), discord.HTTPException):
                message = (
                    "An HTTP exception has occurred: "
                    f"{error.status} {error.__class__.__name__}"
                )
                if error.text:
                    message += f": {error.text}"
                return await ctx.respond(message)
            
            if self.errors_webhook and not isinstance(error, discord.DiscordException):
                await ctx.respond(
                    "An unexpected error has occurred and the developer has been notified.\n"
                    "In the meantime, consider joining the support server.",
                    view=discord.ui.View(
                        discord.ui.Button(
                            label="Support", url="https://discord.gg/Kgdu8J6F2y"
                        ),
                        discord.ui.Button(
                            label="GitHub",
                            url="https://github.com/CLAW1200/Utility-Belt",
                        ),
                    ),
                )
                header = f"Command: `/{ctx.command.qualified_name}`"
                if ctx.guild is not None:
                    header += f" | Guild: `{ctx.guild.name} ({ctx.guild_id})`"
                
                # Add command options to the error message
                options = []
                for option in ctx.interaction.data.get('options', []):
                    if isinstance(option, dict):
                        options.append(f"{option.get('name')}: {option.get('value')}")
                    elif isinstance(option, str):
                        options.append(option)
                options_str = " | ".join(options)

                #put error into file and send it to the webhook
                with open("lastError.log", "w") as f:
                    # ```\n{''.join(format_exception(type(error), error, error.__traceback__))}```
                    f.write(f"{header}\nOptions: `{options_str}`\n{''.join(format_exception(type(error), error, error.__traceback__))}")
                
                return await self.errors_webhook.send(
                    f"{header}\nOptions: `{options_str}`\n",
                    file=discord.File("lastError.log"),
                )
            
        await ctx.edit(
            content="",
            embed=discord.Embed(
                title=error.__class__.__name__,
                description=str(f"{error}"),
                color=discord.Color.red(),
            ),
        )

    async def on_application_command(self, ctx: discord.ApplicationContext):
        # print the command used in the console with the options
        print(f"{ctx.author} ran /{ctx.command.qualified_name}")
        # find user in the database and add 1 to the commands_used for that user
        user = await UserModel.get_or_none(user_id=ctx.author.id)
        if user:
            user.commands_used += 1
            await user.save()
        else:
            await UserModel.update_or_create(
                user_id=ctx.author.id,
                user_name=ctx.author.name,
                user_discriminator=ctx.author.discriminator,
                notes={},
                baned=False,
                commands_used=1,
            )

    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        if before.content != after.content:
            await self.process_commands(after)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        pass
    
    def run(
        self, debug: bool = False, cogs: list[str] | None = None, sync: bool = False
    ) -> None:
        self.load_extensions("jishaku", *cogs or ("cogs", "cogs.task"))
        if sync:
            async def on_connect() -> None:
                await self.sync_commands(delete_existing=not debug)
                print("Synchronized commands.")

            self.on_connect = on_connect

        environ.setdefault("JISHAKU_NO_UNDERSCORE", "1")
        if debug:
            return super().run(getenv("DEBUG_TOKEN", getenv("TOKEN")))

        environ.setdefault("JISHAKU_HIDE", "1")
        super().run(getenv("TOKEN"))
