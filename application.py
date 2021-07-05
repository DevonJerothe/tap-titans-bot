import django
import sys
import os


# Turning off bytecode generation...
sys.dont_write_bytecode = True

# Ensure Django is using our settings module, which contains
# the proper database connection information.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

# This setup call actually handles most of the initialization
# work, once this is done, from this entry point, we can access
# the orm and deal with management commands, etc.
django.setup()


# End Django Bootstrap...
from settings import (
    LOCAL_DATA_DIRECTORY,
    LOCAL_DATA_LOGS_DIRECTORY,
)

from django.core.management import (
    call_command,
)

from gui.main import (
    GUI,
)


def handle_local_directories():
    """
    Generate local directories and files if they aren't already available.
    """
    for directory in [
        LOCAL_DATA_DIRECTORY,
        LOCAL_DATA_LOGS_DIRECTORY,
    ]:
        if not os.path.exists(directory):
            os.makedirs(directory)


def handle_migrations():
    """Handle migration execution through the Django management command.
    """
    call_command(
        "migrate",
    )


if __name__ == "__main__":
    # Local data directory should be built before
    # dealing with any functionality that may need
    # to access that directory.
    handle_local_directories()
    # Migrations are handled after, since we need
    # the database directory available to run here.
    handle_migrations()

    gui = GUI(
        application_name="Tap Titans Bot",
        application_version="1.2.1",
    )
    gui.run()
