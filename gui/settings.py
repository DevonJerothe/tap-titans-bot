from pathlib import Path
from os import path


MEDIA_DIRECTORY = path.join(Path(__file__).resolve().parent.parent, "media")
# Retrieve the file that will be used as an icon for use
# with the system tray implementation.
ICON_FILE = path.join(MEDIA_DIRECTORY, "flame.ico")

# The dt format here is used when displaying event times
# to ensure a more condensed format is used.
DT_FORMAT = "%m/%d/%Y %I:%M:%S"

# Menu definitions can make use of these constants to aid in
# the generation of menu entries.
MENU_DISABLED = "!"
MENU_SEPARATOR = "---"

# Our custom menu titles and strings can be placed here and reused
# when we read events to determine which buttons are pressed.
MENU_BLANK_HEADER = "Menu"
MENU_FORCE_PRESTIGE = "Force Prestige"
MENU_FORCE_STOP = "Force Stop"
MENU_START_SESSION = "Start Session"
MENU_START_EVENT = "Start"
MENU_STOP_SESSION = "Stop Session"
MENU_RESUME_SESSION = "Resume Session"
MENU_PAUSE_SESSION = "Pause Session"
MENU_EVENTS = "Events"
MENU_TOOLS = "Tools"
MENU_TOOLS_LOCAL_DATA = "Local Data"
MENU_TOOLS_GENERATE_DEBUG_SCREENSHOT = "Generate Debug Screenshot"
MENU_TOOLS_MOST_RECENT_LOG = "Most Recent Log"
MENU_INSTANCES = "Instances"
MENU_CONFIGURATIONS_ADD = "Add Configuration"
MENU_CONFIGURATIONS = "Configurations"
MENU_SETTINGS = "Settings"

MENU_DISCORD = "Discord"
MENU_EXIT = "Exit"
MENU_TIMEOUT = "__TIMEOUT__"
