from settings import (
    LOCAL_DATA_DIRECTORY,
    LOCAL_DATA_LOGS_DIRECTORY,
)

from database.database import (
    db,
    router,
)
from database.models.settings.settings import Settings
from database.models.instance.instance import Instance
from database.models.configuration.configuration import Configuration
from database.models.event.event import Event

from gui.main import (
    GUI,
)

import os


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


if __name__ == "__main__":
    # Local data directory should be built before
    # dealing with any functionality that may need
    # to access that directory.
    handle_local_directories()
    # Ensure database tables are upto date and generated
    # where applicable.
    db.create_tables([
        Settings,
        Instance,
        Configuration,
        Event,
    ])
    # Loop through available models, creating them in the
    # migrator before running our router.
    for model in [
        Settings,
        Instance,
        Configuration,
        Event,
    ]:
        router.migrator.create_table(model)

    router.run()

    gui = GUI(
        application_name="Tap Titans Bot",
        application_version="1.2.0",
    )
    gui.run()
