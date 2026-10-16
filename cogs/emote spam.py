from cogs.shared.auto_imports import *
import random

emote_spams = [
    Emote.FALINKS + Emote.FALINKS,
    Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA,
    Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA,
    Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA,
    Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA,
    Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA, Emote.TANGELA + Emote.TANGELA,
    Emote.TANGELA + Emote.TANGELA + Emote.FALINKS + Emote.FALINKS,
    Emote.GYARADOS + Emote.GYRO_W1 + Emote.GYRO_W2,
    Emote.DRACO_KIFE + Emote.HUNGRY_DRUD,
    Emote.EGGY_TROLL + Emote.EGGY_TROLL + Emote.EGGY_TROLL,
    Emote.HAPPY_HAX, Emote.THUMBS_UP, Emote.MARO_COOLGUY, Emote.PORY_Y,
    Emote.SALAZLE_SMILE, Emote.SLOW_WA, Emote.SNORLAX, Emote.TORKOAL_ANGRY,
    Emote.WHIMS, Emote.GOODRA_CONFUSE, Emote.TERA_CROWN, Emote.WOOP,
    Emote.GYARADOS + Emote.GYRO_W1 + Emote.GYRO_W2 + Emote.GOODRA_CONFUSE,
    Emote.CHARGA_PET, Emote.CHARGA_PET, Emote.CHARGA_PET, Emote.CHARGA_PET,
    Emote.CHARGA_PET + Emote.CHARGA_PET,
    Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET,
    Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET,
    Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET,
    Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET + Emote.CHARGA_PET,
]

class Cog(commands.Cog, name="Emote Spam"):
    def __init__(self, bot):
        self.bot = bot
        self.charge_count = 0
        self.emote_spam.start()

    @tasks.loop(hours=1)
    async def emote_spam(self):
        if random.randrange(0, 25) == 5:
            await self.bot.get_channel(1018998738502549634).send(
                random.choice(emote_spams))

    @emote_spam.before_loop
    async def before_emote_spam(self):
        await self.bot.wait_until_ready()

    @slash()
    async def charge(self, interaction: SlashInter):
        """
        Because apparently you cant use animated emoji if you don't have nitro.
        """

        self.charge_count += 1
        s = ""
        i = self.charge_count
        f = []
        while i > 0:
            if i > 50:
                f.append(disnake.File("shared/emotes/charge50.gif"))
                i -= 50
            else:
                s += "<a:charga_pet:1125849966896762950>"
                i -= 1
        if f:
            await interaction.response.send_message(s, files=f)
        else:
            await interaction.response.send_message(s)