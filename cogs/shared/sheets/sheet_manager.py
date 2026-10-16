import gspread
import json
from pathlib import Path

script_dir = Path(__file__).parent

gspread_client = gspread.service_account(script_dir / 'gspread.json')

f = open(script_dir / 'guild_masters.json', 'r')
guild_masters = json.load(f)
f.close()

class SheetManager:
    __managers: dict[int, SheetManager] = {}

    def __init__(self, guild_id: int, master: gspread.Spreadsheet):
        self.id = int(guild_id)
        self.master = master
        self.master.players = self.master.worksheet("Players")
        self.master.seasons = self.master.worksheet("Seasons")
        self.seasons = []
        for row in self.master.seasons.get_all_values():
            if row[2] == "TRUE":
                try:
                    self.seasons.append(gspread_client.open_by_key(row[1]))
                except gspread.exceptions.APIError, PermissionError:
                    print("Failed to open spreadsheet", self.id, self.master.title)



        SheetManager.__managers[self.id] = self

    @staticmethod
    def all() -> list[SheetManager]:
        return list(SheetManager.__managers.values())

    @staticmethod
    def guild_list() -> list[int]:
        return list(SheetManager.__managers.keys())

    @staticmethod
    def get(guild_id: int) -> SheetManager:
        return SheetManager.__managers[guild_id]

get_active_guild_ids = lambda: SheetManager.guild_list()

for g, s in guild_masters.items():
    try:
        sheet = gspread_client.open_by_key(s)
        SheetManager(g, sheet)
    except gspread.exceptions.APIError:
        print("Failed to open master:",g,s)