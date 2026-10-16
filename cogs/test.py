from cogs.shared.auto_imports import *

class Cog(commands.Cog, name="Test"):

    @slash(default_member_permissions=disnake.Permissions(manage_webhooks=True))
    async def ping(self, interaction: SlashInter):
        """For my own sanity to make sure the bot is working.

        Parameters
        ----------
        interaction: Slash Command Interaction
        """
        await interaction.send("Pong!")
