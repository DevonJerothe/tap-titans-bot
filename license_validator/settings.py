from pathlib import Path
from os import path


# Validation Config Name.
# Since this module is reusable, you can use this
# to ensure different local directories are created
# and used to store our needed local data.
VALIDATION_NAME = "tap-titans-bot"
# Validation Config Identifier Secret.
VALIDATION_IDENTIFIER_SECRET = "zPM$mcY$Xc{%aT"

# Base Validation URL.
# This should be the main url with a trailing slash included.
# Additional url's are generated below.
VALIDATION_URL = "https://www.titanbots.net/"
VALIDATION_LICENSES_URL = "%(validation_url)s%(licenses_endpoint)s" % {
    "validation_url": VALIDATION_URL,
    "licenses_endpoint": "licenses",
}
# The retrieval url should be used on the application initialization
# to ensure the license included is currently valid.
VALIDATION_RETRIEVE_URL = "%(validation_licenses_url)s/%(retrieve_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "retrieve_endpoint": "retrieve",
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
VALIDATION_EVENT_URL = "%(validation_licenses_url)s/%(event_endpoint)s" % {
    "validation_licenses_url": VALIDATION_LICENSES_URL,
    "event_endpoint": "event",
}

# Build paths inside our project like this: BASE_DIRECTORY / "subdir".
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
# The user directory and our validation name value is used
# to determine what directory should be searched through
# as well as which files should be downloaded.
LOCAL_DATA_DIRECTORY = path.join(Path.home(), ".%(name)s" % {
    "name": VALIDATION_NAME,
})
LOCAL_DATA_FILES_DIRECTORY = path.join(LOCAL_DATA_DIRECTORY, "files")
# Any additional dependencies can be stored in this directory.
LOCAL_DATA_DEPENDENCIES_DIRECTORY = path.join(LOCAL_DATA_DIRECTORY, "dependencies")
# Any local logs should be stored in this directory.
LOCAL_DATA_LOGS_DIRECTORY = path.join(LOCAL_DATA_DIRECTORY, "logs")
# We'll also store our configurations locally so that a user can stop/start
# a program without retrieving configurations every time.
LOCAL_DATA_CONFIGURATIONS_FILE = path.join(LOCAL_DATA_DIRECTORY, "configurations.titan")
# The configuration file itself should be populated with a default configuration
# (handled elsewhere), and allow for configurations to be specified by the user.
LOCAL_DATA_CONFIGURATION_FILE = path.join(LOCAL_DATA_DIRECTORY, "configuration.txt")
# The license information should be stored in our local data directory
# in a proper text file.
LOCAL_DATA_LICENSE_FILE = path.join(LOCAL_DATA_DIRECTORY, "license.txt")
