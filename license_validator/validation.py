from license_validator.settings import (
    VALIDATION_EXECUTABLE_NAME,
    VALIDATION_NAME,
    VALIDATION_IDENTIFIER_SECRET,
    VALIDATION_URL,
    VALIDATION_SYNCED,
    VALIDATION_SYNC,
    VALIDATION_DEPENDENCIES_CHECK_URL,
    VALIDATION_DEPENDENCIES_RETRIEVE_URL,
    VALIDATION_FILES_CHECK_URL,
    VALIDATION_FILES_RETRIEVE_URL,
    VALIDATION_FILES_SYNC_URL,
    VALIDATION_LICENSE_RETRIEVE_URL,
    VALIDATION_ONLINE_URL,
    VALIDATION_OFFLINE_URL,
    VALIDATION_FLUSH_URL,
    VALIDATION_SESSION_URL,
    VALIDATION_PRESTIGE_URL,
    VALIDATION_VERSIONS_URL,
    LOCAL_DATA_DIRECTORY,
    LOCAL_DATA_FILE_DIRECTORY,
    LOCAL_DATA_DEPENDENCY_DIRECTORY,
    LOCAL_DATA_LOGS_DIRECTORY,
    LOCAL_DATA_LICENSE_FILE,
    LOCAL_DATA_PERSISTENCE_FILE,
    TEMPLATE_CONFIGURATIONS,
)
from license_validator.utilities import (
    get_license,
    set_file,
    sync_file,
    set_dependency,
    changed_contents,
    chunks,
)
from license_validator.exceptions import (
    LicenseRetrievalError,
    LicenseExpirationError,
    LicenseServerError,
    LicenseConnectionError,
    LicenseIntegrityError,
)

from zipfile import ZipFile
from requests_futures.sessions import FuturesSession

import io
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
        self.program_executable = VALIDATION_EXECUTABLE_NAME
        self.program_name = VALIDATION_NAME
        self.program_identifier = VALIDATION_IDENTIFIER_SECRET
        self.program_url = VALIDATION_URL

        self.program_dependencies_check_url = VALIDATION_DEPENDENCIES_CHECK_URL
        self.program_dependencies_retrieve_url = VALIDATION_DEPENDENCIES_RETRIEVE_URL

        self.program_files_check_url = VALIDATION_FILES_CHECK_URL
        self.program_files_retrieve_url = VALIDATION_FILES_RETRIEVE_URL
        self.program_files_sync_url = VALIDATION_FILES_SYNC_URL

        self.license_retrieve_url = VALIDATION_LICENSE_RETRIEVE_URL

        self.program_online_url = VALIDATION_ONLINE_URL
        self.program_offline_url = VALIDATION_OFFLINE_URL
        self.program_flush_url = VALIDATION_FLUSH_URL
        self.program_export_session_url = VALIDATION_SESSION_URL
        self.program_export_prestige_url = VALIDATION_PRESTIGE_URL
        self.program_check_versions_url = VALIDATION_VERSIONS_URL

        self.program_directory = LOCAL_DATA_DIRECTORY
        self.program_file_directory = LOCAL_DATA_FILE_DIRECTORY
        self.program_dependency_directory = LOCAL_DATA_DEPENDENCY_DIRECTORY
        self.program_logs_directory = LOCAL_DATA_LOGS_DIRECTORY
        self.program_license_file = LOCAL_DATA_LICENSE_FILE
        self.program_persistence_file = LOCAL_DATA_PERSISTENCE_FILE

        self.program_configurations_template = TEMPLATE_CONFIGURATIONS
        self.bulk_collect_chunk = 20

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
            self.program_file_directory,
            self.program_dependency_directory,
            self.program_logs_directory,
        ]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Local data files should come after our directories are
        # guaranteed to be available. Opening them in write mode to create.
        for file in [
            self.program_license_file,
            self.program_persistence_file,
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

    def _collect(
        self,
        logger,
        collect,
        collect_plural,
        collect_bulk,
        check_url,
        retrieve_url,
        setter,
        setter_kwargs,
        exclude_data,
    ):
        logger.info(
            "Syncing %(collect_plural)s..." % {
                "collect_plural": collect_plural,
            }
        )
        response = self._post(
            url=check_url,
            data={
                **self.program_data(),
                **exclude_data,
            },
        ).json()

        if response["status"] == VALIDATION_SYNCED:
            logger.info(
               "Done..."
            )
        if response["status"] == VALIDATION_SYNC:
            logger.info(
                "Retrieving %(count)s missing %(collect_plural)s..." % {
                    "count": len(response["missing"]),
                    "collect_plural": collect_plural if len(response["missing"]) > 1 else collect,
                }
            )
            if collect_bulk:
                retrieved = []
                for bulk in chunks(response["missing"], self.bulk_collect_chunk):
                    response = self._post(
                        url=retrieve_url,
                        data={
                            **self.program_data(),
                            collect_plural: json.dumps(bulk),
                        }
                    ).json()
                    for file in response["retrieved"]:
                        setter(
                            instance=file,
                            **setter_kwargs,
                        )
            else:
                for missing in response["missing"]:
                    logger.info(
                        "Retrieving %(missing)s..." % {
                            "missing": missing["name"],
                        }
                    )
                    response = self._post(
                        url=retrieve_url,
                        data={
                            **self.program_data(),
                            collect: missing["pk"],
                        },
                    ).json()
                    setter(
                        instance=response["retrieved"],
                        **setter_kwargs,
                    )
            logger.info(
                "Done..."
            )

    def _sync(
        self,
        logger,
        sync_url,
    ):
        logger.info(
            "Syncing stale files..."
        )
        for version in os.scandir(self.program_file_directory):
            # For each versioned files actually present, we check
            # each once against the authoritative truth from the server...
            authority = self._post(
                url=sync_url,
                data={
                    **self.program_data(),
                    **{
                        "version": version.name,
                    }
                },
            ).json()

            for file in os.scandir(version):
                sync_file(
                    instance=file,
                    instances=authority["program_files"],
                    logger=logger,
                )

    def collect_license_data(self):
        """
        Perform license data collection, only grabbing relevant license information and
        handling validation checks.
        """
        return self._post(
            url=self.license_retrieve_url,
            data=self.program_data(),
        ).json()

    def collect_license(self, logger):
        """
        Perform license collection, retrieving required files and dependencies as needed.
        """
        self.license_data = self.collect_license_data()

        # Handle collection of managed dependencies.
        # Simply retrieving each one and writing it to
        # the users local dependency directory.
        self._collect(
            logger=logger,
            collect="dependency",
            collect_plural="dependencies",
            collect_bulk=False,
            check_url=self.program_dependencies_check_url,
            retrieve_url=self.program_dependencies_retrieve_url,
            setter=set_dependency,
            setter_kwargs={
                "dependency_directory": self.program_dependency_directory,
                "logger": logger,
            },
            exclude_data={
                "exclude_dependencies": json.dumps(self.dependencies(
                    directory=self.program_dependency_directory,
                    extensions=[".zip"],
                )),
            },
        )
        # Handle collection of managed files.
        # Retrieving missing files through a bulk chunked
        # mechanism to avoid timeout issues and long drawn
        # out requests.
        self._collect(
            logger=logger,
            collect="file",
            collect_plural="files",
            collect_bulk=True,
            check_url=self.program_files_check_url,
            retrieve_url=self.program_files_retrieve_url,
            setter=set_file,
            setter_kwargs={
                "file_directory": self.program_file_directory,
                "logger": logger,
            },
            exclude_data={
                "exclude_files": json.dumps(self.files(
                    directory=self.program_file_directory,
                )),
            },
        )
        # Handle syncing of managed files.
        # Syncing will remove any stale files (files that are no longer associated with a program).
        self._sync(
            logger=logger,
            sync_url=self.program_files_sync_url,
        )

    def collect_version(self, version, version_url, location):
        """
        Collect the specified version into the local data directory updates directory.

        We also handle some stale data checking here, and make sure the current executable
        is overwritten with the unarchived version downloaded.
        """
        # We'll extract everything to a the specified location
        # once the newest version has been downloaded...
        executable = os.path.join(
            location,
            self.program_executable,
        )
        response = requests.get(
            url=version_url,
        ).content

        if os.path.isfile(path=executable):
            os.remove(path=executable)

        zipped = ZipFile(io.BytesIO(response))
        zipped.extractall(path=location)

        return executable

    def online(self):
        """
        Set the current license to an online state.

        This is only possible when we actually have a license.
        """
        if self.license_available:
            return self._post(
                url=self.program_online_url,
                data=self.program_data(),
            )

    def offline(self):
        """
        Set the current license to an offline state.

        This is only possible when we actually have a license.
        """
        if self.license_available:
            try:
                return self._post(
                    url=self.program_offline_url,
                    data=self.program_data(),
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
                return self._post(
                    url=self.program_flush_url,
                    data=self.program_data(),
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
                )) if export_contents else "{}",
                **self.program_data(),
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
                **self.program_data(),
            },
        )

    def check_versions(self, version):
        """
        Request the current versions available for the application, the current
        version is passed through to determine if an update is available.
        """
        return self._post(
            url=self.program_check_versions_url,
            data={
                "version": version,
                **self.program_data(),
            },
        )

    def program_data(self):
        return {
            "session": self.session,
            "slug": self.program_name,
            "identifier": self.program_identifier,
            "key": self.license,
        }

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
