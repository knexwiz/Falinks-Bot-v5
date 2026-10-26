from cogs.shared.auto_imports import *
from cogs.shared.season import Season


class Cog(commands.Cog, name="Team Manager"):

    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        initialize_teams(self.bot)

        for gid in get_active_guild_ids():
            guild = self.bot.get_guild(gid)
            for channel in guild.text_channels:
                if channel.name == "team-dashboard":
                    #await channel.purge()
                    await end_dashboard_cycle(channel=channel)

        print("  Dashboard ready")


#######################################################################################################################
#############################                       Dashboard Cycle                       #############################
#######################################################################################################################


dash_embed = disnake.Embed(
    title="Team Dashboard",
    description="You do not need to play in a draft to have a team. "
                "Having a team lets you set your display color and emote for FDL.",
    color=disnake.Color(0xae6800)
)

waiting_embed = lambda c: disnake.Embed(
    title="Team Dashboard",
    description=c,
    color=disnake.Color(0xae6800)
)

async def start_dashboard_cycle(channel: disnake.TextChannel | Any, hold_text: str) -> disnake.Message | None:
    async for message in channel.history(limit=10):
        if message.embeds and next((embed for embed in message.embeds if embed.title == "Team Dashboard"), None):
            keeps = [embed for embed in message.embeds if embed.title != "Team Dashboard"]
            keeps.append(waiting_embed(hold_text))
            return await message.edit(embeds=keeps)
    return None


async def end_dashboard_cycle(channel: disnake.TextChannel | Any, content: str | None = None,
                              *, embeds: list[disnake.Embed] | None = None) -> disnake.Message:
    dash_view = TeamDashboard()
    dash_view.add_guild_specific(channel.guild)

    e = [*embeds, dash_embed] if embeds else [dash_embed]
    m = await channel.send(content, view=dash_view, embeds=e)

    async for message in channel.history(limit=10):
        if m == message: continue
        if message.embeds and next((embed for embed in message.embeds if embed.title == "Team Dashboard"), None):
            keeps = [embed for embed in message.embeds if embed.title != "Team Dashboard"]
            if keeps or message.content:
                await message.edit(embeds=keeps, view=None)
            else:
                await message.delete()

    return m


class TeamDashboard(View):

    def __init__(self):
      super().__init__(timeout=None)

    @add_button(label="Update Team // New Team", style=disnake.ButtonStyle.green, emoji=Emote.MARO_COOLGUY)
    async def modify_team(self, _: Button, interaction: ViewInter):
        team = Team.get(interaction.author)

        if team is None:
            await interaction.response.send_modal(TeamCreate())
        else:
            await interaction.response.send_modal(TeamUpdate(team))

    @add_button(label="Team Roster", style=disnake.ButtonStyle.grey, emoji=Emote.TERA_CROWN)
    @require_team()
    async def team_roster(self, _: Button, interaction: ViewInter, team: Team):
        active_seasons = [season for season in team.season_list if season.roster(team)]

        e = team.embed

        for season in active_seasons:
            for mon in season.roster(team):
                await mon.fetch_emote()

        for season in active_seasons: season.roster_embed(team, embed=e)

        await end_dashboard_cycle(interaction.channel, embeds=[e])

    def add_guild_specific(self, guild: disnake.Guild):
        waivers = False
        for season in Season.list_by_guild(guild):
            if season.signups_open:
                self.add_item(Signup_Button(season))

            if season.waivers_open:
                waivers = True

        if waivers:
            self.add_item(Waiver_Button())
            self.add_item(Trade_Button())


#######################################################################################################################
#############################                    Update // Create Team                    #############################
#######################################################################################################################


class TeamUpdate(Modal):
    # This is what we send players to update their team info (name, code, color, logo, and emote.)

    def __init__(self, team: Team):
        super().__init__(
            title = "Update Team Info",
            components = [
                Label(
                    text="Team Name",
                    description="The name of your team!",
                    component=TextInput(
                        placeholder=team.name,
                        custom_id="team_name",
                        style=disnake.TextInputStyle.short,
                        required=False
                    )
                ),
                Label(
                    text="Team Code",
                    description="3 or 4 letter code for your team.",
                    component=TextInput(
                        placeholder=team.code,
                        custom_id="team_code",
                        style=disnake.TextInputStyle.short,
                        max_length=4,
                        min_length=3,
                        required=False
                    )
                ),
                Label(
                    text="Team Color",
                    description="6 digit color hex code without the #.",
                    component=TextInput(
                        placeholder=f"{team.color.value: 06X}",
                        custom_id="team_color",
                        style=disnake.TextInputStyle.short,
                        max_length=6,
                        min_length=6,
                        required=False
                    )
                ),
                Label(
                    text="Logo Upload",
                    description="The logo for your team. PNG or JPEG only.",
                    component=FileUpload(
                        custom_id="logo_upload",
                        required=False
                    )
                ),
                Label(
                    text="Emote Upload",
                    description="Emote for your team. Should be a smaller image. PNG or JPEG only.",
                    component=FileUpload(
                        custom_id="emote_upload",
                        required=False
                    )
                )
            ]
        )
        self.team = team

    async def callback(self, interaction: ModalInter):
        team = self.team

        await interaction.response.defer(with_message=False)
        await start_dashboard_cycle(interaction.channel,f"Working on team update for {team}...")

        # This is the string where we keep a list of changes for the team. We will add to it with each area filled out.
        s = "```diff"

        # Name is strait forward, nothing really to check here except if it is included.
        new_name = interaction.text_values["team_name"]
        if new_name != "":
            s += f"\n+Team name changed from *{team.name}* to *{new_name}*."
            await team.role.edit(name=new_name)

        # Checking if it is len 3 to 4 shouldn't be necessary (hold over) but we do want to
        # make sure there are no symbols. We also check if the team code is valid, meaning
        # no other team uses it, so it remains an identifier.
        new_code = interaction.text_values["team_code"].upper()
        if new_code != "":
            if len(new_code) < 3 or len(new_code) > 4 or not new_code.isalnum():
                s += f"\n-{new_code} is not a valid team code."
            else:
                old_code = team.code
                worked = team.change_code(new_code)
                if worked:
                    s += f"\n+Team code changed from {old_code} to {new_code}."
                else:
                    s += f"\n-The team code {new_code} is already taken."

        # Put trying to convert the color into a discord accepted object so we don't have to
        # actually logic out checking it.
        new_color = interaction.text_values["team_color"]
        if new_color != "":
            if len(new_color) != 6:
                s += f"\n-{new_color} is not a valid color hex code."
            else:
                try:
                    col = disnake.Color(int(new_color, base=16))
                    await team.role.edit(color=col)
                    s += "\n+Team color changed."
                except ValueError:
                    s += f"\n-{new_color} is not a valid color hex code."

        if interaction.resolved_values["logo_upload"]:
            uploaded_file = interaction.resolved_values["logo_upload"][0]
            if uploaded_file.content_type == "image/png" or uploaded_file.content_type == "image/jpeg":
                new_logo = await uploaded_file.read()
                team.logo = upload_to_git(
                    folder="team logos/",
                    file_name=team.name,
                    extension='png' if uploaded_file.content_type == "image/png" else 'jpeg',
                    new_file=new_logo
                )
                s += f"\n+Team logo updated."
            else:
                s += f"\n-Received invalid logo upload of type {uploaded_file.content_type}. Must be png or jpeg."

        if interaction.resolved_values["emote_upload"]:
            uploaded_file = interaction.resolved_values["emote_upload"][0]
            if uploaded_file.content_type == "image/png" or uploaded_file.content_type == "image/jpeg":
                new_emote = await uploaded_file.read()
                upload_to_git(
                    folder="team emotes/",
                    file_name=team.name,
                    extension='png' if uploaded_file.content_type == "image/png" else 'jpeg',
                    new_file=new_emote
                )

                # noinspection PyBroadException
                try:
                    for emote in interaction.guild.emojis:
                        if str(emote) == team.emote:
                            await emote.delete()
                    emote = await interaction.guild.create_custom_emoji(name=f"__{team.code}", image=new_emote)
                    team.emote = str(emote)
                    s += "\n+Team emote has been updated."
                except:
                    s += "\n-There was an error with the new emote."
            else:
                s += f"\n-Received invalid emote upload of type {uploaded_file.content_type}. Must be png or jpeg."

        # The team itself takes care of sending the info to the sheet.
        team.reflect()

        # Send the changes. (with the team dashboard appended.)
        await end_dashboard_cycle(interaction.channel,
                                  f"There were no changes for {team}."
                                  if s == "```diff" else
                                  f"{team} has updated their team: \n{s}```",
                                  embeds=[team.embed])


class TeamCreate(Modal):
    # This is what we send players to update their team info (name, code, color, logo, and emote.)

    def __init__(self):
        super().__init__(
            title = "Team Sign Up",
            components = [
                Label(
                    text="Team Name",
                    description="The name of your team!",
                    component=TextInput(
                        placeholder= "Team Name",
                        custom_id= "team_name",
                        style= disnake.TextInputStyle.short,
                        min_length= 4,
                        required= True
                    )
                ),
                Label(
                    text="Team Code",
                    description="3 or 4 letter code for your team.",
                    component=TextInput(
                        placeholder= "CODE",
                        custom_id= "team_code",
                        style= disnake.TextInputStyle.short,
                        max_length= 4,
                        min_length= 3,
                        required= True
                    )
                ),
                Label(
                    text="Team Color",
                    description="6 digit color hex code without the #.",
                    component=TextInput(
                        placeholder= "FF00FF",
                        custom_id= "team_color",
                        style= disnake.TextInputStyle.short,
                        max_length= 6,
                        min_length= 6,
                        required= True
                    )
                ),
                Label(
                    text="Logo Upload",
                    description="The logo for your team. PNG or JPEG only. Can be added later",
                    component=FileUpload(
                        custom_id="logo_upload",
                        required=False
                    )
                ),
                Label(
                    text="Emote Upload",
                    description="Emote for your team. Should be a smaller image. PNG or JPEG only. Can be added later",
                    component=FileUpload(
                        custom_id="emote_upload",
                        required=False
                    )
                )
            ]
        )

    async def callback(self, interaction: ModalInter):

        await interaction.response.defer(with_message=False)
        await start_dashboard_cycle(interaction.channel,
                f"Working on signup for {interaction.author.mention}...")

        # This is the string where we keep a list of errors for the team.
        s = "```diff"

        # Name is strait forward, nothing really to check here except if it is included.
        new_name = interaction.text_values["team_name"]

        # Checking if it is len 3 to 4 shouldn't be necessary (hold over) but we do want to
        # make sure there are no symbols. We also check if the team code is valid, meaning
        # no other team uses it, so it remains an identifier.
        new_code = interaction.text_values["team_code"].upper()
        valid = Team.validate_code(new_code, interaction.guild.id)
        if not valid or not new_code.isalnum():
            valid = Team.validate_code(new_name[0:4], interaction.guild.id)
            if valid:
                new_code = new_name[0:4].upper()
            else:
                i = 0
                while i <= 99 and not Team.validate_code(new_name[0:2]+str(i), interaction.guild.id):
                    i += 1
                new_code = new_name[0:2].upper()+str(i)
            s += f"\n-Invalid team code. Set to {new_code} instead."

        # Put trying to convert the color into a discord accepted object so we don't have to
        # actually logic out checking it.
        color_hex = interaction.text_values["team_color"]
        try:
            new_color = disnake.Color(int(color_hex, base=16))
        except ValueError:
            s += f"\n-{color_hex} is not a valid color hex code."
            new_color = disnake.Color.default()

        new_logo = ""
        new_emote = ""

        if interaction.resolved_values["logo_upload"]:
            uploaded_file = interaction.resolved_values["logo_upload"][0]
            if uploaded_file.content_type == "image/png" or uploaded_file.content_type == "image/jpeg":
                logo_byte = await uploaded_file.read()
                new_logo = upload_to_git(
                    folder="team logos/",
                    file_name=new_name,
                    extension='png' if uploaded_file.content_type == "image/png" else 'jpeg',
                    new_file=logo_byte
                )
            else:
                s += f"\n-Received invalid logo upload of type {uploaded_file.content_type}. Must be png or jpeg."

        emote = None
        if interaction.resolved_values["emote_upload"]:
            uploaded_file = interaction.resolved_values["emote_upload"][0]
            if uploaded_file.content_type == "image/png" or uploaded_file.content_type == "image/jpeg":
                emote_byte = await uploaded_file.read()
                upload_to_git(
                    folder="team emotes/",
                    file_name=new_name,
                    extension='png' if uploaded_file.content_type == "image/png" else 'jpeg',
                    new_file=emote_byte
                )

                # noinspection PyBroadException
                try:
                    emote = await interaction.guild.create_custom_emoji(name=f"__{new_code}", image=emote_byte)
                    new_emote = str(emote)
                except:
                    s += "\n-There was an error with the emote."
            else:
                s += f"\n-Received invalid emote upload of type {uploaded_file.content_type}. Must be png or jpeg."

        if emote is not None and "ROLE_ICONS" in interaction.guild.features:
            role = await interaction.guild.create_role(
                name = new_name, color= new_color,
                mentionable=True, icon=emote
            )
        else:
            role = await interaction.guild.create_role(
                name = new_name, color= new_color,
                mentionable=True
            )


        team = Team(
            sheet_id= Team.next_id(interaction.guild.id),
            role= role,
            code= new_code,
            logo= new_logo,
            emote= new_emote,
            utc_offset= 0,
            existing_player=interaction.author.display_name
        )

        # The team itself takes care of sending the info to the sheet.
        team.reflect()

        compare_to_role = None
        for g_role in interaction.guild.roles:
            if g_role.name == "Player":
                compare_to_role = g_role
        for m_role in interaction.author.roles:
            if m_role > compare_to_role:
                compare_to_role = m_role
        await role.edit(position=compare_to_role.position + 1)

        coach = None
        for g_role in interaction.guild.roles:
            if g_role.name == "Team Coach":
                coach = g_role

        if coach is not None:
            await interaction.author.add_roles(role, coach)
        else:
            await interaction.author.add_roles(role)

        # Send the changes.
        await end_dashboard_cycle(interaction.channel,
                                  f"{interaction.author.mention} has signed up with team {team}!"
                                  f"{"\n"+s if s != "```diff" else ""}",
                                  embeds=[team.embed])


#######################################################################################################################
#############################                           Sign Up                           #############################
#######################################################################################################################


class Signup_Button(Button):
    def __init__(self, season: Season):
        self.season = season
        super().__init__(
            label= f"Signup for {str(season)[:65]}",
            style=ButtonStyle.blurple,
            emoji=Emote.HAPPY_HAX
        )

    @require_team(fail_message="You need to make a Team before you can signup!")
    async def callback(self, interaction: ViewInter, team: Team):
        await interaction.response.defer(with_message=False)
        await start_dashboard_cycle(interaction.channel, f"Working on {self.season} signup for {team}...")

        if self.season not in team.season_list:
            self.season.add_team(team)
            await end_dashboard_cycle(interaction.channel, f"{team} has signed up for {self.season}!",
                                      embeds=[team.embed])

        else:
            self.season.remove_team(team)
            await end_dashboard_cycle(interaction.channel, f"{team} has dropped from {self.season}!")


#######################################################################################################################
#############################                           Waiver                            #############################
#######################################################################################################################


class Waiver_Button(Button):
    def __init__(self):
        super().__init__(
            label= f"Waiver Pokémon",
            style=ButtonStyle.red,
            emoji=Emote.TORKOAL_ANGRY
        )

    @require_team()
    async def callback(self, interaction: ViewInter, team: Team):
        waiver_seasons = [season for season in team.season_list if season.waivers_open and len(season.roster(team))]

        if not waiver_seasons:
            await interaction.send("You aren't in any seasons with waivers open...", ephemeral=True)
        elif len(waiver_seasons) == 1:
            await interaction.response.send_modal(Waiver(team, waiver_seasons[0]))
        else:
            await interaction.send("You are in multiple seasons. Please chose one:",
                                   view=View().add_item(SeasonSelector(waiver_seasons, Waiver, team=team)),
                                   ephemeral=True)


class Waiver(Modal):
    def __init__(self, team: Team, season: Season):
        self.team: Team = team
        self.season: Season = season

        super().__init__(
            title="Waiver",
            components=[
                Label(
                    text="Pokemon to drop:",
                    component=StringSelect(
                        placeholder="Pokémon to drop",
                        custom_id="dropping",
                        options=[disnake.SelectOption(label=str(p), emoji=p.emote) for p in season.roster(team)]
                    )
                ),
                Label(
                    text="Pokemon to pick up:",
                    component=TextInput(
                        placeholder="Pokémon you want",
                        custom_id="picking",
                        style=disnake.TextInputStyle.short,
                        required=True
                    )
                )
            ]
        )

    async def callback(self, interaction: ModalInter):

        drop = Pokemon.get(interaction.resolved_values["dropping"][0])
        pick = Pokemon.get(interaction.text_values["picking"])

        await interaction.response.defer(with_message=False)
        await start_dashboard_cycle(interaction.channel,f"Starting waiver for {self.team}, {drop} -> {pick}")

        if drop is None:
            await end_dashboard_cycle(interaction.channel,f"{interaction.author.mention}: "
                                        f"{interaction.resolved_values["dropping"][0]} is not a valid pokemon...")
            return
        if pick is None:
            await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                         f"{interaction.text_values['picking']} is not a valid pokemon...")
            return

        await drop.fetch_emote()
        await pick.fetch_emote()

        if self.season.draft_type == "Tier":
            if self.season.tier(drop) != self.season.tier(pick):
                await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                             f"{drop.mention} and {pick.mention} are not in the same tier...")
                return
        elif self.season.points_remaining(self.team) + self.season.point_cost(drop) - self.season.point_cost(pick) < 0:
            await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                         f"You don't have enough points to pick up {pick.mention}...")
            return

        if self.season.waiver(team = self.team, drop=drop, pickup=pick):
            embed = self.team.sign(pick.embed)
            embed.set_footer(
                text=f"{self.season.tier(pick)} // {embed.footer.text}",
                icon_url=embed.footer.icon_url
            )

            await end_dashboard_cycle(interaction.channel,
                                      f"{self.team} has dropped {drop.mention}, picking up {pick.mention}!",
                                      embeds=[embed])
        else:
            await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                         f"{pick.mention} is not an available pokemon...")


#######################################################################################################################
#############################                            Trade                            #############################
#######################################################################################################################


class Trade_Button(Button):
    def __init__(self):
        super().__init__(
            label=f"Trade Pokémon",
            style=ButtonStyle.red,
            emoji=Emote.VANILUXE_EVIL
        )

    @require_team()
    async def callback(self, interaction: ViewInter, team: Team):
        waiver_seasons = [season for season in team.season_list if season.waivers_open and len(season.roster(team))]

        if not waiver_seasons:
            await interaction.send("You aren't in any seasons where trades are open...", ephemeral=True)
        elif len(waiver_seasons) == 1:
            await interaction.send("Chose a team to trade with:",
                                   view=View().add_item(TradeTeamSelector(team, waiver_seasons[0])), ephemeral=True)
        else:
            followup = lambda t, s: View().add_item(TradeTeamSelector(t, s))
            await interaction.send("You are in multiple seasons. Please chose one:",
                                   view=View().add_item(SeasonSelector(waiver_seasons, followup,
                                                follow_up_text="Chose a team to trade with:", team=team)),
                                   ephemeral=True)


class TradeTeamSelector(StringSelect):
    def __init__(self, team: Team, season: Season):
        self.team: Team = team
        self.season: Season = season

        super().__init__(
            placeholder="Chose the team you want to trade with.",
            custom_id="trade_team",
            options=[disnake.SelectOption(label=t.name, emoji=t.emote, value=t.sheet_id)
                     for t in self.season.team_list if t]
        )

    async def callback(self, interaction: ViewInter):
        other_team = Team.get_from_sheet_id(interaction.values[0], interaction.guild.id)

        if other_team != self.team and other_team is not None:
            await interaction.response.send_modal(Trade(self.team, self.season, other_team))
        else:
            await interaction.send(f"{interaction.values[0]} is not a valid team to trade with...", ephemeral=True)


class Trade(Modal):
    def __init__(self, user_team: Team, season: Season, other_team: Team):
        self.user_team: Team = user_team
        self.season: Season = season
        self.other_team: Team = other_team

        super().__init__(
            title="Trade",
            components=[
                Label(
                    text="Your Pokemon",
                    component=StringSelect(
                        placeholder="Pokémon to trade",
                        custom_id="user_mon",
                        options=[disnake.SelectOption(label=str(p), emoji=p.emote) for p in season.roster(user_team)]
                    )
                ),
                Label(
                    text=f"{other_team.name}'s Pokémon",
                    component=StringSelect(
                        placeholder="Pokémon you want",
                        custom_id="other_mon",
                        options=[disnake.SelectOption(label=str(p), emoji=p.emote) for p in season.roster(other_team)]
                    )
                )
            ]
        )

    async def callback(self, interaction: ModalInter):

        user_mon = Pokemon.get(interaction.resolved_values["user_mon"][0])
        other_mon = Pokemon.get(interaction.resolved_values["other_mon"][0])

        await interaction.response.defer(with_message=False)
        await start_dashboard_cycle(interaction.channel,
                                    f"Starting trade for {self.user_team}, {user_mon} <-> {other_mon}")

        if user_mon is None:
            await end_dashboard_cycle(interaction.channel,f"{interaction.author.mention}: "
                                         f"{interaction.resolved_values["user_mon"][0]} is not a valid pokemon...")
            return
        if other_mon is None:
            await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                         f"{interaction.text_values['other_mon']} is not a valid pokemon...")
            return

        await user_mon.fetch_emote()
        await other_mon.fetch_emote()

        if self.season.draft_type == "Tier":
            if self.season.tier(user_mon) != self.season.tier(other_mon):
                await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                             f"{user_mon.mention} and {other_mon.mention} are not in the same tier...")
                return
        elif self.season.points_remaining(self.user_team) + self.season.point_cost(user_mon) - self.season.point_cost(other_mon) < 0:
            await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                         f"You don't have enough points to pick up {other_mon.mention}...")
            return
        elif self.season.points_remaining(self.other_team) + self.season.point_cost(other_mon) - self.season.point_cost(user_mon) < 0:
            await end_dashboard_cycle(interaction.channel, f"{interaction.author.mention}: "
                                         f"{self.other_team} doesnt have enough points to pick up {user_mon.mention}...")
            return

        await interaction.channel.send(f"{self.other_team}: {self.user_team} has proposed a trade!\n"
                                       f"{self.user_team} gets {other_mon.mention}.\n"
                                       f"{self.other_team} get {user_mon.mention}.\n",
                                       view=View(timeout=None).add_item(TradeFinalize(
                                           self.user_team,self.season,self.other_team,user_mon,other_mon)))
        await end_dashboard_cycle(interaction.channel)


class TradeFinalize(Button):
    def __init__(self, user_team: Team, season: Season, other_team: Team, user_mon: Pokemon, other_mon: Pokemon):
        self.user_team = user_team
        self.season = season
        self.other_team = other_team
        self.user_mon = user_mon
        self.other_mon = other_mon

        super().__init__(
            label="Accept Trade",
            style=ButtonStyle.red,
            emoji=Emote.WHIMS
        )

    @require_team(fail_message="You're really silly, you know that?")
    async def callback(self, interaction: ViewInter, team: Team):
        if team != self.other_team:
            await interaction.send(f"You aren't on team {self.other_team}!", ephemeral=True)
            return

        await interaction.response.defer(with_message=False)
        await start_dashboard_cycle(interaction.channel, f"Finalizing trade...")

        await interaction.message.delete()

        if self.season.trade(team1=self.user_team, team2=self.other_team, poke1=self.user_mon, poke2=self.other_mon):
            await end_dashboard_cycle(interaction.channel,
                                        f"## Trade!\n"
                                        f"{self.user_team} has received {self.other_mon.mention}.\n"
                                        f"{self.other_team} has received {self.user_mon.mention}!",
                                      embeds=[self.user_team.sign(self.other_mon.embed),
                                              self.other_team.sign(self.user_mon.embed)])
        else:
            await end_dashboard_cycle(
                interaction.channel,
                content=f"{interaction.author.mention}: "
                f"Something went horribly wrong with the trade...")

