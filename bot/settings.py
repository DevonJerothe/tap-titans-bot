from pathlib import Path
from os import path


# Build paths inside our project like this: BASE_DIRECTORY / "subdir".
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
# "bot" directory is used to find files within the main
# bot module present in the repo.
BOT_DIRECTORY = path.join(PROJECT_DIRECTORY, "bot")
# Configuration directory will be used
# to house our default configuration file
# as well as deal with some configuration specific utilities.
CONFIGURATION_DIRECTORY = path.join(BOT_DIRECTORY, "configuration")
# Our default configuration file is used to handle some
# default values that we always want in our local configuration.
CONFIGURATION_DEFAULT_FILE = path.join(CONFIGURATION_DIRECTORY, "default.json")
