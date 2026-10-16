import disnake
from disnake.ext import commands, tasks
from disnake.ext.commands import slash_command as slash
from disnake import CommandInteraction as SlashInter

from disnake.ui import Modal
from disnake import ModalInteraction as ModalInter

from disnake.ui import View
from disnake import MessageInteraction as ViewInter
from disnake.ui import button as add_button
from disnake.ui import string_select as add_string_select
from disnake.ui import Button
from disnake import ButtonStyle

from cogs.shared.emotes.emotes import Emote, TypeEmote
from cogs.shared.team import require_team
from cogs.shared.team import Team
from cogs.shared.season import Season
from cogs.shared.season import Match
from cogs.shared.team import initialize as initialize_teams
from cogs.shared.github import upload_to_git

from cogs.shared.season import SeasonSelector

from cogs.shared.pokemon import Pokemon

from cogs.shared.sheets.sheet_manager import get_active_guild_ids

from disnake.ui import Label, TextInput, StringSelect, FileUpload, RoleSelect

from typing import Any