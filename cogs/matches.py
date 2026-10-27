from cogs.shared.auto_imports import *


class Cog(commands.Cog, name="Matches"):

    def __init__(self, bot):
        self.bot = bot
        self.matches_to_post: list[Match] = []


    @slash(default_member_permissions=disnake.Permissions(manage_webhooks=True))
    async def post_weekly_matches(self, interaction: SlashInter, week: int):
        """Posts the matches for a given week to the Matches channel category.

        Parameters
        ----------
        interaction: Slash Command Interaction
        week: The week to post matches for.
        """
        guild = interaction.guild
        if not guild:
            await interaction.send("You should only use this is a server...", ephemeral=True)
            return
        seasons = [s for s in Season.list_by_guild(guild) if s.matches_by_week(week)]

        async def post_matches(season: Season):
            self.matches_to_post.extend(season.matches_by_week(week))

            if not self.post_loop.is_running():
                self.post_loop.start()

            await interaction.channel.send(f"Posted matches for week {week} of {season}")

        if not seasons:
            await interaction.send("There are no active seasons with matches for that week...", ephemeral=True)
        elif len(seasons) == 1:
            await interaction.response.defer()
            await post_matches(seasons[0])
        else:
            await interaction.send("Chose a season to post matches for:", ephemeral=True,
                    view=View().add_item(SeasonSelector(seasons, post_matches, follow_up_only=True)))


    @tasks.loop(seconds=30)
    async def post_loop(self):
        if self.matches_to_post:
            match = self.matches_to_post.pop(0)

            if match.started: return

            guild = match.season.guild
            category_name = "Matches"

            for team in match.teams:
                for player in team.role.members:
                    if player.guild_permissions.administrator:
                        category_name = "Admin Matches"

            matches_category = next((c for c in guild.categories if c.name == category_name), None)

            if not matches_category:
                matches_category = await guild.create_category_channel(category_name)

            match_channel = await guild.create_text_channel(
                name=f"{match.teams[0].code}-vs-{match.teams[1].code}",
                category=matches_category,
                topic=f"Match discussion channel for {match.teams[0].name} vs {match.teams[1].name}",
                overwrites={
                    match.teams[0].role:
                        disnake.PermissionOverwrite(view_channel=True),
                    match.teams[1].role:
                        disnake.PermissionOverwrite(view_channel=True),
                    guild.default_role:
                        disnake.PermissionOverwrite(view_channel=False)
                }
            )

            match.channel_id = match_channel.id

            match.season.reflect_match(match)

            await match_channel.send(
                f"This is the start of the match discussion channel for the week {match.week} match "
                f"{match.teams[0]} vs {match.teams[1]}. Use the /report command once you have played.",
                embeds=[match.season.roster_embed(match.teams[0]), match.season.roster_embed(match.teams[1])]
            )

        else:
            self.post_loop.stop()


    @slash()
    @require_team()
    async def report(self, interaction: SlashInter, team: Team):
        """Use to report your match result.

        Parameters
        ----------
        interaction: Slash Command Interaction
        team: Filled in from @require_team and hidden from the command registration.
        """
        match = Season.get_match(interaction.channel.id)

        if not match:
            await interaction.response.send_message("This isn't a match channel...", ephemeral=True)
            return

        await interaction.send(f"Reporting match for {match.teams[0]} vs {match.teams[1]}. Which team won?",
                               view=ReportView(match))

    @slash()
    @require_team()
    async def ko(self, interaction: SlashInter, team: Team):
        """Generates a KO counter in your Match channel to use during your game.

        Parameters
        ----------
        interaction: Slash Command Interaction
        team: Filled in from @require_team and hidden from the command registration.
        """
        match = Season.get_match(interaction.channel.id)

        if not match:
            await interaction.response.send_message("This isn't a match channel...", ephemeral=True)
            return

        await interaction.response.send_modal(KOStart(match, team))

class ReportView(View):
    def __init__(self, match: Match):
        super().__init__(timeout=None)

        self.add_item(ScoreButton(match, 0, 0))
        self.add_item(ScoreButton(match, 0, 1))
        self.add_item(ScoreButton(match, 1, 0))
        self.add_item(ScoreButton(match, 1, 1))


class ScoreButton(Button):
    def __init__(self, match: Match, win_team_index: int, loose_score: int):
        self.match: Match = match
        self.win_team_index: int = win_team_index
        self.loose_score: int = loose_score

        super().__init__(
            label=f"{match.teams[win_team_index].code} 2-{loose_score}",
            emoji=match.teams[win_team_index].emote,
            style=disnake.ButtonStyle.blurple
        )

    async def callback(self, interaction: ViewInter):
        await interaction.response.defer()
        self.match.results[self.win_team_index].score = 2
        self.match.results[0 if self.win_team_index == 1 else 1].score = self.loose_score
        self.match.season.reflect_match(match=self.match)

        await interaction.message.edit(
            f"Match has been reported by {interaction.author.mention} as a 2-{self.loose_score} win"
            f"for {self.match.teams[self.win_team_index].mention}",
            view=View().add_item(CloseButton(match=self.match))
        )


class CloseButton(Button):
    def __init__(self, match: Match):
        self.match: Match = match

        super().__init__(
            label="Close Channel",
            style=disnake.ButtonStyle.red
        )

    async def callback(self, interaction: ViewInter):
        if self.match.kos_recorded or interaction.author.guild_permissions.manage_webhooks:
            await interaction.response.defer()
            await interaction.channel.delete(reason="Match completed")
        else:
            await interaction.send(
                "You can't close the channel until both players have recorded KOs",
                ephemeral=True)


class KO_Counter:
    def __init__(self, match: Match, team: Team, pokemon_list: list[Pokemon]):
        self.match: Match = match
        self.team: Team = team
        self.pokemon_list: list[Pokemon] = pokemon_list
        self.kos: dict[str, int] = {}
        self.history: list[str] = []
        for pokemon in pokemon_list:
            self.kos[pokemon.dex] = 0

    def add_ko(self, dex_num: str):
        self.kos[dex_num] += 1
        self.history.append(dex_num)

    def undo_ko(self):
        self.kos[self.history.pop()] -= 1

    @property
    def input_string(self) -> str:
        s = "   ".join([f"{p.emote}{self.kos[p.dex]}" for p in self.pokemon_list])
        return f"Recording KOs for {self.team}. Click the buttons to add KOs:\n# {s}"

    @property
    def formal_string(self) -> str:
        m = max((len(str(p)) for p in self.pokemon_list))
        s = "\n".join([f"{p.emote} `{str(p):<{m}} :{self.kos[p.dex]:>2}`" for p in self.pokemon_list])
        return s

    @property
    def final_string(self) -> str:
        s = " ".join([f"{p.emote}{self.kos[p.dex]}" for p in self.pokemon_list])
        return f"The following KOs have been recorded:\n# {s}"


    @property
    def sheet_string(self) -> str:
        return ",".join([f"{p.dex},{self.kos[p.dex]}" for p in self.pokemon_list])


class KOStart(Modal):
    def __init__(self, match: Match, team: Team):
        self.match: Match = match
        self.team: Team = team

        super().__init__(
            title="KOs",
            components=[
                Label(
                    text="Select Pokémon that you brought this week.",
                    component=disnake.ui.CheckboxGroup(
                        min_values=6,
                        custom_id="kos",
                        options=[
                            disnake.GroupOption(label=str(p), value=p.dex)
                            for p in match.season.roster(team)
                        ]
                    )
                )
            ]
        )

    async def callback(self, interaction: ModalInter):
        mons = [p for p in self.match.season.roster(self.team) if p.dex in interaction.resolved_values["kos"]]

        kos = KO_Counter(match=self.match, team=self.team, pokemon_list=mons)

        await interaction.send(kos.input_string, view=KO_View(kos))


class KO_View(View):
    def __init__(self, kos: KO_Counter):
        self.kos = kos

        super().__init__()

        for mon in self.kos.pokemon_list:
            self.add_item(KO_Button(self.kos, mon))

        self.add_item(Undo_KO_Button(kos))
        self.add_item(KO_Report_Button(kos))


class KO_Button(Button):
    def __init__(self, kos: KO_Counter, pokemon: Pokemon):
        self.kos = kos
        self.pokemon = pokemon

        super().__init__(
            label=str(self.pokemon),
            emoji=self.pokemon.emote,
            style=disnake.ButtonStyle.green
        )

    async def callback(self, interaction: ViewInter):
        await interaction.response.defer()
        self.kos.add_ko(self.pokemon.dex)
        await interaction.message.edit(content=self.kos.input_string)

class Undo_KO_Button(Button):
    def __init__(self, kos: KO_Counter):
        self.kos = kos

        super().__init__(
            label="Undo",
            style=disnake.ButtonStyle.red
        )

    async def callback(self, interaction: ViewInter):
        await interaction.response.defer()
        if not self.kos.history: return
        self.kos.undo_ko()
        await interaction.message.edit(content=self.kos.input_string)

class KO_Report_Button(Button):
    def __init__(self, kos: KO_Counter):
        self.kos = kos

        super().__init__(
            label="Report",
            style=disnake.ButtonStyle.blurple
        )

    async def callback(self, interaction: ViewInter):
        await interaction.response.send_modal(Finalize_KO(self.kos))


class Finalize_KO(Modal):
    def __init__(self, kos: KO_Counter):
        self.kos = kos

        super().__init__(
            title="Finalize KOs",
            components=[
                disnake.ui.TextDisplay(
                    content=f"Please confirm that the following KOs are correct:\n\n{self.kos.formal_string}"
                ),
                Label(
                    text="These KOs are correct.",
                    description="Leaving unchecked will let you go back and make edits",
                    component=disnake.ui.Checkbox(custom_id="confirmed")
                )
            ]
        )

    async def callback(self, interaction: ModalInter):

        await interaction.response.defer(with_message=False)
        if interaction.resolved_values["confirmed"]:
            result = next((r for r in self.kos.match.results if r.team == self.kos.team), None)
            result.kos = self.kos.sheet_string
            self.kos.match.season.reflect_match(self.kos.match)
            await interaction.message.edit(content=self.kos.final_string, view=None)






