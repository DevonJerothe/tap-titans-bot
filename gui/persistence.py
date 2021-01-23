import json


class PersistenceUtils(object):
    """
    Utility wrapper for all persistence based settings and options.
    """
    def __init__(self, file, logger):
        """
        Initialize a new utility instance, the file specified should contain all persistence data.
        """
        self.file = file
        self.logger = logger
        # Define our keys expected in the persistence data.
        # These should also be included in the defaults so
        # any updates to this can be synced.
        self.toast_key = "enable_toast_notifications"
        self.failsafe_key = "enable_failsafe"
        self.ad_blocking_key = "enable_ad_blocking"

        self.default_persistence = {
            self.toast_key: True,
            self.failsafe_key: True,
            self.ad_blocking_key: False,
        }
        # Make this private, we can use it through utilities
        # below only to get/set values.
        self._data = self._load_persistence_data(file=self.file)

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
                    content=self.default_persistence,
                )
            # If a generic exception occurs, we'll log it and return
            # the default data to use...
            except Exception as exc:
                self.logger.debug(
                    "An exception occurred while trying to load persistence data, using defaults..."
                )
                data = self.default_persistence,
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
        for key in self.default_persistence:
            if key not in data:
                self.logger.debug(
                    "Persistence key: \"%(key)s\" is missing in persistent data, adding..." % {
                        "key": key,
                    }
                )
                data[key] = self.default_persistence[key]

        for key in list(data.keys()):
            if key not in self.default_persistence:
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

    def set_enable_toast_notifications(self, value):
        """
        Update the toast notifications persisted value.
        """
        self._data[self.toast_key] = value
        self._write_persistence_data()

    def get_enable_toast_notifications(self):
        """
        Retrieve the toast notifications persisted value.
        """
        return self._data[self.toast_key]

    def set_enable_failsafe(self, value):
        """
        Update the failsafe persisted value.
        """
        self._data[self.failsafe_key] = value
        self._write_persistence_data()

    def get_enable_failsafe(self):
        """
        Retrieve the failsafe persisted value.
        """
        return self._data[self.failsafe_key]

    def set_enable_ad_blocking(self, value):
        """
        Update the ad blocking persisted value.
        """
        self._data[self.ad_blocking_key] = value
        self._write_persistence_data()

    def get_enable_ad_blocking(self):
        """
        Retrieve the ad blocking persisted value.
        """
        return self._data[self.ad_blocking_key]
