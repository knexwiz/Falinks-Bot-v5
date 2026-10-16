from enum import StrEnum
from io import BytesIO
import requests

emote_guilds = [
    1128537807191806012,
    1126625155112775813,
    809527517835952190,
    1054186269405610076,
    1054185765233496085,
    1054184993146019942,
    1012176533084971038
]

def get_image_bytes(url):
    r = requests.get(url)
    if r.status_code in range(200, 299):
        img = BytesIO(r.content)
        b = img.getvalue()
        return b
    else:
        print(f'Something went wrong. Response: {r.status_code}')
        return None


class Emote(StrEnum):
    FALINKS = "<a:falinks:887379443822252082>"
    THUMBS_UP = "<:hawlucha_thumpsup:1008434739969007726>"
    POKEBALL = "<:pokeball:1012180033198104657>"

    TANGELA = "<:tangela_shoes:1008434764417617920>"
    GYARADOS = "<:gyarados_scary:1008434755378884658>"
    GYRO_W1 = "<:gyarados_watergun1:1008434756842704906>"
    GYRO_W2 = "<:gyarados_watergun2:1008434758818205886>"
    DRACO_KIFE = "<:dracozolt_knife:1008434760768565339>"
    HUNGRY_DRUD = "<:hungry_hungry_druddigon:1008434762798600202>"
    EGGY_TROLL = "<:eggytroll:1008434767659794532>"
    HAPPY_HAX = "<:happy_hax:1008436004115456000>"
    MARO_COOLGUY = "<:marowak_coolguy:1008434753806016652>"
    PORY_Y = "<:poryY:1011496058620235900>"
    SALAZLE_SMILE = "<:salazzle_smile:1008434752228962344>"
    SLOW_WA = "<:slowpoke_waawaa:1008434747044798564>"
    SNORLAX = "<:snorlax_eatsleep_english:1008434745014763550>"
    TORKOAL_ANGRY = "<:torkoal_angry:1008434741596397690>"
    WHIMS = "<:whimsicott_charm:1008434748756070530>"
    CHARGA_PET = "<a:charga_pet:1125849966896762950>"
    GOODRA_CONFUSE = "<:goodra_confusion:1008434750328930484>"
    TERA_CROWN = "<:terapagos_crown:1465089789794451602>"
    WOOP = "<:__WOOP:1241815615551832145>"
    VANILUXE_EVIL = "<:vanilEVIL:1191995413037842522>"


class TypeEmote(StrEnum):
    NORMAL   = "<:Normal_icon_SV:1560337410171207720>"
    FIRE     = "<:Fire_icon_SV:1560337389803675779>"
    WATER    = "<:Water_icon_SV:1560337421177065633>"
    GRASS    = "<:Grass_icon_SV:1560337394278989944>"
    ELECTRIC = "<:Electric_icon_SV:1560337383797555302>"
    ICE      = "<:Ice_icon_SV:1560337407277142077>"
    FIGHTING = "<:Fighting_icon_SV:1560337387853320242>"
    POISON   = "<:Poison_icon_SV:1560337414000607364>"
    GROUND   = "<:Ground_icon_SV:1560337549455654912>"
    FLYING   = "<:Flying_icon_SV:1560337391523340400>"
    PSYCHIC  = "<:Psychic_icon_SV:1560335195343683685>"
    BUG      = "<:Bug_icon_SV:1560337378651013222>"
    ROCK     = "<:Rock_icon_SV:1560337418589053079>"
    GHOST    = "<:Ghost_icon_SV:1560337392718839818>"
    DRAGON   = "<:Dragon_icon_SV:1560337382115381290>"
    DARK     = "<:Dark_icon_SV:1560337380517355610>"
    STEEL    = "<:Steel_icon_SV:1560337420094939227>"
    FAIRY    = "<:Fairy_icon_SV:1560337385101983855>"