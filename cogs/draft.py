import math
import random
import gspread

from cogs.shared.auto_imports import *
from cogs.shared.season import Season


class Cog(commands.Cog, name="Draft"):

    @slash(default_member_permissions=disnake.Permissions(manage_webhooks=True))
    async def start_draft(self, interaction: SlashInter):
        """Starts a draft int the current channel. Will automatically resume a draft that was interupted.

        Parameters
        ----------
        interaction: Slash Command Interaction
        """
        guild = interaction.guild
        if not guild:
            await interaction.send("You should only use this is a server...", ephemeral=True)
            return
        seasons = [s for s in Season.list_by_guild(guild) if s.draft_type in ["Tier", "Points"]]

        async def new_draft(season: Season):
            season.recache()
            d = Draft(season, season.team_list, sum([len(r) for r in season.rosters.values()]))

            next_pick = d.advance()

            if not next_pick:
                await interaction.send("This season has already drafted...", ephemeral=True)

            s = f"# Draft {season} has started!"

            for team, i in zip(season.team_list, range(len(season.team_list))):
                s += f"\n{i}. {team}"

            await interaction.send(s)

            await interaction.channel.send(f"{next_pick} it is your turn to pick!")


        if not seasons:
            await interaction.send("There are no active seasons...", ephemeral=True)
        elif len(seasons) == 1:
            await new_draft(seasons[0])
        else:
            await interaction.send("Chose a season to start:", ephemeral=True,
                    view=View().add_item(SeasonSelector(seasons, new_draft, follow_up_only=True)))


    @slash()
    @require_team(fail_message="I appreciate the effort...")
    async def pick(self, interaction: SlashInter, team: Team,
                   pokemon: str = commands.Param(autocomplete=Pokemon.autocomplete),
                   override: bool = False):
        """Pick the Pokémon you want durring a draft.

        Parameters
        ----------
        interaction: Slash Command Interaction
        team: Filled in from @require_team and hidden from the command registration.
        pokemon: The name of the Pokémon you want to pick.
        override: Allows Admins to pick for other players, or to allow random picks.
        """
        await interaction.response.defer()


        if not Draft.current:
            await interaction.send(f"There's no draft happening right now...")
            return

        season = Draft.current.season
        current_team = Draft.current.current_pick

        if pokemon.casefold().startswith("random") and override:
            if season.draft_type == "Tier":
                if pokemon[-1].upper() in season.picks_per_tier.keys():
                    needed_tier = pokemon[-1].upper()
                else:
                    needed_tier = [t for t in season.picks_per_tier.keys()
                                    if season.picks_per_tier[t] >
                                    len([p for p in season.roster(current_team) if season.tier(p) == t])][0]
                choices = [p for p in season.tiers.keys() if season.tiers[p] == needed_tier and season.available(p)]
            else:
                choices = [p for p in season.tiers.keys() if season.available(p)]
            poke = Pokemon.get(random.choice(choices))
        else:
            poke = Pokemon.get(pokemon)

        if not poke:
            await interaction.send(f"{Pokemon} is not a Pokémon...")
            return

        tier = season.tier(poke)

        if ((team != current_team) and not (override and
                interaction.author.guild_permissions.manage_webhooks)):
            await interaction.send(f"It is not your turn to pick!")
            return

        if not tier:
            await interaction.send(f"{poke.mention} is not legal this season...")
            return

        if not season.available(poke):
            await interaction.send(f"{poke.mention} has already been taken!")
            return

        if Draft.current.season.draft_type == "Tier":
            if season.picks_per_tier[str(tier)] <= len([p for p in season.roster(current_team) if season.tier(p) == tier]):
                await interaction.send(f"You have already picked all of your {tier} tier Pokémon...")
                return
        else:
            if season.point_cap < season.points_remaining(current_team) + season.point_cost(poke):
                await interaction.send(f"You don't have enough points left to pick {poke.mention}...")
                return

        season.team_sheet.update_cell(row=Draft.current.turn+2, col=Draft.current.round+5, value=f"'{poke.dex}")
        season.rosters[current_team.sheet_id].append(poke)

        await poke.fetch_emote()

        embed = current_team.sign(poke.embed)
        embed.set_footer(
            text=f"{tier} // {embed.footer.text}",
            icon_url=embed.footer.icon_url
        )

        await interaction.send(f"{current_team} has picked {poke.mention}!", embed=embed)

        next_pick = Draft.current.advance()

        if next_pick:
            await interaction.channel.send(f"{next_pick} it is your turn to pick!")
        else:
            await interaction.channel.send(f"# The draft has ended!")

            data = []
            old = []

            if Draft.current.season.draft_type == "Tier":
                tiers = list(season.picks_per_tier)
                top_sort = lambda p: -1 * tiers.index(str(season.tier(p)))
            else:
                top_sort = lambda p: season.point_cost(p)

            for team in season.team_list:
                old.append([p.dex for p in season.roster(team)])
                dex_order = sorted(season.roster(team), key=lambda p: p.dex)
                ordered = sorted(dex_order, key=top_sort, reverse=True)
                season.rosters[team.sheet_id] = ordered
                data.append([p.dex for p in ordered])

            season.team_sheet.update(data,
                range_name=f"E2:{gspread.utils.rowcol_to_a1(row=len(data)+1, col=Draft.current.round+4)}")

            history = season.sheet.add_worksheet("Draft History", rows=len(old), cols=len(old[0]))
            history.update(old)

            await interaction.channel.send("Good job everyone!")


class Draft:
    current: Draft | None = None

    def __init__(self, season: Season, order: list[Team], pick_num: int):
        self.season = season
        self.order = order
        self.pick_num = pick_num - 1
        self.current_pick = None

        Draft.current = self

    def advance(self) -> Team | None:
        self.pick_num += 1

        if self.round >= self.season.total_picks:
            return None
        self.current_pick = self.order[self.turn]
        return self.current_pick

    @property
    def round(self) -> int:
        return math.floor(self.pick_num / len(self.order))

    @property
    def turn(self):
        i = (self.pick_num % len(self.order))
        return i if self.round % 2 == 0 else len(self.order) - i - 1


