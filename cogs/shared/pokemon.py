import disnake
from itertools import islice
from cogs.shared.sheets import sheet_manager
from cogs.shared.emotes.emotes import get_image_bytes, TypeEmote

poke_master_sheet_id = "1J-HkT76l6ESj98K2iubS1tNtV1138X_7n_1-6ZDxn_8"

poke_master = sheet_manager.gspread_client.open_by_key(poke_master_sheet_id)

form_aliases: Dict[str, list[str]] = {
    "Mega": ["M"],
    "Mega-X": ["MX", "Mega X", "X"],
    "Mega-Y": ["MY", "Mega Y", "Y"],
    "Mega-Z": ["MZ", "Mega Z", "Z"],

    "Alola": ["A", "Alolan"],
    "Galar": ["G", "Galarian"],
    "Hisui": ["H", "Hisuian"],
    "Paldea": ["P", "Paldean"],

    "Male": ["M"],
    "Female": ["F"],

    "Paldea-Combat": ["Paldea Combat", "Paldean Combat", "Combat",
                      "Paldea Combat Breed", "Paldean Combat Breed", "Combat Breed"],
    "Paldea-Blaze": ["Paldea Blaze", "Paldean Blaze", "Blaze",
                     "Paldea Blaze Breed", "Paldean Blaze Breed", "Blaze Breed"],
    "Paldea-Aqua": ["Paldea Aqua", "Paldean Aqua", "Aqua",
                    "Paldea Aqua Breed", "Paldean Aqua Breed", "Aqua Breed"],

    "Incarnate": ["I"],
    "Therian": ["T"],

    "Eternal": ["E", "Eternal Flower"],

    "Dusk-Mane": ["Dusk Mane", "DM"],
    "Dawn-Wings": ["Dawn Wings", "DW"],

    "Single-Strike": ["Single Strike", "Single", "Dark"],
    "Rapid-Strike": ["Rapid Strike", "Rapid", "Water"],

    "Ice Rider": ["Ice"],
    "Shadow Rider": ["Shadow"],

    "Teal Mask": ["Teal"],
    "Wellspring": ["Wellspring Mask"],
    "Hearthflame": ["Hearthflame Mask"],
    "Cornerstone": ["Cornerstone Mask"],
}

_colors = {
    "Green": disnake.Color.green(),
    "Red": disnake.Color.red(),
    "Black": disnake.Color(0x000000),
    "Blue": disnake.Color.blue(),
    "White": disnake.Color(0xFFFFFF),
    "Brown": disnake.Color.dark_orange(),
    "Yellow": disnake.Color.yellow(),
    "Purple": disnake.Color.purple(),
    "Pink": disnake.Color.fuchsia(),
    "Gray": disnake.Color.light_gray(),
}

class Pokemon:
    __all: list[Pokemon] = []
    __emote_guilds: list[disnake.Guild] | None = None

    def __init__(self,
                 dex:str,
                 name:str,
                 form:str,
                 types: list[str],
                 stats: dict[str, int],
                 abilities: list[str],
                 color: disnake.Color,
                 ):
        self.dex: str = dex
        self.name: str = name
        self.form: str = form
        self.types: list[str] = types
        self.stats: dict[str, int] = stats
        self.abilities: list[str] = abilities
        self.color: disnake.Color = color
        self.__emote_cached = None

        a = [str(self), self.dex]

        if self.form:
            a.append(f"{self.form} {self.name}")
            a.append(f"{self.form}-{self.name}")
            a.append(f"{self.name}-{self.form}")

            if self.form in form_aliases:
                for f in form_aliases[self.form]:
                    a.append(f"{f} {self.name}")
                    a.append(f"{f}-{self.name}")
                    a.append(f"{self.name} {f}")
                    a.append(f"{self.name}-{f}")

        self.aliases = [p.casefold() for p in a]

        Pokemon.__all.append(self)

    def __str__(self):
        if self.form:
            if self.form.startswith("Mega"):
                if self.form == "Mega":
                    return f"Mega {self.name}"
                else:
                    return f"Mega {self.name} {self.form[-1]}"
            else:
                return f"{self.name} {self.form}"
        else:
            return self.name

    def __eq__(self, other):
        if isinstance(other, Pokemon):
            return self.dex == other.dex
        elif isinstance(other, str):
            o = other.casefold()
            return True if o in self.aliases else self.dex == o
        else:
            return NotImplemented

    @staticmethod
    def pass_guilds(guild_list: list[disnake.Guild]):
        Pokemon.__emote_guilds = guild_list

    @staticmethod
    def get(poke: str) -> Pokemon | None:
        return next((mon for mon in Pokemon.__all if mon == poke and isinstance(mon, Pokemon)), None)

    @property
    def emote(self) -> str | None:
        if self.__emote_cached is not None:
            return self.__emote_cached
        else:
            if Pokemon.__emote_guilds is not None:
                for guild in Pokemon.__emote_guilds:
                    for e in guild.emojis:
                        if e.name == self.dex.replace("-", "_"):
                            self.__emote_cached = str(e)
                            return self.__emote_cached
        return None

    @property
    def embed(self) -> disnake.Embed:
        e = disnake.Embed(
            title=str(self),
            color=self.color,
            description=" ".join([f"{getattr(TypeEmote, t.upper())}`{t.upper():^8}`" for t in self.types]),
        )

        e.set_thumbnail(self.image_url)
        e.set_footer(text=self.dex, icon_url=self.icon_url)

        e.add_field(name=f"Abilit{"y" if len(self.abilities) == 1 else "ies"}",
                    value=", ".join(self.abilities), inline=False)

        stats_head = " | ".join([t.rjust(3) for t in self.stats.keys()])
        stats_body = " | ".join([f"{s:>3}" for s in self.stats.values()])
        e.add_field(name="Stats", value=f"` {stats_head} `\n` {stats_body} `", inline=False)

        return e

    @property
    def image_url(self) -> str:
        return "https://www.serebii.net/pokemonhome/pokemon/" + self.dex + ".png"

    @property
    def icon_url(self) -> str:
        return "https://www.serebii.net/pokedex-champions/icon/" + self.dex + ".png"

    @property
    def mention(self) -> str:
        if self.emote:
            return f"{self.emote} {self}"
        else:
            return f"{self}"

    def partial_match(self, string: str) -> bool:
        for alias in self.aliases:
            if string in alias:
                return True
        return False

    async def fetch_emote(self):
        """Fetches this Pokémon's emote"""
        if self.emote is None and Pokemon.__emote_guilds:
            for guild in Pokemon.__emote_guilds:
                try:
                    emote = await guild.create_custom_emoji(name=self.dex.replace("-", "_"),
                                          image=get_image_bytes(self.image_url))
                    self.__emote_cached = str(emote)
                    return
                except disnake.HTTPException, disnake.NotFound, TypeError, ValueError:
                    pass

    @staticmethod
    async def autocomplete(interaction: disnake.ApplicationCommandInteraction, user_input: str):
        i = user_input.casefold()
        return [str(poke) for poke in list(islice(filter(lambda p: p.partial_match(i), Pokemon.__all),5))]


print("Loading Pokemon...")
_stat_keys = ["HP","ATK","DEF","SPA","SPD","SPE"]
for row in poke_master.worksheet("Current").get_all_values()[1:]:
    pokemon = Pokemon(
        dex=row[1],
        name=row[2],
        form=row[3],
        types=[row[4], row[6]] if row[5] == "" else [row[5]],
        stats=dict(zip(_stat_keys, row[7:13])),
        abilities=row[13].split("|"),
        color=_colors[row[15]]
    )
print("   Done")