from pathlib import Path
from os import path


# Validation Config Name.
# Since this module is reusable, you can use this
# to ensure different local directories are created
# and used to store our needed local data.
VALIDATION_NAME = "tap-titans-bot"
# Validation Config Identifier Secret.
VALIDATION_IDENTIFIER_SECRET = "PAbb|bZc1.'9M4cHH%{"

# Base Validation URL.
# This should be the main url with a trailing slash included.
# Additional url's are generated below.
VALIDATION_URL = "https://www.titanbots.net"
VALIDATION_LICENSES_URL = "%(validation_url)s/%(licenses_endpoint)s" % {
    "validation_url": VALIDATION_URL,
    "licenses_endpoint": "licenses",
}

VALIDATION_SYNCED = "synced"
VALIDATION_SYNC = "sync"

# Dependencies urls can be used to both determine if any are missing,
# and download missing dependencies.
VALIDATION_DEPENDENCIES_CHECK_URL = "%(validation_licenses_url)s/%(dependencies_check_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "dependencies_check_endpoint": "dependencies/check",
}
VALIDATION_DEPENDENCIES_RETRIEVE_URL = "%(validation_licenses_url)s/%(dependencies_retrieve_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "dependencies_retrieve_endpoint": "dependencies/retrieve",
}

# Files urls can be used to both determine if any are missing,
# and download missing files.
VALIDATION_FILES_CHECK_URL = "%(validation_licenses_url)s/%(files_check_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "files_check_endpoint": "files/check",
}
VALIDATION_FILES_RETRIEVE_URL = "%(validation_licenses_url)s/%(files_retrieve_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "files_retrieve_endpoint": "files/retrieve",
}

VALIDATION_LICENSE_RETRIEVE_URL = "%(validation_licenses_url)s/%(license_retrieve_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "license_retrieve_endpoint": "license/retrieve",
}

# State urls can be used to properly set an online and offline state.
VALIDATION_ONLINE_URL = "%(validation_licenses_url)s/%(online_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "online_endpoint": "state/online",
}
VALIDATION_OFFLINE_URL = "%(validation_licenses_url)s/%(offline_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "offline_endpoint": "state/offline",
}
VALIDATION_FLUSH_URL = "%(validation_licenses_url)s/%(flush_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "flush_endpoint": "flush",
}
VALIDATION_SESSION_URL = "%(validation_licenses_url)s/%(session_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "session_endpoint": "session",
}
VALIDATION_PRESTIGE_URL = "%(validation_licenses_url)s/%(prestige_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "prestige_endpoint": "session/prestige",
}
# Build paths inside our project like this: BASE_DIRECTORY / "subdir".
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
# The user directory and our validation name value is used
# to determine what directory should be searched through
# as well as which files should be downloaded.
LOCAL_DATA_DIRECTORY = path.join(Path.home(), ".%(name)s" % {
    "name": VALIDATION_NAME,
})
LOCAL_DATA_FILE_DIRECTORY = path.join(LOCAL_DATA_DIRECTORY, "files")
# Any additional dependencies can be stored in this directory.
LOCAL_DATA_DEPENDENCY_DIRECTORY = path.join(LOCAL_DATA_DIRECTORY, "dependencies")
# Any local logs should be stored in this directory.
LOCAL_DATA_LOGS_DIRECTORY = path.join(LOCAL_DATA_DIRECTORY, "logs")
# The license information should be stored in our local data directory
# in a proper text file.
LOCAL_DATA_LICENSE_FILE = path.join(LOCAL_DATA_DIRECTORY, "license.txt")

TEMPLATE_CONFIGURATIONS = "%(validation_url)s/profile/configurations" % {
    "validation_url": VALIDATION_URL,
}
