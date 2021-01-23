from pathlib import Path
from os import path


# Build paths inside our project like this: BASE_DIRECTORY / "subdir".
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
MEDIA_DIRECTORY = path.join(PROJECT_DIRECTORY, "media")
# Retrieve the file that will be used as an icon for use
# with the system tray implementation.
ICON_FILE = path.join(MEDIA_DIRECTORY, "flame.ico")

# Menu definitions can make use of these constants to aid in
# the generation of menu entries.
MENU_DISABLED = "!"
MENU_SEPARATOR = "---"

# Our custom menu titles and strings can be placed here and reused
# when we read events to determine which buttons are pressed.
MENU_BLANK_HEADER = "Menu"
MENU_FORCE_PRESTIGE = "Force Prestige"
MENU_START_SESSION = "Start Session"
MENU_STOP_SESSION = "Stop Session"
MENU_RESUME_SESSION = "Resume Session"
MENU_PAUSE_SESSION = "Pause Session"
MENU_CONFIGURATIONS = "Configurations"
MENU_UPDATE_LICENSE = "Update License"
MENU_TOOLS = "Tools"
MENU_TOOLS_LOCAL_DATA = "Local Data"
MENU_TOOLS_MOST_RECENT_LOG = "Most Recent Log"
MENU_TOOLS_FLUSH_LICENSE = "Flush License"
MENU_SETTINGS = "Settings"
MENU_SETTINGS_ENABLE_TOAST_NOTIFICATIONS = "Enable Toast Notifications"
MENU_SETTINGS_DISABLE_TOAST_NOTIFICATIONS = "Disable Toast Notifications"
MENU_SETTINGS_ENABLE_FAILSAFE = "Enable Failsafe"
MENU_SETTINGS_DISABLE_FAILSAFE = "Disable Failsafe"
MENU_SETTINGS_ENABLE_AD_BLOCKING = "Enable Ad Blocking"
MENU_SETTINGS_DISABLE_AD_BLOCKING = "Disable Ad Blocking"
MENU_DISCORD = "Discord"
MENU_EXIT = "Exit"
MENU_TIMEOUT = "__TIMEOUT__"
