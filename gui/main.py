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
    MENU_START_EVENT,
    MENU_STOP_SESSION,
    MENU_RESUME_SESSION,
    MENU_PAUSE_SESSION,
    MENU_UPDATE_LICENSE,
    MENU_TOOLS,
    MENU_TOOLS_CHECK_FOR_UPDATES,
    MENU_TOOLS_LOCAL_DATA,
    MENU_TOOLS_GENERATE_DEBUG_SCREENSHOT,
    MENU_TOOLS_MOST_RECENT_LOG,
    MENU_TOOLS_FLUSH_LICENSE,
    MENU_INSTANCES,
    MENU_INSTANCES_EDIT_INSTANCES,
    MENU_INSTANCES_REFRESH_INSTANCES,
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
    MENU_LOCAL_SETTINGS_ENABLE_AUTO_UPDATE,
    MENU_LOCAL_SETTINGS_DISABLE_AUTO_UPDATE,
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
from bot.core.window import (
    WindowHandler,
    WindowNotFoundError,
)

import PySimpleGUIWx as sg
import gui.sg_ext as sgx
import sentry_sdk
import threading
import operator
import webbrowser
import copy
import time
import uuid
import os


class GUIInstanceInternals(object):
    def __init__(
        self,
    ):
        self.force_prestige = False
        self.force_stop = False
        self.stop = False
        self.pause = False
        self.thread = None
        self.session = None


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

        self._instances_internals = []
        self._instances_cache = {}
        self._instances_names = {}
        self._instance_active = None
        self._windows_cache = {}
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

        if not self.license.license_available:
            # No license even available at this point,
            # likely the first time starting, let's prompt
            # for a license right away.
            self.update_license(require=True)

        # Always handling a configuration refresh on initial
        # application startup.
        self.refresh_instances()
        self.refresh_configurations()

        self.tray = sg.SystemTray(
            menu=self.menu(),
            filename=ICON_FILE,
        )

        self.event_map = {
            self.menu_title: self.menu_title_link,
            MENU_FORCE_PRESTIGE: self.force_prestige,
            MENU_FORCE_STOP: self.force_stop,
            MENU_START_SESSION: self.start_session,
            MENU_STOP_SESSION: self.stop_session,
            MENU_RESUME_SESSION: self.resume_session,
            MENU_PAUSE_SESSION: self.pause_session,
            MENU_INSTANCES_EDIT_INSTANCES: self.instances_edit_instances,
            MENU_INSTANCES_REFRESH_INSTANCES: self.instances_refresh_instances,
            MENU_CONFIGURATIONS_EDIT_CONFIGURATIONS: self.configurations_edit_configurations,
            MENU_CONFIGURATIONS_REFRESH_CONFIGURATIONS: self.configurations_refresh_configurations,
            MENU_UPDATE_LICENSE: self.update_license,
            MENU_TOOLS_CHECK_FOR_UPDATES: self.tools_check_for_updates,
            MENU_TOOLS_LOCAL_DATA: self.tools_local_data,
            MENU_TOOLS_GENERATE_DEBUG_SCREENSHOT: self.tools_generate_debug_screenshot,
            MENU_TOOLS_MOST_RECENT_LOG: self.tools_most_recent_log,
            MENU_TOOLS_FLUSH_LICENSE: self.tools_flush_license,
            MENU_LOCAL_SETTINGS_ENABLE_TOAST_NOTIFICATIONS: self.settings_local_enable_toast_notifications,
            MENU_LOCAL_SETTINGS_DISABLE_TOAST_NOTIFICATIONS: self.settings_local_disable_toast_notifications,
            MENU_LOCAL_SETTINGS_ENABLE_FAILSAFE: self.settings_local_enable_failsafe,
            MENU_LOCAL_SETTINGS_DISABLE_FAILSAFE: self.settings_local_disable_failsafe,
            MENU_LOCAL_SETTINGS_ENABLE_AD_BLOCKING: self.settings_local_enable_ad_blocking,
            MENU_LOCAL_SETTINGS_DISABLE_AD_BLOCKING: self.settings_local_disable_ad_blocking,
            MENU_LOCAL_SETTINGS_ENABLE_AUTO_UPDATE: self.settings_local_enable_auto_update,
            MENU_LOCAL_SETTINGS_DISABLE_AUTO_UPDATE: self.settings_local_disable_auto_update,
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
                os.system(self.persist.get_persistence("console_startup_size"))
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
            self.persist.set_persistence(
                key="console_startup_size",
                value=self.window_size,
            )

    def handle_auto_updates(self):
        """
        Handle auto updates of the application.
        """
        if not self.license.license_available:
            return

        self.log_and_toast(
            title="Auto Updates",
            message="Checking For Updates...",
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
                        self.persist.set_persistence(
                            key="auto_update_path",
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

    def internals_check(self, checks):
        """Perform a check against the specified "checks" list.

        Each "check" should contain a tuple with the internal value being checked, as well as the value expected.

        Ex: [
            ("thread", None),
            ("force_prestige", True),
        ]

        Checks if the active instance thread is None and that force_prestige is True.
        """
        for c in checks:
            internal, val = [
                c[0],
                c[1],
            ]
            if internal[0] == "!":
                method = operator.ne
                internal = internal[1:]
            else:
                method = operator.eq
            if not self._instance_active:
                return False
            if method(
                getattr(self._instances_internals[self._instance_active], internal),
                val,
            ):
                return True
        return False

    def handle_instance_activate(self, instance):
        """
        Handle activating a instance and setting it to an "selected" state.
        """
        self.log_and_toast(
            title="Instances",
            message="Activating %(name)s..." % {
                "name": instance,
            }
        )
        instance = self._instances_cache[instance]

        # Simply just update the local selected instance
        # (the gui uses this to determine how to treat signals).
        self._instance_active = instance["pk"]
        self.logger.debug(
            self._instance_active
        )
        self.log_and_toast(
            title="Instances",
            message="Done...",
        )

    def handle_configuration_activate(self, configuration):
        """
        Handle activating a configuration and setting it to an "active" state.
        """
        if self.license.license_available:
            return webbrowser.open_new_tab(
                url=self.license.program_configurations_template + "/%(program_name)s/%(license)s/%(configuration)s/edit" % {
                    "program_name": self.license.program_name,
                    "license": self.license.license,
                    "configuration": self._configurations_cache[configuration]["pk"],
                },
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
    def menu_title_sub(self):
        """
        Return the active instance for at a glance information available.
        """
        if self._instance_active:
            # Include a space so we can avoid reactivating an instance
            # that's already active...
            return self._instances_names[self._instance_active] + " "
        # Defaulting to a dash if no instances are available
        # (stale license?).
        return "(No Instance)"

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
            default_path=self.persist.get_persistence("auto_update_path"),
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

    def toast(self, title, message, icon_path=ICON_FILE, duration=2.5, instance=None):
        """
        Send a toast notification to the system tray.
        """
        if self.persist.get_persistence("enable_toast_notifications"):
            if instance:
                title = "%(title)s | %(instance)s" % {
                    "title": title,
                    "instance": self._instances_names[instance],
                }
            return self.notifier.show_toast(
                title=title,
                msg=message,
                icon_path=icon_path,
                duration=duration,
                threaded=True,
            )

    def log_and_toast(self, title, message, duration=2.5, instance=None):
        """
        Log and toast a given message and title.
        """
        if instance == self._instance_active or not instance:
            self.logger.info(message)
            self.toast(title=title, message=message, duration=duration, instance=instance)

    def menu(self):
        """
        Generate the menu used by the system tray application.
        """
        return [
            self.menu_entry(text=MENU_BLANK_HEADER), [
                self.menu_entry(text=self.menu_title),
                self.menu_entry(text=self.menu_title_sub),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_FORCE_PRESTIGE, disabled=self.internals_check(checks=[("thread", None), ("force_prestige", True)])),
                self.menu_entry(text=MENU_FORCE_STOP, disabled=self.internals_check(checks=[("thread", None), ("force_stop", True)])),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_START_SESSION, disabled=self.internals_check(checks=[("!thread", None)])),
                self.menu_entry(text=MENU_STOP_SESSION, disabled=self.internals_check(checks=[("thread", None)])),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_RESUME_SESSION, disabled=self.internals_check(checks=[("thread", None), ("pause", False)])),
                self.menu_entry(text=MENU_PAUSE_SESSION, disabled=self.internals_check(checks=[("thread", None), ("pause", True)])),
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
                    self.menu_entry(text=MENU_TOOLS_GENERATE_DEBUG_SCREENSHOT),
                    self.menu_entry(text=MENU_TOOLS_MOST_RECENT_LOG),
                ],
                self.menu_entry(text=MENU_INSTANCES),
                [
                    self.menu_entry(text=MENU_INSTANCES_EDIT_INSTANCES),
                    self.menu_entry(text=MENU_INSTANCES_REFRESH_INSTANCES),
                    self.menu_entry(separator=True),
                    *self.refresh_instances(refresh=False)
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
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_ENABLE_TOAST_NOTIFICATIONS, disabled=self.persist.get_persistence("enable_toast_notifications")),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_DISABLE_TOAST_NOTIFICATIONS, disabled=not self.persist.get_persistence("enable_toast_notifications")),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_ENABLE_FAILSAFE, disabled=self.persist.get_persistence("enable_failsafe")),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_DISABLE_FAILSAFE, disabled=not self.persist.get_persistence("enable_failsafe")),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_ENABLE_AD_BLOCKING, disabled=self.persist.get_persistence("enable_ad_blocking")),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_DISABLE_AD_BLOCKING, disabled=not self.persist.get_persistence("enable_ad_blocking")),
                    self.menu_entry(separator=True),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_ENABLE_AUTO_UPDATE, disabled=self.persist.get_persistence("enable_auto_update")),
                    self.menu_entry(text=MENU_LOCAL_SETTINGS_DISABLE_AUTO_UPDATE, disabled=not self.persist.get_persistence("enable_auto_update")),
                ],
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_DISCORD),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_EXIT),
            ],
        ]

    def refresh(self, **kwargs):
        """
        Refresh the system tray menu.
        """
        # Reset our bot application thread
        # if it is no longer alive.
        if (
            self._instance_active
            and self._instances_internals[self._instance_active].thread
            and not self._instances_internals[self._instance_active].thread.is_alive()
        ):
            self._instances_internals[self._instance_active].thread.join()
            self._instances_internals[self._instance_active].thread = None

        self.tray.update(menu=self.menu())

    def refresh_instances(self, refresh=True, **kwargs):
        """
        Refresh the instances available for a user. The data stored here is done so in a way that it can be
        viewed within a menu, some additional information is stored about each instance in the instances cache.
        """
        if refresh:
            try:
                instances_response = self.license.collect_instances()
                instances_response = instances_response.json()
                # Updating the cache through a deepcopy of the response...
                # Response is expected to contain a dictionary of instances.
                self._instance_active = None
                self._instances_cache = copy.deepcopy(instances_response)
                self._instances_names = {instance["pk"]: instance["name"] for instance in self._instances_cache.values()}
                self._instances_internals = {instance["pk"]: GUIInstanceInternals() for instance in self._instances_cache.values()}
                self.logger.debug(
                    "Instances cache has been updated..."
                )
                self.logger.debug(
                    self._instances_cache
                )
            # If any license errors occur here, we log it and pass, so no configurations are
            # loaded, this occurs if an expired license or disabled license is encountered.
            except (LicenseRetrievalError, LicenseExpirationError, LicenseServerError, LicenseConnectionError, LicenseIntegrityError) as exc:
                self.logger.info(
                    "Error occurred while retrieving instances, skipping..."
                )
        # Begin populating menu entries...
        menu_entries = []

        for instance in self._instances_cache.values():
            text = "%(instance_name)s" % {
                "instance_name": instance["name"],
            }
            if self._instance_active is None or self._instance_active == instance["pk"]:
                self._instance_active = instance["pk"]
                text += " (ACTIVE)"
            # Append the instance to the menu entry, selected instances
            # are disabled for local modification.
            menu_entries.append(
                self.menu_entry(text=text, disabled=self._instance_active == instance["pk"])
            )
        return menu_entries

    def refresh_windows(self, **kwargs):
        """
        Refresh the windows available for selection for a user. The data stored here is done so in a way
        that it can be viewed within a prompt, some additional information is stored about each window
        so bot sessions know which window to access.
        """
        win = WindowHandler()
        win.enumerate()

        self._windows_cache = {
            win.text: win.hwnd for win in win.filter(
                filter_title=[
                    "nox",
                    "noxplayer",
                    "memu",
                ],
            )
        }

    def refresh_configurations(self, refresh=True, **kwargs):
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
            # Append the configuration to the menu entry.
            menu_entries.append(
                self.menu_entry(text=configuration["name"]),
            )
        return menu_entries

    def menu_title_link(self, **kwargs):
        """
        "menu_title" event functionality.
        """
        return webbrowser.open_new_tab(
            url=self.license.program_url,
        )

    def stop_func(self, instance):
        """
        Return the current internal ``stop`` value.
        """
        return self._instances_internals[instance].stop

    def pause_func(self, instance):
        """
        Return the current internal``pause`` value.
        """
        return self._instances_internals[instance].pause

    def force_prestige_func(self, instance, _set=False):
        """
        Return the current internal ``force_prestige`` value.

        Also handling a toggle reset here, whenever force prestige is set to True,
        we also want to reset the value.
        """
        if _set:
            # Allow for an optional setting parameter to handle
            # our func "reset". This should be called once whatever
            # function is being executed is completed.
            self._instances_internals[instance].force_prestige = False
        return self._instances_internals[instance].force_prestige

    def force_prestige(self, instance):
        """
        "force_prestige" event functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log_and_toast(
                instance=instance,
                title="Force Prestige",
                message="Forcing Prestige..."
            )
            self._instances_internals[instance].force_prestige = True

    def force_stop_func(self, instance, _set=False):
        """
        Return the current internal ``_force_stop`` value.

        Also handling a toggle reset here, whenever force prestige is set to True,
        we also want to reset the value.
        """
        if _set:
            # Allow for an optional setting parameter to handle
            # our func "reset". This should be called once whatever
            # function is being executed is completed.
            self._instances_internals[instance].force_stop = False
        return self._instances_internals[instance].force_stop

    def force_stop(self, instance):
        """
        "force_stop" event functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log_and_toast(
                instance=instance,
                title="Force Stop",
                message="Forcing Stop...",
            )
            self._instances_internals[instance].force_stop = True

    def instance_func(self):
        """Return the current internal ``_instance_active`` value.
        """
        return self._instance_active

    def start_session(self, instance):
        """
        "start_session" event functionality.
        """
        # We always refresh windows on session start prompt, so the most
        # recent windows are available and our cache is upto date upon selection.
        self.refresh_windows()
        # Default "remembered" values are persisted and used in between
        # session starts to avoid annoying re-selection of values...
        default_window = self.persist.get_persistence("last_window_choice")
        default_configuration = self.persist.get_persistence("last_configuration_choice")

        if default_window and default_window not in self._windows_cache:
            self.persist.set_persistence(
                key="last_window_choice",
                value=None,
            )
            default_window = None
        if default_configuration and default_configuration not in self._configurations_cache:
            self.persist.set_persistence(
                key="last_configuration_choice",
                value=None,
            )
            default_configuration = None

        event, values = sgx.PopupWindowConfiguration(
            title="Start Session",
            submit_text=MENU_START_EVENT,
            windows=tuple(window_name for window_name in self._windows_cache.keys()),
            configurations=tuple(configuration_name for configuration_name in self._configurations_cache.keys()),
            icon=ICON_FILE,
            default_window=default_window,
            default_configuration=default_configuration,
        )

        if event == MENU_START_EVENT:
            window, configuration = (
                values[0],
                values[1],
            )
            if not window or not configuration:
                self.log_and_toast(
                    title="Start Session",
                    message="Invalid Window Or Configuration Selected...",
                    instance=instance,
                )
            if window and configuration:
                # Ensure the persisted last selected window and configuration
                # are saved...
                self.persist.set_persistence(
                    key="last_window_choice",
                    value=window,
                )
                self.persist.set_persistence(
                    key="last_configuration_choice",
                    value=configuration,
                )
                if not self._instances_internals[instance].thread:
                    self.log_and_toast(
                        instance=instance,
                        title="Session",
                        message="Starting Session...",
                    )
                    self._instances_internals[instance].stop = False
                    self._instances_internals[instance].pause = False
                    self._instances_internals[instance].session = uuid.uuid4().hex
                    self._instances_internals[instance].thread = threading.Thread(
                        target=Bot,
                        kwargs={
                            "application_name": self.application_name,
                            "application_version": self.application_version,
                            "application_discord": self.application_discord,
                            "license_obj": self.license,
                            "instance": instance,
                            "instance_name": self._instances_names[instance],
                            "instance_func": self.instance_func,
                            "window": window,
                            "configuration_pk": self._configurations_cache[configuration]["pk"],
                            "session": self._instances_internals[instance].session,
                            "force_prestige_func": self.force_prestige_func,
                            "force_stop_func": self.force_stop_func,
                            "stop_func": self.stop_func,
                            "pause_func": self.pause_func,
                            "toast_func": self.toast,
                            "get_persistence": self.persist.get_persistence,

                        },
                    )
                    self._instances_internals[instance].thread.start()

    def stop_session(self, instance):
        """
        "stop_session" functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log_and_toast(
                instance=instance,
                title="Session",
                message="Stopping Session...",
            )
            self._instances_internals[instance].stop = True
            self._instances_internals[instance].session = None
            self._instances_internals[instance].thread.join()
            self._instances_internals[instance].thread = None

    def pause_session(self, instance):
        """
        "pause_session" functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log_and_toast(
                instance=instance,
                title="Session",
                message="Pausing Session...",
            )
            self._instances_internals[instance].pause = True

    def resume_session(self, instance):
        """
        "resume_session" functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log_and_toast(
                instance=instance,
                title="Session",
                message="Resuming Session...",
            )
            self._instances_internals[instance].pause = False

    def instances_edit_instances(self, **kwargs):
        """
        "instances_edit_instances" event functionality.

        Note: Instances currently housed on the same page as configurations, same url used for now.
        """
        if self.license.license_available:
            return webbrowser.open_new_tab(
                url=self.license.program_configurations_template + "/%(program_name)s/%(license)s" % {
                    "program_name": self.license.program_name,
                    "license": self.license.license,
                }
            )

    def instances_refresh_instances(self, **kwargs):
        """
        "configurations_refresh_instances" event functionality.
        """
        if self.license.license_available:
            self.log_and_toast(
                title="Instances",
                message="Refreshing Instances...",
            )
            self.refresh_instances()
            self.log_and_toast(
                title="Instances",
                message="Done...",
            )

    def configurations_edit_configurations(self, **kwargs):
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

    def configurations_refresh_configurations(self, **kwargs):
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

    def update_license(self, require=False, **kwargs):
        """
        "update_license" functionality.
        """
        popup_kwargs = {
            "message": "Enter License Key: ",
            "title": "Update License",
        }
        text = self.text_input_popup(
            **popup_kwargs
        )

        # If the user presses "cancel", text == None.
        # If the user enters nothing, text == "".

        if require:
            if text is None:
                # Forcing a value and user hit exit/cancel,
                # Exit the application...
                raise SystemExit
            if text == "":
                while text == "":
                    text = self.text_input_popup(
                        **popup_kwargs
                    )
                    if text is None:
                        # Re raise system exit on looped exit.
                        raise SystemExit
        else:
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

    def tools_check_for_updates(self, **kwargs):
        """
        "tools_check_for_updates" functionality.
        """
        self.handle_auto_updates()

    def tools_local_data(self, **kwargs):
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

    def tools_generate_debug_screenshot(self, **kwargs):
        """
        "tools_generate_debug_screenshot" functionality.
        """
        window = self.text_input_popup(
            message="Please enter the emulator window you would like to generate a debug screenshot against:",
            title="Debug Window",
            default_text="NoxPlayer",
        )

        if window:
            self.log_and_toast(
                title="Debug Screenshot",
                message="Capturing Debug Screenshot For Window: \"%(window)s\" Now..." % {
                    "window": window,
                },
            )

            win = WindowHandler()
            win.enumerate()

            try:
                win = win.filter_first(filter_title=window)
                # Capturing a screenshot of the window, this proves useful
                # to make sure a user can check to see if the bot is able
                # to see the emulator screen correctly.
                capture = win.screenshot()
                capture.show()

                self.log_and_toast(
                    title="Debug Screenshot",
                    message="Done...",
                )
            except WindowNotFoundError:
                self.logger.info(
                    "Window: \"%(window)s\" Not Found..." % {
                        "window": window,
                    }
                )

    def tools_most_recent_log(self, **kwargs):
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

    def tools_flush_license(self, **kwargs):
        """
        "tools_flush_license" functionality.
        """
        self.log_and_toast(
            title="Flush License",
            message="Flushing License...",
        )
        self.license.flush(instance=self._instance_active)
        self.log_and_toast(
            title="Flush License",
            message="Done...",
        )

    def settings_local_enable_toast_notifications(self, **kwargs):
        """
        "settings_local_enable_toast_notifications" functionality.
        """
        self.persist.set_persistence(
            key="enable_toast_notifications",
            value=True,
        )
        self.log_and_toast(
            title="Toast Notifications",
            message="Enabled Toast Notifications...",
        )

    def settings_local_disable_toast_notifications(self, **kwargs):
        """
        "settings_local_disable_toast_notifications" functionality.
        """
        self.persist.set_persistence(
            key="enable_toast_notifications",
            value=False,
        )
        self.log_and_toast(
            title="Toast Notifications",
            message="Disabled Toast Notifications...",
        )

    def settings_local_enable_failsafe(self, **kwargs):
        """
        "settings_local_enable_failsafe" functionality.
        """
        self.persist.set_persistence(
            key="enable_failsafe",
            value=True,
        )
        self.log_and_toast(
            title="Failsafe",
            message="Enabled Failsafe...",
        )

    def settings_local_disable_failsafe(self, **kwargs):
        """
        "settings_local_disable_failsafe" functionality.
        """
        self.persist.set_persistence(
            key="enable_failsafe",
            value=False,
        )
        self.log_and_toast(
            title="Failsafe",
            message="Disabled Failsafe..."
        )

    def settings_local_enable_ad_blocking(self, **kwargs):
        """
        "settings_local_enable_ad_blocking" functionality.
        """
        self.persist.set_persistence(
            key="enable_ad_blocking",
            value=True,
        )
        self.log_and_toast(
            title="Ad Blocking",
            message="Enabled Ad Blocking...",
        )

    def settings_local_disable_ad_blocking(self, **kwargs):
        """
        "settings_local_disable_ad_blocking" functionality.
        """
        self.persist.set_persistence(
            key="enable_ad_blocking",
            value=False,
        )
        self.log_and_toast(
            title="Ad Blocking",
            message="Disabled Ad Blocking...",
        )

    def settings_local_enable_auto_update(self, **kwargs):
        """
        "settings_local_enable_auto_update" functionality.
        """
        self.persist.set_persistence(
            key="enable_auto_update",
            value=True,
        )
        self.log_and_toast(
            title="Auto Update",
            message="Enabled Auto Updates...",
        )

    def settings_local_disable_auto_update(self, **kwargs):
        """
        "settings_local_enable_auto_update" functionality.
        """
        self.persist.set_persistence(
            key="enable_auto_update",
            value=False,
        )
        self.log_and_toast(
            title="Auto Update",
            message="Disabled Auto Updates...",
        )

    def discord(self, **kwargs):
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

    def exit(self, **kwargs):
        """
        "exit" event functionality.
        """
        self.log_and_toast(
            title="Exit",
            message="Exiting...",
        )
        for instance in self._instances_cache.values():
            self.stop_session(instance=instance["pk"])
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
            # Handle auto console sizing...
            self.handle_console_size()
            # Handle auto update checks
            # (only if enabled locally)...
            if self.persist.get_persistence("enable_auto_update"):
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
                    # Dynamic menu entry checks...
                    if event_text in self._instances_cache:
                        self.handle_instance_activate(
                            instance=event_text,
                        )
                    if event_text in self._configurations_cache:
                        self.handle_configuration_activate(
                            configuration=event_text,
                        )
                else:
                    event_func(instance=self._instance_active)
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
            for instance in self._instances_cache.values():
                self.stop_session(instance=instance["pk"])
