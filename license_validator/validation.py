from license_validator.settings import (
    VALIDATION_NAME,
    VALIDATION_IDENTIFIER_SECRET,
    VALIDATION_RETRIEVE_URL,
    VALIDATION_ONLINE_URL,
    VALIDATION_OFFLINE_URL,
    VALIDATION_FLUSH_URL,
    VALIDATION_SESSION_URL,
    VALIDATION_PRESTIGE_URL,
    LOCAL_DATA_DIRECTORY,
    LOCAL_DATA_FILES_DIRECTORY,
    LOCAL_DATA_DEPENDENCIES_DIRECTORY,
    LOCAL_DATA_LOGS_DIRECTORY,
    LOCAL_DATA_LICENSE_FILE,
    TEMPLATE_CONFIGURATIONS,
)
from license_validator.utilities import (
    get_license,
    set_files,
    set_dependencies,
    changed_contents,
)
from license_validator.exceptions import (
    LicenseRetrievalError,
    LicenseExpirationError,
    LicenseServerError,
    LicenseConnectionError,
    LicenseIntegrityError,
)

from requests_futures.sessions import FuturesSession

import os
import json
import requests


class LicenseValidator(object):
    """
    LicenseValidator class may be used to encapsulate all functionality used when validating
    a license key.

    Modify the settings.py file to manage the class instance generated.
    """

    def __init__(self):
        """
        Initializing will setup and find certain variables and/or system files, the license key
        needed to validate certain things may not be present on initialization, that will properly
        update an attribute that we can use to determine our conditional paths.
        """
        self.program_name = VALIDATION_NAME
        self.program_identifier = VALIDATION_IDENTIFIER_SECRET
        self.program_retrieve_url = VALIDATION_RETRIEVE_URL
        self.program_online_url = VALIDATION_ONLINE_URL
        self.program_offline_url = VALIDATION_OFFLINE_URL
        self.program_flush_url = VALIDATION_FLUSH_URL
        self.program_export_session_url = VALIDATION_SESSION_URL
        self.program_export_prestige_url = VALIDATION_PRESTIGE_URL

        self.program_directory = LOCAL_DATA_DIRECTORY
        self.program_files_directory = LOCAL_DATA_FILES_DIRECTORY
        self.program_dependencies_directory = LOCAL_DATA_DEPENDENCIES_DIRECTORY
        self.program_logs_directory = LOCAL_DATA_LOGS_DIRECTORY
        self.program_license_file = LOCAL_DATA_LICENSE_FILE

        self.program_configurations_template = TEMPLATE_CONFIGURATIONS

        # Ensure local data directories are at least generated
        # if they aren't already.
        self.handle_local_directories()
        # Populated during retrieval.
        self.session = None
        self.license_data = None

    @property
    def license_available(self):
        """
        Determine if a license is actually available and currently set to a real value.
        """
        return get_license(
            license_file=self.program_license_file,
            only_check_exists=True,
        )

    @property
    def license(self):
        """
        Return the current value license.
        """
        return get_license(
            license_file=self.program_license_file,
        )

    def handle_local_directories(self):
        """
        Generate local directories and files if they aren't already available.
        """
        for directory in [
            self.program_directory,
            self.program_files_directory,
            self.program_dependencies_directory,
            self.program_logs_directory,
        ]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Local data files should come after our directories are
        # guaranteed to be available. Opening them in write mode to create.
        for file in [
            self.program_license_file,
        ]:
            if not os.path.exists(file):
                with open(file, mode="w"):
                    pass

    @staticmethod
    def _post(url, background=False, data=None):
        request_args = {
            "url": url,
            "data": data,
            "timeout": (
                60,   # Connection.
                600,  # Read.
            ),
        }
        try:
            if background:
                # Return immediately after firing background request...
                # This allows caller to continue running.
                return FuturesSession().post(**request_args)
            else:
                response = requests.post(**request_args)
        except requests.ConnectionError as err:
            # Server is down, connection is not working, return the error
            # along with our explicit connection error.
            raise LicenseConnectionError(err)

        if response.status_code == 404:
            raise LicenseRetrievalError()
        if response.status_code == 403:
            raise LicenseExpirationError(
                response.text,
            )
        if response.status_code == 400:
            raise LicenseIntegrityError()
        if response.status_code == 500:
            raise LicenseServerError()

        return response

    def _retrieve(self, url, include_files=True, set_data=True, logger=None, update_license_data=True):
        """
        Utility function to handle retrieving any license based urls.

        The url specified will determine what is being accessed.
        """
        response = self._post(
            url=url,
            data=self.program_data(
                include_files=include_files,
            ),
        )

        # Convert response to json data equivalent.
        # We now have access to all license data needed.
        if update_license_data:
            self.license_data = response.json()
        if set_data:
            set_files(
                files_directory=self.program_files_directory,
                files=self.license_data["program"]["files"],
                logger=logger,
            )
            set_dependencies(
                dependencies_directory=self.program_dependencies_directory,
                dependencies=self.license_data["program"]["dependencies"],
                logger=logger,
            )
        return response

    def retrieve(self, include_files=True, set_data=True, update_license_data=True, logger=None):
        """
        Retrieve the current license.

        We expect the license to be available at this point, the information returned here will be in a json
        dictionary of information. It should be noted that we only ever return images that aren't already
        available in the users local data directory.

        Once the data is retrieved, we will call some additional helper methods so that we can
        successfully update the users local data as needed.
        """
        return self._retrieve(
            url=self.program_retrieve_url,
            include_files=include_files,
            set_data=set_data,
            update_license_data=update_license_data,
            logger=logger,
        )

    def online(self):
        """
        Set the current license to an online state.

        This is only possible when we actually have a license.
        """
        if self.license_available:
            return self._retrieve(
                url=self.program_online_url,
                include_files=False,
                set_data=False,
                update_license_data=False,
            )

    def offline(self):
        """
        Set the current license to an offline state.

        This is only possible when we actually have a license.
        """
        if self.license_available:
            try:
                return self._retrieve(
                    url=self.program_offline_url,
                    include_files=False,
                    set_data=False,
                    update_license_data=False,
                )
            except Exception:
                pass

    def flush(self):
        """
        Flush the users current license.

        This is only possible when we actually have a license.
        """
        if self.license_available:
            try:
                return self._retrieve(
                    url=self.program_flush_url,
                    include_files=False,
                    set_data=False,
                    update_license_data=False,
                )
            except Exception:
                pass

    def export_session(self, export_contents=None, original_contents=None, extra={}):
        """
        Export a users session and exported contents to the backend.

        "original_contents" can be included to perform some additional parsing
        with the set of exports to determine which values have changed.
        """
        return self._post(
            url=self.program_export_session_url,
            data={
                "export_contents": json.dumps(export_contents or {} if not original_contents else changed_contents(
                    export_contents=export_contents,
                    original_contents=original_contents,
                )) if export_contents else None,
                **self.program_data(include_files=False),
                **extra,
            },
        )

    def export_prestige(self, prestige_contents):
        """
        Export a users prestige and the data associated.
        """
        return self._post(
            url=self.program_export_prestige_url,
            data={
                "prestige_contents": json.dumps(prestige_contents),
                **self.program_data(include_files=False),
            },
        )

    def program_data(self, include_files=True):
        """
        Return a JSON formatted string containing all of our validation data required to retrieve a license.
        """
        dct = {
            "session": self.session,
            "slug": self.program_name,
            "identifier": self.program_identifier,
            "key": self.license,
        }
        if include_files:
            dct.update({
                "exclude_files": json.dumps(self.files(
                    directory=self.program_files_directory,
                )),
                "exclude_dependencies": json.dumps(self.dependencies(
                    directory=self.program_dependencies_directory,
                    extensions=[".zip"],
                )),
            })
        return dct

    @property
    def expiration(self):
        """
        Return the expiration date for the validated license.
        """
        if not self.license_data:
            return None

        return "%(expiration)s (%(expiration_days)s day(s))." % {
            "expiration": self.license_data["expiration"],
            "expiration_days": self.license_data["expiration_days"],
        }

    @staticmethod
    def files(directory):
        """
        Return a list of files currently present in specified directory.

        Files should be stored in the base files directory, each within their own version directory.
        This format is required to properly send over our existing files whenever we retrieve license data.

        Passing in extensions will ensure that only files with the specified extensions are included.
        """
        lst = []

        with os.scandir(directory) as scan:
            for version in scan:
                for file in os.scandir(version.path):
                    lst.append((
                        version.name,
                        file.name,
                    ))
        return lst

    @staticmethod
    def dependencies(directory, extensions=None):
        """
        Return a list of dependencies currently present in the specified directory.

        Dependencies should be stored in the base dependencies directory, each with an associated .zip
        folder, and an extracted directory.

        Versions are ignored with dependencies so we can safely generate a list of file names
        without worrying about any version information.
        """
        if not extensions:
            extensions = []

        lst = []

        with os.scandir(directory) as scan:
            for file in scan:
                if extensions:
                    if os.path.splitext(file.name)[1] in extensions:
                        lst.append(file.name)
                else:
                    # Just append the file name, extension
                    # does not matter in this case.
                    lst.append(file.name)
        return lst
