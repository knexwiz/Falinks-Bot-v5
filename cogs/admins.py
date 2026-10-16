from cogs.shared.auto_imports import *

class Cog(commands.Cog, name="Admin Functions"):

    @slash(default_member_permissions=disnake.Permissions(manage_webhooks=True))
    async def pseudo(self, interaction: SlashInter, role: disnake.Role):
        """Allows you to act as another team role to complete admin functions. Lasts 10 minutes.

        Parameters
        ----------
        interaction: Slash Command Interaction
        role: The team role you want to act as.
        """
        team = Team.pseudo(interaction.author, role)
        if team:
            await interaction.send(f"Now acting as team {team}", ephemeral=True)
        else:
            await interaction.send(f"Didn't find a team for {role}", ephemeral=True)


    @slash(default_member_permissions=disnake.Permissions(manage_webhooks=True))
    async def force_season_refresh(self, interaction: SlashInter):
        """Make manual edits to the season sheet to show immediately. Otherwise, info is cached every 3 hours.

        Parameters
        ----------
        interaction: Slash Command Interaction
        """
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is not None:
            for season in Season.list_by_guild(guild):
                season.recache()
            await interaction.send("Seasons refreshed", ephemeral=True)