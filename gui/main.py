from gui.persistence import (
    PersistenceUtils,
)
from gui.utilities import (
    get_most_recent_log_file,
    create_gui_logger,
)
from gui.settings import (
    ICON_FILE,
    MENU_DISABLED,
    MENU_SEPARATOR,
    MENU_BLANK_HEADER,
    MENU_FORCE_PRESTIGE,
    MENU_FORCE_STOP,
    MENU_START_SESSION,
    MENU_STOP_SESSION,
    MENU_RESUME_SESSION,
    MENU_PAUSE_SESSION,
    MENU_UPDATE_LICENSE,
    MENU_TOOLS,
    MENU_TOOLS_CHECK_FOR_UPDATES,
    MENU_TOOLS_LOCAL_DATA,
    MENU_TOOLS_MOST_RECENT_LOG,
    MENU_TOOLS_FLUSH_LICENSE,
    MENU_CONFIGURATIONS,
    MENU_CONFIGURATIONS_EDIT_CONFIGURATIONS,
    MENU_CONFIGURATIONS_REFRESH_CONFIGURATIONS,
    MENU_LOCAL_SETTINGS,
    MENU_LOCAL_SETTINGS_ENABLE_TOAST_NOTIFICATIONS,
    MENU_LOCAL_SETTINGS_DISABLE_TOAST_NOTIFICATIONS,
    MENU_LOCAL_SETTINGS_ENABLE_FAILSAFE,
    MENU_LOCAL_SETTINGS_DISABLE_FAILSAFE,
    MENU_LOCAL_SETTINGS_ENABLE_AD_BLOCKING,
    MENU_LOCAL_SETTINGS_DISABLE_AD_BLOCKING,
    MENU_DISCORD,
    MENU_EXIT,
    MENU_TIMEOUT,
)

from win10toast import ToastNotifier

from license_validator.validation import LicenseValidator
from license_validator.exceptions import (
    LicenseRetrievalError,
    LicenseExpirationError,
    LicenseServerError,
    LicenseConnectionError,
    LicenseIntegrityError,
)
from license_validator.utilities import (
    set_license,
)

from bot.core.bot import (
    Bot,
)

import PySimpleGUIWx as sg
import gui.sg_ext as sgx
import sentry_sdk
import threading
import webbrowser
import copy
import time
import uuid
import os


class GUI(object):
    def __init__(
        self,
        application_name,
        application_version,
        application_discord,
    ):
        sg.ChangeLookAndFeel(
            index="SystemDefault",
        )

        self._force_prestige = False
        self._force_stop = False
        self._stop = False
        self._pause = False
        self._thread = None
        self._session = None

        self._configurations_cache = {}

        self.application_name = application_name
        self.application_version = application_version
        self.application_discord = application_discord

        self.notifier = ToastNotifier()

        self.license = LicenseValidator()
        self.logger = create_gui_logger(
            log_directory=self.license.program_logs_directory,
            log_name=self.license.program_name,
        )
        self.persist = PersistenceUtils(
            file=self.license.program_persistence_file,
            logger=self.logger,
        )
        self.tray = sg.SystemTray(
            menu=self.menu(),
            filename=ICON_FILE,
        )

        if not self.license.license_available:
            # No license even available at this point,
            # likely the first time starting, let's prompt
            # for a license right away.
            self.update_license()

        self.event_map = {
            self.menu_title: self.menu_title_link,
            MENU_FORCE_PRESTIGE: self.force_prestige,
            MENU_FORCE_STOP: self.force_stop,
            MENU_START_SESSION: self.start_session,
            MENU_STOP_SESSION: self.stop_session,
            MENU_RESUME_SESSION: self.resume_session,
            MENU_PAUSE_SESSION: self.pause_session,
            MENU_CONFIGURATIONS_EDIT_CONFIGURATIONS: self.configurations_edit_configurations,
            MENU_CONFIGURATIONS_REFRESH_CONFIGURATIONS: self.configurations_refresh_configurations,
            MENU_UPDATE_LICENSE: self.update_license,
            MENU_TOOLS_CHECK_FOR_UPDATES: self.tools_check_for_updates,
            MENU_TOOLS_LOCAL_DATA: self.tools_local_data,
            MENU_TOOLS_MOST_RECENT_LOG: self.tools_most_recent_log,
            MENU_TOOLS_FLUSH_LICENSE: self.tools_flush_license,
            MENU_LOCAL_SETTINGS_ENABLE_TOAST_NOTIFICATIONS: self.settings_local_enable_toast_notifications,
            MENU_LOCAL_SETTINGS_DISABLE_TOAST_NOTIFICATIONS: self.settings_local_disable_toast_notifications,
            MENU_LOCAL_SETTINGS_ENABLE_FAILSAFE: self.settings_local_enable_failsafe,
            MENU_LOCAL_SETTINGS_DISABLE_FAILSAFE: self.settings_local_disable_failsafe,
            MENU_LOCAL_SETTINGS_ENABLE_AD_BLOCKING: self.settings_local_enable_ad_blocking,
            MENU_LOCAL_SETTINGS_DISABLE_AD_BLOCKING: self.settings_local_disable_ad_blocking,
            MENU_DISCORD: self.discord,
            MENU_EXIT: self.exit,
            MENU_TIMEOUT: self.refresh,
        }

    def handle_console_size(self):
        """
        Handle resizing the application console.
        """
        try:
            if self.window_size:
                # We also only ever actually set the terminal size when it's
                # possible to gather the current size.
                os.system(self.persist.get_console_startup_size())
        except Exception:
            # If anything fails while trying to update the window
            # size for the user, we can simply just continue execution
            # to avoid breaking the application completely.
            self.logger.info(
                "An error occurred while attempting to modify the console size, skipping..."
            )

    def remember_console_size(self):
        """
        Handle "remembering" the current size of the console.
        """
        window_size = self.window_size

        if window_size:
            # Only ever persisting the value when something valid can even be
            # gathered from the terminal.
            self.persist.set_console_startup_size(
                value=self.window_size,
            )

    def handle_auto_updates(self):
        """
        Handle auto updates of the application.
        """
        if not self.license.license_available:
            return

        self.logger.info(
            "Checking for application updates..."
        )
        # Check to see if any new versions are available...
        # We would expect to handle this on application startup.
        try:
            check_response = self.license.check_versions(version=self.application_version)
            check_response = check_response.json()
            # Depending on the status of our response, this will either tell
            # us to download the newest version, or just continue.
            if check_response["status"] == "requires_update":
                self.logger.info(
                    "Your current application version (%(current)s) is behind the newest version (%(newest)s), "
                    "you can use the prompt to automatically update to the newest version now..." % {
                        "current": self.application_version,
                        "newest": check_response["version"],
                    }
                )
                confirm = self.ok_cancel_popup(
                    text="A newer version is available, would you like to update from version %(current)s to "
                         "version %(newest)s?" % {
                            "current": self.application_version,
                            "newest": check_response["version"],
                         },
                    title="New Version Available",
                )
                if confirm:
                    # If the user has decided that they want to update
                    # their application, we also want to determine where to
                    # put the newest version...
                    location = self.folder_popup(
                        message="Choose Installation Directory",
                        title="Choose Install Directory",
                    )
                    if location:
                        # Ensure the location chosen is saved so upon the next
                        # update or restart, same location is used throughout.
                        self.persist.set_auto_update_path(
                            value=location,
                        )
                        self.logger.info(
                            "Attempting to download the newest application version (%(newest)s) now..." % {
                                "newest": check_response["version"],
                            }
                        )
                        self.logger.info(
                            "The application will be installed into the following location: \"%(location)s\"..." % {
                                "location": location,
                            }
                        )
                        self.logger.info(
                            "Downloading..."
                        )
                        # Handle the downloading of the newest version into our
                        # data directory and overwrite the original executable
                        # with it...
                        try:
                            executable = self.license.collect_version(
                                version=check_response["version"],
                                version_url=check_response["url"],
                                location=location,
                            )
                            self.logger.info(
                                "Newest version was successfully retrieved and downloaded, you can safely restart your application now using "
                                "the newest .exe file available here: \"%(executable)s\"... Your current application may not work correctly "
                                "until you have restarted the application..." % {
                                    "executable": executable,
                                }
                            )
                        except Exception:
                            self.logger.info(
                                "An error occurred while trying to download the newest version of the "
                                "application, skipping... You can download the newest version manually using "
                                "this link: %(download)s" % {
                                    "download": check_response["url"],
                                }
                            )
                            sentry_sdk.capture_exception()
                    else:
                        self.logger.info(
                            "No location was chosen, skipping..."
                        )
                else:
                    self.logger.info(
                        "Skipping application auto updates... The application may not work properly until you've updated to the "
                        "newest version..."
                    )
            if check_response["status"] == "success":
                self.logger.info(
                    "Application is up to date..."
                )
        # Broad exception case will just log some information and
        # updates are skipped...
        except Exception:
            self.logger.info(
                "An error occurred while trying to check version for auto "
                "updating, skipping..."
            )

    def handle_configuration_activate(self, configuration):
        """
        Handle activating a configuration and setting it to an "active" state.
        """
        self.logger.info(
            "Activating %(name)s..." % {
                "name": configuration,
            }
        )
        self.toast(
            title="Configurations",
            message="Activating %(name)s..." % {
                "name": configuration,
            },
        )
        configuration = self._configurations_cache[configuration]

        # Send a post event to the backend to set the given configuration
        # to an active state.
        activate_response = self.license.activate_configuration(configuration=configuration["pk"])
        activate_response = activate_response.json()
        # Updating the cache since the returned data here should be the same
        # as a normal refresh, but our active configuration has changed.
        self._configurations_cache = copy.deepcopy(activate_response)
        self.logger.debug(
            "Configurations cache has been updated following active configuration change..."
        )
        self.logger.debug(
            self._configurations_cache
        )

    @property
    def menu_title(self):
        """
        Return the application name and application version merged gracefully.
        """
        return "%(application_name)s (%(application_version)s)" % {
            "application_name": self.application_name,
            "application_version": self.application_version,
        }

    @property
    def window_size(self):
        """
        Retrieve the current window size.
        """
        try:
            size = os.get_terminal_size()
        except OSError:
            # This is mostly a development shim but other cases might occur
            # where no terminal size can be gathered... In which case, we'll
            # just return a none type value.
            return None
        return "mode con: cols=%(cols)s lines=%(lines)s" % {
            "cols": size.columns,
            "lines": size.lines,
        }

    @staticmethod
    def menu_entry(
        text=None,
        disabled=False,
        separator=False,
    ):
        if not separator and not text:
            raise ValueError(
                "You must specify one of: 'text' or 'separator' arguments."
            )
        if separator:
            return MENU_SEPARATOR

        # Starting with a blank entry text value.
        # We can add to this as we execute.
        entry = ""

        # A disabled entry should have the proper character appended early.
        if disabled:
            entry += MENU_DISABLED

        # When finished, ensure the specified text is
        # appended to the entries current value.
        return entry + text

    @staticmethod
    def ok_cancel_popup(text, title):
        """
        Generate and display a yes no prompt that returns a boolean.
        """
        return sgx.PopupOkCancelTitled(
            text,
            title=title,
            icon=ICON_FILE,
        ) == "OK"

    def folder_popup(self, message, title):
        """
        Generate and display a popup box that displays some text and asks for a directory/location.
        """
        return sg.PopupGetFolder(
            message=message,
            title=title,
            default_path=self.persist.get_auto_update_path(),
            icon=ICON_FILE,
        )

    def text_input_popup(self, message, title, size=None, default_text=None, icon=None):
        """
        Generate and display a popup box that displays some text and grabs user input.
        """
        return sg.PopupGetText(
            message=message,
            title=title,
            default_text=default_text or self.license.license,
            size=size or (500, 20),
            icon=icon or ICON_FILE,
        )

    def toast(self, title, message, icon_path=ICON_FILE, duration=2.5):
        """
        Send a toast notification to the system tray.
        """
        if self.persist.get_enable_toast_notifications():
            return self.notifier.show_toast(
                title=title,
                msg=message,
                icon_path=icon_path,
                duration=duration,
                threaded=True,
            )

    def log_and_toast(self, title, message):
        """
        Log and toast a given message and title.
        """
        self.logger.info(message)
        self.toast(title=title, message=message)

    def menu(self):
        """
        Generate the menu used by the system tray application.
        """
        return [
            self.menu_entry(text=MENU_BLANK_HEADER), [
                self.menu_entry(text=self.menu_title),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_FORCE_PRESTIGE, disabled=self._thread is None or self._force_prestige is True),
                self.menu_entry(text=MENU_FORCE_STOP, disabled=self._thread is None or self._force_stop is True),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_START_SESSION, disabled=self._thread is not None),
                self.menu_entry(text=MENU_STOP_SESSION, disabled=self._thread is None),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_RESUME_SESSION, disabled=self._thread is None or self._pause is False),
                self.menu_entry(text=MENU_PAUSE_SESSION, disabled=self._thread is None or self._pause is True),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_TOOLS),
                [
                    self.menu_entry(text=MENU_TOOLS_CHECK_FOR_UPDATES),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_TOOLS_LOCAL_DATA),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_UPDATE_LICENSE),
                    self.menu_entry(text=MENU_TOOLS_FLUSH_LICENSE),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_TOOLS_MOST_RECENT_LOG),
                ],
                self.menu_entry(text=MENU_CONFIGURATIONS),
                [
                    self.menu_entry(text=MENU_CONFIGURATIONS_EDIT_CONFIGURATIONS),
                    self.menu_entry(text=MENU_CONFIGURATIONS_REFRESH_CONFIGURATIONS),
                    self.menu_entry(separator=True),
                    *self.refresh_configurations(refresh=False)
                ],
                self.menu_entry(text=MENU_LOCAL_SETTINGS),
                [
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_ENABLE_TOAST_NOTIFICATIONS, disabled=self.persist.get_enable_toast_notifications()),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_DISABLE_TOAST_NOTIFICATIONS, disabled=not self.persist.get_enable_toast_notifications()),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_ENABLE_FAILSAFE, disabled=self.persist.get_enable_failsafe()),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_DISABLE_FAILSAFE, disabled=not self.persist.get_enable_failsafe()),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_ENABLE_AD_BLOCKING, disabled=self.persist.get_enable_ad_blocking()),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_DISABLE_AD_BLOCKING, disabled=not self.persist.get_enable_ad_blocking()),
                ],
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_DISCORD),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_EXIT),
            ],
        ]

    def refresh(self):
        """
        Refresh the system tray menu.
        """
        # Reset our bot application thread
        # if it is no longer alive.
        if self._thread and not self._thread.is_alive():
            self._thread.join()
            self._thread = None

        self.tray.update(menu=self.menu())

    def refresh_configurations(self, refresh=True):
        """
        Refresh the configurations available for a user. The data stored here is done so in a way
        that in can be viewed within a menu, some additional information is stored about the keys about
        each one.
        """
        if refresh:
            try:
                configurations_response = self.license.collect_configurations()
                configurations_response = configurations_response.json()
                # Updating the cache through a deepcopy of the response...
                # Response is expected to contain a dictionary of configurations.
                self._configurations_cache = copy.deepcopy(configurations_response)
                self.logger.debug(
                    "Configurations cache has been updated..."
                )
                self.logger.debug(
                    self._configurations_cache
                )
            # If any license errors occur here, we log it and pass, so no configurations are
            # loaded, this occurs if an expired license or disabled license is encountered.
            except (LicenseRetrievalError, LicenseExpirationError, LicenseServerError, LicenseConnectionError, LicenseIntegrityError):
                self.logger.info(
                    "Error occurred while retrieving configurations, skipping..."
                )
        # Begin populating menu entries...
        menu_entries = []

        for configuration in self._configurations_cache.values():
            if configuration["active"]:
                text = "%(configuration_name)s (ACTIVE)" % {
                    "configuration_name": configuration["name"],
                }
            else:
                text = configuration["name"]
            # Append the configuration to the menu entry, active configurations
            # are disabled for local modification.
            menu_entries.append(
                self.menu_entry(text=text, disabled=configuration["active"]),
            )
        return menu_entries

    def menu_title_link(self):
        """
        "menu_title" event functionality.
        """
        return webbrowser.open_new_tab(
            url=self.license.program_url,
        )

    def stop_func(self):
        """
        Return the current internal ``_stop`` value.
        """
        return self._stop

    def pause_func(self):
        """
        Return the current internal``_pause`` value.
        """
        return self._pause

    def force_prestige_func(self, _set=False):
        """
        Return the current internal ``_force_prestige`` value.

        Also handling a toggle reset here, whenever force prestige is set to True,
        we also want to reset the value.
        """
        if _set:
            # Allow for an optional setting parameter to handle
            # our func "reset". This should be called once whatever
            # function is being executed is completed.
            self._force_prestige = False
        return self._force_prestige

    def force_prestige(self):
        """
        "force_prestige" event functionality.
        """
        if self._thread is not None:
            self.log_and_toast(
                title="Force Prestige",
                message="Forcing Prestige..."
            )
            self._force_prestige = True

    def force_stop_func(self, _set=False):
        """
        Return the current interval ``_force_stop`` value.

        Also handling a toggle reset here, whenever force prestige is set to True,
        we also want to reset the value.
        """
        if _set:
            # Allow for an optional setting parameter to handle
            # our func "reset". This should be called once whatever
            # function is being executed is completed.
            self._force_stop = False
        return self._force_stop

    def force_stop(self):
        """
        "force_stop" event functionality.
        """
        if self._thread is not None:
            self.log_and_toast(
                title="Force Stop",
                message="Forcing Stop...",
            )
            self._force_stop = True

    def start_session(self):
        """
        "start_session" event functionality.
        """
        if not self._thread:
            self.log_and_toast(
                title="Session",
                message="Starting Session...",
            )
            self._stop = False
            self._pause = False
            self._session = uuid.uuid4().hex
            self._thread = threading.Thread(
                target=Bot,
                kwargs={
                    "application_name": self.application_name,
                    "application_version": self.application_version,
                    "application_discord": self.application_discord,
                    "license_obj": self.license,
                    "session": self._session,
                    "force_prestige_func": self.force_prestige_func,
                    "force_stop_func": self.force_stop_func,
                    "stop_func": self.stop_func,
                    "pause_func": self.pause_func,
                    "toast_func": self.toast,
                    "failsafe_enabled_func": self.persist.get_enable_failsafe,
                    "ad_blocking_enabled_func": self.persist.get_enable_ad_blocking,
                },
            )
            self._thread.start()

    def stop_session(self):
        """
        "stop_session" functionality.
        """
        if self._thread is not None:
            self.log_and_toast(
                title="Session",
                message="Stopping Session...",
            )
            self._stop = True
            self._pause = False
            self._session = None
            self._thread.join()
            self._thread = None

    def pause_session(self):
        """
        "pause_session" functionality.
        """
        if self._thread is not None:
            self.log_and_toast(
                title="Session",
                message="Pausing Session...",
            )
            self._pause = True

    def resume_session(self):
        """
        "resume_session" functionality.
        """
        if self._thread is not None:
            self.log_and_toast(
                title="Session",
                message="Resuming Session...",
            )
            self._pause = False

    def configurations_edit_configurations(self):
        """
        "configurations_edit_configurations" event functionality.
        """
        if self.license.license_available:
            return webbrowser.open_new_tab(
                url=self.license.program_configurations_template + "/%(program_name)s/%(license)s" % {
                    "program_name": self.license.program_name,
                    "license": self.license.license,
                }
            )

    def configurations_refresh_configurations(self):
        """
        "configurations_refresh_configurations" event functionality.
        """
        if self.license.license_available:
            self.log_and_toast(
                title="Configurations",
                message="Refreshing Configurations...",
            )
            self.refresh_configurations()
            self.log_and_toast(
                title="Configurations",
                message="Done...",
            )

    def update_license(self):
        """
        "update_license" functionality.
        """
        text = self.text_input_popup(
            message="Enter License Key: ",
            title="Update License",
        )

        # If the user presses "cancel", text == None.
        # If the user enters nothing, text == "".
        if text is None or text == "":
            return
        # Strip the license key in case any characters
        # are included due to copy/paste, etc.
        text = text.strip()
        # Late return if user enters only spaces or
        # some other weird edge case.
        if not text:
            return

        # Update the license text that's handled
        # by the license validation utilities.
        self.log_and_toast(
            title="License",
            message="Updating License: %(text)s..." % {
                "text": text,
            }
        )
        set_license(
            license_file=self.license.program_license_file,
            text=text,
        )
        self.log_and_toast(
            title="License",
            message="Done..."
        )

    def tools_check_for_updates(self):
        """
        "tools_check_for_updates" functionality.
        """
        self.log_and_toast(
            title="Auto Updates",
            message="Checking For Updates...",
        )
        self.handle_auto_updates()

    def tools_local_data(self):
        """
        "tools_local_data" functionality.
        """
        self.log_and_toast(
            title="Local Data",
            message="Opening Local Data Directory...",
        )
        os.startfile(
            filepath=self.license.program_directory,
        )
        self.log_and_toast(
            title="Local Data",
            message="Done...",
        )

    def tools_most_recent_log(self):
        """
        "tools_most_recent_log" functionality.
        """
        file = get_most_recent_log_file(
            log_directory=self.license.program_logs_directory,
        )
        if file:
            self.log_and_toast(
                title="Recent Logs",
                message="Opening Most Recent Log...",
            )
            os.startfile(
                filepath=file,
            )
            self.log_and_toast(
                title="Recent Logs",
                message="Done...",
            )
        else:
            self.log_and_toast(
                title="Recent Logs",
                message="No Recent Log Available To Open...",
            )

    def tools_flush_license(self):
        """
        "tools_flush_license" functionality.
        """
        self.log_and_toast(
            title="Flush License",
            message="Flushing License...",
        )
        self.license.flush()
        self.log_and_toast(
            title="Flush License",
            message="Done...",
        )

    def settings_local_enable_toast_notifications(self):
        """
        "settings_local_enable_toast_notifications" functionality.
        """
        self.persist.set_enable_toast_notifications(value=True)
        self.log_and_toast(
            title="Toast Notifications",
            message="Enabled Toast Notifications...",
        )

    def settings_local_disable_toast_notifications(self):
        """
        "settings_local_disable_toast_notifications" functionality.
        """
        self.persist.set_enable_toast_notifications(value=False)
        self.log_and_toast(
            title="Toast Notifications",
            message="Disabled Toast Notifications...",
        )

    def settings_local_enable_failsafe(self):
        """
        "settings_local_enable_failsafe" functionality.
        """
        self.persist.set_enable_failsafe(value=True)
        self.log_and_toast(
            title="Failsafe",
            message="Enabled Failsafe...",
        )

    def settings_local_disable_failsafe(self):
        """
        "settings_local_disable_failsafe" functionality.
        """
        self.persist.set_enable_failsafe(value=False)
        self.log_and_toast(
            title="Failsafe",
            message="Disabled Failsafe..."
        )

    def settings_local_enable_ad_blocking(self):
        """
        "settings_local_enable_ad_blocking" functionality.
        """
        self.persist.set_enable_ad_blocking(value=True)
        self.log_and_toast(
            title="Ad Blocking",
            message="Enabled Ad Blocking...",
        )

    def settings_local_disable_ad_blocking(self):
        """
        "settings_local_disable_ad_blocking" functionality.
        """
        self.persist.set_enable_ad_blocking(value=False)
        self.log_and_toast(
            title="Ad Blocking",
            message="Disabled Ad Blocking...",
        )

    def discord(self):
        """
        "discord" event functionality.
        """
        self.log_and_toast(
            title="Discord",
            message="Opening Discord...",
        )
        webbrowser.open_new_tab(
            url=self.application_discord,
        )
        self.log_and_toast(
            title="Discord",
            message="Done...",
        )

    def exit(self):
        """
        "exit" event functionality.
        """
        self.log_and_toast(
            title="Exit",
            message="Exiting...",
        )
        self.stop_session()
        # SystemExit to leave with valid return code.
        # We don't want any exceptions raised.
        raise SystemExit

    def purge_stale_logs(self, days=3):
        """
        Purge any logs present that are older than the specified amount of days.
        """
        for log in os.listdir(self.license.program_logs_directory):
            if os.path.getmtime(os.path.join(self.license.program_logs_directory, log)) < time.time() - days * 86400:
                self.logger.info(
                    "Purging Stale Log: \"%(log)s\"..." % {
                        "log": log,
                    }
                )
                if os.path.isfile(os.path.join(self.license.program_logs_directory, log)):
                    os.remove(os.path.join(self.license.program_logs_directory, log))

    def run(self):
        """
        Begin main runtime loop for application.
        """
        try:
            # Always handling a configuration refresh on initial
            # application startup.
            self.refresh_configurations()
            # Handle auto console sizing...
            self.handle_console_size()
            # Handle auto update checks...
            self.handle_auto_updates()

            self.logger.info("===================================================================================")
            self.logger.info(
                "%(application_name)s GUI (v%(version)s) Initialized..." % {
                    "application_name": self.application_name,
                    "version": self.application_version,
                }
            )
            self.logger.info(
                "Use the system tray application below to start/stop a bot session, some additional tools are present "
                "that may also prove useful if you run into any issues."
            )
            self.logger.info(
                "If you are running into issues and require support, please use the discord for this program or "
                "contact the support team for additional help."
            )
            self.logger.info("===================================================================================")
            self.purge_stale_logs()
            # Sentry can have some tags set for any issues that
            # crop up during our gui functionality...
            sentry_sdk.set_tag("package", "gui")
            sentry_sdk.set_tag("license", self.license.license)

            while True:
                event_text = self.tray.read(timeout=100)
                event_func = self.event_map.get(event_text)

                if not event_func:
                    # Also check to see if a configuration is being set
                    # as active, this is handled dynamically based on the
                    # cached configurations.
                    if event_text in self._configurations_cache:
                        self.handle_configuration_activate(
                            configuration=event_text,
                        )
                else:
                    event_func()
        except Exception:
            self.logger.info(
                "An unknown exception was encountered... The error has been reported to the support team."
            )
            sentry_sdk.capture_exception()
            # Let the user press enter to shut their application
            # down. In case some information is needed from the terminal.
            input("\nPress \"Enter\" to exit...")
        finally:
            # Always set our "remembered" console size on exit.
            self.remember_console_size()
            # Always stop session on application termination...
            self.stop_session()
