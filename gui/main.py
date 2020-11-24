from gui.utilities import (
    get_most_recent_log_file,
    create_gui_logger,
)
from gui.settings import (
    ICON_FILE,
    MENU_DISABLED,
    MENU_SEPARATOR,
    MENU_BLANK_HEADER,
    MENU_START_SESSION,
    MENU_STOP_SESSION,
    MENU_UPDATE_CONFIGURATION,
    MENU_UPDATE_CONFIGURATION_DEFAULTS,
    MENU_UPDATE_LICENSE,
    MENU_TOOLS,
    MENU_TOOLS_LOCAL_DATA,
    MENU_TOOLS_MOST_RECENT_LOG,
    MENU_TOOLS_FLUSH_LICENSE,
    MENU_DISCORD,
    MENU_EXIT,
    MENU_TIMEOUT,
)

from license_validator.validation import LicenseValidator
from license_validator.utilities import (
    set_license,
)

from bot.core.bot import (
    Bot,
)
from bot.configuration.utilities import (
    set_local_configuration,
)

import PySimpleGUIWx as sg
import sentry_sdk
import threading
import webbrowser
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

        self._stop = False
        self._thread = None
        self._session = None

        self.application_name = application_name
        self.application_version = application_version
        self.application_discord = application_discord

        self.license = LicenseValidator()
        self.tray = sg.SystemTray(
            menu=self.menu(),
            filename=ICON_FILE,
        )
        self.logger = create_gui_logger(
            log_directory=self.license.program_logs_directory,
            log_name=self.license.program_name,
        )

        if not self.license.license_available:
            # No license even available at this point,
            # likely the first time starting, let's prompt
            # for a license right away.
            self.update_license()

        # We'll always set our configuration once on initialization.
        # This means if one doesn't exist, defaults are used, if one does exist,
        # new options will be generated if needed.
        self.update_configuration(open_file=False)
        self.event_map = {
            MENU_START_SESSION: self.start_session,
            MENU_STOP_SESSION: self.stop_session,
            MENU_UPDATE_CONFIGURATION: self.update_configuration,
            MENU_UPDATE_CONFIGURATION_DEFAULTS: self.update_configuration_defaults,
            MENU_UPDATE_LICENSE: self.update_license,
            MENU_TOOLS_LOCAL_DATA: self.tools_local_data,
            MENU_TOOLS_MOST_RECENT_LOG: self.tools_most_recent_log,
            MENU_TOOLS_FLUSH_LICENSE: self.tools_flush_license,
            MENU_DISCORD: self.discord,
            MENU_EXIT: self.exit,
            MENU_TIMEOUT: self.refresh,
        }

    @property
    def menu_title(self):
        """
        Return the application name and application version merged gracefully.
        """
        return "%(application_name)s (%(application_version)s)" % {
            "application_name": self.application_name,
            "application_version": self.application_version,
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
    def yes_no_popup(text):
        """
        Generate and display a yes no prompt that returns a boolean.
        """
        return sg.PopupYesNo(
            text,
            icon=ICON_FILE
        ) == "Yes"

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

    def menu(self):
        """
        Generate the menu used by the system tray application.
        """
        return [
            self.menu_entry(text=MENU_BLANK_HEADER), [
                self.menu_entry(text=self.menu_title),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_START_SESSION, disabled=self._thread is not None),
                self.menu_entry(text=MENU_STOP_SESSION, disabled=self._thread is None),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_UPDATE_CONFIGURATION),
                self.menu_entry(text=MENU_UPDATE_CONFIGURATION_DEFAULTS),
                self.menu_entry(text=MENU_UPDATE_LICENSE),
                self.menu_entry(separator=True),
                self.menu_entry(text=MENU_TOOLS),
                [
                    self.menu_entry(text=MENU_TOOLS_LOCAL_DATA),
                    self.menu_entry(text=MENU_TOOLS_MOST_RECENT_LOG),
                    self.menu_entry(text=MENU_TOOLS_FLUSH_LICENSE),
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

    def stop_func(self):
        """
        Return the current internal ``_stop`` value.
        """
        return self._stop

    def start_session(self):
        """
        "start_session" event functionality.
        """
        if not self._thread:
            self._stop = False
            self._session = uuid.uuid4().hex
            self._thread = threading.Thread(
                target=Bot,
                kwargs={
                    "application_name": self.application_name,
                    "application_version": self.application_version,
                    "application_discord": self.application_discord,
                    "license_obj": self.license,
                    "session": self._session,
                    "stop_func": self.stop_func,
                },
            )
            self._thread.start()

    def stop_session(self):
        """
        "stop_session" functionality.
        """
        if self._thread is not None:
            self._stop = True
            self._session = None
            self._thread.join()
            self._thread = None

    def update_configuration(self, defaults=False, open_file=True):
        """
        "update_configuration" event functionality.
        """
        # Before we open up the configuration file for modification,
        # we perform a check to see if we need to generate the default
        # data to be put in it.
        set_local_configuration(
            local_configuration_file=self.license.program_configuration_file,
            defaults=defaults,
        )
        if not defaults:
            if open_file:
                os.startfile(
                    filepath=self.license.program_configuration_file,
                )

    def update_configuration_defaults(self, open_file=False):
        """
        "update_configuration_defaults" event functionality.
        """
        if self.yes_no_popup(
            text="Are you sure? Reverting to defaults will purge your current local configuration.",
        ):
            self.update_configuration(
                defaults=True,
                open_file=open_file,
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
        set_license(
            license_file=self.license.program_license_file,
            text=text,
        )

    def tools_local_data(self):
        """
        "tools_local_data" functionality.
        """
        os.startfile(
            filepath=self.license.program_directory,
        )

    def tools_most_recent_log(self):
        """
        "tools_most_recent_log" functionality.
        """
        file = get_most_recent_log_file(
            log_directory=self.license.program_logs_directory,
        )
        if file:
            return os.startfile(
                filepath=file,
            )

    def tools_flush_license(self):
        """
        "tools_flush_license" functionality.
        """
        return self.license.flush()

    def discord(self):
        """
        "discord" event functionality.
        """
        return webbrowser.open_new_tab(
            url=self.application_discord,
        )

    def exit(self):
        """
        "exit" event functionality.
        """
        raise SystemExit

    def run(self):
        """
        Begin main runtime loop for application.
        """
        try:
            self.logger.info("===================================================================================")
            self.logger.info(
                "%(application_name)s GUI Initialized..." % {
                    "application_name": self.application_name,
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
            # Sentry can have some tags set for any issues that
            # crop up during our gui functionality...
            sentry_sdk.set_tag("package", "gui")
            sentry_sdk.set_tag("license", self.license.license)

            while True:
                # Always retrieve the event on each loop. An event is grabbed
                # when our application or menu entries are pressed.
                event = self.event_map.get(self.tray.read(
                    timeout=100,
                ))
                if event:
                    event()
        except Exception:
            self.logger.info(
                "An unknown exception was encountered... The error has been reported to the support team."
            )
            sentry_sdk.capture_exception()
            # Let the user press enter to shut their application
            # down. In case some information is needed from the terminal.
            input("\nPress \"Enter\" to exit...")
        finally:
            # Always stop session on application termination...
            self.stop_session()
