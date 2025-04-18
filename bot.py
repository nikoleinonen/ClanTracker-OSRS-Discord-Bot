import discord
from discord import app_commands
from discord.app_commands import Choice
from dotenv import load_dotenv
import os
import json
import secrets
import string
import asyncio
import logging
import traceback
import re
from typing import Dict, Optional, Set, Tuple, List, Any
import random
from collections import OrderedDict
from aiohttp import web
import io

# --- Logging Setup (Stream Only for Production) ---
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log_level = logging.INFO

# Configure root logger
logger = logging.getLogger()
logger.setLevel(log_level)

# Remove existing handlers if any (important for re-running)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add Console Handler (stdout/stderr)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# --- Configuration ---
load_dotenv() # (Local Development Only)

# Bot Settings
TOKEN: Optional[str] = os.getenv('DISCORD_BOT_TOKEN')
CATEGORY_NAME: str = os.getenv('CLANTRACKER_CATEGORY_NAME', "ClanTracker")
INFO_CHANNEL_NAME: str = os.getenv('CLANTRACKER_INFO_CHANNEL', "ct-info")
CONFIG_CHANNEL_NAME: str = os.getenv('CLANTRACKER_CONFIG_CHANNEL', "ct-config")
MANUAL_POINTS_CHANNEL_NAME: str = os.getenv('CLANTRACKER_MANUAL_POINTS_CHANNEL', "ct-manual-points")
COMMANDS_CHANNEL_NAME: str = os.getenv('CLANTRACKER_COMMANDS_CHANNEL', "ct-commands")
CHANNEL_NAMES: List[str] = [
    INFO_CHANNEL_NAME,
    CONFIG_CHANNEL_NAME,
    MANUAL_POINTS_CHANNEL_NAME,
    COMMANDS_CHANNEL_NAME
]

# --- Dynamic Status Configuration ---
STATUS_GUILD_ID_STR: Optional[str] = os.getenv('STATUS_GUILD_ID')
STATUS_CHANNEL_ID_STR: Optional[str] = os.getenv('STATUS_CHANNEL_ID')
STATUS_GUILD_ID: Optional[int] = int(STATUS_GUILD_ID_STR) if STATUS_GUILD_ID_STR and STATUS_GUILD_ID_STR.isdigit() else None
STATUS_CHANNEL_ID: Optional[int] = int(STATUS_CHANNEL_ID_STR) if STATUS_CHANNEL_ID_STR and STATUS_CHANNEL_ID_STR.isdigit() else None
DEFAULT_STATUS_MESSAGE: str = os.getenv('DEFAULT_BOT_STATUS', ":wine_glass:")

# --- Database Configuration ---
INSPECT_DB_GUILD_ID_STR: Optional[str] = os.getenv('INSPECT_DATABASE_GUILD_ID')
INSPECT_DB_CHANNEL_ID_STR: Optional[str] = os.getenv('INSPECT_DATABASE_CHANNEL_ID')
INSPECT_DB_GUILD_ID: Optional[int] = int(INSPECT_DB_GUILD_ID_STR) if INSPECT_DB_GUILD_ID_STR and INSPECT_DB_GUILD_ID_STR.isdigit() else None
INSPECT_DB_CHANNEL_ID: Optional[int] = int(INSPECT_DB_CHANNEL_ID_STR) if INSPECT_DB_CHANNEL_ID_STR and INSPECT_DB_CHANNEL_ID_STR.isdigit() else None

AUTHORIZED_USERS_STR: Optional[str] = os.getenv('AUTHORIZED_USERS')
AUTHORIZED_USERNAMES: Set[str] = set() # Initialize as empty set

# Data Storage
DATA_DIR: str = os.getenv('DATA_DIR', 'data')
IDENTIFIER_FILE_NAME: str = "clan_identifiers.json"
IDENTIFIER_FILE: str = os.path.join(DATA_DIR, IDENTIFIER_FILE_NAME)
IDENTIFIER_LENGTH: int = 8

# Responses
RESPONSES_DIR: str = "commands"
HYD_FILE_NAME: str = "hyd.txt"
HYD_FILE_PATH: str = os.path.join(RESPONSES_DIR, HYD_FILE_NAME)

# External Links
GITHUB_APP_README_MD_LINK: str = os.getenv('GITHUB_APP_README_MD_LINK', "")
GITHUB_BOT_README_MD_LINK: str = os.getenv('GITHUB_BOT_README_MD_LINK', "")
OFFICIAL_DISCORD_LINK: str = os.getenv('OFFICIAL_DISCORD_LINK', "https://discord.gg/y4tmVW9p")

# Bot Discord Permissions
# -> Manage Channels, View Channels, Send Messages, Read Message History, Manage Messages
BOT_PERMISSIONS: int = 76816

# --- Global Storage for Identifiers ---
server_identifiers: Dict[str, Dict[str, str]] = {}


# --- Initial Message Content Constants ---
# These constants define the text content for messages sent on guild join.
# They use .format() placeholders like {variable_name} which will be filled in later.
# Naming Convention: MSG_{Number}_{ChannelVariableName}

# ------------------------------------------------------
# === Messages for INFO_CHANNEL_NAME ('ct-info') ===
# ------------------------------------------------------
MSG_1_INFO_CHANNEL_NAME = (
    "# **Thank you for using ClanTracker OSRS!**\n"
    "**--------------------------------------------------------------**\n"
    "### Your unique Clan Identifier: `{clan_identifier}`\n"
    "-# Share this with your clan members!\n\n\n"
    "I have automatically created text channels for you under **{CATEGORY_NAME}** category:\n"
    "1. `#{INFO_CHANNEL_NAME}`\n"
    "2. `#{CONFIG_CHANNEL_NAME}`\n"
    "3. `#{MANUAL_POINTS_CHANNEL_NAME}`\n"
    "4. `#{COMMANDS_CHANNEL_NAME}`\n"
    "ㅤ"
)

MSG_2_INFO_CHANNEL_NAME = (
    "ㅤ\n"
    "# Documentation\n\n"
    "ClanTracker OSRS <:GitHub:1362721053713109015> [**LINK**]({GITHUB_APP_README_MD_LINK})\n"
    "ClanTracker OSRS Discord Bot <:GitHub:1362721053713109015> [**LINK**]({GITHUB_BOT_README_MD_LINK})\n\n\n"
    "# [Official Discord]({OFFICIAL_DISCORD_LINK})"
)

# ------------------------------------------------------
# === Messages for CONFIG_CHANNEL_NAME ('ct-config') ===
# ------------------------------------------------------
MSG_1_CONFIG_CHANNEL_NAME = (
    "```ini\n"
    "[discord]\n"
    "clan_identifier = {clan_identifier}\n"
    "```"
)

# --------------------------------------------------------------------
# === Messages for MANUAL_POINTS_CHANNEL_NAME ('ct-manual-points') ===
# --------------------------------------------------------------------
MSG_1_MANUAL_POINTS_CHANNEL_NAME = (
    "# **Manual Points**\n\n"
    "Post manual points here. **Use one message per player.** Edit the existing message to update that player's info!\n"
    "-# Updates are not sent automatically, users must manually update the data or restart the application.\n\n"
    "**Format and example of 2 different players:**\n"
    "```ini\n"
    "[TurboGigaChad21]\n"
    "grandmaster_ca = true\n"
    "has_life = false\n"
    "killed_zuk_blindfolded = true\n"
    "thinks_forestry_was_top_notch_update = false\n"
    "```\n"
    "```ini\n"
    "[Burger73]\n"
    "grandmaster_ca = false\n"
    "has_life = true\n"
    "killed_zuk_blindfolded = false\n"
    "thinks_forestry_was_top_notch_update = true\n"
    "```\n"
    "etc...\n\n"
    "Documentation <:GitHub:1362721053713109015> [**LINK**]({GITHUB_APP_README_MD_LINK})\n\n"
    "## ***REMOVE THIS MESSAGE***\n\n"
    "-# Leave this channel empty if you're not using manual points."
)

# ----------------------------------------------------------
# === Messages for COMMANDS_CHANNEL_NAME ('ct-commands') ===
# ----------------------------------------------------------
MSG_1_COMMANDS_CHANNEL_NAME = (
    "Bot commands for ClanTracker should be used in this channel.\n"
    "Type `/` to see available commands.\n\n"
    "Documentation <:GitHub:1362721053713109015> [**LINK**]({GITHUB_BOT_README_MD_LINK})"
)

# --- Structure Defining Which Messages Go Where ---
# This dictionary maps the channel name VARIABLE to a list of message constants
# defined above, in the order they should be sent.
# TO EDIT MESSAGES:
# 1. Change the content in the MSG_... constants above.
# 2. Add/Remove/Reorder the constants in the lists below.
INITIAL_MESSAGES_BY_CHANNEL: Dict[str, List[str]] = {
    INFO_CHANNEL_NAME: [
        MSG_1_INFO_CHANNEL_NAME,
        MSG_2_INFO_CHANNEL_NAME
    ],
    CONFIG_CHANNEL_NAME: [
        MSG_1_CONFIG_CHANNEL_NAME
    ],
    MANUAL_POINTS_CHANNEL_NAME: [
        MSG_1_MANUAL_POINTS_CHANNEL_NAME,
    ],
    COMMANDS_CHANNEL_NAME: [
        MSG_1_COMMANDS_CHANNEL_NAME,
    ]
}


# --- Helper Functions (Bot & API) ---

def load_identifiers() -> None:
    global server_identifiers
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        logger.info(f"Ensured data directory exists: {DATA_DIR}")

        with open(IDENTIFIER_FILE, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        validated_data: Dict[str, Dict[str, str]] = {}
        for gid, data in loaded_data.items():
            if isinstance(gid, str) and gid.isdigit() and \
               isinstance(data, dict) and \
               'identifier' in data and isinstance(data['identifier'], str) and \
               'name' in data and isinstance(data['name'], str):
                validated_data[gid] = data
            else:
                logger.warning(f"Invalid format for guild ID '{gid}' in {IDENTIFIER_FILE}. Skipping.")
        server_identifiers = validated_data
        logger.info(f"Loaded {len(server_identifiers)} valid identifiers from {IDENTIFIER_FILE}")
    except FileNotFoundError:
        logger.warning(f"{IDENTIFIER_FILE} not found. Starting with empty identifiers. Will be created if needed.")
        server_identifiers = {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding {IDENTIFIER_FILE}. Starting with empty identifiers. Please check/delete the file.", exc_info=True)
        server_identifiers = {} # Start fresh if file is corrupt
    except Exception as e:
        logger.error(f"An unexpected error occurred loading identifiers: {e}", exc_info=True)
        server_identifiers = {}

def save_identifiers() -> None:
    global server_identifiers
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(IDENTIFIER_FILE, 'w', encoding='utf-8') as f:
            json.dump(server_identifiers, f, indent=4)
        logger.info(f"Saved {len(server_identifiers)} identifiers to {IDENTIFIER_FILE}")
    except Exception as e:
        logger.error(f"Error saving identifiers to {IDENTIFIER_FILE}: {e}", exc_info=True)

def generate_unique_identifier(existing_identifiers_set: Set[str]) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        identifier = ''.join(secrets.choice(alphabet) for _ in range(IDENTIFIER_LENGTH))
        if identifier not in existing_identifiers_set:
            return identifier

# --- API Helper Functions ---

def find_guild_id_by_identifier(clan_identifier: str) -> Optional[str]:
    """Finds the Guild ID string associated with a clan identifier."""
    global server_identifiers # Use the bot's loaded identifiers
    for guild_id, data in server_identifiers.items():
        if data.get('identifier') == clan_identifier:
            return guild_id
    return None

def find_guild_info_by_identifier(clan_identifier: str) -> Optional[Tuple[str, str]]:
    """Finds the Guild ID string and Guild Name associated with a clan identifier."""
    global server_identifiers
    for guild_id, data in server_identifiers.items():
        if data.get('identifier') == clan_identifier:
            return guild_id, data.get('name', 'Unknown Name') # Return ID and Name
    return None

def clean_message_content(content: str) -> str:
    """Removes code blocks and surrounding whitespace/backticks."""
    pattern = r'```(?:ini\n)?(.*?)```'
    cleaned = re.sub(pattern, r'\1', content, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip().strip('`')

def parse_ini_data(messages: list[discord.Message]) -> OrderedDict[str, OrderedDict[str, Optional[str]]]:
    """
    Parses INI-like data from Discord messages, preserving the order
    of sections and keys as they appear from oldest to newest message.
    """
    structured_config: OrderedDict[str, OrderedDict[str, Optional[str]]] = OrderedDict()
    full_config_string = ""
    # Process messages from oldest to newest (top to bottom in Discord)
    for message in reversed(messages):
        cleaned_content = clean_message_content(message.content)
        if cleaned_content:
            full_config_string += cleaned_content + "\n"

    if not full_config_string.strip():
        logger.debug("No valid INI content found in messages after cleaning.")
        return OrderedDict()

    current_section_name: Optional[str] = None
    current_section_dict: Optional[OrderedDict[str, Optional[str]]] = None
    line_number = 0

    for line in full_config_string.splitlines():
        line_number += 1
        line = line.strip()

        if not line or line.startswith('#') or line.startswith(';'):
            continue

        section_match = re.match(r'^\[(.*?)\]$', line)
        if section_match:
            current_section_name = section_match.group(1).strip()
            if not current_section_name:
                 logger.warning(f"Skipping empty section header '[]' at line ~{line_number}")
                 current_section_name = None
                 current_section_dict = None
                 continue
            if current_section_name in structured_config:
                logger.debug(f"Duplicate section '[{current_section_name}]' found at line ~{line_number}. Merging keys.")
                current_section_dict = structured_config[current_section_name]
            else:
                current_section_dict = OrderedDict()
                structured_config[current_section_name] = current_section_dict
            continue

        kv_match = re.match(r'^([^#;=\s][^=:]*?)\s*(?:[:=]\s*(.*))?$', line)
        if kv_match:
            key = kv_match.group(1).strip()
            value = kv_match.group(2)
            value = value.strip() if value is not None else None

            if current_section_dict is None:
                logger.warning(f"Key '{key}' found outside of any section at line ~{line_number}. Skipping.")
                continue

            if key in current_section_dict:
                logger.debug(f"Duplicate key '{key}' in section '[{current_section_name}]' at line ~{line_number}. Overwriting.")

            current_section_dict[key] = value
            continue

        logger.warning(f"Could not parse line ~{line_number}: '{line}'. Skipping.")

    if not structured_config:
         logger.debug("Parsing completed, but no valid sections or keys were found.")

    return structured_config


# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True # Needed for reading message content for status & legacy commands & API
intents.guilds = True
intents.guild_messages = True # Needed for on_message and on_message_delete in guilds

# --- Client Setup ---
# Use a Client subclass to easily integrate setup_hook
class ClanTrackerClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.web_server_task = None # To hold the web server task

    async def setup_hook(self) -> None:
        """Called after login but before connecting to the Gateway. Ideal for setup."""
        logger.info("Running setup_hook...")

        # --- Start Web Server ---
        # Create the task but don't await it here, let it run in the background
        self.web_server_task = self.loop.create_task(self.start_web_server())

        # --- Sync Application Commands ---
        try:
            # Sync globally - might take time to propagate initially
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} application command(s) globally.")
        except Exception as e:
            logger.error(f"Failed to sync application commands: {e}", exc_info=True)

    async def on_ready(self) -> None:
        """Fires when the bot successfully connects to Discord and sets presence."""
        logger.info(f'Bot is ready! Logged in as {self.user} (ID: {self.user.id})')

        # --- Initial Status Update ---
        await update_status_from_channel(self)

        # Log invite URL
        if self.user:
            invite_url = f'https://discord.com/api/oauth2/authorize?client_id={self.user.id}&permissions={BOT_PERMISSIONS}&scope=bot%20applications.commands'
            logger.info(f'Invite URL: {invite_url}')
        else:
            logger.warning("Could not determine client user ID for invite link.")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Handles bot joining a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        logger.info(f"Starting setup process in '{guild.name}'...")

        # 1. Ensure Identifier exists or is created/saved
        clan_identifier = await _ensure_identifier(guild)
        if clan_identifier is None:
             logger.error(f"Failed to generate or retrieve a clan identifier for '{guild.name}'. Aborting setup.")
             await _notify_permission_error(guild, "Internal State", "generate clan identifier (contact support)")
             return

        # 2. Setup Category and Channels
        category, channels = await _setup_category_and_channels(guild)
        if category is None:
            logger.error(f"Failed to create or find category '{CATEGORY_NAME}' in '{guild.name}'. Setup incomplete.")
            return

        missing_channels = [name for name, chan in channels.items() if chan is None]
        if missing_channels:
             logger.warning(f"One or more required channels could not be created or found in '{guild.name}': {', '.join(missing_channels)}. Some functionality might be impaired.")
             if CONFIG_CHANNEL_NAME in missing_channels or COMMANDS_CHANNEL_NAME in missing_channels:
                  await _notify_permission_error(guild, "Manage Channels", f"create required channels ({', '.join(missing_channels)})")

        # 3. Send Initial Messages
        bot_perms = guild.me.guild_permissions
        if not bot_perms.send_messages or not bot_perms.read_message_history:
            perm_list = []
            if not bot_perms.send_messages: perm_list.append("Send Messages")
            if not bot_perms.read_message_history: perm_list.append("Read Message History")
            logger.warning(f"Missing critical permissions ({', '.join(perm_list)}) in '{guild.name}'. Cannot reliably send initial messages.")
            await _notify_permission_error(guild, ', '.join(perm_list), "send initial setup messages")
        else:
            await _send_initial_messages(guild, channels, clan_identifier)

        logger.info(f"Setup process finished for guild: {guild.name}")

    async def on_message(self, message: discord.Message) -> None:
        """Handles incoming messages."""
        if message.author.bot or message.guild is None:
            return

        # --- Status Channel Check ---
        if STATUS_GUILD_ID and STATUS_CHANNEL_ID and \
           message.guild.id == STATUS_GUILD_ID and message.channel.id == STATUS_CHANNEL_ID:
            logger.info(f"Message received in status channel ({message.channel.id}). Triggering status update.")
            await update_status_from_channel(self)
            return

        # --- !ping - bot response speed testing ---
        if message.content.strip().lower() == "!ping":
            if message.channel.name == COMMANDS_CHANNEL_NAME:
                try:
                    await message.channel.send("Pong!")
                    logger.debug(f"Responded to !ping in #{message.channel.name} (Guild: {message.guild.name})")
                except discord.Forbidden:
                    logger.warning(f"Cannot send Pong! response in #{message.channel.name} (Guild: {message.guild.name}) - Missing Send Messages permission.")
                except Exception as e:
                    logger.error(f"Error responding to !ping in {message.channel.name}: {e}", exc_info=True)
            else:
                 logger.debug(f"Ignored !ping command outside #{COMMANDS_CHANNEL_NAME} in guild {message.guild.name}")

    async def on_message_delete(self, message: discord.Message) -> None:
        """Handles message deletion."""
        if message.guild is None:
            return

        # --- Status Channel Check ---
        if STATUS_GUILD_ID and STATUS_CHANNEL_ID and \
           message.guild.id == STATUS_GUILD_ID and message.channel.id == STATUS_CHANNEL_ID:
            logger.info(f"Message deleted in status channel ({message.channel.id}). Triggering status update.")
            await asyncio.sleep(1.5)
            await update_status_from_channel(self)

    # --- AIOHTTP Web Server Methods ---
    async def start_web_server(self):
        """Sets up and starts the aiohttp web server."""
        app = web.Application()
        # Pass 'self' (the client instance) to the handler if needed, or access globally
        app.router.add_get('/api/clan_info/{clan_identifier}', self.get_clan_info_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        # Railway provides the PORT env var, default to 8080 for local dev
        port = int(os.getenv('PORT', 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        logger.info(f"Starting web server on port {port}...")
        try:
            await site.start()
            logger.info("Web server started successfully.")
            # Keep it running until the bot closes
            # await asyncio.Event().wait() # This would block, not needed here as it runs in background task
        except Exception as e:
            logger.error(f"Failed to start web server: {e}", exc_info=True)
            # Optionally handle cleanup or bot shutdown if API is critical
            # await self.close()

    async def get_clan_info_handler(self, request: web.Request):
        """Handles API requests for clan info."""
        clan_identifier = request.match_info.get('clan_identifier', None)
        if not clan_identifier:
            logger.warning("[API] Request missing clan_identifier.")
            return web.json_response({"error": "Missing clan_identifier path parameter"}, status=400)

        logger.info(f"[API] Received request for clan identifier: {clan_identifier}")

        # 1. Find Guild ID using the bot's loaded data
        guild_id_str = find_guild_id_by_identifier(clan_identifier) # Use helper
        if not guild_id_str:
            logger.warning(f"[API] Clan identifier not found: {clan_identifier}")
            return web.json_response({"error": f"Clan Identifier '{clan_identifier}' not found."}, status=404)

        try:
            guild_id = int(guild_id_str)
        except ValueError:
             logger.error(f"[API] Invalid Guild ID '{guild_id_str}' found for identifier '{clan_identifier}'.")
             return web.json_response({"error": "Internal Server Error: Invalid Guild ID associated."}, status=500)

        # 2. Get guild using the BOT'S client object
        # Ensure bot is ready before accessing cache heavily
        await self.wait_until_ready()
        guild = self.get_guild(guild_id)
        if guild is None:
            # Optional: Try fetching if not in cache, but get_guild is usually sufficient
            logger.warning(f"[API] Guild {guild_id} not found in bot's cache for identifier '{clan_identifier}'. Attempting fetch...")
            try:
                guild = await self.fetch_guild(guild_id) # Use bot's fetch_guild
            except discord.NotFound:
                 logger.error(f"[API] Guild {guild_id} not found via fetch.")
                 return web.json_response({"error": f"Discord Server (Guild ID: {guild_id}) could not be found."}, status=404)
            except discord.Forbidden:
                 logger.error(f"[API] Forbidden error fetching guild {guild_id}.")
                 return web.json_response({"error": f"Forbidden: Bot lacks permissions to access server details (Guild ID: {guild_id})."}, status=403)
            except Exception as e:
                 logger.error(f"[API] Error fetching guild {guild_id}: {e}", exc_info=True)
                 return web.json_response({"error": "Internal Server Error: Failed fetching server details."}, status=500)

        logger.info(f"[API] Found Guild: {guild.name} (ID: {guild.id})")

        config_data = OrderedDict()
        manual_points_data = OrderedDict()

        # --- Process ct-config ---
        config_channel = discord.utils.get(guild.text_channels, name=CONFIG_CHANNEL_NAME)
        if config_channel:
            logger.info(f"[API] Found Config Channel: #{config_channel.name}")
            try:
                # Check bot's permissions IN THE CONTEXT OF THE BOT ITSELF
                bot_member = guild.me # The bot's member object in this guild
                if not config_channel.permissions_for(bot_member).read_message_history:
                     logger.warning(f"[API] Missing read history permission in #{config_channel.name} for guild '{guild.name}'. Config data will be empty.")
                     # Return error or empty? Let's return error as config is crucial
                     return web.json_response({"error": f"Forbidden: Bot lacks permissions to read #{CONFIG_CHANNEL_NAME}."}, status=403)
                else:
                    # Fetch using bot's client directly (async iterator)
                    messages = [msg async for msg in config_channel.history(limit=None) if not msg.author.bot]
                    config_data = parse_ini_data(messages) # Use the parsing function
                    logger.info(f"[API] Parsed {len(config_data)} sections from {CONFIG_CHANNEL_NAME}")

            except discord.Forbidden:
                 logger.error(f"[API] Forbidden error accessing #{config_channel.name}")
                 return web.json_response({"error": f"Forbidden: Bot lacks permissions in #{CONFIG_CHANNEL_NAME}."}, status=403)
            except discord.HTTPException as e:
                 logger.error(f"[API] HTTP error processing {CONFIG_CHANNEL_NAME}: {e}", exc_info=True)
                 return web.json_response({"error": f"Internal Server Error processing {CONFIG_CHANNEL_NAME} (HTTP {e.status})."}, status=502) # 502 Bad Gateway might fit
            except Exception as e:
                 logger.error(f"[API] Error processing {CONFIG_CHANNEL_NAME}: {e}", exc_info=True)
                 return web.json_response({"error": f"Internal Server Error processing {CONFIG_CHANNEL_NAME}."}, status=500)
        else:
            logger.error(f"[API] Channel '{CONFIG_CHANNEL_NAME}' not found in guild '{guild.name}'.")
            return web.json_response({"error": f"Required channel '{CONFIG_CHANNEL_NAME}' not found."}, status=404) # Config channel is required

        # --- Process ct-manual-points (Optional) ---
        manual_points_channel = discord.utils.get(guild.text_channels, name=MANUAL_POINTS_CHANNEL_NAME)
        if manual_points_channel:
            logger.info(f"[API] Found Manual Points Channel: #{manual_points_channel.name}")
            try:
                bot_member = guild.me
                if not manual_points_channel.permissions_for(bot_member).read_message_history:
                     logger.warning(f"[API] Missing read history permission in #{manual_points_channel.name}. Manual points will be empty.")
                     # Don't return error, just empty data for optional channel
                else:
                    messages = [msg async for msg in manual_points_channel.history(limit=None) if not msg.author.bot]
                    manual_points_data = parse_ini_data(messages)
                    logger.info(f"[API] Parsed {len(manual_points_data)} sections from {MANUAL_POINTS_CHANNEL_NAME}")
            except discord.Forbidden:
                 logger.warning(f"[API] Forbidden error accessing #{manual_points_channel.name}. Manual points will be empty.")
            except discord.HTTPException as e:
                 logger.error(f"[API] HTTP error processing {MANUAL_POINTS_CHANNEL_NAME}: {e}. Manual points will be empty.", exc_info=True)
            except Exception as e:
                 logger.error(f"[API] Error processing {MANUAL_POINTS_CHANNEL_NAME}: {e}", exc_info=True)
                 logger.warning(f"[API] Error processing {MANUAL_POINTS_CHANNEL_NAME}. Manual points will be empty.")
        else:
             logger.warning(f"[API] Optional channel '{MANUAL_POINTS_CHANNEL_NAME}' not found in guild '{guild.name}'.")

        # --- Construct final response ---
        final_response = OrderedDict([
            ("config", config_data),
            ("manual_points", manual_points_data)
        ])

        # Use json.dumps with OrderedDict support via lambda for aiohttp response
        return web.json_response(final_response, dumps=lambda d: json.dumps(d, ensure_ascii=False))


# Instantiate the client
client = ClanTrackerClient(intents=intents)
tree = client.tree # Make tree accessible for command decorators

# --- Status Update Helper ---
async def update_status_from_channel(bot_client: ClanTrackerClient) -> None:
    """Fetches the message from the designated channel and updates the bot's status."""
    if not STATUS_GUILD_ID or not STATUS_CHANNEL_ID:
        logger.debug("Status Guild ID or Channel ID not configured. Skipping dynamic status update.")
        if bot_client.activity is None or bot_client.activity.name != DEFAULT_STATUS_MESSAGE:
             try:
                 activity = discord.CustomActivity(name=DEFAULT_STATUS_MESSAGE)
                 await bot_client.change_presence(status=discord.Status.online, activity=activity)
                 logger.info(f"Set default bot status: '{DEFAULT_STATUS_MESSAGE}'")
             except Exception as e:
                 logger.error(f"Failed to set default bot status: {e}", exc_info=True)
        return

    status_text = DEFAULT_STATUS_MESSAGE
    channel: Optional[discord.TextChannel] = None

    try:
        await bot_client.wait_until_ready() # Ensure cache is ready

        guild = bot_client.get_guild(STATUS_GUILD_ID)
        if not guild:
            logger.error(f"Could not find Guild with ID {STATUS_GUILD_ID} for status update.")
            return

        channel = guild.get_channel(STATUS_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
             logger.error(f"Could not find TextChannel with ID {STATUS_CHANNEL_ID} in Guild '{guild.name}' for status update.")
             return

        if not channel.permissions_for(guild.me).read_message_history:
            logger.warning(f"Missing 'Read Message History' permission in status channel #{channel.name} ({channel.id}). Using default status.")
        else:
            messages = [msg async for msg in channel.history(limit=1)]
            if messages:
                content = messages[0].content.strip()
                if content:
                    status_text = content
                    if len(status_text) > 128:
                        logger.warning(f"Status message from channel {channel.id} is too long ({len(status_text)} chars). Truncating.")
                        status_text = status_text[:125] + "..."
                else:
                    logger.info(f"Latest message in status channel #{channel.name} ({channel.id}) is empty. Using default status.")
            else:
                logger.info(f"Status channel #{channel.name} ({channel.id}) is empty. Using default status.")

    except discord.Forbidden:
        logger.error(f"Permission error (Forbidden) accessing status channel #{channel.name if channel else STATUS_CHANNEL_ID}. Using default status.")
    except discord.HTTPException as e:
         logger.error(f"HTTP error accessing status channel #{channel.name if channel else STATUS_CHANNEL_ID}: {e}. Using default status.")
    except Exception as e:
        logger.error(f"Unexpected error updating status from channel: {e}", exc_info=True)

    # --- Set the bot's presence/status ---
    try:
        current_activity = bot_client.activity
        if isinstance(current_activity, discord.CustomActivity) and current_activity.name == status_text:
            logger.debug(f"Status already set to '{status_text}'. Skipping update.")
            return

        activity = discord.CustomActivity(name=status_text)
        await bot_client.change_presence(status=discord.Status.online, activity=activity)
        logger.info(f"Set bot status to: '{status_text}' (Source: {'Channel' if channel and status_text != DEFAULT_STATUS_MESSAGE else 'Default'})")
    except Exception as e:
        logger.error(f"Failed to set bot status: {e}", exc_info=True)


# --- Guild Join Helper Functions ---
async def _notify_permission_error(guild: discord.Guild, permission_needed: str, action: str) -> None:
    error_message = (
        f"Error: I need the '{permission_needed}' permission to {action} in the server '{guild.name}'. "
        f"Please grant the necessary permissions and re-invite me, or manually create the required "
        f"'{CATEGORY_NAME}' category and channels ({', '.join(CHANNEL_NAMES)})."
    )
    logger.error(f"Missing '{permission_needed}' permission in guild '{guild.name}' (ID: {guild.id}) to {action}.")
    try:
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            await guild.system_channel.send(error_message)
            logger.info(f"Sent permission error notification to system channel in '{guild.name}'.")
        elif guild.owner and not guild.owner.bot:
             try:
                 await guild.owner.send(f"Permission Error in '{guild.name}':\n{error_message}")
                 logger.info(f"Sent permission error notification via DM to owner of '{guild.name}'.")
             except (discord.Forbidden, discord.HTTPException):
                 logger.warning(f"Could not DM owner of '{guild.name}' about permission error.")
        else:
            logger.warning(f"Could not find a suitable channel or user to notify about permission error in '{guild.name}'.")
    except discord.Forbidden:
        logger.error(f"Missing 'Send Messages' permission in the system channel of '{guild.name}'. Cannot notify about the original error.")
    except AttributeError:
        logger.warning(f"Could not find system channel or owner for guild '{guild.name}'.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while trying to notify about permissions in '{guild.name}': {e}", exc_info=True)

async def _setup_category_and_channels(guild: discord.Guild) -> Tuple[Optional[discord.CategoryChannel], Dict[str, Optional[discord.TextChannel]]]:
    category: Optional[discord.CategoryChannel] = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    created_category = False
    if category is None:
        logger.info(f"Creating category '{CATEGORY_NAME}' in guild '{guild.name}'...")
        try:
            if not guild.me.guild_permissions.manage_channels:
                 await _notify_permission_error(guild, "Manage Channels", f"create category '{CATEGORY_NAME}'")
                 return None, {}
            category = await guild.create_category(CATEGORY_NAME)
            logger.info(f"Category '{CATEGORY_NAME}' created successfully in '{guild.name}'.")
            created_category = True
        except discord.Forbidden:
            await _notify_permission_error(guild, "Manage Channels", f"create category '{CATEGORY_NAME}'")
            return None, {}
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating category '{CATEGORY_NAME}' in '{guild.name}': {e}", exc_info=True)
            return None, {}
        except Exception as e:
            logger.error(f"An unexpected error occurred creating category '{CATEGORY_NAME}' in '{guild.name}': {e}", exc_info=True)
            return None, {}
    elif not created_category:
         logger.info(f"Category '{CATEGORY_NAME}' already exists in guild '{guild.name}'.")

    if not category:
        logger.error(f"Category object is unexpectedly None after creation/check in '{guild.name}'. Cannot create channels.")
        return None, {}

    channels: Dict[str, Optional[discord.TextChannel]] = {name: None for name in CHANNEL_NAMES}
    can_manage_channels_in_cat = category.permissions_for(guild.me).manage_channels
    if not can_manage_channels_in_cat:
         await _notify_permission_error(guild, "Manage Channels", f"create channels within '{CATEGORY_NAME}'")
         for channel_name in CHANNEL_NAMES:
             channels[channel_name] = discord.utils.get(category.text_channels, name=channel_name)
         return category, channels

    for channel_name in CHANNEL_NAMES:
        existing_channel = discord.utils.get(category.text_channels, name=channel_name)
        if existing_channel is None:
            logger.info(f"Creating channel '{channel_name}' in category '{CATEGORY_NAME}' for guild '{guild.name}'...")
            try:
                created_channel = await guild.create_text_channel(channel_name, category=category)
                logger.info(f"Channel '{channel_name}' created successfully in '{guild.name}'.")
                channels[channel_name] = created_channel
            except discord.Forbidden:
                await _notify_permission_error(guild, "Manage Channels", f"create channel '{channel_name}'")
                continue
            except discord.HTTPException as e:
                logger.error(f"HTTP error creating channel '{channel_name}' in '{guild.name}': {e}", exc_info=True)
                continue
            except Exception as e:
                logger.error(f"An unexpected error occurred creating channel '{channel_name}' in '{guild.name}': {e}", exc_info=True)
                continue
        else:
            logger.info(f"Channel '{channel_name}' already exists in category '{CATEGORY_NAME}' for guild '{guild.name}'.")
            channels[channel_name] = existing_channel

    return category, channels

async def _ensure_identifier(guild: discord.Guild) -> Optional[str]:
    global server_identifiers
    guild_id_str = str(guild.id)
    clan_identifier: Optional[str] = None
    needs_save = False

    current_identifiers_set: Set[str] = {
        data['identifier']
        for data in server_identifiers.values()
        if isinstance(data, dict) and 'identifier' in data
    }

    entry = server_identifiers.get(guild_id_str)

    if isinstance(entry, dict) and 'identifier' in entry:
        clan_identifier = entry['identifier']
        logger.info(f"Guild '{guild.name}' (ID: {guild_id_str}) re-joined or identifier exists. Using: {clan_identifier}")
        if entry.get('name') != guild.name:
            logger.info(f"Server name changed for Guild ID {guild_id_str}: '{entry.get('name')}' -> '{guild.name}'. Updating record.")
            entry['name'] = guild.name
            needs_save = True
    else:
        if entry is not None:
             logger.warning(f"Found existing entry for Guild ID {guild_id_str} but in unexpected format or missing identifier. Generating new one.")

        clan_identifier = generate_unique_identifier(current_identifiers_set)
        server_identifiers[guild_id_str] = {'name': guild.name, 'identifier': clan_identifier}
        needs_save = True
        logger.info(f"Generated new identifier for guild '{guild.name}' (ID: {guild_id_str}): {clan_identifier}")

    if needs_save:
        save_identifiers()

    return clan_identifier

# --- _send_initial_messages function ---
async def _send_initial_messages(
    guild: discord.Guild,
    channels: Dict[str, Optional[discord.TextChannel]],
    clan_identifier: str
) -> None:
    """Sends the pre-defined initial messages to the appropriate channels if they are empty."""
    logger.info(f"Attempting to send initial content to channels in '{guild.name}'...")

    # Helper function to safely send a message
    async def send_safe(channel: Optional[discord.TextChannel], content: str, channel_name_for_log: str):
        if not channel:
            logger.warning(f"Cannot send message because channel object for '{channel_name_for_log}' is None in '{guild.name}'.")
            return False
        if not channel.permissions_for(guild.me).send_messages:
            logger.warning(f"Missing 'Send Messages' permission in #{channel.name} ('{channel_name_for_log}') for guild '{guild.name}'.")
            return False
        try:
            await channel.send(content, suppress_embeds=True)
            return True
        except discord.Forbidden:
            logger.error(f"Missing 'Send Messages' permission in #{channel.name} ('{channel_name_for_log}') for guild '{guild.name}' despite initial check.")
            return False
        except discord.HTTPException as e:
             logger.error(f"HTTP error sending message to #{channel.name} ('{channel_name_for_log}') in '{guild.name}': {e}", exc_info=True)
             return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to #{channel.name} ('{channel_name_for_log}') in '{guild.name}': {e}", exc_info=True)
            return False

    # Helper function to check if a channel is empty
    async def is_channel_empty(channel: Optional[discord.TextChannel], channel_name_for_log: str) -> bool:
        if not channel: return True # Treat non-existent channel as "empty" for skipping purposes
        if not channel.permissions_for(guild.me).read_message_history:
             logger.warning(f"Missing 'Read Message History' in #{channel.name} ('{channel_name_for_log}'). Assuming channel is not empty.")
             return False
        try:
            # Fetch exactly one message. If it exists, the channel is not empty.
            history = [msg async for msg in channel.history(limit=1)]
            is_empty = not history
            logger.debug(f"Channel #{channel.name} ('{channel_name_for_log}') history check: {'Empty' if is_empty else 'Not Empty'}")
            return is_empty
        except (discord.Forbidden, discord.HTTPException) as e:
             logger.error(f"Error checking history for #{channel.name} ('{channel_name_for_log}'): {e}. Assuming not empty.")
             return False
        except Exception as e:
             logger.error(f"Unexpected error checking history for #{channel.name} ('{channel_name_for_log}'): {e}. Assuming not empty.", exc_info=True)
             return False

    # Prepare all variables needed for formatting the message templates
    format_kwargs = {
        "clan_identifier": clan_identifier,
        "CATEGORY_NAME": CATEGORY_NAME,
        "INFO_CHANNEL_NAME": INFO_CHANNEL_NAME,
        "CONFIG_CHANNEL_NAME": CONFIG_CHANNEL_NAME,
        "MANUAL_POINTS_CHANNEL_NAME": MANUAL_POINTS_CHANNEL_NAME,
        "COMMANDS_CHANNEL_NAME": COMMANDS_CHANNEL_NAME,
        "GITHUB_APP_README_MD_LINK": GITHUB_APP_README_MD_LINK,
        "GITHUB_BOT_README_MD_LINK": GITHUB_BOT_README_MD_LINK,
        "OFFICIAL_DISCORD_LINK": OFFICIAL_DISCORD_LINK,
    }

    # Iterate through the defined structure (INITIAL_MESSAGES_BY_CHANNEL)
    for channel_name_var, message_constants_list in INITIAL_MESSAGES_BY_CHANNEL.items():
        channel_object = channels.get(channel_name_var) # Get the actual discord.TextChannel object

        if not channel_object:
            logger.warning(f"Could not find or create channel for variable '{channel_name_var}' in '{guild.name}'. Skipping initial messages for it.")
            continue # Skip to the next channel in the structure

        actual_channel_name = channel_object.name # For logging

        if await is_channel_empty(channel_object, actual_channel_name):
            logger.info(f"Channel #{actual_channel_name} is empty. Sending initial messages...")
            success_count = 0
            total_messages = len(message_constants_list)

            for i, message_template in enumerate(message_constants_list):
                try:
                    # Format the message template using all available variables
                    formatted_content = message_template.format(**format_kwargs)
                except KeyError as e:
                    logger.error(f"Formatting error in message template for #{actual_channel_name} (message {i+1}/{total_messages}). Missing key: {e}. Sending raw template.")
                    formatted_content = f"⚠️ **Bot Error:** Missing formatting key `{e}`.\nRaw content:\n```\n{message_template}\n```"
                except Exception as e:
                     logger.error(f"Unexpected formatting error in message template for #{actual_channel_name} (message {i+1}/{total_messages}): {e}. Sending raw template.", exc_info=True)
                     formatted_content = f"⚠️ **Bot Error:** Unexpected formatting error.\nRaw content:\n```\n{message_template}\n```"


                if await send_safe(channel_object, formatted_content, actual_channel_name):
                    success_count += 1
                    # Add a small delay between messages to avoid rate limits and allow users to read
                    if i < total_messages - 1:
                        await asyncio.sleep(0.8)
                else:
                    logger.error(f"Failed to send message {i+1}/{total_messages} to #{actual_channel_name}. Stopping message dump for this channel.")
                    # Send a fallback error message if possible
                    await send_safe(channel_object,
                        f"**Welcome to ClanTracker OSRS!**\nYour identifier: `{clan_identifier}`.\n"
                        f"An error occurred sending the full setup info to this channel (#{actual_channel_name}). Please ensure the bot has 'Send Messages' permission here.",
                        actual_channel_name
                    )
                    break # Stop sending messages to THIS channel if one fails

            if success_count == total_messages:
                logger.info(f"Successfully sent all {total_messages} initial messages to #{actual_channel_name}.")
            else:
                 logger.warning(f"Sent {success_count}/{total_messages} messages to #{actual_channel_name} before encountering an issue.")

        else:
            logger.info(f"Channel #{actual_channel_name} in '{guild.name}' is not empty or history check failed. Skipping initial message dump.")

    logger.info(f"Initial content setup phase finished for guild '{guild.name}'.")

# --- Helper Function to Update Discord Messages ---
async def _update_identifier_in_guild_channels(
    guild_id: int,
    old_identifier: str,
    new_identifier: str,
    bot_client: ClanTrackerClient # Pass the client instance
) -> None:
    """
    Attempts to find and update the clan identifier in the ct-info and ct-config
    channels of a specific guild after it has been changed.
    """
    logger.info(f"Attempting to update identifier display in Guild ID {guild_id} from '{old_identifier}' to '{new_identifier}'...")

    try:
        await bot_client.wait_until_ready() # Ensure client is ready
        guild = bot_client.get_guild(guild_id)

        if not guild:
            logger.warning(f"Could not find Guild {guild_id} in cache to update identifier messages.")
            return # Cannot proceed if guild isn't found

        bot_member = guild.me # Bot's member object in this guild

        # --- Update ct-info Channel ---
        info_channel = discord.utils.get(guild.text_channels, name=INFO_CHANNEL_NAME)
        if info_channel:
            logger.debug(f"Found channel #{INFO_CHANNEL_NAME} in Guild {guild.name} ({guild_id}).")
            perms = info_channel.permissions_for(bot_member)
            if not perms.read_message_history:
                logger.warning(f"Missing 'Read Message History' permission in #{INFO_CHANNEL_NAME} (Guild {guild_id}). Cannot search for message to update.")
            elif not perms.manage_messages:
                 logger.warning(f"Missing 'Manage Messages' permission in #{INFO_CHANNEL_NAME} (Guild {guild_id}). Cannot edit message.")
            else:
                try:
                    target_info_line = f"### Your unique Clan Identifier: `{old_identifier}`"
                    found_info_msg = False
                    async for message in info_channel.history(limit=20):
                        if target_info_line in message.content and message.author == bot_client.user:
                            logger.info(f"Found message containing old identifier '{old_identifier}' in #{INFO_CHANNEL_NAME} (Msg ID: {message.id}).")
                            new_content = message.content.replace(
                                target_info_line,
                                f"### Your unique Clan Identifier: `{new_identifier}`"
                            )
                            await message.edit(content=new_content, suppress=True)
                            logger.info(f"Successfully updated identifier in #{INFO_CHANNEL_NAME} (Guild {guild_id}).")
                            found_info_msg = True
                            break

                    if not found_info_msg:
                         logger.warning(f"Could not find the message containing '{target_info_line}' in the last 20 messages of #{INFO_CHANNEL_NAME} (Guild {guild_id}).")

                except discord.Forbidden:
                    logger.error(f"Forbidden error while trying to edit message in #{INFO_CHANNEL_NAME} (Guild {guild_id}). Check 'Manage Messages' permission.")
                except discord.HTTPException as e:
                    logger.error(f"HTTP error editing message in #{INFO_CHANNEL_NAME} (Guild {guild_id}): {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Unexpected error updating message in #{INFO_CHANNEL_NAME} (Guild {guild_id}): {e}", exc_info=True)
        else:
            logger.warning(f"Channel #{INFO_CHANNEL_NAME} not found in Guild {guild.name} ({guild_id}). Cannot update identifier message.")


        # --- Update ct-config Channel ---
        config_channel = discord.utils.get(guild.text_channels, name=CONFIG_CHANNEL_NAME)
        if config_channel:
            logger.debug(f"Found channel #{CONFIG_CHANNEL_NAME} in Guild {guild.name} ({guild_id}).")
            perms = config_channel.permissions_for(bot_member)
            if not perms.read_message_history:
                logger.warning(f"Missing 'Read Message History' permission in #{CONFIG_CHANNEL_NAME} (Guild {guild_id}). Cannot search for message.")
            elif not perms.manage_messages:
                 logger.warning(f"Missing 'Manage Messages' permission in #{CONFIG_CHANNEL_NAME} (Guild {guild_id}). Cannot edit message.")
            else:
                try:
                    target_config_line = f"clan_identifier = {old_identifier}"
                    found_config_msg = False
                    async for message in config_channel.history(limit=5):
                        cleaned_content = clean_message_content(message.content)
                        if target_config_line in cleaned_content and message.author == bot_client.user:
                            logger.info(f"Found message containing old identifier config '{old_identifier}' in #{CONFIG_CHANNEL_NAME} (Msg ID: {message.id}).")
                            format_kwargs = {"clan_identifier": new_identifier}
                            try:
                                new_content = MSG_1_CONFIG_CHANNEL_NAME.format(**format_kwargs)
                            except KeyError as e:
                                logger.error(f"Formatting error in MSG_1_CONFIG_CHANNEL_NAME template. Missing key: {e}. Cannot update config message.")
                                continue
                            await message.edit(content=new_content, suppress=True)
                            logger.info(f"Successfully updated identifier in #{CONFIG_CHANNEL_NAME} (Guild {guild_id}).")
                            found_config_msg = True
                            break
                    if not found_config_msg:
                         logger.warning(f"Could not find the message containing '{target_config_line}' in the last 5 messages of #{CONFIG_CHANNEL_NAME} (Guild {guild_id}).")

                except discord.Forbidden:
                    logger.error(f"Forbidden error while trying to edit message in #{CONFIG_CHANNEL_NAME} (Guild {guild_id}). Check 'Manage Messages' permission.")
                except discord.HTTPException as e:
                    logger.error(f"HTTP error editing message in #{CONFIG_CHANNEL_NAME} (Guild {guild_id}): {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Unexpected error updating message in #{CONFIG_CHANNEL_NAME} (Guild {guild_id}): {e}", exc_info=True)
        else:
            logger.warning(f"Channel #{CONFIG_CHANNEL_NAME} not found in Guild {guild.name} ({guild_id}). Cannot update identifier message.")

    except Exception as e:
        logger.error(f"Unexpected error during identifier update process for Guild {guild_id}: {e}", exc_info=True)

    logger.info(f"Finished identifier display update attempt for Guild ID {guild_id}.")


# --- Slash Command Check ---
def is_in_commands_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.channel, discord.TextChannel):
            if interaction.channel.name == COMMANDS_CHANNEL_NAME:
                return True
            else:
                logger.warning(f"User {interaction.user} (ID: {interaction.user.id}) tried to use command '/{interaction.command.name if interaction.command else 'unknown'}' in incorrect channel #{interaction.channel.name} (Guild: {interaction.guild.name if interaction.guild else 'N/A'}).")
                try:
                    await interaction.response.send_message(
                        f"❌ This command can only be used in the `#{COMMANDS_CHANNEL_NAME}` channel.",
                        ephemeral=True
                    )
                except discord.InteractionResponded:
                    try:
                        await interaction.followup.send(f"❌ This command can only be used in the `#{COMMANDS_CHANNEL_NAME}` channel.", ephemeral=True)
                    except Exception: pass
                except Exception as e:
                    logger.error(f"Error sending command channel restriction message: {e}", exc_info=True)
                return False
        else:
            logger.warning(f"User {interaction.user} (ID: {interaction.user.id}) tried to use command '/{interaction.command.name if interaction.command else 'unknown'}' outside of a standard text channel.")
            try:
                 await interaction.response.send_message("❌ This command can only be used in a server's text channel.", ephemeral=True)
            except discord.InteractionResponded:
                 try:
                     await interaction.followup.send("❌ This command can only be used in a server's text channel.", ephemeral=True)
                 except Exception: pass
            except Exception as e:
                 logger.error(f"Error sending non-text-channel restriction message: {e}", exc_info=True)
            return False
    return app_commands.check(predicate)

def is_in_database_channel():
    """Checks if the command is invoked in the configured database inspection channel."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not INSPECT_DB_GUILD_ID or not INSPECT_DB_CHANNEL_ID:
            logger.error(f"User {interaction.user} tried to use /database, but INSPECT_DATABASE_GUILD_ID or INSPECT_DATABASE_CHANNEL_ID are not configured.")
            try:
                await interaction.response.send_message(
                    "❌ This command is disabled because the inspection channel is not configured in the bot's environment.",
                    ephemeral=True
                )
            except discord.InteractionResponded: pass
            except Exception as e: logger.error(f"Error sending database config error message: {e}", exc_info=True)
            return False

        if not interaction.guild or interaction.guild.id != INSPECT_DB_GUILD_ID:
            logger.warning(f"User {interaction.user} tried to use /database outside the configured guild (Guild: {interaction.guild.name if interaction.guild else 'N/A'}).")
            try:
                await interaction.response.send_message(
                    f"❌ This command can only be used in the designated server.",
                    ephemeral=True
                )
            except discord.InteractionResponded: pass
            except Exception as e: logger.error(f"Error sending database guild restriction message: {e}", exc_info=True)
            return False

        if not interaction.channel or interaction.channel.id != INSPECT_DB_CHANNEL_ID:
            logger.warning(f"User {interaction.user} tried to use /database in the wrong channel (Channel: #{interaction.channel.name if interaction.channel else 'N/A'}).")
            try:
                await interaction.response.send_message(
                    f"❌ This command can only be used by the developer in the designated channel.",
                    ephemeral=True
                )
            except discord.InteractionResponded: pass
            except Exception as e: logger.error(f"Error sending database channel restriction message: {e}", exc_info=True)
            return False

        # Check if bot has permissions to send files in this specific channel
        if isinstance(interaction.channel, discord.TextChannel):
            bot_member = interaction.guild.me
            if not interaction.channel.permissions_for(bot_member).attach_files:
                logger.error(f"Bot lacks 'Attach Files' permission in the database inspection channel #{interaction.channel.name} (ID: {interaction.channel.id}).")
                try:
                    await interaction.response.send_message(
                        "❌ I don't have permission to attach files in this channel, which is required for the `/database` command.",
                        ephemeral=True
                    )
                except discord.InteractionResponded: pass
                except Exception as e: logger.error(f"Error sending database permission error message: {e}", exc_info=True)
                return False
        else: # Should not happen due to guild/channel ID check
             logger.warning("Database command used in a non-text channel context unexpectedly.")
             return False


        return True # All checks passed
    return app_commands.check(predicate)

# Check for Authorized Users
def is_authorized_user():
    """Checks if the command invoker is in the AUTHORIZED_USERNAMES set."""
    async def predicate(interaction: discord.Interaction) -> bool:
        global AUTHORIZED_USERNAMES # Access the global set populated at startup

        if not AUTHORIZED_USERNAMES:
            logger.error(f"Authorization check failed: AUTHORIZED_USERS environment variable is not set or empty. Denying access to '/{interaction.command.name if interaction.command else 'unknown'}' for user {interaction.user}.")
            try:
                await interaction.response.send_message(
                    "❌ This command is restricted, but the list of authorized users is not configured in the bot's environment.",
                    ephemeral=True
                )
            except discord.InteractionResponded: pass
            except Exception as e: logger.error(f"Error sending authorization config error message: {e}", exc_info=True)
            return False

        # Compare using lowercase for case-insensitivity
        invoker_username_lower = interaction.user.name.lower()

        if invoker_username_lower in AUTHORIZED_USERNAMES:
            logger.debug(f"User '{interaction.user.name}' is authorized for command '/{interaction.command.name if interaction.command else 'unknown'}'.")
            return True
        else:
            logger.warning(f"User '{interaction.user.name}' (ID: {interaction.user.id}) attempted to use restricted command '/{interaction.command.name if interaction.command else 'unknown'}' but is not in the authorized list.")
            try:
                await interaction.response.send_message(
                    f"❌ You are not authorized to use this command.",
                    ephemeral=True
                )
            except discord.InteractionResponded: pass
            except Exception as e: logger.error(f"Error sending authorization restriction message: {e}", exc_info=True)
            return False
    return app_commands.check(predicate)

# --- HYD Slash Command ---
@tree.command(name="hyd", description="Ask how the bot feels right now :)")
@is_in_commands_channel()
async def hyd_command(interaction: discord.Interaction):
    """Handles the /hyd command."""
    try:
        # Ensure response directory/file exists
        os.makedirs(RESPONSES_DIR, exist_ok=True)
        if not os.path.exists(HYD_FILE_PATH):
            logger.warning(f"HYD response file not found at: {HYD_FILE_PATH}. Creating default.")
            with open(HYD_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("Shut up im thinking.\n")
                f.write("Just processing bits and bytes.\n")
                f.write("Ask me later, I'm compiling.\n")
            possible_responses = ["Feeling operational."]
        else:
            with open(HYD_FILE_PATH, 'r', encoding='utf-8') as f:
                possible_responses = [line.strip() for line in f if line.strip()]

        if not possible_responses:
            logger.warning(f"HYD response file is empty: {HYD_FILE_PATH}")
            await interaction.response.send_message("I... have no words. Literally. The response file is empty.", ephemeral=True)
            return

        response = random.choice(possible_responses)
        await interaction.response.send_message(response)
        logger.info(f"Command '/hyd' executed successfully by {interaction.user} in #{interaction.channel.name}")

    except Exception as e:
        logger.error(f"Error executing /hyd command: {e}", exc_info=True)
        if not interaction.response.is_done():
            try:
                await interaction.response.send_message("Sorry, I encountered an error while trying to express my existential dread.", ephemeral=True)
            except Exception: pass

# --- Database Inspection Command ---
@tree.command(name="database", description="Sends the content of the clan identifiers database file.")
@is_in_database_channel() # Apply the specific channel check
@is_authorized_user() # Ensure only authorized users can access this command
async def database_command(interaction: discord.Interaction):
    """Handles the /database command to view the identifier file."""
    logger.info(f"Command '/database' invoked by {interaction.user} in channel #{interaction.channel.name}")

    # Defer the response - reading file might take a moment
    # Send non-ephemeral deferral so the final message is public in the channel
    await interaction.response.defer(thinking=True)

    try:
        # Check if file exists
        if not os.path.exists(IDENTIFIER_FILE):
            logger.warning(f"Database file not found at {IDENTIFIER_FILE} when executing /database.")
            await interaction.followup.send(f"⚠️ The database file (`{IDENTIFIER_FILE_NAME}`) was not found in the expected location (`{DATA_DIR}`).")
            return

        # Read the file content
        with open(IDENTIFIER_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            logger.info(f"Database file {IDENTIFIER_FILE} is empty.")
            await interaction.followup.send(f"ℹ️ The database file (`{IDENTIFIER_FILE_NAME}`) is currently empty.")
            return

        # Send the content as a file attachment
        # Use io.StringIO to treat the string content like a file
        file_data = io.StringIO(content)
        discord_file = discord.File(fp=file_data, filename=IDENTIFIER_FILE_NAME)

        await interaction.followup.send(f"📄 Here is the content of `{IDENTIFIER_FILE_NAME}`:", file=discord_file)
        logger.info(f"Successfully sent database file content for /database command requested by {interaction.user}.")

    except discord.Forbidden:
         logger.error(f"Forbidden error sending database file for /database command. Check 'Attach Files' permission in #{interaction.channel.name}.")
         # We already deferred, so followup is needed. The check should prevent this, but handle defensively.
         try:
             await interaction.followup.send("❌ I encountered a permission error trying to send the file. Please ensure I can 'Attach Files' in this channel.")
         except Exception: pass # Avoid further errors if followup fails
    except discord.HTTPException as e:
         logger.error(f"HTTP error sending database file for /database command: {e}", exc_info=True)
         try:
             await interaction.followup.send(f"❌ An HTTP error occurred while trying to send the file (Status: {e.status}). Please try again later.")
         except Exception: pass
    except Exception as e:
        logger.error(f"Error executing /database command: {e}", exc_info=True)
        try:
            # Check if already responded via followup before sending another
            if interaction.is_expired(): # Check if interaction is still valid
                 logger.warning("Interaction expired before sending final error for /database.")
                 return
            # Attempt to send a generic error if no specific one was caught and sent
            await interaction.followup.send("❌ An unexpected error occurred while retrieving the database file.")
        except Exception as e_resp:
            logger.error(f"Failed to send error message for /database command: {e_resp}", exc_info=True)

# --- Autocomplete for Clan Identifiers ---
async def clan_identifier_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[Choice[str]]:
    """Autocompletes clan identifiers for commands."""
    global server_identifiers
    choices = []
    current_lower = current.lower()

    # Create a list of (identifier, name) tuples for easier sorting/filtering
    identifier_list = [
        (data.get('identifier', ''), data.get('name', 'Unknown Server'))
        for data in server_identifiers.values()
        if isinstance(data, dict) and data.get('identifier')
    ]

    # Sort primarily by identifier, secondarily by name for consistency
    identifier_list.sort()

    for identifier, name in identifier_list:
        if not identifier: # Skip if identifier is somehow empty
            continue
        # Match if current input is in identifier OR server name
        if current_lower in identifier.lower() or current_lower in name.lower():
            # Display format: IDENTIFIER (Server Name)
            display_name = f"{identifier} ({name})"
            # Truncate display name if too long for Discord's limit (100 chars)
            if len(display_name) > 100:
                display_name = display_name[:97] + "..."
            choices.append(Choice(name=display_name, value=identifier))
        # Stop adding choices if we reach Discord's limit (25)
        if len(choices) >= 25:
            break
    return choices

# --- Remove Clan Entry Command ---
@tree.command(name="remove_clan_entry", description="Removes a clan entry from the database using its identifier.")
@is_in_database_channel() # Restrict to the database channel
@is_authorized_user() # Ensure only authorized users can access this command
@app_commands.describe(clan_identifier="The unique identifier of the clan entry to remove.")
@app_commands.autocomplete(clan_identifier=clan_identifier_autocomplete) # Add autocomplete
async def remove_clan_entry_command(interaction: discord.Interaction, clan_identifier: str):
    """Handles the /remove_clan_entry command."""
    logger.info(f"Command '/remove_clan_entry' invoked by {interaction.user} for identifier '{clan_identifier}' in channel #{interaction.channel.name}")

    # Defer ephemerally - only the invoker needs to see the result
    await interaction.response.defer(ephemeral=True, thinking=True)

    global server_identifiers # We need to modify this global dict

    guild_id_to_delete: Optional[str] = None
    guild_name_deleted: str = "Unknown Name"

    # Find the guild ID associated with the provided identifier
    found_info = find_guild_info_by_identifier(clan_identifier)

    if found_info:
        guild_id_to_delete, guild_name_deleted = found_info
        logger.info(f"Found Guild ID '{guild_id_to_delete}' (Name: '{guild_name_deleted}') associated with identifier '{clan_identifier}'.")
    else:
        logger.warning(f"Clan identifier '{clan_identifier}' not found in the database for removal.")
        await interaction.followup.send(f"❌ Clan identifier `{clan_identifier}` was not found in the database.", ephemeral=True)
        return

    # Proceed with deletion
    try:
        if guild_id_to_delete in server_identifiers:
            del server_identifiers[guild_id_to_delete]
            logger.info(f"Removed entry for Guild ID '{guild_id_to_delete}' (Identifier: '{clan_identifier}') from memory.")

            # Save the updated identifiers to the file
            save_identifiers() # This function already logs success/failure
            logger.info(f"Successfully saved database after removing entry for identifier '{clan_identifier}'.")

            await interaction.followup.send(
                f"✅ Successfully removed the entry for clan identifier `{clan_identifier}` "
                f"(associated with Guild ID `{guild_id_to_delete}`, Name: `{guild_name_deleted}`).",
                ephemeral=True
            )
        else:
            # This case should technically not happen if find_guild_info_by_identifier worked, but handle defensively
            logger.error(f"Inconsistency: Found identifier '{clan_identifier}' but Guild ID '{guild_id_to_delete}' was not in server_identifiers dict during deletion attempt.")
            await interaction.followup.send(f"❌ An internal inconsistency occurred. Could not find Guild ID `{guild_id_to_delete}` to delete, even though the identifier was initially found. Please check the logs.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error removing or saving identifier '{clan_identifier}' (Guild ID: {guild_id_to_delete}): {e}", exc_info=True)
        # Attempt to reload identifiers to revert in-memory changes if save failed? Or just report error. Let's report.
        # load_identifiers() # Optional: uncomment to try and revert memory state on error
        await interaction.followup.send(f"❌ An unexpected error occurred while trying to remove the entry for `{clan_identifier}`. Please check the bot logs.", ephemeral=True)

# --- Replace Clan Entry Command ---
@tree.command(name="replace_clan_entry", description="Replaces an existing clan identifier with a new one.")
@is_in_database_channel() # Restrict to the database channel
@is_authorized_user() # Ensure only authorized users can access this command
@app_commands.describe(
    old_clan_identifier="The current identifier of the clan entry to modify.",
    new_clan_identifier=f"The new identifier (1-{IDENTIFIER_LENGTH} chars, A-Z, 0-9, must be unique)."
)
@app_commands.autocomplete(old_clan_identifier=clan_identifier_autocomplete) # Autocomplete for the old identifier
async def replace_clan_entry_command(
    interaction: discord.Interaction,
    old_clan_identifier: str,
    new_clan_identifier: str
):
    """Handles the /replace_clan_entry command."""
    logger.info(f"Command '/replace_clan_entry' invoked by {interaction.user} to replace '{old_clan_identifier}' with '{new_clan_identifier}' in channel #{interaction.channel.name}")

    # Defer ephemerally
    await interaction.response.defer(ephemeral=True, thinking=True)

    global server_identifiers # We need to modify this global dict
    global client # Need access to the client instance

    # --- 1. Find the entry to modify ---
    guild_id_to_modify: Optional[str] = None
    guild_name_modified: str = "Unknown Name"
    found_info = find_guild_info_by_identifier(old_clan_identifier)

    if found_info:
        guild_id_to_modify, guild_name_modified = found_info
        logger.info(f"Found Guild ID '{guild_id_to_modify}' (Name: '{guild_name_modified}') associated with identifier '{old_clan_identifier}' for replacement.")
    else:
        logger.warning(f"Old clan identifier '{old_clan_identifier}' not found in the database for replacement.")
        await interaction.followup.send(f"❌ The original clan identifier `{old_clan_identifier}` was not found in the database.", ephemeral=True)
        return

    # --- 2. Validate the NEW identifier ---
    new_id_clean = new_clan_identifier.strip().upper() # Clean and enforce uppercase

    # Check length
    if not (1 <= len(new_id_clean) <= IDENTIFIER_LENGTH):
        logger.warning(f"Validation failed for new identifier '{new_id_clean}': Invalid length ({len(new_id_clean)}).")
        await interaction.followup.send(
            f"❌ Validation Failed: The new identifier `{new_id_clean}` is invalid. "
            f"It must be between 1 and {IDENTIFIER_LENGTH} characters long.",
            ephemeral=True
        )
        return

    # Check characters (A-Z, 0-9)
    if not re.match(r'^[A-Z0-9]+$', new_id_clean):
        logger.warning(f"Validation failed for new identifier '{new_id_clean}': Invalid characters.")
        await interaction.followup.send(
            f"❌ Validation Failed: The new identifier `{new_id_clean}` contains invalid characters. "
            f"Only uppercase letters (A-Z) and digits (0-9) are allowed.",
            ephemeral=True
        )
        return

    # Check if the user is trying to replace it with the same identifier
    if old_clan_identifier == new_id_clean:
        logger.info(f"User attempted to replace '{old_clan_identifier}' with itself. No changes needed.")
        await interaction.followup.send(
            f"ℹ️ The new identifier (`{new_id_clean}`) is the same as the old one (`{old_clan_identifier}`). No changes were made.",
            ephemeral=True
        )
        return

    # Check uniqueness (ensure NEW id isn't used by ANOTHER guild)
    conflicting_guild_id: Optional[str] = None
    conflicting_guild_name: str = "Unknown"
    for gid, data in server_identifiers.items():
        # Check if another guild (gid != guild_id_to_modify) already uses the new identifier
        if gid != guild_id_to_modify and isinstance(data, dict) and data.get('identifier') == new_id_clean:
            conflicting_guild_id = gid
            conflicting_guild_name = data.get('name', 'Unknown Name')
            break # Found a conflict

    if conflicting_guild_id:
        logger.warning(f"Validation failed for new identifier '{new_id_clean}': Already in use by Guild ID '{conflicting_guild_id}' (Name: '{conflicting_guild_name}').")
        await interaction.followup.send(
            f"❌ Validation Failed: The new identifier `{new_id_clean}` is already in use by another server "
            f"(Name: `{conflicting_guild_name}`, Guild ID: `{conflicting_guild_id}`). "
            f"Please choose a unique identifier.",
            ephemeral=True
        )
        return

    # --- 3. Perform the replacement ---
    try:
        # Ensure the entry still exists (defensive check)
        if guild_id_to_modify in server_identifiers and isinstance(server_identifiers[guild_id_to_modify], dict):
            server_identifiers[guild_id_to_modify]['identifier'] = new_id_clean
            logger.info(f"Updated identifier in memory for Guild ID '{guild_id_to_modify}' from '{old_clan_identifier}' to '{new_id_clean}'.")

            # Save the updated identifiers to the file
            save_identifiers() # This function already logs success/failure
            logger.info(f"Successfully saved database after replacing identifier for Guild ID '{guild_id_to_modify}'.")

            # Attempt to update the messages in the target guild's channels
            # We run this *after* saving and *before* confirming to the user
            # Convert guild_id_to_modify to int for the helper function
            try:
                guild_id_int = int(guild_id_to_modify)
                # Run the update task - await it directly so we know if it had immediate issues
                # (though it logs its own progress/errors)
                await _update_identifier_in_guild_channels(guild_id_int, old_clan_identifier, new_id_clean, client)
            except ValueError:
                 logger.error(f"Could not convert Guild ID '{guild_id_to_modify}' to integer. Skipping Discord message update.")
            except Exception as update_err:
                 logger.error(f"An error occurred initiating the Discord message update for Guild {guild_id_to_modify}: {update_err}", exc_info=True)


            await interaction.followup.send(
                f"✅ Successfully replaced the identifier for **{guild_name_modified}** (Guild ID: `{guild_id_to_modify}`).\n"
                f"Old Identifier: `{old_clan_identifier}`\n"
                f"New Identifier: `{new_id_clean}`\n"
                f"_(Attempted to update display messages in the server.)_", # Optional: Add note
                ephemeral=True
            )
        else:
            # This case should technically not happen if find_guild_info_by_identifier worked initially, but handle defensively
            logger.error(f"Inconsistency: Guild ID '{guild_id_to_modify}' (for old id '{old_clan_identifier}') was not found in server_identifiers dict during replacement attempt.")
            await interaction.followup.send(f"❌ An internal inconsistency occurred. Could not find the entry for Guild ID `{guild_id_to_modify}` to update. Please check the logs.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error replacing or saving identifier '{old_clan_identifier}' -> '{new_id_clean}' (Guild ID: {guild_id_to_modify}): {e}", exc_info=True)
        # Don't attempt reload here, just report error
        await interaction.followup.send(f"❌ An unexpected error occurred while trying to replace the identifier `{old_clan_identifier}` with `{new_id_clean}`. Please check the bot logs.", ephemeral=True)

# --- Command Check Error Handler ---
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handles errors during application command execution."""
    command_name = interaction.command.name if interaction.command else "unknown command"

    if isinstance(error, app_commands.CheckFailure):
        logger.warning(f"CheckFailure for command '/{command_name}' by {interaction.user} in channel #{interaction.channel.name if interaction.channel else 'DM'}. User already notified.")
        pass # Predicate already sent message
    elif isinstance(error, app_commands.CommandNotFound):
         logger.warning(f"Command not found attempt by {interaction.user}: {interaction.data.get('name', 'N/A')}")
         if not interaction.response.is_done():
             await interaction.response.send_message("Sorry, I don't recognize that command.", ephemeral=True)
    elif isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        logger.error(f"Error invoking command '/{command_name}': {original_error}", exc_info=original_error)
        error_message = "🤕 Oops! Something went wrong while running that command."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                 await interaction.followup.send(error_message, ephemeral=True)
        except Exception as e_resp:
             logger.error(f"Failed to send error message to user for command '/{command_name}': {e_resp}", exc_info=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        missing_perms = ', '.join(error.missing_permissions)
        logger.error(f"BotMissingPermissions for command '/{command_name}' in channel #{interaction.channel.name}: Needs {missing_perms}")
        error_message = f"❌ I lack the required permissions to do that: `{missing_perms}`."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                await interaction.followup.send(error_message, ephemeral=True)
        except Exception as e_resp:
             logger.error(f"Failed to send BotMissingPermissions message: {e_resp}", exc_info=True)
    else:
        logger.error(f"Unhandled application command error for '/{command_name}': {error}", exc_info=True)
        error_message = "An unexpected error occurred."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
        except Exception as e_resp:
             logger.error(f"Failed to send generic error message: {e_resp}", exc_info=True)


# --- Bot Start Function ---
def prepare_bot() -> bool:
    """Checks essential configuration and loads initial data."""
    global AUTHORIZED_USERNAMES

    logger.info("Preparing bot...")
    # Check for required environment variables
    if not TOKEN:
        logger.critical("CRITICAL ERROR: DISCORD_BOT_TOKEN environment variable not set. Bot cannot start.")
        return False
    if not GITHUB_APP_README_MD_LINK:
         logger.warning("Configuration Warning: GITHUB_APP_README_MD_LINK environment variable is not set. Please ensure it is configured.")
    if not GITHUB_BOT_README_MD_LINK:
         logger.warning("Configuration Warning: GITHUB_BOT_README_MD_LINK environment variable is not set. Please ensure it is configured.")
    if not OFFICIAL_DISCORD_LINK or "y4tmVW9p" in OFFICIAL_DISCORD_LINK:
         logger.warning("Configuration Warning: OFFICIAL_DISCORD_LINK is not set or uses the default invite. Please set this environment variable.")

    load_identifiers()

    if not STATUS_GUILD_ID or not STATUS_CHANNEL_ID:
        logger.warning("STATUS_GUILD_ID or STATUS_CHANNEL_ID environment variables not set. Dynamic status updates will be disabled.")

    # --- Log Database Inspection Status ---
    if INSPECT_DB_GUILD_ID and INSPECT_DB_CHANNEL_ID:
        logger.info(f"Database inspection command (/database) enabled for Guild ID {INSPECT_DB_GUILD_ID}, Channel ID {INSPECT_DB_CHANNEL_ID}.")

        # --- Process Authorized Users ---
        if AUTHORIZED_USERS_STR:
            # Split by comma, strip whitespace, convert to lowercase, filter out empty strings
            raw_names = [name.strip().lower() for name in AUTHORIZED_USERS_STR.split(',')]
            AUTHORIZED_USERNAMES = {name for name in raw_names if name} # Use set comprehension to store unique, non-empty names
            if AUTHORIZED_USERNAMES:
                 logger.info(f"Database commands restricted to users: {', '.join(sorted(list(AUTHORIZED_USERNAMES)))}")
            else:
                 logger.error("AUTHORIZED_USERS environment variable was set, but contained no valid usernames after parsing. Database commands will be inaccessible.")
        else:
            logger.error("AUTHORIZED_USERS environment variable is not set. Database commands will be inaccessible.")
            AUTHORIZED_USERNAMES = set()

    else:
        logger.warning("Database inspection command (/database) is disabled. Set INSPECT_DATABASE_GUILD_ID and INSPECT_DATABASE_CHANNEL_ID environment variables to enable.")

    # Ensure src/responses directory exists for hyd command
    try:
        os.makedirs(RESPONSES_DIR, exist_ok=True)
        logger.info(f"Ensured responses directory exists: {RESPONSES_DIR}")
    except Exception as e:
        logger.error(f"Could not create responses directory '{RESPONSES_DIR}': {e}", exc_info=True)

    logger.info("Bot preparation complete.")
    return True

# --- Main Execution Block ---
if __name__ == "__main__":
    if prepare_bot():
        logger.info("Starting bot and web server...")
        try:
            # Run the client using the subclass and its setup_hook
            # log_handler=None prevents discord.py from setting up its own root logger handlers
            client.run(TOKEN, log_handler=None)
        except discord.PrivilegedIntentsRequired as e:
            logger.critical("\n" + "="*60 +
                  f"\nCRITICAL ERROR: Privileged intent(s) ({e.shard_id}) not enabled.\n"
                  "Please enable Guilds, Guild Messages, and Message Content intents in the Discord Developer Portal:\n"
                  "Application -> Bot -> Privileged Gateway Intents\n" +
                  "="*60)
        except discord.LoginFailure:
            logger.critical("\n" + "="*60 +
                  "\nCRITICAL ERROR: Invalid Discord Bot Token.\n"
                  "Please check the DISCORD_BOT_TOKEN environment variable.\n" +
                  "="*60)
        except Exception as e:
            logger.critical(f"\nAn unexpected critical error occurred during bot execution: {e}", exc_info=True)
            logger.critical("Bot execution stopped.")
    else:
        logger.error("Bot preparation failed. Exiting.")