import os
import pathlib

APPLICATION_NAME = "tap-titans-bot"
# The project directory is useful so we can build out paths to our different
# sub directories that are used by the different pieces of the program.
PROJECT_DIRECTORY = pathlib.Path(__file__).resolve().parent
# Secret key is django based and purely used to setup
# our framework, this isn't production facing so this is fine.
SECRET_KEY = "6few3nci_q_o@l1dlbk81%wcxe!*6r29yu629&d97!hiqat9fa"
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
# Database settings, we're using SQLite to ensure out of the box,
# a user can just run the app without much additional setup.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": LOCAL_DATABASE,
    },
}
# This is another django facing setting, ensuring the database
# module is included and initialized by the Django ORM.
INSTALLED_APPS = (
    "database",
)
# This will suppress a warning that pops up when a default auto field
# isn't chosen...
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Any local logs should be stored in this directory.
# This is also passed into our gui functionality where needed.
LOCAL_DATA_LOGS_DIRECTORY = os.path.join(LOCAL_DATA_DIRECTORY, "logs")
