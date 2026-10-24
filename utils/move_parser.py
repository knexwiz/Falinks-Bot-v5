import json
import pandas as pd

with open("moves.json", "r", encoding="utf-8") as r:
    moves = json.loads(r.read())

move_list = []

flags = ['heal', 'contact', 'bullet', 'slicing', 'wind', 'sound', 'dance', 'pulse', 'bite', 'recharge', 'charge',
         'punch', 'powder']

targets = {
    'normal':	"Single",
    'allAdjacentFoes'	:"Spread",
    'self':	"Self",
    'any'	:"Single",
    'adjacentAllyOrSelf':	"Self",
    'allyTeam':	"Self",
    'adjacentAlly'	:"Self",
    'allySide':	"Self",
    'allAdjacent'	:"Spread",
    'all':	"Field",
    'scripted':"Counter",
    'adjacentFoe': "Sigle",
    'allies':	"Self",
    'randomNormal':	"Random",
    'foeSide': "Hazard"
}

for move in moves.values():
    if "isMax" in move or "isZ" in move:
        continue

    if "isNonstandard" in move and move["isNonstandard"] == "CAP":
        continue

    tags = ""



    for f in move["flags"]:
        if f in flags:
            if tags != "": tags += " | "
            tags += f

    if "secondary" in move and move["secondary"] and "status" in move["secondary"] and move["secondary"]["chance"] >= 50:
        print(move["name"])

    move_list.append(
        {
            "Name": move["name"],
            "Type": move["type"],
            "Cat": move["category"],
            "BP": move["basePower"] if move["category"] != "Status" else "-",
            "Acc": move["accuracy"] if move["accuracy"] != True else "-",
            "PP": move["pp"],
            "Priority": move["priority"],
            "Target": targets[move["target"]],
            "Tags": tags
        }
    )


df = pd.DataFrame(move_list)
df.to_csv("Move Sheet.csv", index=False)