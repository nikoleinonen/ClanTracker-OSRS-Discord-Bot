import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import json
import secrets
import string
import asyncio
import logging
import traceback
import re # Added for parsing helpers
from typing import Dict, Optional, Set, Tuple, List, Any
import random
from collections import OrderedDict # Ensure OrderedDict is imported
from aiohttp import web # For the web server API

# --- Logging Setup (Stream Only for Production) ---
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log_level = logging.INFO # Keep INFO level for production, or change as needed

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
# --- End Logging Setup ---

# --- Configuration ---
load_dotenv() # Load .env file for local development, Railway uses its own env vars

# Bot Settings
TOKEN: Optional[str] = os.getenv('DISCORD_BOT_TOKEN')
CATEGORY_NAME: str = os.getenv('CLANTRACKER_CATEGORY_NAME', "ClanTracker-OSRS") # Use env var or default
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
DEFAULT_STATUS_MESSAGE: str = os.getenv('DEFAULT_BOT_STATUS', "Tracking OSRS Clans") # Default status

# Data Storage
DATA_DIR: str = "/data"
IDENTIFIER_FILE_NAME: str = "clan_identifiers.json"
IDENTIFIER_FILE: str = os.path.join(DATA_DIR, IDENTIFIER_FILE_NAME)
IDENTIFIER_LENGTH: int = 8

# Responses
RESPONSES_DIR: str = "commands"
HYD_FILE_NAME: str = "hyd.txt"
HYD_FILE_PATH: str = os.path.join(RESPONSES_DIR, HYD_FILE_NAME)

# External Links
GITHUB_README_MD_LINK: str = os.getenv('GITHUB_README_MD_LINK', "https://github.com/YOUR_USERNAME/YOUR_REPO/blob/main/info.md") # <-- TODO: Set this in Railway env vars!

# Bot Discord Permissions
BOT_PERMISSIONS: int = 68624

# --- Global Storage for Identifiers ---
server_identifiers: Dict[str, Dict[str, str]] = {}

# --- Initial Message Content Constants ---
# Keep all MSG_... constants as they are, but ensure they use the channel name variables
# Example adjustment (apply similarly to others):
MSG_INFO_WELCOME = (
    "**Thank you for using ClanTracker OSRS!**\n\n"
    "Your unique Clan Identifier: `{clan_identifier}`\n"
    "(Share this with your clan members for the desktop application)\n\n"
    f"I have automatically created channels for you under the **{CATEGORY_NAME}** category:\n"
    f"1.  `#{INFO_CHANNEL_NAME}`: General information and guides.\n"
    f"2.  `#{CONFIG_CHANNEL_NAME}`: Stores settings for your clan's desktop application.\n"
    f"3.  `#{MANUAL_POINTS_CHANNEL_NAME}`: Used for manual points.\n"
    f"4.  `#{COMMANDS_CHANNEL_NAME}`: Bot commands must be used here."
)
MSG_INFO_CONFIG_INTRO = (
    "------------------------------------\n"
    f"**About `#{CONFIG_CHANNEL_NAME}`:**\n\n"
    f"`#{CONFIG_CHANNEL_NAME}` is where you define the global settings for your clan's ClanTracker application. Clan leaders should edit messages here following the specified format.\n\n"
    "Settings are defined in `INI` format within messages in that channel. The desktop app will fetch these settings by using the Clan Identifier.\n\n"
    "**Configuration Sections Overview:**"
)
MSG_INFO_CONFIG_TEMPLE = (
    "```ini\n"
    "[templeosrs_group_id]\n"
    "# Your templeOSRS group ID. Found at the end of your group's TempleOSRS URL.\n"
    "# Example: https://templeosrs.com/groups/overview.php?id=YOUR_ID_HERE\n"
    "templeosrs_group_id = YOUR_ID_HERE\n"
    "```"
)
MSG_INFO_CONFIG_THEME = (
    "```ini\n"
    "[theme]\n"
    "# Set your clan's theme for the application.\n"
    "# Use hex color codes (#RRGGBB).\n"
    "background_color_custom = #0E0E0E\n"
    "menu_color_custom = #151515\n"
    "accent_color_custom = #124080\n"
    "selected_color_custom = #0d3265\n"
    "txt_color_custom = #D2D2D2\n"
    "```"
)
MSG_INFO_CONFIG_RANKS = (
    "```ini\n"
    "[ranks]\n"
    "# Define clan ranks based on total points.\n"
    "# rank_thresholds: Comma-separated list of minimum points for each rank (lowest first).\n"
    "# rank_titles: Comma-separated list of rank names (matching thresholds, lowest first).\n"
    "# num_ranks: Total number of ranks defined (must match list lengths).\n"
    "rank_thresholds = 0, 5, 10, 20, 40, 60, 80, 120, 160, 180, 200\n"
    "rank_titles = Burger, Rank 1, Rank 2, Rank 3, Rank 4, Rank 5, Rank 6, Rank 7, Rank 8, Rank 9, Rank 10\n"
    "num_ranks = 11\n"
    "```"
)
MSG_INFO_CONFIG_RECORDS = (
    "```ini\n"
    "[records_include]\n"
    "# Which time-based TempleOSRS records should contribute to the 'Records Held' count?\n"
    "# Set to 'true' to include, 'false' to exclude.\n"
    "6h = true\n"
    "day = false\n"
    "72h = false\n"
    "week = false\n"
    "month = false\n"
    "year = false\n"
    "```"
)
MSG_INFO_CONFIG_CUSTOMKEYS = (
    "```ini\n"
    "[custom_keys]\n"
    "# Define custom keys/flags for members. Useful for points requiring combined data.\n"
    "# These can group related activities (e.g., different raid types).\n"
    "# Default examples (you can modify or add your own):\n"
    "burger_raids = chambers of xeric, tombs of amascut, theatre of blood\n"
    "regular_raids = chambers of xeric, theatre of blood, tombs of amascut expert\n"
    "cm_raids = chambers of xeric challenge mode, theatre of blood challenge mode\n"
    "all_raids = chambers of xeric, chambers of xeric challenge mode, theatre of blood, theatre of blood challenge mode, tombs of amascut, tombs of amascut expert\n"
    "```"
)
MSG_INFO_CONFIG_VISIBLE = (
    "```ini\n"
    "[visible_categories]\n"
    "# Which data categories to display on the 'Members' tab in the application.\n"
    "# Format: internal_key | Display Name = true\n"
    "# Default visible categories are already set in the application's base config.\n"
    "# You can override or add more here.\n"
    "total_level | Total Level = true\n"
    "total_xp | Total XP = true\n"
    "```"
)
MSG_INFO_CONFIG_HIDDEN = (
    "```ini\n"
    "[hidden_categories]\n"
    "# This section in the base config lists all available categories you *can* show.\n"
    "# To see the full list of available categories, please refer to the info.md file\n"
    f"# on the project's GitHub page: {GITHUB_README_MD_LINK}\n"
    "# To make a hidden category visible, copy its line to the [visible_categories]\n"
    "# section above and set its value to 'true'.\n"
    "# Example (if you wanted to show EHP):\n"
    "# ehp | EHP = true  (<- Add this line under [visible_categories])\n"
    "```"
)
MSG_INFO_CONFIG_POINTS = (
    "```ini\n"
    "[points_CATEGORY_NAME]\n"
    "# Define point values for different achievements or stats.\n"
    "# Replace CATEGORY_NAME with a descriptive name (e.g., points_skills, points_bossing).\n"
    "# Format depends on the point type.\n"
    "# Example: [points_capes]\n"
    "# quest_cape = 10\n"
    "```\n\n"
    "**Detailed Point Configuration:**\n"
    "For comprehensive details on how to configure the `[points_...]` sections, please refer to the `info.md` file in the project's GitHub repository. Reading it directly on GitHub is recommended for better formatting:\n"
    f"{GITHUB_README_MD_LINK}\n"
)
MSG_INFO_MANUAL_POINTS_EXPLAIN = (
    "------------------------------------\n"
    f"**About `#{MANUAL_POINTS_CHANNEL_NAME}`:**\n\n"
    "This channel is used to record points for achievements or activities that **cannot** be automatically tracked via APIs (like Wise Old Man, TempleOSRS, CollectionLog.net, HiScores etc.).\n\n"
    "**Format (Strictly ONE message per player):**\n"
    "Clan leaders (or designated members) should post **one message per player** in this channel using the following INI format:\n"
    "```ini\n"
    "[PlayerRSN]\n"
    "# Replace PlayerRSN with the player's exact RuneScape Name\n"
    "\n"
    "# Use the specific achievement keys defined by your clan leadership\n"
    f"# These keys might be defined in #{CONFIG_CHANNEL_NAME} or clan documentation\n"
    "quest_cape = true\n"
    "diary_cape = true\n"
    "infernal_cape_attempts = 5\n"
    "clan_event_participation = 12\n"
    "# Add other manual points as needed...\n"
    "```\n\n"
    "**Important Instructions:**\n"
    "- **One Message Per Player:** Do NOT post multiple messages for the same player.\n"
    "- **Edit to Update:** To change a player's manual points, **EDIT** their existing message in this channel. Do not post a new one.\n"
    "- **Accuracy:** Ensure RuneScape Names (RSNs) are spelled correctly, including spaces and capitalization, as they appear in-game.\n"
    "- **Permissions:** Consider setting channel permissions so only specific roles (e.g., Leaders, Admins) can post or edit messages here to maintain data integrity.\n\n"
    "The desktop application will read all messages in this channel and parse the points based on these entries.\n\n"
    "------------------------------------\n"
    "Need help? Ask in your clan's support channel or check the project documentation."
)
MSG_CONFIG_INTRO = (
    "**ClanTracker Configuration**\n\n"
    "This channel stores the settings for your clan that the desktop application will use.\n\n"
    "**Instructions for Clan Leaders:**\n"
    f"1.  Define your clan settings here using `INI` format within messages (see `#{INFO_CHANNEL_NAME}` for examples).\n"
    "2.  **Example:** `[templeosrs_group_id]\ntempleosrs_group_id = YOUR_ID_HERE` (Replace with your actual TempleOSRS group ID).\n"
    "3.  The desktop application will fetch these settings when a user provides the clan identifier.\n\n"
    "**Important:** Only clan leaders should modify messages here. Consider adjusting channel permissions accordingly."
)
MSG_CONFIG_IDENTIFIER = (
    "------------------------------------\n"
    "**Your unique Clan Identifier is:** `{clan_identifier}`\n"
    "Share this identifier **only** with your clan members. They will need it for the ClanTracker desktop application.\n"
    "------------------------------------"
)
MSG_MANUAL_POINTS_INTRO = (
    "**Manual Point Submissions**\n\n"
    "Post player points here. **One message per player.** Edit existing messages to update.\n\n"
    "**Format:**\n"
    "```ini\n"
    "[PlayerRSN]\n"
    "key1 = value1\n"
    "key2 = value2\n"
    "```\n"
    f"*(See `#{INFO_CHANNEL_NAME}` for detailed instructions and keys)*"
)
# --- End Initial Message Content Constants ---


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

# --- API Helper Functions (Moved from get_clan_information.py) ---

def find_guild_id_by_identifier(clan_identifier: str) -> Optional[str]:
    """Finds the Guild ID string associated with a clan identifier."""
    global server_identifiers # Use the bot's loaded identifiers
    for guild_id, data in server_identifiers.items():
        if data.get('identifier') == clan_identifier:
            return guild_id
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

        # --- Legacy ping command (Example) ---
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
# (Keep _notify_permission_error, _setup_category_and_channels, _ensure_identifier, _send_initial_messages functions exactly as they were in the original bot.py)
# ... Make sure they use the correct channel name variables ...
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

async def _send_initial_messages(
    guild: discord.Guild,
    channels: Dict[str, Optional[discord.TextChannel]],
    clan_identifier: str
) -> None:
    logger.info(f"Attempting to send initial content to channels in '{guild.name}'...")

    async def send_safe(channel: Optional[discord.TextChannel], content: str, channel_var_name: str):
        if not channel:
            logger.warning(f"Cannot send message because channel object for {channel_var_name} is None in '{guild.name}'.")
            return False
        if not channel.permissions_for(guild.me).send_messages:
            logger.warning(f"Missing 'Send Messages' permission in #{channel.name} ({channel_var_name}) for guild '{guild.name}'.")
            return False
        try:
            await channel.send(content)
            return True
        except discord.Forbidden:
            logger.error(f"Missing 'Send Messages' permission in #{channel.name} ({channel_var_name}) for guild '{guild.name}' despite initial check.")
            return False
        except discord.HTTPException as e:
             logger.error(f"HTTP error sending message to #{channel.name} ({channel_var_name}) in '{guild.name}': {e}", exc_info=True)
             return False
        except Exception as e:
            logger.error(f"Unexpected error sending message to #{channel.name} ({channel_var_name}) in '{guild.name}': {e}", exc_info=True)
            return False

    async def is_channel_empty(channel: Optional[discord.TextChannel], channel_var_name: str) -> bool:
        if not channel: return True
        if not channel.permissions_for(guild.me).read_message_history:
             logger.warning(f"Missing 'Read Message History' in #{channel.name} ({channel_var_name}). Assuming channel is not empty.")
             return False
        try:
            history = [msg async for msg in channel.history(limit=1)]
            return not history
        except (discord.Forbidden, discord.HTTPException) as e:
             logger.error(f"Error checking history for #{channel.name} ({channel_var_name}): {e}. Assuming not empty.")
             return False

    # --- Send to Info Channel ---
    info_channel = channels.get(INFO_CHANNEL_NAME)
    if info_channel and await is_channel_empty(info_channel, "INFO_CHANNEL_NAME"):
        logger.info(f"Sending initial messages to #{INFO_CHANNEL_NAME} in '{guild.name}'.")
        messages_to_send = [
            MSG_INFO_WELCOME.format(
                clan_identifier=clan_identifier, CATEGORY_NAME=CATEGORY_NAME,
                INFO_CHANNEL_NAME=INFO_CHANNEL_NAME, CONFIG_CHANNEL_NAME=CONFIG_CHANNEL_NAME,
                MANUAL_POINTS_CHANNEL_NAME=MANUAL_POINTS_CHANNEL_NAME, COMMANDS_CHANNEL_NAME=COMMANDS_CHANNEL_NAME
            ),
            MSG_INFO_CONFIG_INTRO.format(CONFIG_CHANNEL_NAME=CONFIG_CHANNEL_NAME),
            MSG_INFO_CONFIG_TEMPLE, MSG_INFO_CONFIG_THEME, MSG_INFO_CONFIG_RANKS,
            MSG_INFO_CONFIG_RECORDS, MSG_INFO_CONFIG_CUSTOMKEYS, MSG_INFO_CONFIG_VISIBLE,
            MSG_INFO_CONFIG_HIDDEN.format(GITHUB_README_MD_LINK=GITHUB_README_MD_LINK),
            MSG_INFO_CONFIG_POINTS.format(GITHUB_README_MD_LINK=GITHUB_README_MD_LINK),
            MSG_INFO_MANUAL_POINTS_EXPLAIN.format(
                CONFIG_CHANNEL_NAME=CONFIG_CHANNEL_NAME, MANUAL_POINTS_CHANNEL_NAME=MANUAL_POINTS_CHANNEL_NAME
            )
        ]
        success_count = 0
        for i, msg_content in enumerate(messages_to_send):
            if await send_safe(info_channel, msg_content, "INFO_CHANNEL_NAME"):
                success_count += 1
                if i < len(messages_to_send) - 1: await asyncio.sleep(0.8)
            else:
                logger.error(f"Failed to send message {i+1} to #{INFO_CHANNEL_NAME}. Stopping info message dump.")
                await send_safe(info_channel,
                    f"**Welcome to ClanTracker OSRS!**\nYour identifier: `{clan_identifier}`.\n"
                    f"An error occurred sending the full setup info. Please check my permissions (Send Messages, Read History) in this channel or contact support.",
                    "INFO_CHANNEL_NAME"
                )
                break
        if success_count == len(messages_to_send):
             logger.info(f"Finished sending initial messages to #{INFO_CHANNEL_NAME} in '{guild.name}'.")
    elif info_channel:
         logger.info(f"Channel #{INFO_CHANNEL_NAME} in '{guild.name}' is not empty or history check failed. Skipping initial message dump.")
    else:
         logger.warning(f"Could not find or create #{INFO_CHANNEL_NAME} channel in '{guild.name}'. Cannot send info messages.")

    # --- Send to Config Channel ---
    config_channel = channels.get(CONFIG_CHANNEL_NAME)
    if config_channel and await is_channel_empty(config_channel, "CONFIG_CHANNEL_NAME"):
         logger.info(f"Sending initial messages to #{CONFIG_CHANNEL_NAME} in '{guild.name}'.")
         await send_safe(config_channel, MSG_CONFIG_INTRO.format(INFO_CHANNEL_NAME=INFO_CHANNEL_NAME), "CONFIG_CHANNEL_NAME")
         await asyncio.sleep(0.5)
         await send_safe(config_channel, MSG_CONFIG_IDENTIFIER.format(clan_identifier=clan_identifier), "CONFIG_CHANNEL_NAME")
    elif config_channel:
         logger.info(f"Channel #{CONFIG_CHANNEL_NAME} in '{guild.name}' is not empty or history check failed. Skipping initial messages.")
    else:
        logger.warning(f"Could not find or create #{CONFIG_CHANNEL_NAME} channel in '{guild.name}'. Cannot send config messages.")

    # --- Send to Manual Points Channel ---
    manual_points_channel = channels.get(MANUAL_POINTS_CHANNEL_NAME)
    if manual_points_channel and await is_channel_empty(manual_points_channel, "MANUAL_POINTS_CHANNEL_NAME"):
        logger.info(f"Sending initial message to #{MANUAL_POINTS_CHANNEL_NAME} in '{guild.name}'.")
        await send_safe(manual_points_channel, MSG_MANUAL_POINTS_INTRO.format(INFO_CHANNEL_NAME=INFO_CHANNEL_NAME), "MANUAL_POINTS_CHANNEL_NAME")
    elif manual_points_channel:
         logger.info(f"Channel #{MANUAL_POINTS_CHANNEL_NAME} in '{guild.name}' is not empty or history check failed. Skipping initial message.")
    else:
        logger.warning(f"Could not find or create #{MANUAL_POINTS_CHANNEL_NAME} channel in '{guild.name}'. Cannot send manual points intro.")

    # --- Send to Commands Channel (Optional Intro) ---
    commands_channel = channels.get(COMMANDS_CHANNEL_NAME)
    if commands_channel and await is_channel_empty(commands_channel, "COMMANDS_CHANNEL_NAME"):
        logger.info(f"Sending initial message to #{COMMANDS_CHANNEL_NAME} in '{guild.name}'.")
        await send_safe(commands_channel, f"Bot commands for ClanTracker should be used in this channel.\nType `/` to see available commands.", "COMMANDS_CHANNEL_NAME")
    elif commands_channel:
         logger.info(f"Channel #{COMMANDS_CHANNEL_NAME} in '{guild.name}' is not empty or history check failed. Skipping initial message.")
    else:
        logger.warning(f"Could not find or create #{COMMANDS_CHANNEL_NAME} channel in '{guild.name}'. Cannot send commands intro.")

    logger.info(f"Initial content setup phase finished for guild '{guild.name}'.")


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

# --- HYD Slash Command ---
@tree.command(name="hyd", description="Ask how the bot feels today :)")
@is_in_commands_channel()
async def hyd_command(interaction: discord.Interaction):
    """Handles the /hyd command."""
    try:
        # Ensure response directory/file exists
        os.makedirs(RESPONSES_DIR, exist_ok=True)
        if not os.path.exists(HYD_FILE_PATH):
            logger.warning(f"HYD response file not found at: {HYD_FILE_PATH}. Creating default.")
            with open(HYD_FILE_PATH, 'w', encoding='utf-8') as f:
                f.write("Feeling operational.\n")
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
    logger.info("Preparing bot...")
    if not TOKEN:
        logger.critical("CRITICAL ERROR: DISCORD_BOT_TOKEN environment variable not set. Bot cannot start.")
        return False
    if not GITHUB_README_MD_LINK or "YOUR_USERNAME/YOUR_REPO" in GITHUB_README_MD_LINK:
         logger.warning("Configuration Warning: GITHUB_README_MD_LINK is not set or uses the default placeholder. Please set this environment variable.")

    load_identifiers()

    if not STATUS_GUILD_ID or not STATUS_CHANNEL_ID:
        logger.warning("STATUS_GUILD_ID or STATUS_CHANNEL_ID environment variables not set. Dynamic status updates will be disabled.")

    # Ensure src/responses directory exists for hyd command
    try:
        os.makedirs(RESPONSES_DIR, exist_ok=True)
        logger.info(f"Ensured responses directory exists: {RESPONSES_DIR}")
    except Exception as e:
        logger.error(f"Could not create responses directory '{RESPONSES_DIR}': {e}", exc_info=True)
        # Decide if this is critical - maybe not if hyd isn't essential

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