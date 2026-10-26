import disnake
from disnake import Guild

import cogs.shared.sheets.sheet_manager as sheet_manager
import gspread

from cogs.shared.pokemon import Pokemon
from cogs.shared.team import Team

from functools import wraps
from datetime import datetime, timedelta

def cache(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, "__cache"):
            self.__cache = {}
        if not hasattr(self, "__initial_cache"):
            self.__initial_cache = datetime.now()

        if self.__initial_cache - datetime.now() > timedelta(hours=3):
            self.__cache = {}
            self.__initial_cache = datetime.now()

        if func.__name__ not in self.__cache:
            self.__cache[func.__name__] = func(self, *args, **kwargs)
        return self.__cache[func.__name__]

    return wrapper


class Season:
    __list = []

    def __init__(self, guild: disnake.Guild, sheet: gspread.Spreadsheet):
        self.guild = guild
        self.sheet = sheet
        self.rosters: dict[str, list[Pokemon]] = {}
        self.tiers: dict[str, str | int] = {}
        self.matches: list[Match] = []
        self.__cache = {}
        self.__initial_cache = datetime.now()

        self.recache()

        Season.__list.append(self)

    @property
    @cache
    def team_sheet(self) -> gspread.Worksheet:
        return self.sheet.worksheet("Teams")

    @property
    @cache
    def matches_sheet(self) -> gspread.Worksheet:
        return self.sheet.worksheet("Matches")

    @property
    @cache
    def pokemon_sheet(self) -> gspread.Worksheet:
        return self.sheet.worksheet("Pokemon Ranks")

    @property
    @cache
    def waiver_sheet(self) -> gspread.Worksheet:
        return self.sheet.worksheet("Waiver List")

    @property
    @cache
    def setup(self) -> gspread.Worksheet:
        return self.sheet.worksheet("Setup")

    @property
    @cache
    def signups_open(self) -> bool:
        cell = self.setup.acell("B2")
        return cell.value == "TRUE"

    @property
    @cache
    def waivers_open(self) -> bool:
        cell = self.setup.acell("B3")
        return cell.value == "TRUE"

    @property
    @cache
    def draft_type(self) -> str:
        cell = self.setup.acell("A11")
        if cell is None: return ""
        return str(cell.value)

    @property
    @cache
    def point_cap(self) -> int:
        cell = self.setup.acell("D10")
        return int(str(cell.value)) if cell.value.isdigit() else 100

    @property
    @cache
    def picks_per_tier(self) -> dict[str, int]:
        r = self.setup.get("E3:F10", major_dimension=gspread.utils.Dimension.cols)
        d = dict(zip(r[0], [int(c) if c.isdigit() else 0 for c in r[1]]))
        zeros = []
        for k, v in d.items():
            if v == 0: zeros.append(k)
        for r in zeros: d.pop(r)
        return d

    @property
    @cache
    def total_picks(self) -> int:
        if self.draft_type == "Tier":
            return sum(self.picks_per_tier.values())
        else:
            cell = self.setup.acell("D11")
            return int(str(cell.value)) if cell.value.isdigit() else 10

    @property
    @cache
    def week_count(self) -> int:
        cell = self.setup.acell("B4")
        return int(str(cell.value)) if cell.value.isdigit() else 1

    @staticmethod
    def list_by_guild(guild: Guild) -> list[Season]:
        l = []
        for season in Season.__list:
            if season.guild == guild:
                l.append(season)
        return l

    def add_team(self, team: Team):
        self.team_sheet.append_row([team.sheet_id], table_range='A1')
        team.season_list.append(self)
        self.rosters[team.sheet_id] = []

    def remove_team(self, team: Team):
        team.season_list.remove(self)
        cell = self.team_sheet.find(team.sheet_id, in_column=1)
        self.team_sheet.delete_rows(start_index=cell.row)
        self.rosters.pop(team.sheet_id)

    @property
    def team_list(self) -> list[Team]:
        return list(filter(None, [Team.get_from_sheet_id(team_id, self.guild.id) for team_id in self.rosters.keys()]))


    def roster(self, team: Team) -> list[Pokemon]:
        if team.sheet_id not in self.rosters:
            return []
        return self.rosters[team.sheet_id]

    def roster_embed(self, team: Team, *, embed: disnake.Embed | None = None) -> disnake.Embed:
        v = "".join([(str(p.emote) if p.emote else str(p)) for p in self.roster(team)])

        if embed is None: return team.embed.add_field("Roster", value=v)
        else: embed.add_field(name=str(self), value=v)
        return embed

    def tier(self, pokemon: Pokemon) -> int | str | None:
        if pokemon.dex in self.tiers:
            return self.tiers[pokemon.dex]
        else:
            return None

    def point_cost(self, pokemon: Pokemon) -> int:
        t = self.tier(pokemon)
        return t if isinstance(t, int) else 0

    def points_remaining(self, team: Team) -> int | None:
        if team.sheet_id not in self.rosters or self.draft_type == "Tier":
            return None
        else:
            # noinspection PyTypeChecker
            return self.point_cap - sum([self.tier(pokemon) for pokemon in self.roster(team)])

    def available(self, pokemon: Pokemon | str) -> bool:
        if isinstance(pokemon, str):
            if pokemon not in self.tiers: return False
        elif not (pokemon.dex in self.tiers): return False
        for r in self.rosters.values():
            if pokemon in r: return False
        return True

    def waiver(self, *, team: Team, drop: Pokemon, pickup: Pokemon) -> bool:
        if team.sheet_id in self.rosters and drop in self.rosters[team.sheet_id] and self.available(pickup):
            cell = self.team_sheet.find(drop.dex)
            if cell is not None:
                cell.value = pickup.dex
                self.rosters[team.sheet_id][self.rosters[team.sheet_id].index(drop)] = pickup
                self.team_sheet.update_cells([cell])

                next_row = len(self.waiver_sheet.get_all_values()) + 1

                self.waiver_sheet.insert_row(
                    [team.sheet_id, "", drop.dex, pickup.dex, self.current_week], index=next_row)

                return True
        return False

    def trade(self, team1: Team, team2: Team, poke1: Pokemon, poke2: Pokemon) -> bool:
        if (team1.sheet_id in self.rosters and team2.sheet_id in self.rosters and
            poke1 in self.rosters[team1.sheet_id] and poke2 in self.rosters[team2.sheet_id]):
            cell1 = self.team_sheet.find(poke1.dex)
            cell2 = self.team_sheet.find(poke2.dex)
            if cell1 is not None and cell2 is not None:
                cell1.value = poke2.dex
                cell2.value = poke1.dex
                self.rosters[team1.sheet_id][self.rosters[team1.sheet_id].index(poke1)] = poke2
                self.rosters[team2.sheet_id][self.rosters[team2.sheet_id].index(poke2)] = poke1
                self.team_sheet.update_cells([cell1, cell2])

                next_row = len(self.waiver_sheet.get_all_values()) + 1

                self.waiver_sheet.insert_row(
                    [team1.sheet_id, team2.sheet_id, poke1.dex, poke2.dex, self.current_week], index=next_row)

                return True
        return False

    def matches_by_week(self, week: int) -> list[Match]:
        return [match for match in self.match_list if match.week == week]

    @staticmethod
    def get_match(channel_id: int) -> Match | None:
        for season in Season.__list:
            for match in season.matches:
                if match.channel_id == channel_id:
                    return match
        return None

    @property
    def current_week(self) -> int:
        weeks = [m.week for m in self.matches if m.started]
        if weeks:
            return max(weeks)
        else: return 0


    def reflect_match(self, match: Match) -> None:
        row = [
            match.week,
            str(match.channel_id),
            match.results[0].team.sheet_id,
            f"=TEAM_NAME(C{match.index})",
            match.results[0].score,
            match.results[0].kos,
            match.results[1].team.sheet_id,
            f"=TEAM_NAME(G{match.index})",
            match.results[1].score,
            match.results[1].kos
        ]

        self.matches_sheet.update(
            values=[row],
            range_name=f"A{match.index}:J{match.index}",
            value_input_option=gspread.utils.ValueInputOption.user_entered
        )


    def __str__(self):
        cell = self.setup.acell("G1")
        return cell.value

    def recache(self):
        self.__cache = {}
        self.__initial_cache = datetime.now()

        self.rosters: dict[str, list[Pokemon]] = {}

        for row in self.team_sheet.get_all_values()[1:]:
            team = Team.get_from_sheet_id(row[0], self.guild.id)
            if team is not None and self not in team.season_list:
                team.season_list.append(self)
            self.rosters[row[0]] = list(filter(None, [Pokemon.get(p) for p in row[4:]]))

        self.tiers: dict[str, str | int] = {}


        if self.draft_type == "Tier":
            picks = self.picks_per_tier
            low = list(picks.keys())[-1].upper()
            for row in self.pokemon_sheet.get_all_values()[1:]:
                if row[4].upper() in picks: self.tiers[row[1]] = row[4].upper()
                if row[4].casefold() == "low": self.tiers[row[1]] = low
        else:
            rows = self.pokemon_sheet.get_all_values()[1:]
            low = min([int(row[4]) for row in rows if row[4].isdigit()])
            for row in rows:
                if row[4].isdigit(): self.tiers[row[1]] = int(row[4])
                if row[4].casefold() == "low": self.tiers[row[1]] = low


        self.matches: list[Match] = []
        match_data = self.matches_sheet.get_all_values()
        for row, i in zip(match_data[2:], range(3, len(match_data) + 1)):
            t1 = Team.get_from_sheet_id(row[2], self.guild.id)
            t2 = Team.get_from_sheet_id(row[6], self.guild.id)
            if row[0].isdigit() and t1 and t2:
                self.matches.append(
                    Match(
                        season=self,
                        index=i,
                        week=int(row[0]),
                        channel_id=int(row[1]) if row[1].isdigit() else None,
                        results=[
                            Result(
                                team=t1,
                                score=int(row[4]) if row[4].isdigit() else None,
                                kos=row[5],
                            ),
                            Result(
                                team=t2,
                                score=int(row[8]) if row[8].isdigit() else None,
                                kos=row[9],
                            )
                        ]
                    )
                )


def initialize(bot: disnake.ext.commands.Bot):
    for m in sheet_manager.SheetManager.all():
        for sheet in m.seasons:
            guild = bot.get_guild(m.id)
            Season(guild, sheet)


class Match:
    def __init__(self, season: Season,  index: int, week: int, channel_id: int | None, results: list[Result]):
        self.season: Season = season
        self.index: int = index
        self.week: int = week
        self.channel_id: int | None = channel_id
        self.results: list[Result] = results

    @property
    def teams(self) -> list[Team]:
        return [r.team for r in self.results]

    @property
    def started(self) -> bool:
        return self.channel_id is None

    @property
    def finished(self) -> bool:
        for r in self.results:
            if r.score is None:
                return True
        return False

    @property
    def kos_recorded(self) -> bool:
        for r in self.results:
            if not r.kos:
                return False
        return True


class Result:
    def __init__(self, team: Team, score: int | None, kos: str):
        self.team: Team = team
        self.score: int | None = score
        self.kos: str = kos



class SeasonSelector(disnake.ui.StringSelect):
    def __init__(self, seasons: list[Season], followup: Any, *, follow_up_text = "", follow_up_only = False, **kwargs):
        self.kwargs: dict = kwargs
        self.seasons: list[Season] = seasons
        self.followup = followup
        self.follow_up_text = follow_up_text
        self.follow_up_only = follow_up_only

        super().__init__(
            placeholder="Choose a season",
            custom_id="season",
            options=[str(season) for season in self.seasons]
        )

    async def callback(self, interaction: ViewInter):
        for season in self.seasons:
            if str(season) == interaction.values[0]:
                if self.follow_up_only:
                    await self.followup(season=season, **self.kwargs)
                elif self.follow_up_text != "":
                    await interaction.send(self.follow_up_text,
                                           view=self.followup(season=season, **self.kwargs),
                                           ephemeral=True)
                else:
                    await interaction.response.send_modal(self.followup(season=season, **self.kwargs))
                break
        else:
            await interaction.send("Couldn't find a season...", ephemeral=True)




