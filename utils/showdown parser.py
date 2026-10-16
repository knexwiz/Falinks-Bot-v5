import json
import pandas
import chompjs


with open("champslearnsets") as r:
    text = str(r.read())
    champs = chompjs.parse_js_object(text)


with open("pokedex.json", "r", encoding="utf-8") as r:
    pokedex = json.loads(r.read())

with open("learnsets.json", "r", encoding="utf-8") as r:
    nat_learn = json.loads(r.read())

with open("moves.json", "r", encoding="utf-8") as r:
    moves = json.loads(r.read())


serebii_form_codes = {'Mega': "m", 'Mega-X': "mx", 'Mega-Y': "my", 'Alola': "a", 'Galar': "g", 'Hisui': "h",
                      'Paldea-Combat': "p", 'Paldea-Blaze': "b", 'Paldea-Aqua': "a", 'Paldea': "p", 'Mega-Z': "mz",
                      'Primal': "m", 'Attack': "a", 'Defense': "d", 'Speed': "s", 'Sandy': "c", 'Trash': "s",
                      'Heat': "h", 'Wash': "w", 'Frost': "f", 'Fan': "s", 'Mow': "m", 'Origin': "o", 'Sky': "s",
                      'Blue-Striped': "b", 'White-Striped': "w", 'Therian': "t", 'Black': "b", 'White': "w",
                      'Eternal': "e", 'Female': "f", '10%': "10", 'Complete': "c", 'Unbound': "u", 'Pom-Pom': "p",
                      "Pa'u": "pau", 'Sensu': "s", 'Dusk': "d", 'Midnight': "m", 'Dusk-Mane': "dm", 'Dawn-Wings': "dw",
                      'Crowned': "c", 'Rapid-Strike': "r", "ice": "i", 'Shadow': "s", 'Bloodmoon': "b", 'Roaming': "r",
                      'Wellspring': "w", 'Hearthflame': "h", 'Cornerstone': "c", 'Terastal': "t", 'Stellar': "s"}

name_form_override = {"Deoxys": "Normal", "Tornadus": "Incarnate", "Thundurus": "Incarnate", "Landorus": "Incarnate",
                      "Oricorio": "Baille", "Lycanroc": "Midday", "Urshifu": "Single-Strike", "Enamorus": "Incarnate",
                      "Ogerpon": "Teal Mask", "Meowstic": "Male", "Indeedee": "Male", "Basculegion": "Male",
                      "Oinkologne": "Male", "Hoopa": "Confined", "Shaymin": "Land", "Wormadam": "Plant"}

form_override = {'M-Mega': 'Mega', "Ice": "Ice Rider", "Shadow": "Shadow Rider", 'Curly-Mega': "Mega", "F": "Female"}

never_sub = ['Alola', 'Galar', 'Hisui']

name_exceptions = ["Calyrex", "Wormadam", "Lycanroc", "Kyurem"]

illegal_forms = ["Gmax", 'Alola-Totem', 'Cosplay', 'Rock-Star', 'Belle', 'Pop-Star', 'PhD', 'Libre', 'Original',
                 'Hoenn', 'Sinnoh', 'Unova', 'Kalos', 'Partner', 'Starter', 'World', 'Spiky-eared', 'Sunny', 'Rainy',
                 'Snowy', 'Sunshine', 'East', 'Bug', 'Dark', 'Dragon', 'Electric', 'Fairy', 'Fighting', 'Fire',
                 'Flying', 'Ghost', 'Grass', 'Ground', 'Ice', 'Poison', 'Psychic', 'Rock', 'Steel', 'Water', 'Zen',
                 'Galar-Zen', 'Summer', 'Autumn', 'Winter', 'Resolute', 'Pirouette', 'Douse', 'Shock', 'Burn', 'Chill',
                 'Bond', 'Ash', 'Icy Snow', 'Polar', 'Tundra', 'Continental', 'Garden', 'Elegant', 'Modern', 'Marine',
                 'Archipelago', 'High Plains', 'Sandstorm', 'River', 'Monsoon', 'Savanna', 'Sun', 'Ocean', 'Jungle',
                 'Fancy', 'Pokeball', 'F-Mega', 'Blade', 'Small', 'Large', 'Super', 'Neutral', 'Totem', 'School',
                 'Orange', 'Yellow', 'Green', 'Blue', 'Indigo', 'Violet', 'Meteor', 'Busted', 'Busted-Totem', 'Ultra',
                 'Original-Mega', 'Gulping', 'Gorging', 'Low-Key', 'Low-Key-Gmax', 'Antique', 'Ruby-Cream',
                 'Matcha-Cream', 'Mint-Cream', 'Lemon-Cream', 'Ruby-Swirl', 'Caramel-Swirl', 'Rainbow-Swirl', 'Noice',
                 'Hangry', 'Eternamax', 'Rapid-Strike-Gmax', 'Dada', 'Four', 'Hero', 'Droopy', 'Stretchy', 'Curly-Mega',
                 'Droopy-Mega', 'Stretchy-Mega', 'Three-Segment', 'Artisan', 'Masterpiece', 'Teal-Tera',
                 'Wellspring-Tera', 'Hearthflame-Tera', 'Cornerstone-Tera', "Sandy", "Trash", "Dusk", "White"]

complete_dex = []

for name, dex in pokedex.items():
    if "isNonstandard" in dex.keys() and (dex["isNonstandard"] == "Custom" or dex["isNonstandard"] == "CAP"):
        continue
    if "forme" in dex and dex["forme"] in illegal_forms and dex["baseSpecies"] not in name_exceptions:
        continue
    if "forme" in dex and dex["forme"] == "Alola" and dex["baseSpecies"] == "Pikachu":
        continue

    form = ""
    oform = ""
    if "forme" in dex:
        oform = dex["forme"]
        form = dex["forme"] if dex["forme"] not in form_override else form_override[dex["forme"]]
    elif dex["name"] in name_form_override: form = name_form_override[dex["name"]]

    propername = dex["baseSpecies"] if "baseSpecies" in dex else dex["name"]

    champion_moveset = []
    nat_moveset = []
    gen9_moveset = []

    name_options = [n.lower() for n in [name+oform, propername+oform, name, propername]]
    if form in never_sub: name_options = [n.lower() for n in [name+oform, propername+oform]]
    if propername == "Mega Floette": name_options["Floette Eternal"]

    for n in name_options:
        if n in champs:
            champion_moveset = champs[n]["learnset"].keys()
            break


    for n in name_options:
        if n in nat_learn:
            if "learnset" not in nat_learn[n]:
                continue
            nat_moveset = nat_learn[n]["learnset"].keys()
            for move, gens in nat_learn[n]["learnset"].items():
                for g in gens:
                    if g[0] == "9":
                        gen9_moveset.append(move)
            break

    tag = ""
    if propername.lower() in pokedex and "tags" in pokedex[propername.lower()]:
        tag = pokedex[propername.lower()]["tags"][0]
    elif "tags" in dex:
        tag = dex["tags"][0]

    all_movesets=[champion_moveset, gen9_moveset, nat_moveset]

    if dex["name"] == "Toxtricity":
        for ms in all_movesets:
            ms.append("Parabolic Charge")
            ms.append("Magnetic Flux")
            dex["abilities"].append("Minus")

    if dex["name"] == "Squawkabilly":
        dex["abilities"].append("Sheer Force")

    complete_dex.append({
        "num": f"{dex["num"]:03d}-{serebii_form_codes[form]}" if form in serebii_form_codes else f"{dex["num"]:03d}",
        "name": propername,
        "form": form,
        "type1": dex["types"][0] if len(dex["types"]) == 2 else "",
        "type2": dex["types"][0] if len(dex["types"]) == 1 else "",
        "type3": dex["types"][1] if len(dex["types"]) == 2 else "",
        **dex["baseStats"],
        "abilities": "|".join(dex["abilities"].values()),
        "tags":  tag,
        "color": dex["color"],
        "champions": "|".join([moves[m]["name"] for m in champion_moveset]),
        "gen9": "|".join([moves[m]["name"] for m in gen9_moveset]),
        "natdex": "|".join([moves[m]["name"] for m in nat_moveset]),
    })


df = pandas.DataFrame(complete_dex)
df.to_csv("Pokemon Master Sheet.csv", index=False)
