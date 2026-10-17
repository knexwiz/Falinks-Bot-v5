import gspread
import cogs.shared.sheets.sheet_manager as setup
import pandas as pd
import functools
import inspect
import disnake
from datetime import datetime, timedelta

class Team:
    __list = {}
    __pseudos = {}

    def __init__(self, *, sheet_id: str, role: disnake.Role, code: str,
                 logo: str, emote: str, utc_offset: int, existing_player: str):
        self.sheet_id = sheet_id
        self.role = role
        self.code = code.upper()
        self.logo = logo
        self.emote = emote
        self.utc_offset = utc_offset
        self.player_name = existing_player

        self.season_list = []

        Team.__list[self.role.id] = self

    @property
    def color(self) -> disnake.Color:
        return self.role.color

    @property
    def name(self) -> str:
        return self.role.name

    @property
    def mention(self) -> str:
        return self.emote + self.role.mention

    @property
    def embed(self) -> disnake.Embed:
        embed = disnake.Embed(
            title=self.name,
            description=f"{self.emote}{" " if self.emote else ""}{self.code}",
            color=self.role.color,
        )
        embed.set_footer(
            text=", ".join([m.display_name for m in self.role.members]),
            icon_url=next((m.display_avatar.url for m in self.role.members),None)
        )
        embed.set_thumbnail(self.logo)
        return embed

    @property
    def full_emote(self) -> disnake.Emoji | None:
        return next((e for e in self.role.guild.emojis if str(e) == self.emote), None)

    def sign(self, embed: disnake.Embed):
        embed.set_author(
            name=self.name,
            icon_url=self.full_emote.url if self.full_emote else None,
        )
        embed.colour = self.color
        return embed

    def __str__(self):
        return self.mention

    def set_player(self, player: disnake.Member | disnake.User) -> None:
        self.player_name = player.display_name

    def change_code(self, new_code: str) -> bool:
        valid = Team.validate_code(new_code, self.role.guild.id)
        if valid:
            self.code = new_code.upper()
            return True
        else:
            return False

    @staticmethod
    def validate_code(code: str, guild_id: int) -> bool:
        testcode = code.upper()
        for team in Team.__list.values():
            if team.role.guild.id == guild_id and team.code == testcode:
                return False
        return True


    def reflect(self) -> None:
        row = [
            self.sheet_id,
            self.player_name,
            "",
            self.role.name,
            self.code,
            f"{self.role.id}",
            self.logo,
            self.emote,
            f"{self.role.color.value:06X}",
            self.utc_offset
        ]

        player_sheet = setup.SheetManager.get(self.role.guild.id).master.players
        cell = player_sheet.find(self.sheet_id, in_column=1)
        if cell is not None:
            player_sheet.update(values=[row], range_name=f"A{cell.row}:J{cell.row}")
        else:
            player_sheet.append_row(row, table_range='A1')

    @staticmethod
    def next_id(guild_id: int) -> str:
        player_ids = setup.SheetManager.get(guild_id).master.players.get_all_values(
            major_dimension=gspread.utils.Dimension.cols)[0]

        s = player_ids[-1][0]
        try:
            i = int(player_ids[-1][1:]) + 1
        except ValueError:
            i = 0

        while f"{s}{i:02d}" in player_ids:
            i += 1

        return f"{s}{i:02d}"

    @staticmethod
    def pseudo(member: disnake.Member | disnake.User, role: disnake.Role) -> Team | None:
        if role.id in Team.__list:
            team = Team.__list[role.id]
            Team.__pseudos[member.id] = {"team": team, "time": datetime.now()}
            return team
        else:
            return None

    @staticmethod
    def get(member: disnake.Member | disnake.User) -> Team | None:
        if member.id in Team.__pseudos and datetime.now() - Team.__pseudos[member.id]["time"] < timedelta(minutes=10):
            return Team.__pseudos[member.id]["team"]

        for role in member.roles:
            if role.id in Team.__list:
                team = Team.__list[role.id]
                team.set_player(member)
                return team
        return None

    @staticmethod
    def get_from_sheet_id(sheet_id: str, guild_id: int) -> Team | None:
        for team in Team.__list.values():
            if team.sheet_id == sheet_id and team.role.guild.id == guild_id:
                return team
        return None

    @staticmethod
    def get_from_role_id(role_id: int) -> Team | None:
        if role_id in Team.__list:
            return Team.__list[role_id]
        return None


def require_team(require=True, *, fail_message=None):
    if fail_message is None:
        fail_message = (
            "You don't have a team..."
            if require
            else "You already have a team..."
        )

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            sig_2 = inspect.signature(func)
            param_names = list(sig_2.parameters.keys())

            if "interaction" in kwargs:
                interaction = kwargs["interaction"]
            elif "interaction" in param_names:
                interaction = args[param_names.index("interaction")]
            else:
                raise RuntimeError(
                    f"require_team: no 'interaction' param found in {func.__name__}"
                )
            team = Team.get(interaction.author)

            if require:
                if team is None:
                    await interaction.response.send_message(fail_message, ephemeral=True)
                    return None
                return await func(*args, team=team, **kwargs)
            else:
                if team is not None:
                    await interaction.response.send_message(fail_message, ephemeral=True)
                    return None
                return await func(*args, **kwargs)

        # Hide 'team' from the framework's signature inspection
        sig = inspect.signature(func)
        params = [p for p in sig.parameters.values() if p.name != "team"]
        wrapper.__signature__ = sig.replace(parameters=params)

        return wrapper
    return decorator


def initialize(bot: disnake.ext.commands.Bot) -> None:
    for m in setup.SheetManager.all():
        table = m.master.players.get_all_values()
        df = pd.DataFrame(table[1:], columns=table[0])
        for index, row in df.iterrows():
            if row["Role ID"]:
                role = bot.get_guild(m.id).get_role(int(row["Role ID"]))
                if role is not None:
                    Team(
                        sheet_id=row["ID"],
                        role=role,
                        code=row["Code"],
                        logo=row["Logo"],
                        emote=row["Emote"],
                        utc_offset=row["UTC Offset"],
                        existing_player=row["Player"]
                    )
    import cogs.shared.season as season
    season.initialize(bot)



