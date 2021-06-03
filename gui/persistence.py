import json


class PersistenceUtils(object):
    """
    Utility wrapper for all persistence based settings and options.
    """
    def __init__(self, file, logger):
        """
        Initialize a new utility instance, the file specified should contain all persistence data.
        """
        self.__default_persistence = None

        self.file = file
        self.logger = logger

        # Define our keys expected in the persistence data.
        # These should also be included in the defaults so
        # any updates to this can be synced.
        self._persistence = (
            ("enable_toast_notifications", True),
            ("enable_failsafe", True),
            ("enable_ad_blocking", False),
            ("enable_auto_update", True),
            ("auto_update_path", ""),
            ("console_startup_size", "mode con: cols=140 lines=200"),
            ("last_window_choice", None),
            ("last_configuration_choice", None),
        )

        # Make this private, we can use it through utilities
        # below only to get/set values.
        self._data = self._load_persistence_data(file=self.file)

    @property
    def _default_persistence(self):
        """Retrieve the default persistence values.
        """
        if not self.__default_persistence:
            self.__default_persistence = {
                key: default for key, default in self._persistence
            }
        return self.__default_persistence

    def _load_persistence_data(self, file):
        """
        Load all the existing data in the file specified, if no data is available, we'll
        setup some generic defaults that can be used.
        """
        with open(file, mode="r") as data:
            try:
                data = json.loads(data.read())
                data = self._sync_persistence(data=data)
            # We have no content in the persistence file at all,
            # we'll just setup the defaults.
            except json.JSONDecodeError:
                self.logger.debug(
                    "No persistence data is available, writing defaults..."
                )
                data = self._write_persistence_data(
                    content=self._default_persistence,
                )
            # If a generic exception occurs, we'll log it and return
            # the default data to use...
            except Exception as exc:
                self.logger.debug(
                    "An exception occurred while trying to load persistence data, using defaults..."
                )
                data = self._default_persistence,
        self.logger.debug(
            "Persistence data: %(persisted)s" % {
                "persisted": data,
            }
        )
        return data

    def _sync_persistence(self, data):
        """
        Sync the persistence data to ensure a valid file with missing
        keys includes all the values.
        """
        for key in self._default_persistence:
            if key not in data:
                self.logger.debug(
                    "Persistence key: \"%(key)s\" is missing in persistent data, adding..." % {
                        "key": key,
                    }
                )
                data[key] = self._default_persistence[key]

        for key in list(data.keys()):
            if key not in self._default_persistence:
                self.logger.debug(
                    "Persistence key: \"%(key)s\" is present in persistent data, but no longer present in defaults, removing..." % {
                        "key": key,
                    }
                )
                del data[key]
        return data

    def _write_persistence_data(self, content=None):
        """
        Write the given content to the persistence file.
        """
        if not content:
            content = self._data
        with open(self.file, mode="w") as data:
            data.write(json.dumps(content))
        return content

    def get_persistence(self, key):
        """Retrieve one of the available persistence keys.
        """
        return self._data[key]

    def set_persistence(self, key, value):
        """Update one of the available persistence keys.
        """
        self._data[key] = value
        self._write_persistence_data()
