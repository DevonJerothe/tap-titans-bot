from settings import (
    APPLICATION_NAME,
    LOCAL_DATA_LOGS_DIRECTORY,
)

from database.models.settings.settings import (
    Settings,
)
from database.models.instance.instance import (
    Instance,
)
from database.models.configuration.configuration import (
    Configuration,
)
from database.models.event.event import (
    Event,
)

from gui.utilities import (
    get_most_recent_log_file,
    create_gui_logger,
)
from gui.settings import (
    DT_FORMAT,
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
    MENU_EVENTS,
    MENU_TOOLS,
    MENU_TOOLS_LOCAL_DATA,
    MENU_TOOLS_MOST_RECENT_LOG,
    MENU_INSTANCES,
    MENU_CONFIGURATIONS_ADD,
    MENU_CONFIGURATIONS,
    MENU_SETTINGS,
    MENU_EXIT,
    MENU_TIMEOUT,
)

from bot.core.bot import (
    Bot,
)
from bot.core.window import (
    WindowHandler,
)

import PySimpleGUIWx as sg
import gui.sg_ext as sgx
import threading
import locale
import operator
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
        self._events_cache = []

        self.settings_obj_changed = False
        self.settings_obj = Settings.get()

        self.application_name = application_name
        self.application_version = application_version

        self.logger = create_gui_logger(
            log_directory=LOCAL_DATA_LOGS_DIRECTORY,
            log_name=APPLICATION_NAME,
        )

        # Always handling a configuration refresh on initial
        # application startup.
        self.refresh_instances()
        self.refresh_configurations()

        self.tray = sg.SystemTray(
            menu=self.menu(),
            filename=ICON_FILE,
        )

        # An issue with wx here, upon creating the system tray, the locale is being
        # changed to the system default, with errors cropping up with windows 10...
        # See this discussion
        # https://discuss.wxpython.org/t/what-is-wxpython-doing-to-the-locale-to-makes-pandas-crash/34606/20
        # Fix for now is to set the locale after this erroneous one is set.
        try:
            locale.setlocale(locale.LC_ALL, locale.getdefaultlocale()[0])
        except locale.Error:
            self.logger.info(
                "Unable to set the locale..."
            )

        self.event_map = {
            MENU_FORCE_PRESTIGE: self.force_prestige,
            MENU_FORCE_STOP: self.force_stop,
            MENU_START_SESSION: self.start_session,
            MENU_STOP_SESSION: self.stop_session,
            MENU_RESUME_SESSION: self.resume_session,
            MENU_PAUSE_SESSION: self.pause_session,
            MENU_EVENTS: self.events,
            MENU_TOOLS_LOCAL_DATA: self.tools_local_data,
            MENU_TOOLS_MOST_RECENT_LOG: self.tools_most_recent_log,
            MENU_CONFIGURATIONS_ADD: self.configurations_add,
            MENU_SETTINGS: self.settings,
            MENU_EXIT: self.exit,
            MENU_TIMEOUT: self.refresh,
        }

    def get_settings_obj(self):
        """Utility method to retrieve the setting object if it's been changed since the last
        time it's been retrieved.
        """
        if self.settings_obj_changed:
            # If the settings have changed (handled through the gui),
            # we'll "re-retrieve" the settings instance.
            self.settings_obj.get()
            self.settings_obj_changed = False

        return self.settings_obj

    def handle_console_size(self):
        """Handle resizing the application console.
        """
        try:
            if self.window_size:
                # We also only ever actually set the terminal size when it's
                # possible to gather the current size.
                os.system(self.settings_obj.console_size)
        except Exception:
            # If anything fails while trying to update the window
            # size for the user, we can simply just continue execution
            # to avoid breaking the application completely.
            self.logger.info(
                "An error occurred while attempting to modify the console size, skipping..."
            )

    def remember_console_size(self):
        """Handle "remembering" the current size of the console.
        """
        window_size = self.window_size

        if window_size:
            # Only ever persisting the value when something valid can even be
            # gathered from the terminal.
            self.settings_obj.console_size = window_size
            self.settings_obj.save()

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
        """Handle activating a instance and setting it to a "selected" state.
        """
        self.log(
            message="Activating %(name)s..." % {
                "name": instance,
            }
        )
        instance = self._instances_cache[instance]

        # Simply just update the local selected instance
        # (the gui uses this to determine how to treat signals).
        self._instance_active = instance.id
        self.logger.debug(
            self._instance_active
        )
        self.log(
            message="Done...",
        )

    def handle_configuration_activate(self, configuration):
        """Handle opening and modifying a configuration.
        """
        configuration_obj = self._configurations_cache[configuration]
        event, values = sgx.PopupWindowConfiguration(
            title="Edit Configuration: %s" % configuration,
            configuration_obj=configuration_obj,
            icon=ICON_FILE,
        )
        if event in ["Delete", "Save", "Replicate"]:
            if event == "Replicate":
                configuration_obj.id = None
                configuration_obj.name = "%(name)s (COPY)" % {
                    "name": configuration_obj.name,
                }
                configuration_obj.save()
                self.log(
                    message="Configuration: \"%(name)s\" Has Been Replicated Successfully..." % {
                        "name": configuration_obj.name,
                    }
                )
            if event == "Delete":
                Configuration.delete().where(Configuration.id == configuration_obj.id).execute()
                self.log(
                    message="Configuration: \"%(name)s\" Has Been Deleted Successfully..." % {
                        "name": configuration_obj.name,
                    }
                )
            if event == "Save":
                # Save the configuration back into the object
                # selected for modification.
                try:
                    Configuration.update(**values).where(Configuration.id == configuration_obj.id).execute()
                except Exception as exc:
                    self.log(
                        message="An Error Occurred While Trying To Save Configuration: %s" % exc
                    )
                else:
                    self.log(
                        message="Configuration: \"%(name)s\" Has Been Saved Successfully..." % {
                            "name": values["name"],
                        }
                    )
            # Always refresh available configurations
            # when the event is finished.
            self.refresh_configurations()

    @property
    def menu_title(self):
        """Return the application name and application version merged gracefully.
        """
        return "%(application_name)s (%(application_version)s)" % {
            "application_name": self.application_name,
            "application_version": self.application_version,
        }

    @property
    def menu_title_sub(self):
        """Return the active instance for at a glance information available.
        """
        if self._instance_active:
            # Include a space so we can avoid reactivating an instance
            # that's already active...
            return self._instances_names[self._instance_active] + " "
        return "(No Instance)"

    @property
    def window_size(self):
        """Retrieve the current window size.
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

    def log(self, message, instance=None):
        """Log and toast a given message and title.
        """
        if instance == self._instance_active or not instance:
            self.logger.info(message)

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
                self.menu_entry(text=MENU_EVENTS),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_TOOLS),
                [
                    self.menu_entry(text=MENU_TOOLS_LOCAL_DATA),
                    self.menu_entry(text=MENU_TOOLS_MOST_RECENT_LOG),
                ],
                self.menu_entry(text=MENU_INSTANCES),
                [
                    *self.refresh_instances(refresh=False)
                ],
                self.menu_entry(text=MENU_CONFIGURATIONS),
                [
                    self.menu_entry(text=MENU_CONFIGURATIONS_ADD),
                    self.menu_entry(separator=True),
                    *self.refresh_configurations(refresh=False)
                ],
                self.menu_entry(text=MENU_SETTINGS),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_EXIT),
            ],
        ]

    def refresh(self, **kwargs):
        """Refresh the system tray menu.
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
        """Refresh the instances available for a user. The data stored here is done so in a way that it can be
        viewed within a menu, some additional information is stored about each instance in the instances cache.
        """
        if refresh:
            instances = Instance().generate_defaults()
            instances = Instance.select().execute()
            self._instance_active = None
            self._instances_cache = {
                instance.name: instance
                for instance in instances
            }
            self._instances_names = {instance.id: instance.name for instance in self._instances_cache.values()}
            self._instances_internals = {instance.id: GUIInstanceInternals() for instance in self._instances_cache.values()}
            self.logger.debug(
                "Instances cache has been updated..."
            )
            self.logger.debug(
                self._instances_cache
            )
        # Begin populating menu entries...
        menu_entries = []

        for instance in self._instances_cache.values():
            text = "%(instance_name)s" % {
                "instance_name": instance.name,
            }
            if self._instance_active is None or self._instance_active == instance.id:
                self._instance_active = instance.id
                text += " (ACTIVE)"
            # Append the instance to the menu entry, selected instances
            # are disabled for local modification.
            menu_entries.append(
                self.menu_entry(text=text, disabled=self._instance_active == instance.id)
            )
        return menu_entries

    def refresh_windows(self, **kwargs):
        """Refresh the windows available for selection for a user. The data stored here is done so in a way
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
        """Refresh the configurations available for a user. The data stored here is done so in a way
        that in can be viewed within a menu, some additional information is stored about the keys about
        each one.
        """
        if refresh:
            configurations = Configuration().generate_defaults()
            configurations = Configuration.select().execute()
            self._configurations_cache = {
                configuration.name: configuration
                for configuration in configurations
            }
            self.logger.debug(
                "Configurations cache has been updated..."
            )
            self.logger.debug(
                self._configurations_cache
            )
        # Begin populating menu entries...
        menu_entries = []

        for configuration in self._configurations_cache.values():
            # Append the configuration to the menu entry.
            menu_entries.append(
                self.menu_entry(text=configuration.name),
            )
        return menu_entries

    def refresh_events(self, **kwargs):
        """Refresh the events currently available. The data stored here is done so in a way
        that it can be refreshed as needed on a polling basis through our main runtime loop.
        """
        self._events_cache = Event.select().order_by(-Event.timestamp).execute()

    def stop_func(self, instance):
        """Return the current internal ``stop`` value.
        """
        return self._instances_internals[instance].stop

    def pause_func(self, instance):
        """Return the current internal``pause`` value.
        """
        return self._instances_internals[instance].pause

    def force_prestige_func(self, instance, _set=False):
        """Return the current internal ``force_prestige`` value.

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
        """"force_prestige" event functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log(
                message="Forcing Prestige...",
                instance=instance,
            )
            self._instances_internals[instance].force_prestige = True

    def force_stop_func(self, instance, _set=False):
        """Return the current internal ``_force_stop`` value.

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
        """"force_stop" event functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log(
                message="Forcing Stop...",
                instance=instance,
            )
            self._instances_internals[instance].force_stop = True

    def instance_func(self):
        """Return the current internal ``_instance_active`` value.
        """
        return self._instance_active

    def start_session(self, instance):
        """"start_session" event functionality.
        """
        # We always refresh windows on session start prompt, so the most
        # recent windows are available and our cache is upto date upon selection.
        self.refresh_windows()
        # Default "remembered" values are persisted and used in between
        # session starts to avoid annoying re-selection of values...
        default_window = self.settings_obj.last_window
        default_configuration = self.settings_obj.last_configuration

        if default_window and default_window not in self._windows_cache:
            self.settings_obj.last_window = None
            self.settings_obj.save()
            default_window = None
        if default_configuration and default_configuration not in self._configurations_cache:
            self.settings_obj.last_configuration = None
            self.settings_obj.save()
            default_configuration = None

        event, values = sgx.PopupWindowStartSession(
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
                self.log(
                    message="Invalid Window Or Configuration Selected...",
                    instance=instance,
                )
            if window and configuration:
                self.settings_obj.last_window = window
                self.settings_obj.last_configuration = configuration
                self.settings_obj.save()

                if not self._instances_internals[instance].thread:
                    self.log(
                        message="Starting Session...",
                        instance=instance,
                    )
                    self._instances_internals[instance].stop = False
                    self._instances_internals[instance].force_stop = False
                    self._instances_internals[instance].pause = False
                    self._instances_internals[instance].session = uuid.uuid4().hex
                    self._instances_internals[instance].thread = threading.Thread(
                        target=Bot,
                        kwargs={
                            "application_name": self.application_name,
                            "application_version": self.application_version,
                            "event": Event,
                            "instance": instance,
                            "instance_name": self._instances_names[instance],
                            "instance_func": self.instance_func,
                            "window": window,
                            "configuration": self._configurations_cache[configuration].prep(),
                            "session": self._instances_internals[instance].session,
                            "get_settings_obj": self.get_settings_obj,
                            "force_prestige_func": self.force_prestige_func,
                            "force_stop_func": self.force_stop_func,
                            "stop_func": self.stop_func,
                            "pause_func": self.pause_func,
                        },
                    )
                    self._instances_internals[instance].thread.start()

    def stop_session(self, instance):
        """"stop_session" functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log(
                message="Stopping Session...",
                instance=instance,
            )
            self._instances_internals[instance].stop = True
            self._instances_internals[instance].session = None
            self._instances_internals[instance].thread.join()
            self._instances_internals[instance].thread = None

    def pause_session(self, instance):
        """"pause_session" functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log(
                message="Pausing Session...",
                instance=instance,
            )
            self._instances_internals[instance].pause = True

    def resume_session(self, instance):
        """"resume_session" functionality.
        """
        if self._instances_internals[instance].thread is not None:
            self.log(
                message="Resuming Session...",
                instance=instance,
            )
            self._instances_internals[instance].pause = False

    def events(self, **kwargs):
        """"events" functionality.
        """
        self.refresh_events()

        event, values = sgx.PopupWindowEvents(
            title="Events",
            events=[
                [event.instance.name, event.timestamp.strftime(format=DT_FORMAT), event.event]
                for event in self._events_cache
            ],
            icon=ICON_FILE,
        )
        if event == "Delete Highlighted":
            delete = [self._events_cache[index].id for index in values["table"]]
            delete = Event.delete().where(Event.id << delete).execute()
            self.log(
                message="Successfully Deleted %(count)s Event(s)..." % {
                    "count": delete,
                },
            )

    def tools_local_data(self, **kwargs):
        """"tools_local_data" functionality.
        """
        self.log(
            message="Opening Local Data Directory...",
        )
        os.startfile(
            filepath=LOCAL_DATA_LOGS_DIRECTORY,
        )
        self.log(
            message="Done...",
        )

    def tools_most_recent_log(self, **kwargs):
        """"tools_most_recent_log" functionality.
        """
        file = get_most_recent_log_file(
            log_directory=LOCAL_DATA_LOGS_DIRECTORY,
        )
        if file:
            self.log(
                message="Opening Most Recent Log...",
            )
            os.startfile(
                filepath=file,
            )
            self.log(
                message="Done...",
            )
        else:
            self.log(
                message="No Recent Log Available To Open...",
            )

    def configurations_add(self, **kwargs):
        """"configurations_add" event functionality.
        """
        self.log(
            message="Adding New Configuration..."
        )
        configuration = Configuration.create()
        self.log(
            message="New Configuration: \"%(name)s\" Was Added Successfully..." % {
                "name": configuration.name,
            }
        )
        # Always refresh post add so the newest configuration is available
        # in our cached data and within thr gui.
        self.refresh_configurations()

    def settings(self, **kwargs):
        """"settings" event functionality.
        """
        event, values = sgx.PopupWindowSettings(
            title="Settings",
            settings_obj=self.settings_obj,
            icon=ICON_FILE,
        )
        if event == "Save":
            try:
                self.settings_obj.update(**values).execute()
                self.settings_obj = self.settings_obj.get()
                self.settings_obj_changed = True
            except Exception as exc:
                self.log(
                    "An Error Occurred While Trying To Save Settings: %s" % exc
                )
            else:
                self.log(
                    "Settings Have Been Saved Successfully..."
                )

    def exit(self, **kwargs):
        """"exit" event functionality.
        """
        self.log("Exiting...")

        for instance in self._instances_cache.values():
            self.stop_session(instance=instance.id)
        # SystemExit to leave with valid return code.
        # We don't want any exceptions raised.
        raise SystemExit

    def purge_stale_logs(self):
        """Purge any logs present that are older than the configured amount of days.
        """
        for log in os.listdir(LOCAL_DATA_LOGS_DIRECTORY):
            if os.path.getmtime(os.path.join(LOCAL_DATA_LOGS_DIRECTORY, log)) < time.time() - self.settings_obj.log_purge_days * 86400:
                self.logger.info(
                    "Purging Stale Log: \"%(log)s\"..." % {
                        "log": log,
                    }
                )
                if os.path.isfile(os.path.join(LOCAL_DATA_LOGS_DIRECTORY, log)):
                    os.remove(os.path.join(LOCAL_DATA_LOGS_DIRECTORY, log))

    def run(self):
        """Begin main runtime loop for application.
        """
        try:
            # Handle auto console sizing...
            self.handle_console_size()

            self.logger.info("===================================================================================")
            self.logger.info(
                "%(application_name)s GUI (v%(version)s) Initialized..." % {
                    "application_name": self.application_name,
                    "version": self.application_version,
                }
            )
            self.logger.info("===================================================================================")

            self.purge_stale_logs()

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

        except Exception as exc:
            self.logger.info(
                "An unknown exception was encountered... %(exception)s" % {
                    "exception": exc,
                }
            )
            # Let the user press enter to shut their application
            # down. In case some information is needed from the terminal.
            input("\nPress \"Enter\" to exit...")
        finally:
            # Always set our "remembered" console size on exit.
            self.remember_console_size()
            # Always stop session on application termination...
            for instance in self._instances_cache.values():
                self.stop_session(instance=instance.id)
