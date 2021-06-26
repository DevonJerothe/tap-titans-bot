import os
import pathlib

APPLICATION_NAME = "tap-titans-bot"
# The project directory is useful so we can build out paths to our different
# sub directories that are used by the different pieces of the program.
PROJECT_DIRECTORY = pathlib.Path(__file__).resolve().parent
# The bot directory houses many of the files needed to ensure a bot session
# can be ran correctly and the proper data is processed.
BOT_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "bot")
# The data directory houses our images and schema files.
BOT_DATA_DIRECTORY = os.path.join(BOT_DIRECTORY, "data")
# The images directory houses all images used by a bot session.
BOT_DATA_IMAGES_DIRECTORY = os.path.join(BOT_DATA_DIRECTORY, "images")
# The schema directory houses all of the configurations used by a bot session.
BOT_DATA_SCHEMA_DIRECTORY = os.path.join(BOT_DATA_DIRECTORY, "schema")
# The configuration file contains all global configurations.
BOT_DATA_SCHEMA_CONFIGURATION_FILE = os.path.join(BOT_DATA_SCHEMA_DIRECTORY, "schema.json")

# The database directory houses all models and database utilities.
DATABASE_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "database")
# The models directory houses all database models and their associated
# model instances and migrations schemas.
MODELS_DIRECTORY = os.path.join(DATABASE_DIRECTORY, "models")

# Any local data files should be kept here...
# We use this as the main source of data or persistent
# information. Databases/files/logs/etc.
LOCAL_DATA_DIRECTORY = os.path.join(pathlib.Path.home(), ".%s" % APPLICATION_NAME)
# Main database file path.
LOCAL_DATABASE = os.path.join(LOCAL_DATA_DIRECTORY, "database.sqlite")
# Database settings and toggles, lifted from the peewee documentation:
# http://docs.peewee-orm.com/en/latest/peewee/database.html#recommended-settings
LOCAL_DATABASE_SETTINGS = {
    "journal_mode": "wal",
    "cache_size": -1 * 64000,
    "foreign_keys": 1,
    "ignore_check_constraints": 0,
    "synchronous": 0,
}

# Any local logs should be stored in this directory.
# This is also passed into our gui functionality where needed.
LOCAL_DATA_LOGS_DIRECTORY = os.path.join(LOCAL_DATA_DIRECTORY, "logs")
