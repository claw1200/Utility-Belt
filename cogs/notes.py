import discord
from core import Cog, Context, models

async def note_write(ctx : Context, note_title, note_content):
    # Create a new note
    note = {
        note_title: note_content
    }

    user = await models.UserModel.get_or_none(user_id = ctx.author.id)
    if user:
        user.notes = {**user.notes, **note}
        await user.save()
    else:
        await models.UserModel.update_or_create(
            user_id=ctx.author.id,
            user_name=ctx.author.name,
            user_discriminator=ctx.author.discriminator,
            notes=note,
            baned=False,
            commands_used=1
        )

async def get_notes(ctx : Context):
    # Return a list of note titles for selection
    user = await models.UserModel.get_or_none(user_id = ctx.author.id)
    if user:
        # return a dictionary of note titles and content
        notes = user.notes.items()
        return notes
    else:
        return None
    
async def note_delete(ctx : Context, note_title):
    # Delete a note
    user = await models.UserModel.get_or_none(user_id = ctx.author.id)
    if user:
        notes = user.notes
        if note_title in notes:
            del notes[note_title]
            await user.save()
            return True
        else:
            return False
    else:
        return False
    

class NoteSelect(discord.ui.Select):
    def __init__(self, notes) -> None:
        super().__init__(
            placeholder="Choose a note",
            options=[
                discord.SelectOption(
                    label=note[0], # Title
                    description=note[1][:100]
                )
                for note in notes
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        options = self.options
        note_title = interaction.data["values"][0]
        assert isinstance(note_title, str)
        for option in options:
            if option.label == note_title:
                note_content = option.description
                break
        
        # find which element in the list has value=note_title        
        embed = discord.Embed(
            title=note_title,
            description=note_content,
            color=0x5865F2,
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

class Notes(Cog):
    """
    Notes commands
    """

    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="note",
        description="Write a note",
    )
    @discord.option(
        "note_title",
        description="The title of the note",
        type=str
    )
    @discord.option(
        "note_content",
        description="The content of the note",
        type=str
    )

    async def note_write_command(self, ctx: Context, note_title: str, note_content: str):
        """Write a note"""
        await ctx.defer()
        await note_write(ctx, note_title, note_content)
        await ctx.respond(content="Note written")


    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="note-view",
        description="View a note",
    )

    async def note_view_command(self, ctx: Context):
        """View a note"""
        await ctx.defer()
        assert self.bot.user
        embed = discord.Embed(
            title="Notes",
            description=(
                "Choose a note from the dropdown below to see the content."
            ),
            colour=0x5865F2,
        )
        embed.set_thumbnail(url=ctx.author.avatar.url)
        notes = await get_notes(ctx)
        if notes:
            await ctx.respond(embed=embed, view=discord.ui.View(NoteSelect(notes))
            )
        else:
            await ctx.respond(content="No notes found")

    
    @discord.slash_command(
        integration_types={
        discord.IntegrationType.guild_install,
        discord.IntegrationType.user_install,
        },
        name="note-delete",
        description="Delete a note",
    )
    @discord.option(
        "note_title",
        description="The title of the note",
        type=str
    )

    async def note_delete_command(self, ctx: Context, note_title: str):
        """Delete a note"""
        await ctx.defer()
        if await note_delete(ctx, note_title):
            await ctx.respond(content="Note deleted")
        else:
            await ctx.respond(content="Note not found")

