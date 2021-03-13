from license_validator.exceptions import (
    LicenseRetrievalError,
    LicenseExpirationError,
    LicenseServerError,
    LicenseConnectionError,
    LicenseIntegrityError,
)

from bot.core.window import WindowHandler, WindowNotFoundError
from bot.core.scheduler import TitanScheduler
from bot.core.imagesearch import image_search_area, click_image
from bot.core.imagecompare import compare_images
from bot.core.exceptions import (
    LicenseAuthenticationError,
    GameStateException,
    StoppedException,
    PausedException,
    ExportContentsException,
)
from bot.core.utilities import (
    create_logger,
    decrypt_secret,
)

from itertools import cycle
from pyautogui import FailSafeException

from PIL import Image

import sentry_sdk
import pyperclip
import datetime
import random
import copy
import numpy
import time
import json
import cv2
import os


class Bot(object):
    """
    Core Bot Instance.
    """
    def __init__(
        self,
        application_name,
        application_version,
        application_discord,
        session,
        license_obj,
        force_prestige_func,
        force_stop_func,
        stop_func,
        pause_func,
        toast_func,
        failsafe_enabled_func,
        ad_blocking_enabled_func,
    ):
        """
        Initialize a new Bot instance.

        The license specified may or may not be valid, we perform our validation and retrieval
        during initialization and correctly error out if needed.
        """
        self.application_name = application_name
        self.application_version = application_version
        self.application_discord = application_discord

        self.files = {}             # Program Files.
        self.configurations = {}    # Global Program Configurations
        self.configuration = {}     # Local Bot Configurations.

        self.export_orig_contents = {}     # Store the original set of export data.
        self.export_current_contents = {}  # Most recent contents.

        # force_prestige_func is used to correctly handle the ability
        # to force a prestige to take place during a running session.
        self.force_prestige_func = force_prestige_func
        # force_stop_func is used to correctly handle the ability
        # to force a stop to take place during a running session.
        self.force_stop_func = force_stop_func
        # stop_func is used to correctly handle our threading functionality.
        # A ``bot`` is initialized through some method that invokes a new thread.
        # We require an argument that should represent a function to determine when to exit.
        self.stop_func = stop_func
        # pause_func is used to correctly handle pause/resume functionality.
        # Function is used to determine when pause and resume should take
        # place during runtime.
        self.pause_func = pause_func
        self.pause_date = None
        # toast_func can be used to send messages to the gui system
        # directly from a bot while it's running.
        self.toast_func = toast_func

        # Additionally, certain configurations are persisted
        # locally and can be enabled/disabled through the gui.
        self.failsafe_enabled_func = failsafe_enabled_func
        self.ad_blocking_enabled_func = ad_blocking_enabled_func

        # Custom scheduler is used currently to handle
        # stop_func functionality when running pending
        # jobs, this avoids large delays when waiting
        # to pause/stop
        self.schedule = TitanScheduler(
            stop_func=self.stop_func,
            pause_func=self.pause_func,
            force_stop_func=self.force_stop_func,
            force_prestige_func=self.force_prestige_func,
        )
        # Flag to represent initial scheduling to help
        # determine whether or not reset safe functions
        # should be determined and modified.
        self.scheduled = False
        # The last screenshot variable is used to store image objects
        # that are taken every time game state is checked, if the last
        # screenshot is ever the same as the current one, the emulator has
        # most likely frozen.
        self.last_screenshot = None

        self.session = session
        self.license = license_obj
        self.license.session = self.session

        # Update sentry tags in case of unhandled exceptions
        # occurring while user runs session.
        sentry_sdk.set_tag("package", "bot")
        sentry_sdk.set_tag("session", self.session)

        self.logger, self.stream = create_logger(
            log_directory=self.license.program_logs_directory,
            log_name=self.license.program_name,
            session_id=self.session,
        )

        # Begin License Validation...
        # Any of the below failures should exit us out of the
        # session that is being initialized.
        try:
            try:
                self.logger.info(
                    "Requesting license information..."
                )
                self.logger.info(
                    "Note: If this is your first time running a session, this process could take a while, please don't "
                    "cancel or attempt to manually close your session while this is running... If this is taking a very "
                    "long time, you can hard exit the application and contact support for additional help."
                )
                self.logger.debug(
                    self.license.license
                )
                self.license.flush()
                self.license.collect_license(logger=self.logger)
                self.license.online()
                self.logger.info(
                    "Your license has been requested and validated successfully!"
                )
            except TimeoutError:
                self.logger.info(
                    "Authentication timeout was reached... Check your internet connection and please try again."
                )
            except LicenseRetrievalError:
                self.logger.info(
                    "Invalid license entered. Double check your license and please try again. This could also be caused when you are "
                    "using an older version of the application."
                )
                raise
            except LicenseExpirationError as err:
                self.logger.info(
                    "Your license has expired (%(license_expiration)s), please contact support or extend your license "
                    "and try again." % {
                        "license_expiration": err,
                    }
                )
                raise
            except LicenseIntegrityError:
                self.logger.info(
                    "A license integrity error was encountered, you can flush your license "
                    "with the tools present in the system tray application. This can happen when "
                    "multiple users are trying to use the same license, or when your application is "
                    "terminated unexpectedly."
                )
                raise
            except LicenseServerError:
                self.logger.info(
                    "The license server did not respond, or a server error has occurred, the error has been "
                    "reported to the support team."
                )
                raise
            except LicenseConnectionError as err:
                self.logger.info(
                    "Connection error encountered while requesting license, please try again later."
                )
                self.logger.debug(err)
                raise
            except Exception:
                self.logger.info(
                    "An unknown error was encountered while requesting your license and has been "
                    "reported to the support team."
                )
                sentry_sdk.capture_exception()
                raise
        except Exception:
            self.logger.info("===================================================================================")
            self.logger.info(
                "If you continue to experience issues with your license, contact support for additional help. If your error "
                "has been reported to the support team, your license and session may be required."
            )
            self.logger.info("License: %(license)s" % {
                "license": self.license.license,
            })
            self.logger.info("Session: %(session)s" % {
                "session": self.session,
            })
            self.logger.info("===================================================================================")
            raise SystemExit

        # At this point, our license should have been retrieved, and all of our
        # configuration values should be available for parsing.
        self.configure_dependencies()
        self.configure_files()
        self.configure_configuration()
        self.configure_configurations()

        try:
            self.handle = WindowHandler()
            self.window = self.handle.filter_first(
                filter_title=self.configuration["emulator_window"],
            )
            self.window.configure(
                enable_failsafe_func=self.failsafe_enabled_func,
                force_stop_func=self.force_stop_func,
            )
        except WindowNotFoundError:
            self.logger.info(
                "Unable to find the configured window (%(window)s), make sure the window is visible and try again. "
                "Your window should also be at the specified size (480x800x160DPI). If you're having trouble "
                "finding your window, you can use the multi instance manager on your emulator to use a custom window "
                "title instead of the default." % {
                    "window": self.configuration["emulator_window"],
                },
            )
            # Set license offline since we are not in main loop
            # yet (which usually handles this).
            self.license.offline()
            # SystemExit to just "exit".
            raise SystemExit

        # Begin running the bot once all dependency/configuration/files/variables
        # have been handled and are ready to go.
        self.run()

    def configure_configuration(self):
        """
        Configure the local configuration used by the bot.
        """
        self.logger.info("Configuring local configuration...")
        # The settings housed here are configurable by the user locally.
        # The file should just be loaded and placed into our configuration.
        self.configuration = self.license.license_data["configuration"]
        self.logger.debug(
            "Local Configuration: Loaded..."
        )
        self.logger.debug(
            self.configuration
        )

    def configure_dependencies(self):
        """
        Configure the dependencies used by the bot.
        """
        pass

    def configure_files(self):
        """
        Configure the files available and used by the bot.
        """
        self.logger.info("Configuring files...")
        # Our local license/application directory should contain a directory of images
        # with their versions, the bot does not care about the versions other than making
        # sure the most recent one is being used. We handle that logic here.
        with os.scandir(self.license.program_file_directory) as scan:
            for version in scan:
                for file in os.scandir(version.path):
                    self.files[file.name.split(".")[0]] = file.path
        self.logger.debug(
            "Program Files: Loaded..."
        )

    def configure_configurations(self):
        """
        Configure the configurations available and used by the bot.
        """
        self.logger.info("Configuring configurations...")
        # Globally available and any configurations retrieved through our
        # license can be handled here.
        self.configurations = json.loads(decrypt_secret(self.license.license_data["program"]["configurations"]))
        # Hide the global configurations being used...
        # Knowing that they're loaded is fine here.
        self.logger.debug(
            "Global Configurations: Loaded..."
        )

    def configure_additional(self):
        """
        Configure any additional variables or values that can be used throughout session runtime.
        """
        # GLOBAL INFO.
        self.image_tabs = {
            self.files["travel_master_icon"]: "master",
            self.files["travel_heroes_icon"]: "heroes",
            self.files["travel_equipment_icon"]: "equipment",
            self.files["travel_pets_icon"]: "pets",
            self.files["travel_artifacts_icon"]: "artifacts",
            self.files["travel_shop_icon"]: "shop",
        }

        # Artifact Data.
        # ------------------
        # "upgrade_map_keys" - List of keys present in the artifact maps.
        # "upgrade_map_key_unmapped" - The key used to find unmapped artifacts.
        # "upgrade_map_key_ordering" - The key used to determine the order of artifacts.
        # "upgrade_map_key_limits" - The key used to determine the limits of artifacts.
        # "mapping_enabled" - Whether or not the mapping functionality is enabled.
        # "upgrade_map" - The map containing all artifact options from a configuration.
        # "upgrade_artifacts" - A list of artifacts to upgrade, one at a time, during a session.
        # "next_artifact_upgrade" - The next single artifact that will be upgraded if maps are disabled.
        self.upgrade_map_keys = ["1", "5", "25", "max"]
        self.upgrade_map_key_unmapped = "unmapped"
        self.upgrade_map_key_ordering = "percentOrder"
        self.upgrade_map_key_limits = "mappedLimits"
        self.mapping_enabled = False
        self.upgrade_map = json.loads(self.configuration["artifacts_upgrade_map"])
        self.upgrade_artifacts = None
        self.next_artifact_upgrade = None

        if self.configuration["artifacts_enabled"] and self.configuration["artifacts_upgrade_enabled"]:
            # Shuffled artifact settings will shuffle everything in the map,
            # this is done regardless of maps being enabled or not.
            if self.configuration["artifacts_shuffle"]:
                for key in self.upgrade_map_keys + [self.upgrade_map_key_unmapped]:
                    random.shuffle(self.upgrade_map[key])
            for key in self.upgrade_map_keys:
                if self.upgrade_map[key]:
                    self.mapping_enabled = True
                    break

            # No maps are actually being used, in which case, we can just
            # go ahead and setup some per prestige upgrade options.
            if not self.mapping_enabled:
                if self.upgrade_map[self.upgrade_map_key_unmapped]:
                    self.upgrade_artifacts = cycle(self.upgrade_map[self.upgrade_map_key_unmapped])
                    self.next_artifact_upgrade = next(self.upgrade_artifacts)

        # Session Data.
        # ------------------
        # "powerful_hero" - most powerful hero currently in game.
        self.powerful_hero = None

        # Per Prestige Data.
        # ------------------
        # "close_to_max_ready" - Store a flag to denote that a close to max prestige is ready.
        # "master_levelled" - Store a flag to denote the master being levelled.
        self.close_to_max_ready = False
        self.master_levelled = False

        # Shop Data.
        # ------------------
        # "shop_pets_purchase_pets" - Store the configured purchase pets (if any).
        if self.configuration["shop_pets_purchase_enabled"] and self.configuration["shop_pets_purchase_pets"]:
            self.shop_pets_purchase_pets = self.configuration["shop_pets_purchase_pets"].split(",")
        else:
            self.shop_pets_purchase_pets = []

        self.logger.debug(
            "Additional Configurations: Loaded..."
        )
        self.logger.debug("\"powerful_hero\": %s" % self.powerful_hero)
        self.logger.debug("\"upgrade_map_keys\": %s" % self.upgrade_map_keys)
        self.logger.debug("\"upgrade_map_key_unmapped\": %s" % self.upgrade_map_key_unmapped)
        self.logger.debug("\"mapping_enabled\": %s" % self.mapping_enabled)
        self.logger.debug("\"upgrade_map\": %s" % self.upgrade_map)
        self.logger.debug("\"upgrade_map_key_ordering\": %s" % self.upgrade_map_key_ordering)
        self.logger.debug("\"upgrade_artifacts\": %s" % self.upgrade_artifacts)
        self.logger.debug("\"next_artifact_upgrade\": %s" % self.next_artifact_upgrade)
        self.logger.debug("\"close_to_max_ready\": %s" % self.close_to_max_ready)
        self.logger.debug("\"master_levelled\": %s" % self.master_levelled)
        self.logger.debug("\"shop_pets_purchase_pets\": %s" % self.shop_pets_purchase_pets)

    def schedule_functions(self):
        """
        Loop through each available function used during runtime, setting up
        and configuring a scheduler for each one.

        The following options should be included on each scheduled functions:

        - "enabled"  - Should this function be scheduled at all?
        - "interval" - How long (in seconds) between each execution?
        - "reset"    - Should this function be ignored when the scheduler is cleared and reinitialized?
        """
        _schedule = {
            self.check_game_state: {
                "enabled": self.configurations["global"]["check_game_state"]["check_game_state_enabled"],
                "interval": self.configurations["global"]["check_game_state"]["check_game_state_interval"],
                "reset": True,
            },
            self.check_license: {
                "enabled": self.configurations["global"]["check_license"]["check_license_enabled"],
                "interval": self.configurations["global"]["check_license"]["check_license_interval"],
                "reset": False,
            },
            self.export_data: {
                "enabled": self.configuration["export_data_enabled"] and not self.configuration["abyssal"],
                "interval": self.configuration["export_data_interval"],
                "reset": True,
            },
            self.tap: {
                "enabled": self.configuration["tapping_enabled"],
                "interval": self.configuration["tapping_interval"],
                "reset": True,
            },
            self.fight_boss: {
                "enabled": self.configurations["global"]["fight_boss"]["fight_boss_enabled"],
                "interval": self.configurations["global"]["fight_boss"]["fight_boss_interval"],
                "reset": True,
            },
            self.eggs: {
                "enabled": self.configurations["global"]["eggs"]["eggs_enabled"],
                "interval": self.configurations["global"]["eggs"]["eggs_interval"],
                "reset": False,
            },
            self.inbox: {
                "enabled": self.configurations["global"]["inbox"]["inbox_enabled"],
                "interval": self.configurations["global"]["inbox"]["inbox_interval"],
                "reset": False,
            },
            self.daily_rewards: {
                "enabled": self.configurations["global"]["daily_rewards"]["daily_rewards_enabled"],
                "interval": self.configurations["global"]["daily_rewards"]["daily_rewards_interval"],
                "reset": False,
            },
            self.achievements: {
                "enabled": self.configurations["global"]["achievements"]["achievements_enabled"],
                "interval": self.configurations["global"]["achievements"]["achievements_interval"],
                "reset": False,
            },
            self.level_master: {
                "enabled": self.configuration["level_master_enabled"],
                "interval": self.configuration["level_master_interval"],
                "reset": True,
            },
            self.level_skills: {
                "enabled": self.configuration["level_skills_enabled"],
                "interval": self.configuration["level_skills_interval"],
                "reset": True,
            },
            self.activate_skills: {
                "enabled": self.configuration["activate_skills_enabled"],
                "interval": self.configuration["activate_skills_interval"],
                "reset": True,
            },
            self.level_heroes_quick: {
                "enabled": self.configuration["level_heroes_quick_enabled"],
                "interval": self.configuration["level_heroes_quick_interval"],
                "reset": True,
            },
            self.level_heroes: {
                "enabled": self.configuration["level_heroes_enabled"],
                "interval": self.configuration["level_heroes_interval"],
                "reset": True,
            },
            self.shop_pets: {
                "enabled": self.configuration["shop_pets_purchase_enabled"],
                "interval": self.configuration["shop_pets_purchase_interval"],
                "reset": False,
            },
            self.shop_video_chest: {
                "enabled": self.configuration["shop_video_chest_enabled"],
                "interval": self.configuration["shop_video_chest_interval"],
                "reset": False,
            },
            self.perks: {
                "enabled": self.configuration["perks_enabled"],
                "interval": self.configuration["perks_interval"],
                "reset": False,
            },
            self.prestige: {
                "enabled": self.configuration["prestige_time_enabled"],
                "interval": self.configuration["prestige_time_interval"],
                "reset": True,
            },
            self.prestige_close_to_max: {
                "enabled": self.configuration["prestige_close_to_max_enabled"],
                "interval": self.configurations["global"]["prestige_close_to_max"]["prestige_close_to_max_interval"],
                "reset": True,
            },
        }

        schedule_first_time = False

        if not self.scheduled:
            schedule_first_time = True
        else:
            # If scheduling has already taken place at least once, we'll only clear
            # the functions that are reset safe, others are ignored and are left as-is.
            self.cancel_scheduled_function(tags=[
                function.__name__ for function in _schedule if _schedule[function]["reset"]
            ])

        for function, data in _schedule.items():
            if not schedule_first_time and self.scheduled and not data["reset"]:
                continue
            if data["enabled"]:
                # We wont schedule any functions that also
                # have an interval of zero.
                if data["interval"] > 0:
                    self.schedule_function(
                        function=function,
                        interval=data["interval"],
                    )
                else:
                    self.logger.debug(
                        "Function: \"%(function)s\" is scheduled to run but the interval is set to zero, skipping..." % {
                            "function": function.__name__,
                        }
                    )
        if schedule_first_time:
            # If were scheduling for the first time, we flip this flag once
            # after initial scheduling, this lets us reschedule and respect reset
            # flags on each subsequent reschedule.
            self.scheduled = True

    def schedule_function(self, function, interval):
        """
        Schedule a given function to run periodically.
        """
        self.logger.debug(
            "Function: \"%(function)s\" is scheduled to run every %(interval)s second(s)..." % {
                "function": function.__name__,
                "interval": interval,
            }
        )
        self.schedule.every(interval=interval).seconds.do(job_func=function).tag(function.__name__)

    def cancel_scheduled_function(self, tags):
        """
        Cancel a scheduled function if currently scheduled to run.
        """
        if not isinstance(tags, list):
            tags = [tags]
        for tag in tags:
            self.schedule.clear(tag)

    def execute_startup_functions(self):
        """
        Execute any functions that should be ran right away following a successful session start.
        """
        for function, data in {
            self.check_game_state: {
                "enabled": self.configurations["global"]["check_game_state"]["check_game_state_enabled"],
                "execute": self.configurations["global"]["check_game_state"]["check_game_state_on_start"],
            },
            self.export_data: {
                "enabled": self.configuration["export_data_enabled"] and not self.configuration["abyssal"],
                "execute": self.configurations["global"]["export_data"]["export_data_on_start"],
            },
            self.fight_boss: {
                "enabled": self.configurations["global"]["fight_boss"]["fight_boss_enabled"],
                "execute": self.configurations["global"]["fight_boss"]["fight_boss_on_start"],
            },
            self.eggs: {
                "enabled": self.configurations["global"]["eggs"]["eggs_enabled"],
                "execute": self.configurations["global"]["eggs"]["eggs_on_start"],
            },
            self.level_master: {
                "enabled": self.configuration["level_master_enabled"],
                "execute": self.configuration["level_master_on_start"],
            },
            self.level_skills: {
                "enabled": self.configuration["level_skills_enabled"],
                "execute": self.configuration["level_skills_on_start"],
            },
            self.activate_skills: {
                "enabled": self.configuration["activate_skills_enabled"],
                "execute": self.configuration["activate_skills_on_start"],
            },
            self.inbox: {
                "enabled": self.configurations["global"]["inbox"]["inbox_enabled"],
                "execute": self.configurations["global"]["inbox"]["inbox_on_start"],
            },
            # Tap comes before daily rewards because issues may crop up when
            # a fairy is displayed when trying to collect rewards. Tapping first
            # gets rid of and collects fairies before that can happen.
            self.tap: {
                "enabled": self.configurations["global"]["tap"]["tap_enabled"],
                "execute": self.configurations["global"]["tap"]["tap_on_start"],
            },
            self.daily_rewards: {
                "enabled": self.configurations["global"]["daily_rewards"]["daily_rewards_enabled"],
                "execute": self.configurations["global"]["daily_rewards"]["daily_rewards_on_start"],
            },
            self.achievements: {
                "enabled": self.configurations["global"]["achievements"]["achievements_enabled"],
                "execute": self.configurations["global"]["achievements"]["achievements_on_start"],
            },
            self.level_heroes_quick: {
                "enabled": self.configuration["level_heroes_quick_enabled"],
                "execute": self.configuration["level_heroes_quick_on_start"],
            },
            self.level_heroes: {
                "enabled": self.configuration["level_heroes_enabled"],
                "execute": self.configuration["level_heroes_on_start"],
            },
            self.shop_pets: {
                "enabled": self.configuration["shop_pets_purchase_enabled"],
                "execute": self.configuration["shop_pets_purchase_on_start"],
            },
            self.shop_video_chest: {
                "enabled": self.configuration["shop_video_chest_enabled"],
                "execute": self.configuration["shop_video_chest_on_start"],
            },
            self.perks: {
                "enabled": self.configuration["perks_enabled"],
                "execute": self.configuration["perks_on_start"],
            },
        }.items():
            if data["enabled"] and data["execute"]:
                self.logger.debug(
                    "Function: \"%(function)s\" is enabled and set to run on startup, executing now..." % {
                        "function": function.__name__,
                    }
                )
                # Startup functions should still have the run checks
                # executed... Since a manual pause or stop while these
                # are running should be respected by the bot.
                self.run_checks()
                function()

    def handle_timeout(
        self,
        count,
        timeout,
    ):
        """
        Handle function timeouts throughout bot execution.

        The given count is incremented by one and checked to see
        if we have exceeded the specified dynamic timeout.
        """
        self.logger.debug(
            "Handling timeout %(count)s/%(timeout)s..." % {
                "count": count,
                "timeout": timeout,
            }
        )
        count += 1

        if count <= timeout:
            return count

        # Raising a timeout error if the specified count is over
        # our timeout after incrementing it by one.
        raise TimeoutError()

    def _check_game_state_reboot(self):
        """
        Reboot the emulator if possible, raising a game state exception if it is not possible.
        """
        self.logger.info(
            "Unable to handle current game state, attempting to recover and restart application..."
        )
        # Attempting to drag the screen and use the emulator screen
        # directly to travel to the home screen to recover.
        self.drag(
            start=self.configurations["points"]["check_game_state"]["emulator_drag_start"],
            end=self.configurations["points"]["check_game_state"]["emulator_drag_end"],
            pause=self.configurations["parameters"]["check_game_state"]["emulator_drag_pause"],
        )
        self.click(
            point=self.configurations["points"]["check_game_state"]["emulator_home_point"],
            clicks=self.configurations["parameters"]["check_game_state"]["emulator_home_clicks"],
            interval=self.configurations["parameters"]["check_game_state"]["emulator_home_interval"],
            pause=self.configurations["parameters"]["check_game_state"]["emulator_home_pause"],
            offset=self.configurations["parameters"]["check_game_state"]["emulator_home_offset"],
        )
        # The home screen should be active and the icon present on screen.
        found, position, image = self.search(
            image=self.files["application_icon"],
            region=self.configurations["regions"]["check_game_state"]["application_icon_search_area"],
            precision=self.configurations["parameters"]["check_game_state"]["application_icon_search_precision"],
        )
        if found:
            self.logger.info(
                "Application icon found, attempting to open game now..."
            )
            self.click_image(
                image=image,
                position=position,
                pause=self.configurations["parameters"]["check_game_state"]["application_icon_click_pause"],
            )
            return
        else:
            self.logger.info(
                "Unable to find the application icon to handle crash recovery, if your emulator is currently on the "
                "home screen, crash recovery is working as intended, please ensure the tap titans icon is available "
                "and visible."
            )
            self.logger.info(
                "If the application icon is visible and you're still getting this error, please contact support for "
                "additional help."
            )
            self.logger.info(
                "If your game crashed and the home screen wasn't reached through this function, you may need to enable "
                "the \"Virtual button on the bottom\" setting in your emulator, this will enable the option for the bot "
                "to travel to the home screen."
            )
        raise GameStateException()

    def _check_game_state_generic(self):
        """
        Handle the generic game state check.
        """
        timeout_check_game_state_generic_cnt = 0
        timeout_check_game_state_generic_max = self.configurations["parameters"]["check_game_state"]["check_game_state_generic_timeout"]

        while True:
            # Attempting to travel to the main screen
            # in game. This will for sure have our
            # game state icons, and likely some of the
            # travel icons.
            self.travel_to_main_screen()

            try:
                if not self.search(
                        image=[
                            # Exit.
                            self.files["large_exit"],
                            # Misc.
                            self.files["fight_boss_icon"],
                            self.files["leave_boss_icon"],
                            # Travel Tabs.
                            self.files["travel_master_icon"],
                            self.files["travel_heroes_icon"],
                            self.files["travel_equipment_icon"],
                            self.files["travel_pets_icon"],
                            self.files["travel_artifacts_icon"],
                            # Explicit Game State Images.
                            self.files["coin_icon"],
                            self.files["master_icon"],
                            self.files["relics_icon"],
                            self.files["options_icon"],
                        ],
                        precision=self.configurations["parameters"]["check_game_state"]["state_precision"],
                )[0]:
                    timeout_check_game_state_generic_cnt = self.handle_timeout(
                        count=timeout_check_game_state_generic_cnt,
                        timeout=timeout_check_game_state_generic_max,
                    )
                    # Pause slightly in between our checks...
                    # We don't wanna check too quickly.
                    time.sleep(self.configurations["parameters"]["check_game_state"]["check_game_state_pause"])
                else:
                    # Game state is fine, exit with no errors.
                    break
            except TimeoutError:
                # Rebooting whenever the generic checks fail
                # for whatever reason...
                self._check_game_state_reboot()

    def _check_game_state_fairies(self):
        """
        Handle the fairies based game state check.
        """
        timeout_check_game_state_fairies_cnt = 0
        timeout_check_game_state_fairies_max = self.configurations["parameters"]["check_game_state"]["check_game_state_fairies_timeout"]

        try:
            while self.search(
                image=self.files["fairies_no_thanks"],
                region=self.configurations["regions"]["fairies"]["no_thanks_area"],
                precision=self.configurations["parameters"]["fairies"]["no_thanks_precision"],
            )[0]:
                timeout_check_game_state_fairies_cnt = self.handle_timeout(
                    count=timeout_check_game_state_fairies_cnt,
                    timeout=timeout_check_game_state_fairies_max,
                )
                # A fairy is on the screen, since this is a game state check, we're going to
                # actually decline the ad in this case after clicking on the middle of the screen.
                self.click(
                    point=self.configurations["points"]["main_screen"]["top_middle"],
                    clicks=self.configurations["parameters"]["check_game_state"]["fairies_pre_clicks"],
                    interval=self.configurations["parameters"]["check_game_state"]["fairies_pre_interval"],
                    pause=self.configurations["parameters"]["check_game_state"]["fairies_pre_pause"],
                )
                self.find_and_click_image(
                    image=self.files["fairies_no_thanks"],
                    region=self.configurations["regions"]["fairies"]["no_thanks_area"],
                    precision=self.configurations["parameters"]["fairies"]["no_thanks_precision"],
                    pause=self.configurations["parameters"]["fairies"]["no_thanks_pause"],
                )
        except TimeoutError:
            # Reboot if the ad is unable to be closed for some reason
            # in game, the reboot lets us get a fresh start...
            self._check_game_state_reboot()

    def _check_game_state_frozen(self):
        """
        Handle the frozen emulator based game state check.
        """
        # We'll travel to the main screen whenever handling a frozen check,
        # this will have the most movement *if* the game isn't currently frozen.
        self.travel_to_main_screen()

        if not self.last_screenshot:
            self.last_screenshot = self.snapshot(
                region=self.configurations["regions"]["check_game_state"]["frozen_screenshot_area"],
                pause=self.configurations["parameters"]["check_game_state"]["frozen_screenshot_pause"],
            )
        # Comparing the last screenshot available with the current
        # screenshot of the emulator screen.
        self.last_screenshot, duplicates = self.duplicates(
            image=self.last_screenshot,
            region=self.configurations["regions"]["check_game_state"]["frozen_screenshot_area"],
            pause_before_check=self.configurations["parameters"]["check_game_state"]["frozen_screenshot_before_pause"],
        )
        if duplicates:
            self._check_game_state_reboot()

    def check_game_state(self):
        """
        Perform a check on the emulator to determine whether or not the game state is no longer
        in a valid place to derive that the game is still running. The emulator may crash
        during runtime, we can at least attempt to recover.
        """
        self.logger.debug(
            "Checking game state..."
        )

        # A couple of different methods are used to determine a game state...
        # Different odd use cases occur within the game that we check for here
        # and solve through this method.

        # 1. A fairy ad is stuck on the screen...
        #    This one is odd, but can be solved by clicking on the middle
        #    of the screen and then trying to collect the ad.
        self._check_game_state_fairies()
        # 2. The game has frozen completely, we track this by taking a screenshot of the entire
        #    screen when we're in here and comparing it to the last one taken each time, if the
        #    images are the same, we should reboot the game.
        self._check_game_state_frozen()
        # 3. The generic game state check, we try to travel to the main game screen
        #    and then we look for some key images that would mean we are still in the game.
        self._check_game_state_generic()

    def check_license(self):
        """
        Perform a check against the license server to determine whether or not the license
        in question and program being accessed has revoked access in some way.

        Access may be revoked when:

        - License has expired.
        - License has been deleted.
        - License is already online and being retrieved with a different session.
        - Program has had changes made that break the current bot.
        """
        try:
            self.logger.debug(
                "Checking license status..."
            )
            self.license.collect_license_data()
        except TimeoutError:
            self.logger.info(
                "Authentication timeout was reached... Check your internet connection and please try again."
            )
            raise LicenseAuthenticationError()
        except LicenseExpirationError as err:
            self.logger.info(
                "Your license has expired (%(license_expiration)s), please contact support or extend your license "
                "and try again." % {
                    "license_expiration": err,
                }
            )
            raise LicenseAuthenticationError()
        except LicenseIntegrityError:
            self.logger.info(
                "A license integrity error was encountered, you can flush your license "
                "with the tools present in the system tray application. This can happen when "
                "multiple users are trying to use the same license, or when your application is "
                "terminated unexpectedly."
            )
            raise LicenseAuthenticationError()
        except Exception:
            self.logger.info(
                "License or backend configuration has changed and is no longer valid, "
                "a new version or release may be available, if not, please contact support."
            )
            raise LicenseAuthenticationError()

    def snapshot(
        self,
        region=None,
        scale=None,
        pause=0.0
    ):
        """
        Take a snapshot of the current windows screen.

        This helper utility ensures that our local variable is updated, and that
        any required downsizing is also applied everywhere.
        """
        snapshot = self.window.screenshot(
            region=region,
        )

        # Scaling the screenshot by the specified amounts if specified.
        # This may prove useful if we need to take many snapshots in
        # quick succession.
        if scale:
            snapshot.thumbnail((
                snapshot.width * scale,
                snapshot.height * scale,
            ))
        if pause:
            time.sleep(
                pause
            )
        return snapshot

    def process(
        self,
        image=None,
        region=None,
        scale=1,
        threshold=None,
        invert=False,
    ):
        """
        Attempt to process a specified image or screenshot region.
        """
        img = image or self.snapshot(region=region)
        img = numpy.array(img)

        # Scale and desaturate the image, this improves some of the
        # optical character recognition functionality.
        img = cv2.resize(
            src=img,
            dsize=None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
        img = cv2.cvtColor(
            src=img,
            code=cv2.COLOR_BGR2GRAY,
        )

        if threshold:
            # Threshold allows us to blotch out or remove some image data if it is not
            # within a certain rgb bound.
            retr, img = cv2.threshold(
                src=img,
                thresh=190,
                maxval=255,
                type=cv2.THRESH_BINARY,
            )
            contours, hier = cv2.findContours(
                image=img,
                mode=cv2.RETR_EXTERNAL,
                method=cv2.CHAIN_APPROX_SIMPLE,
            )

            # Draw black over any contours smaller than the threshold specified.
            for contour in contours:
                if cv2.contourArea(contour=contour) < threshold:
                    cv2.drawContours(
                        image=img,
                        contours=[contour],
                        contourIdx=0,
                        color=(0,),
                        thickness=-1,
                    )

        if invert:
            img = cv2.bitwise_not(
                src=img,
            )
        return Image.fromarray(
            obj=img,
        )

    def search(
        self,
        image,
        region=None,
        precision=0.8,
        im=None,
    ):
        """
        Search for the specified image(s) on the current window.

        Image may be passed in as a list, or a singular image string.

        A tuple is always returned here, containing the following information
        in the following index locations:

        0: True/False  (Image found).
        1: [X, Y]      (Image position).
        2: image.png   (Image name).
        """
        search_kwargs = {
            "x1": region[0] if region else self.window.x,
            "y1": region[1] if region else self.window.y,
            "x2": region[2] if region else self.window.width,
            "y2": region[3] if region else self.window.height,
            "precision": precision,
            "im": im if region else self.snapshot() if not im else im,
        }

        pos = [-1, -1]
        img = image

        if isinstance(image, list):
            for i in image:
                self.logger.debug(
                    "Searching for image: \"%(image)s\"..." % {
                        "image": i,
                    }
                )
                img = i
                pos = image_search_area(
                    window=self.window,
                    image=img,
                    **search_kwargs
                )
                # If we're looping over a list of images, we need to add a slight
                # interval in between searches, otherwise our emulator may experience
                # some odd flashing issues. This is also a performance boost to prevent
                # quick subsequent calls.
                time.sleep(self.configurations["global"]["search"]["search_list_interval"])

                if pos[0] != -1:
                    break
        else:
            self.logger.debug(
                "Searching for image: \"%(image)s\"..." % {
                    "image": img,
                }
            )
            pos = image_search_area(
                window=self.window,
                image=img,
                **search_kwargs
            )

        found = pos != [-1, -1]

        if found:
            self.logger.debug(
                "Image: \"%(image)s\" found!" % {
                    "image": img,
                }
            )
            if region:
                # If a region was specified, we'll need to take the
                # position gathered, and convert it back to our proper
                # width and height top left point...
                pos = (
                    region[0] + pos[0],
                    region[1] + pos[1],
                )
        return (
            found,
            pos,
            img,
        )

    def duplicates(
        self,
        image,
        region=None,
        pause_before_check=0.0,
        threshold=10,
    ):
        """
        Check that a given snapshot is the exact same as the current snapshot available.
        """
        if not image:
            image = self.snapshot(
                region=region,
            )
            # Force image, false return. The second iteration will now
            # contain our proper image and valid dupe status.
            return image, False
        latest = self.snapshot(
            region=region,
            pause=pause_before_check,
        )
        return latest, compare_images(
            image_one=image,
            image_two=latest,
            threshold=threshold,
        )

    def point_is_color(
        self,
        point,
        color,
    ):
        """
        Check that a specific point is currently a certain color.
        """
        try:
            return self.snapshot().getpixel(
                xy=tuple(point),
            ) == tuple(color)
        except IndexError:
            # image index is out of range.
            # possible when snapshot and tuple contain information
            # that conflicts.
            return False

    def point_is_color_range(
        self,
        point,
        color_range,
    ):
        """
        Check that a specific point is currently within a color range.
        """
        try:
            pixel = self.snapshot().getpixel(
                xy=tuple(point),
            )
        except IndexError:
            # image index is out of range.
            # possible when snapshot and tuple contain information
            # that conflicts.
            return False
        # Additional checks here to determine that pixel falls within
        # the range specified...
        return (
            color_range[0][0] <= pixel[0] <= color_range[0][1]
            and color_range[1][0] <= pixel[1] <= color_range[1][1]
            and color_range[2][0] <= pixel[2] <= color_range[2][1]
        )

    @staticmethod
    def point_is_region(
        point,
        region,
    ):
        """
        Check that a specific point is currently within a region.
        """
        return (
            region[0] <= point[0] <= region[2]
            and region[1] <= point[1] <= region[3]
        )

    @staticmethod
    def _click(
        point,
        window,
        clicks=1,
        interval=0.0,
        button="left",
        offset=5,
        pause=0.001,
    ):
        window.click(
            point=point,
            clicks=clicks,
            interval=interval,
            button=button,
            offset=offset,
            pause=pause,
        )

    def click(
        self,
        point,
        window=None,
        clicks=1,
        interval=0.0,
        button="left",
        offset=5,
        pause=0.001,
        timeout=None,
        timeout_search_while_not=True,
        timeout_search_kwargs=None,
    ):
        """
        Perform a click on the current window.
        """
        _click_kwargs = {
            "point": point,
            "window": window or self.window,
            "clicks": clicks,
            "interval": interval,
            "button": button,
            "offset": offset,
            "pause": pause,
        }
        if not timeout:
            self._click(
                **_click_kwargs,
            )
        else:
            # Timeouts are enabled, looping and try/excepting properly
            # to handle this and pausing proper. This works similarly to the
            # find and click timeouts, but we must use searching here explicitly.
            timeout_cnt = 0

            if timeout_search_while_not:
                while not self.search(
                    **timeout_search_kwargs
                )[0]:
                    self._click(
                        **_click_kwargs,
                    )
                    timeout_cnt = self.handle_timeout(
                        count=timeout_cnt,
                        timeout=timeout,
                    )
            else:
                while self.search(
                    **timeout_search_kwargs
                )[0]:
                    self._click(
                        **_click_kwargs,
                    )
                    timeout_cnt = self.handle_timeout(
                        count=timeout_cnt,
                        timeout=timeout,
                    )

    def _find_and_click_image(
        self,
        image,
        region=None,
        precision=0.8,
        clicks=1,
        interval=0.0,
        button="left",
        offset=5,
        pause=0.0,
        pause_not_found=0.0,
    ):
        found, position, img = self.search(
            image=image,
            region=region,
            precision=precision,
        )
        if found:
            self.click_image(
                image=img,
                position=position,
                clicks=clicks,
                interval=interval,
                button=button,
                offset=offset,
                pause=pause,
            )
        else:
            time.sleep(
                pause_not_found
            )
        # Always returning whether or not we found and most likely,
        # clicked on the image specified.
        return found

    def find_and_click_image(
        self,
        image,
        region=None,
        precision=0.8,
        clicks=1,
        interval=0.0,
        button="left",
        offset=5,
        pause=0.0,
        pause_not_found=0.0,
        timeout=None,
        timeout_search_while_not=True,
        timeout_search_kwargs=None,
    ):
        """
        Attempt to find and click on the specified image on the current window.

        Optional timeout parameters can be applied here to handle while loops to try
        and maximize the efficiency of finding and clicking, note that if a timeout is used,
        the calling functions should be wrapped in a try/except to handle timeouts.
        """
        _find_and_click_kwargs = {
            "image": image,
            "region": region,
            "precision": precision,
            "clicks": 1,
            "interval": interval,
            "button": button,
            "offset": offset,
            "pause": pause,
            "pause_not_found": pause_not_found,
        }
        if not timeout:
            return self._find_and_click_image(
                **_find_and_click_kwargs,
            )
        else:
            # Timeouts are enabled, looping and try/excepting properly
            # to handle this and pausing proper.
            timeout_cnt = 0

            if timeout_search_kwargs:
                if timeout_search_while_not:
                    while not self.search(
                        **timeout_search_kwargs
                    )[0]:
                        self._find_and_click_image(
                            **_find_and_click_kwargs,
                        )
                        timeout_cnt = self.handle_timeout(
                            count=timeout_cnt,
                            timeout=timeout,
                        )
                else:
                    while self.search(
                        **timeout_search_kwargs
                    )[0]:
                        self._find_and_click_image(
                            **_find_and_click_kwargs,
                        )
                        timeout_cnt = self.handle_timeout(
                            count=timeout_cnt,
                            timeout=timeout,
                        )
            else:
                while not self._find_and_click_image(
                    **_find_and_click_kwargs,
                ):
                    timeout_cnt = self.handle_timeout(
                        count=timeout_cnt,
                        timeout=timeout,
                    )

    def _drag(
        self,
        start,
        end,
        button="left",
        pause=0.0,
    ):
        self.window.drag(
            start=start,
            end=end,
            button=button,
            pause=pause,
        )

    def drag(
        self,
        start,
        end,
        button="left",
        pause=0.0,
        timeout=None,
        timeout_search_while_not=True,
        timeout_search_kwargs=None,
    ):
        """
        Perform a drag on the current window.
        """
        _drag_kwargs = {
            "start": start,
            "end": end,
            "button": button,
            "pause": pause,
        }
        if not timeout:
            self._drag(
                **_drag_kwargs,
            )
        else:
            # Timeouts are enabled, looping and try/excepting properly
            # to handle this and pausing proper. This works similarly to the
            # find and click timeouts, but we must use searching here explicitly.
            timeout_cnt = 0

            if timeout_search_while_not:
                while not self.search(
                    **timeout_search_kwargs
                )[0]:
                    self.drag(
                        **_drag_kwargs,
                    )
                    timeout_cnt = self.handle_timeout(
                        count=timeout_cnt,
                        timeout=timeout,
                    )
            else:
                while self.search(
                    **timeout_search_kwargs
                )[0]:
                    self._drag(
                        **_drag_kwargs,
                    )
                    timeout_cnt = self.handle_timeout(
                        count=timeout_cnt,
                        timeout=timeout,
                    )

    def click_image(
        self,
        image,
        position,
        clicks=1,
        interval=0.0,
        button="left",
        offset=5,
        pause=0.0,
    ):
        """
        Perform a click on a particular image on the current window.
        """
        click_image(
            window=self.window,
            image=image,
            position=position,
            button=button,
            clicks=clicks,
            interval=interval,
            offset=offset,
            pause=pause,
        )

    def fight_boss(self):
        """
        Ensure a boss is being fought currently if one is available.
        """
        if not self.search(
            image=[
                self.files["fight_boss_icon"],
                self.files["reconnect_icon"],
            ],
            region=self.configurations["regions"]["fight_boss"]["search_area"],
            precision=self.configurations["parameters"]["fight_boss"]["search_precision"]
        )[0]:
            # Return early, boss fight is already in progress.
            # or, we're almost at another fight.
            self.logger.debug(
                "Boss fight is already initiated or a non boss encounter is active..."
            )
        else:
            try:
                # Handle reconnection before trying to start a normal boss fight...
                # We'll use a longer graceful pause period here for reconnecting.
                if self.find_and_click_image(
                    image=self.files["reconnect_icon"],
                    region=self.configurations["regions"]["fight_boss"]["search_area"],
                    precision=self.configurations["parameters"]["fight_boss"]["search_precision"],
                    pause=self.configurations["parameters"]["fight_boss"]["reconnect_pause"],
                ):
                    self.logger.info(
                        "Attempting to reconnect and initiate boss fight..."
                    )
                    return
                self.logger.info(
                    "Attempting to initiate boss fight..."
                )
                self.find_and_click_image(
                    image=self.files["fight_boss_icon"],
                    region=self.configurations["regions"]["fight_boss"]["search_area"],
                    precision=self.configurations["parameters"]["fight_boss"]["search_precision"],
                    pause=self.configurations["parameters"]["fight_boss"]["search_pause"],
                    pause_not_found=self.configurations["parameters"]["fight_boss"]["search_pause_not_found"],
                    timeout=self.configurations["parameters"]["fight_boss"]["fight_boss_timeout"],
                    timeout_search_while_not=False,
                    timeout_search_kwargs={
                        "image": self.files["fight_boss_icon"],
                        "region": self.configurations["regions"]["fight_boss"]["search_area"],
                        "precision": self.configurations["parameters"]["fight_boss"]["search_precision"],
                    },
                )
            except TimeoutError:
                self.logger.info(
                    "Boss fight could not be initiated, skipping..."
                )
            self.logger.info(
                "Boss fight initiated..."
            )

    def leave_boss(self):
        """
        Ensure a boss is not being fought currently.
        """
        if self.search(
            image=self.files["fight_boss_icon"],
            region=self.configurations["regions"]["fight_boss"]["search_area"],
            precision=self.configurations["parameters"]["fight_boss"]["search_precision"]
        )[0]:
            # Return early, a boss fight is not already in progress,
            # or, we're almost at another boss fight.
            self.logger.info(
                "Boss fight is already not active..."
            )
        else:
            try:
                self.find_and_click_image(
                    image=self.files["leave_boss_icon"],
                    region=self.configurations["regions"]["leave_boss"]["search_area"],
                    precision=self.configurations["parameters"]["leave_boss"]["search_precision"],
                    pause=self.configurations["parameters"]["leave_boss"]["search_pause"],
                    pause_not_found=self.configurations["parameters"]["leave_boss"]["search_pause_not_found"],
                    timeout=self.configurations["parameters"]["leave_boss"]["leave_boss_timeout"],
                    timeout_search_kwargs={
                        "image": self.files["fight_boss_icon"],
                        "region": self.configurations["regions"]["fight_boss"]["search_area"],
                        "precision": self.configurations["parameters"]["fight_boss"]["search_precision"],
                    },
                )
            except TimeoutError:
                self.logger.info(
                    "Boss fight is not currently in progress, continuing..."
                )

    def fairies(self):
        """
        Check for any fairy prompts on screen, and deal with them accordingly.
        """
        # Attempt to just collect the ad rewards...
        # If the "collect" text is present, then the
        # user must have VIP status or a season pass.
        collected = self.find_and_click_image(
            image=self.files["fairies_collect"],
            region=self.configurations["regions"]["fairies"]["collect_area"],
            precision=self.configurations["parameters"]["fairies"]["collect_precision"],
            pause=self.configurations["parameters"]["fairies"]["collect_pause"],
        )
        if collected:
            self.logger.info(
                "Fairy ad has been collected..."
            )
        if not collected:
            # Is there even ad ad on the screen?
            found, no_thanks_pos, image = self.search(
                image=self.files["fairies_no_thanks"],
                region=self.configurations["regions"]["fairies"]["no_thanks_area"],
                precision=self.configurations["parameters"]["fairies"]["no_thanks_precision"],
            )
            if found:
                # No ad can be collected without watching an ad.
                # We can loop and wait for a disabled ad to be blocked.
                # (This is done through ad blocking, unrelated to our code here).
                if self.ad_blocking_enabled_func():
                    self.logger.info(
                        "Attempting to collect ad rewards through ad blocking..."
                    )
                    try:
                        self.find_and_click_image(
                            image=self.files["fairies_watch"],
                            region=self.configurations["regions"]["fairies"]["ad_block_collect_area"],
                            precision=self.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                            pause=self.configurations["parameters"]["fairies"]["ad_block_pause"],
                            pause_not_found=self.configurations["parameters"]["fairies"]["ad_block_pause_not_found"],
                            timeout=self.configurations["parameters"]["fairies"]["ad_block_timeout"],
                            timeout_search_kwargs={
                                "image": self.files["fairies_collect"],
                                "region": self.configurations["regions"]["fairies"]["ad_block_collect_area"],
                                "precision": self.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                            },
                        )
                    except TimeoutError:
                        self.logger.info(
                            "Unable to handle fairy ad through ad blocking, skipping..."
                        )
                        self.click_image(
                            image=image,
                            position=no_thanks_pos,
                            pause=self.configurations["parameters"]["fairies"]["no_thanks_pause"],
                        )
                        return
                    # At this point, the collect options is available
                    # to the user, attempt to collect the fairy reward.
                    self.find_and_click_image(
                        image=self.files["fairies_collect"],
                        region=self.configurations["regions"]["fairies"]["ad_block_collect_area"],
                        precision=self.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                        pause=self.configurations["parameters"]["fairies"]["ad_block_pause"],
                        timeout=self.configurations["parameters"]["fairies"]["ad_block_timeout"],
                    )
                    self.logger.info(
                        "Fairy ad has been collected through ad blocking..."
                    )
                else:
                    # Ads can not be collected for the user.
                    # Let's just press our no thanks button.
                    self.logger.info(
                        "Fairy ad could not be collected, skipping..."
                    )
                    self.click_image(
                        image=image,
                        position=no_thanks_pos,
                        pause=self.configurations["parameters"]["fairies"]["no_thanks_pause"],
                    )

    def daily_rewards(self):
        """
        Check to see if any daily rewards are available and collect them.
        """
        if self.find_and_click_image(
            image=self.files["daily_rewards_icon"],
            region=self.configurations["regions"]["daily_rewards"]["search_area"],
            precision=self.configurations["parameters"]["daily_rewards"]["search_precision"],
            pause=self.configurations["parameters"]["daily_rewards"]["search_pause"],
        ):
            self.logger.info(
                "Daily rewards are available, collecting now..."
            )
            if self.find_and_click_image(
                image=self.files["daily_rewards_collect"],
                region=self.configurations["regions"]["daily_rewards"]["collect_area"],
                precision=self.configurations["parameters"]["daily_rewards"]["collect_precision"],
                pause=self.configurations["parameters"]["daily_rewards"]["collect_pause"],
            ):
                # Successfully grabbed daily rewards, we'll perform some simple clicks
                # on the screen to skip some of the reward prompts.
                self.click(
                    point=self.configurations["points"]["main_screen"]["top_middle"],
                    clicks=self.configurations["parameters"]["daily_rewards"]["post_collect_clicks"],
                    interval=self.configurations["parameters"]["daily_rewards"]["post_collect_interval"],
                    pause=self.configurations["parameters"]["daily_rewards"]["post_collect_pause"],
                )

    def eggs(self):
        """
        Check if any eggs are available and collect them.
        """
        if self.find_and_click_image(
            image=self.files["eggs_icon"],
            region=self.configurations["regions"]["eggs"]["search_area"],
            precision=self.configurations["parameters"]["eggs"]["search_precision"],
            pause=self.configurations["parameters"]["eggs"]["search_pause"],
        ):
            self.logger.info(
                "Eggs are available, collecting now..."
            )
            # Eggs are collected automatically, we'll just need to perform
            # some taps on the screen to speed up the process.
            self.click(
                point=self.configurations["points"]["main_screen"]["middle"],
                clicks=self.configurations["parameters"]["eggs"]["post_collect_clicks"],
                interval=self.configurations["parameters"]["eggs"]["post_collect_interval"],
                pause=self.configurations["parameters"]["eggs"]["post_collect_pause"],
            )

    def inbox(self):
        """
        Check if any inbox notifications are available, getting rid of the prompt if it's present.
        """
        if self.find_and_click_image(
            image=self.files["inbox_icon"],
            region=self.configurations["regions"]["inbox"]["search_area"],
            precision=self.configurations["parameters"]["inbox"]["search_precision"],
            pause=self.configurations["parameters"]["inbox"]["search_pause"],
        ):
            self.logger.info(
                "Inbox is present, attempting to collect any gifts/rewards..."
            )
            self.click(
                point=self.configurations["points"]["inbox"]["clan_header"],
                pause=self.configurations["parameters"]["inbox"]["click_pause"],
            )
            if self.find_and_click_image(
                image=self.files["inbox_collect_all"],
                region=self.configurations["regions"]["inbox"]["collect_all_area"],
                precision=self.configurations["parameters"]["inbox"]["collect_all_precision"],
                pause=self.configurations["parameters"]["inbox"]["collect_all_pause"],
            ):
                # Also clicking on the screen in the middle a couple
                # of times, ensuring rewards are collected...
                self.click(
                    point=self.configurations["points"]["main_screen"]["top_middle"],
                    clicks=self.configurations["parameters"]["inbox"]["collect_all_wait_clicks"],
                    interval=self.configurations["parameters"]["inbox"]["collect_all_wait_interval"],
                    pause=self.configurations["parameters"]["inbox"]["collect_all_wait_pause"],
                )
                self.logger.info(
                    "Inbox rewards collected successfully..."
                )
            self.find_and_click_image(
                image=self.files["large_exit"],
                region=self.configurations["regions"]["inbox"]["exit_area"],
                precision=self.configurations["parameters"]["inbox"]["exit_precision"],
                pause=self.configurations["parameters"]["inbox"]["exit_pause"],
            )

    def achievements(self):
        """
        Check if any achievements are available to collect.
        """
        self.travel_to_master()
        self.logger.info(
            "Checking if achievements are available to collect..."
        )
        # Do things slightly different here, if the achievements icon
        # is not on the screen, it means there's likely either the "new" or "X"
        # number of available achievements to collect.
        if not self.search(
            image=self.files["achievements_icon"],
            region=self.configurations["regions"]["achievements"]["search_area"],
            precision=self.configurations["parameters"]["achievements"]["search_precision"],
        )[0]:
            self.click(
                point=self.configurations["points"]["achievements"]["achievements_icon"],
                pause=self.configurations["parameters"]["achievements"]["icon_pause"],
            )
            # Also ensure the daily tab is opened.
            self.find_and_click_image(
                image=self.files["achievements_daily_header"],
                region=self.configurations["regions"]["achievements"]["daily_header_area"],
                precision=self.configurations["parameters"]["achievements"]["daily_header_precision"],
                pause=self.configurations["parameters"]["achievements"]["daily_header_pause"],
            )
            while True:
                found, position, image = self.search(
                    image=self.files["achievements_collect"],
                    region=self.configurations["regions"]["achievements"]["collect_area"],
                    precision=self.configurations["parameters"]["achievements"]["collect_precision"],
                )
                if found:
                    self.logger.info(
                        "Collecting achievement..."
                    )
                    self.click_image(
                        image=image,
                        position=position,
                        pause=self.configurations["parameters"]["achievements"]["collect_pause"],
                    )
                else:
                    self.find_and_click_image(
                        image=self.files["large_exit"],
                        region=self.configurations["regions"]["achievements"]["exit_area"],
                        precision=self.configurations["parameters"]["achievements"]["exit_precision"],
                        pause=self.configurations["parameters"]["achievements"]["exit_pause"],
                    )
                    break

    def level_master(self):
        """
        Level the sword master in game.
        """
        if not self.master_levelled:
            self.travel_to_master()
            self.logger.info(
                "Attempting to level the sword master in game..."
            )
            self.click(
                point=self.configurations["points"]["level_master"]["level"],
                clicks=self.configurations["parameters"]["level_master"]["level_clicks"],
                interval=self.configurations["parameters"]["level_master"]["level_interval"],
            )
            if self.configuration["level_master_once_per_prestige"]:
                self.master_levelled = True

    def level_skills(self):
        """
        Level all skills in game.
        """
        self.travel_to_master(collapsed=False)
        self.logger.info(
            "Attempting to level all skills in game..."
        )
        for skill, region, point, max_point, clicks in zip(
            self.configurations["global"]["skills"]["skills"],
            self.configurations["regions"]["level_skills"]["skill_regions"],
            self.configurations["points"]["level_skills"]["skill_points"],
            self.configurations["points"]["level_skills"]["max_points"],
            [
                level for level in [
                    self.configuration["%(skill)s_level_amount" % {
                        "skill": skill,
                    }] for skill in self.configurations["global"]["skills"]["skills"]
                ]
            ],
        ):
            if clicks != "disable" and not self.search(
                image=[
                    self.files["level_skills_max_level"],
                    self.files["level_skills_cancel_active_skill"],
                ],
                region=region,
                precision=self.configurations["parameters"]["level_skills"]["max_level_precision"],
            )[0]:
                # Actually level the skill in question.
                # Regardless of max or amount specification.
                self.logger.info(
                    "Levelling %(skill)s now..." % {
                        "skill": skill,
                    }
                )
                if clicks != "max":
                    # Just level the skill the specified amount of clicks.
                    # 1-35 most likely if frontend enforces values proper.
                    self.click(
                        point=point,
                        clicks=int(clicks),
                        interval=self.configurations["parameters"]["level_skills"]["level_clicks_interval"],
                        pause=self.configurations["parameters"]["level_skills"]["level_clicks_pause"],
                    )
                else:
                    # Attempt to max the skill out using the "level X"
                    # option that pops up when a user levels a skill.
                    timeout_level_max_cnt = 0
                    timeout_level_max_max = self.configurations["parameters"]["level_skills"]["timeout_level_max"]

                    try:
                        while not self.search(
                            image=[
                                self.files["level_skills_max_level"],
                                self.files["level_skills_cancel_active_skill"],
                            ],
                            region=region,
                            precision=self.configurations["parameters"]["level_skills"]["max_level_precision"],
                        )[0]:
                            self.click(
                                point=point,
                                pause=self.configurations["parameters"]["level_skills"]["level_max_click_pause"]
                            )
                            if self.point_is_color_range(
                                point=max_point,
                                color_range=self.configurations["colors"]["level_skills"]["max_level_range"],
                            ):
                                self.click(
                                    point=max_point,
                                    pause=self.configurations["parameters"]["level_skills"]["level_max_pause"],
                                )
                            timeout_level_max_cnt = self.handle_timeout(
                                count=timeout_level_max_cnt,
                                timeout=timeout_level_max_max,
                            )
                    except TimeoutError:
                        self.logger.info(
                            "%(skill)s could not be maxed, skipping..." % {
                                "skill": skill,
                            }
                        )

    def activate_skills(self):
        """
        Activate the enabled skills in game.
        """
        self.travel_to_main_screen()
        self.logger.info(
            "Activating skills in game..."
        )
        for enabled in [
            skill for skill, enabled in [
                (s, self.configuration["%(skill)s_activate" % {
                    "skill": s,
                }]) for s in self.configurations["global"]["skills"]["skills"]
            ] if enabled
        ]:
            self.logger.info(
                "Activating %(skill)s now..." % {
                    "skill": enabled,
                }
            )
            self.click(
                point=self.configurations["points"]["activate_skills"]["skill_points"][enabled],
                pause=self.configurations["parameters"]["activate_skills"]["activate_pause"],
            )

    def _level_heroes_ensure_max(self):
        """
        Ensure the "BUY Max" option is selected for the hero levelling process.
        """
        if not self.search(
            image=self.files["heroes_level_buy_max"],
            region=self.configurations["regions"]["level_heroes"]["buy_max_area"],
            precision=self.configurations["parameters"]["level_heroes"]["buy_max_precision"],
        )[0]:
            # The buy max option isn't currently set, we'll set it and then
            # continue...
            self.logger.info(
                "Heroes \"BUY Max\" option not found, attempting to set now..."
            )
            try:
                self.click(
                    point=self.configurations["points"]["level_heroes"]["buy_max"],
                    pause=self.configurations["parameters"]["level_heroes"]["buy_max_pause"],
                    timeout=self.configurations["parameters"]["level_heroes"]["timeout_buy_max"],
                    timeout_search_kwargs={
                        "image": self.files["heroes_level_buy_max_open"],
                        "region": self.configurations["regions"]["level_heroes"]["buy_max_open_area"],
                        "precision": self.configurations["parameters"]["level_heroes"]["buy_max_open_precision"],
                    },
                )
                # At this point, we should be able to perform a simple find and click
                # on the buy max button, we'll pause after than and then our loop should
                # end above.
                self.find_and_click_image(
                    image=self.files["heroes_level_buy_max_open"],
                    region=self.configurations["regions"]["level_heroes"]["buy_max_open_area"],
                    precision=self.configurations["parameters"]["level_heroes"]["buy_max_open_precision"],
                    pause=self.configurations["parameters"]["level_heroes"]["buy_max_open_pause"],
                    timeout=self.configurations["parameters"]["level_heroes"]["timeout_buy_max_open"],
                    timeout_search_kwargs={
                        "image": self.files["heroes_level_buy_max"],
                        "region": self.configurations["regions"]["level_heroes"]["buy_max_area"],
                        "precision": self.configurations["parameters"]["level_heroes"]["buy_max_precision"],
                    },
                )
            except TimeoutError:
                self.logger.info(
                    "Unable to set heroes levelling to \"BUY Max\", skipping..."
                )

    def _level_heroes_on_screen(self):
        """
        Level all current heroes on the game screen.
        """
        # Make sure we're still on the heroes screen...
        self.travel_to_heroes(scroll=False, collapsed=False)
        self.collapse_prompts()
        self.logger.info(
            "Levelling heroes on screen now..."
        )

        clicks = self.configurations["parameters"]["level_heroes"]["hero_level_clicks"] if (
            not self.configuration["level_heroes_masteries_unlocked"]
        ) else 1

        for point in self.configurations["points"]["level_heroes"]["possible_hero_level_points"]:
            # Looping through possible clicks so we can check if we should level, if not, we can early
            # break and move to the next point.
            for i in range(clicks):
                # Only ever actually clicking on the hero if we know for sure a "level" is available.
                # We do this by checking the color of the point.
                if not self.point_is_color_range(
                    point=(
                        point[0] + self.configurations["parameters"]["level_heroes"]["check_possible_point_x_padding"],
                        point[1],
                    ),
                    color_range=self.configurations["colors"]["level_heroes"]["level_heroes_click_range"],
                ):
                    self.click(
                        point=point,
                        interval=self.configurations["parameters"]["level_heroes"]["hero_level_clicks_interval"],
                        pause=self.configurations["parameters"]["level_heroes"]["hero_level_clicks_pause"],
                    )
                else:
                    break
        # Perform an additional sleep once levelling is totally
        # complete, this helps avoid issues with clicks causing
        # a hero detail sheet to pop up.
        time.sleep(self.configurations["parameters"]["level_heroes"]["hero_level_post_pause"])

    def _check_headgear(self):
        """
        Check the headgear in game currently, performing a swap if one is ready to take place.
        """
        while self.point_is_color_range(
            point=self.configurations["points"]["headgear_swap"]["skill_upgrade_wait"],
            color_range=self.configurations["colors"]["headgear_swap"]["skill_upgrade_wait_range"]
        ):
            # Sleep slightly before checking again that the skill
            # notification has disappeared.
            time.sleep(self.configurations["parameters"]["headgear_swap"]["headgear_swap_wait_pause"])

        check_index = self.configuration["headgear_swap_check_hero_index"]

        for typ in [
            "ranged", "melee", "spell",
        ]:
            if self.search(
                image=self.files["%(typ)s_icon" % {"typ": typ}],
                region=self.configurations["regions"]["headgear_swap"]["type_icon_areas"][check_index],
                precision=self.configurations["parameters"]["headgear_swap"]["type_icon_precision"],
            )[0]:
                if self.powerful_hero == typ:
                    # Powerful hero is the same as before, we will not actually
                    # swap any gear yet.
                    self.logger.info(
                        "%(typ)s hero is still the most powerful hero, skipping headgear swap..." % {
                            "typ": typ.capitalize(),
                        }
                    )
                else:
                    self.logger.info(
                        "%(typ)s hero is the most powerful hero, attempting to swap headgear..." % {
                            "typ": typ.capitalize(),
                        }
                    )
                    self.powerful_hero = typ
                    self.headgear_swap()

    def level_heroes_quick(self):
        """
        Level the heroes in game quickly.
        """
        self.travel_to_heroes(collapsed=False)
        self.logger.info(
            "Attempting to level the heroes in game quickly..."
        )

        self._level_heroes_ensure_max()

        # Loop through the specified amount of level loops for quick
        # levelling...
        for i in range(self.configuration["level_heroes_quick_loops"]):
            self.logger.info(
                "Levelling heroes quickly..."
            )
            self._level_heroes_on_screen()
        # If headgear swapping is turned on, we always check once heroes
        # are done being levelled quickly.
        if self.configuration["headgear_swap_enabled"]:
            self._check_headgear()

    def level_heroes(self):
        """
        Level the heroes in game.
        """
        def drag_heroes_panel(
            top=True,
            callback=None,
            stop_on_max=False
        ):
            """
            Drag the heroes panel to the top or bottom. A callback can be passed in and will be executed when a drag is complete.
            """
            img, dupe, max_found = (
                None,
                False,
                False,
            )
            timeout_heroes_dupe_cnt = 0
            timeout_heroes_dupe_max = self.configurations["parameters"]["level_heroes"]["timeout_heroes_dupe"]

            while not dupe:
                try:
                    if callback:
                        callback()
                    self.drag(
                        start=self.configurations["points"]["travel"]["scroll"]["drag_top" if top else "drag_bottom"],
                        end=self.configurations["points"]["travel"]["scroll"]["drag_bottom" if top else "drag_top"],
                        pause=self.configurations["parameters"]["travel"]["drag_pause"],
                    )
                    if stop_on_max and self.search(
                        image=self.files["heroes_max_level"],
                        region=self.configurations["regions"]["level_heroes"]["max_level_search_area"],
                        precision=self.configurations["parameters"]["level_heroes"]["max_level_search_precision"],
                    )[0]:
                        # Breaking early since if we stop early, we can skip
                        # directly to the callbacks (if passed in).
                        break
                    img, dupe = self.duplicates(
                        image=img,
                        region=self.configurations["regions"]["travel"]["duplicate_area"],
                    )
                    timeout_heroes_dupe_cnt = self.handle_timeout(
                        count=timeout_heroes_dupe_cnt,
                        timeout=timeout_heroes_dupe_max,
                    )
                except TimeoutError:
                    self.logger.info(
                        "Max level hero could not be found, ending check now..."
                    )
                    break

        self.travel_to_heroes(collapsed=False)
        self.logger.info(
            "Attempting to level the heroes in game..."
        )

        self._level_heroes_ensure_max()

        found, position, image = self.search(
            image=self.files["heroes_max_level"],
            region=self.configurations["regions"]["level_heroes"]["max_level_search_area"],
            precision=self.configurations["parameters"]["level_heroes"]["max_level_search_precision"],
        )
        if found:
            self.logger.info(
                "Max levelled hero found, levelling first set of heroes only..."
            )
            self._level_heroes_on_screen()
        else:
            # Otherwise, we'll scroll and look for a max level hero,
            # or we will find a duplicate (bottom of tab) and just begin
            # levelling heroes.
            drag_heroes_panel(
                top=False,
                stop_on_max=True,
            )
            drag_heroes_panel(
                callback=self._level_heroes_on_screen,
            )
        # If headgear swapping is turned on, we always check once heroes
        # are done being levelled.
        if self.configuration["headgear_swap_enabled"]:
            self._check_headgear()

    def _shop_ensure_prompts_closed(self):
        """
        Ensure any prompts or panels open in the shop panel are closed.

        This is important so we don't have any bundles open for extended time.
        """
        self.find_and_click_image(
            image=self.files["small_shop_exit"],
            region=self.configurations["regions"]["shop"]["small_shop_exit_area"],
            precision=self.configurations["parameters"]["shop"]["small_shop_exit_precision"],
            pause=self.configurations["parameters"]["shop"]["small_shop_exit_pause"],
        )

    def shop_pets(self):
        """
        Perform all shop function related to purchasing pets in game.
        """
        self.travel_to_shop(
            stop_image_kwargs={
                "image": self.files["shop_daily_deals_header"],
                "precision": self.configurations["parameters"]["shop_pets"]["daily_deals_precision"],
            },
        )
        self.logger.info(
            "Attempting to purchase pets from the shop..."
        )

        timeout_shop_pets_search_cnt = 0
        timeout_shop_pets_search_max = self.configurations["parameters"]["shop_pets"]["timeout_search_daily_deals"]

        try:
            while not (
                self.search(
                    image=self.files["shop_daily_deals_header"],
                    precision=self.configurations["parameters"]["shop_pets"]["daily_deals_precision"],
                )[0] and
                self.search(
                    image=self.files["shop_chests_header"],
                    precision=self.configurations["parameters"]["shop_pets"]["chests_precision"],
                )[0]
            ):
                # Looping until both the daily deals and chests headers
                # are present, since at that point, daily deals are on the screen
                # to search through.
                timeout_shop_pets_search_cnt = self.handle_timeout(
                    count=timeout_shop_pets_search_cnt,
                    timeout=timeout_shop_pets_search_max,
                )
                self.drag(
                    start=self.configurations["points"]["shop"]["scroll"]["slow_drag_bottom"],
                    end=self.configurations["points"]["shop"]["scroll"]["slow_drag_top"],
                    pause=self.configurations["parameters"]["shop"]["slow_drag_pause"],
                )
                self._shop_ensure_prompts_closed()
        except TimeoutError:
            self.logger.info(
                "Unable to travel to the daily deals panel in the shop, skipping..."
            )
            # Always travel to the main screen following execution
            # so we don't linger on this panel.
            self.travel_to_main_screen()
            return

        # At this point we can be sure that the daily deals
        # panel is open and can be parsed.
        for pet in self.shop_pets_purchase_pets:
            found, position, image = self.search(
                image=self.files["pet_%(pet)s" % {"pet": pet}],
                precision=self.configurations["parameters"]["shop_pets"]["pet_precision"],
            )
            if found:
                self.logger.info(
                    "Pet: \"%(pet)s\" found on screen, checking if purchase is possible..." % {
                        "pet": pet,
                    }
                )
                # Click on the pet, if it hasn't already been purchased, the correct header should
                # be present on the screen that we can use to purchase.
                self.click(
                    point=position,
                    pause=self.configurations["parameters"]["shop_pets"]["check_purchase_pause"],
                )
                # Check for the purchase header now...
                if self.search(
                    image=self.files["shop_pet_header"],
                    region=self.configurations["regions"]["shop_pets"]["shop_pet_header_area"],
                    precision=self.configurations["parameters"]["shop_pets"]["shop_pet_header_precision"],
                )[0]:
                    self.logger.info(
                        "Pet: \"%(pet)s\" can be purchased, purchasing now..." % {
                            "pet": pet,
                        }
                    )
                    self.click(
                        point=self.configurations["points"]["shop_pets"]["purchase_pet"],
                        pause=self.configurations["parameters"]["shop_pets"]["purchase_pet_pause"],
                    )
                    # After buying the pet, we will click on the middle of the screen
                    # TWICE, we don't want to accidentally click on anything in the shop.
                    self.click(
                        point=self.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.configurations["parameters"]["shop"]["post_purchase_clicks"],
                        interval=self.configurations["parameters"]["shop"]["post_purchase_interval"],
                        pause=self.configurations["parameters"]["shop"]["post_purchase_pause"],
                    )
                else:
                    self.logger.info(
                        "Pet: \"%(pet)s\" can not be purchased, it's likely already been bought, skipping..." % {
                            "pet": pet,
                        }
                    )
                    self._shop_ensure_prompts_closed()
        self._shop_ensure_prompts_closed()
        # Always travel to the main screen following execution
        # so we don't linger on this panel.
        self.travel_to_main_screen()

    def shop_video_chest(self):
        """
        Perform all shop functionality related to collecting the video chest in game.
        """
        self.travel_to_shop(
            stop_image_kwargs={
                "image": self.files["shop_watch_video_header"],
                "precision": self.configurations["parameters"]["shop_video_chest"]["watch_video_precision"],
            },
        )
        self.logger.info(
            "Attempting to collect the video chest from the shop..."
        )

        timeout_shop_video_chest_cnt = 0
        timeout_shop_video_chest_max = self.configurations["parameters"]["shop_video_chest"]["timeout_search_watch_video"]

        try:
            while not (
                self.search(
                    image=self.files["shop_watch_video_header"],
                    precision=self.configurations["parameters"]["shop_video_chest"]["watch_video_precision"],
                )[0] and
                self.search(
                    image=self.files["shop_diamonds_header"],
                    precision=self.configurations["parameters"]["shop_video_chest"]["diamonds_precision"],
                )[0]
            ):
                # Looping until both the watch video header and diamonds header
                # are present, since at that point, video chest is on the screen to search.
                timeout_shop_video_chest_cnt = self.handle_timeout(
                    count=timeout_shop_video_chest_cnt,
                    timeout=timeout_shop_video_chest_max,
                )
                self.drag(
                    start=self.configurations["points"]["shop"]["scroll"]["slow_drag_bottom"],
                    end=self.configurations["points"]["shop"]["scroll"]["slow_drag_top"],
                    pause=self.configurations["parameters"]["shop"]["slow_drag_pause"],
                )
                self._shop_ensure_prompts_closed()
        except TimeoutError:
            self.logger.info(
                "Unable to travel to the video chest in the shop, skipping..."
            )
            # Always travel to the main screen following execution
            # so we don't linger on this panel.
            self.travel_to_main_screen()
            return

        # At this point we can be sure that the video chest panel is open
        # and can be parsed.
        collect_found, collect_position, collect_image = self.search(
            image=self.files["shop_collect_video_icon"],
            precision=self.configurations["parameters"]["shop_video_chest"]["collect_video_icon_precision"],
        )
        if collect_found:
            # Collect is available, just collect and finish.
            self.logger.info(
                "Video chest collection is available, collecting now..."
            )
            self.click(
                point=collect_position,
                pause=self.configurations["parameters"]["shop_video_chest"]["collect_pause"],
            )
            # Collection happens here.
            self.click(
                point=self.configurations["points"]["shop_video_chest"]["collect_point"],
                pause=self.configurations["parameters"]["shop_video_chest"]["collect_point_pause"],
            )
            # After collecting the chest, we will click on the middle of the screen
            # TWICE, we don't want to accidentally click on anything in the shop.
            self.click(
                point=self.configurations["points"]["main_screen"]["top_middle"],
                clicks=self.configurations["parameters"]["shop"]["post_purchase_clicks"],
                interval=self.configurations["parameters"]["shop"]["post_purchase_interval"],
                pause=self.configurations["parameters"]["shop"]["post_purchase_pause"],
            )

        watch_found, watch_position, watch_image = self.search(
            image=self.files["shop_watch_video_icon"],
            precision=self.configurations["parameters"]["shop_video_chest"]["watch_video_icon_precision"],
        )
        if watch_found:
            if self.ad_blocking_enabled_func():
                # Watch is available, we'll only do this if ad blocking is enabled.
                self.logger.info(
                    "Video chest watch is available, collecting now..."
                )
                self.click(
                    point=watch_position,
                    pause=self.configurations["parameters"]["shop_video_chest"]["watch_pause"],
                )
                while self.search(
                    image=self.files["shop_video_chest_header"],
                    region=self.configurations["regions"]["shop_video_chest"]["video_chest_header_area"],
                    precision=self.configurations["parameters"]["shop_video_chest"]["video_chest_header_precision"],
                )[0]:
                    # Looping until the header has disappeared so we properly support the ad blocking
                    # video chest watch.
                    self.click(
                        point=self.configurations["points"]["shop_video_chest"]["collect_point"],
                        pause=self.configurations["parameters"]["shop_video_chest"]["collect_pause"],
                    )
                # After collecting the chest, we will click on the middle of the screen
                # TWICE, we don't want to accidentally click on anything in the shop.
                self.click(
                    point=self.configurations["points"]["main_screen"]["top_middle"],
                    clicks=self.configurations["parameters"]["shop"]["post_purchase_clicks"],
                    interval=self.configurations["parameters"]["shop"]["post_purchase_interval"],
                    pause=self.configurations["parameters"]["shop"]["post_purchase_pause"],
                )
            else:
                self.logger.info(
                    "Video chest watch is available but ad blocking is disabled, skipping..."
                )
        if not collect_found and not watch_found:
            self.logger.info(
                "No video chest is available to collect, skipping..."
            )
        self._shop_ensure_prompts_closed()
        # Always travel to the main screen following execution
        # so we don't linger on this panel.
        self.travel_to_main_screen()

    def perks(self):
        """
        Perform all perk related functionality in game, using/purchasing perks if enabled.
        """
        self.collapse()
        # The perk suffix is used to ensure tournament perks are used
        # if enabled and a tournament is running, suffix is applied
        # at the end of the perks list below.
        perk_suffix = ""

        if (
            self.configuration["perks_use_separate_in_tournament"]
            and self.point_is_color_range(
                point=self.configurations["points"]["tournaments"]["tournaments_status"],
                color_range=self.configurations["colors"]["tournaments"]["tournaments_in_progress_range"],
            )
        ):
            # A tournament is in progress and separate perks are enabled,
            # we'll use whatever perks are enabled for a tournament.
            self.logger.info(
                "Tournament perks are enabled, those will be used instead..."
            )
            perk_suffix = "_tournament"

        self.travel_to_master(collapsed=False)
        self.logger.info(
            "Using perks in game..."
        )
        # Travel to the bottom (ish) of the master tab, we'll scroll until
        # we've found the correct perk, since that's the last one available.
        try:
            self.drag(
                start=self.configurations["points"]["travel"]["scroll"]["drag_bottom"],
                end=self.configurations["points"]["travel"]["scroll"]["drag_top"],
                pause=self.configurations["parameters"]["travel"]["drag_pause"],
                timeout=self.configurations["parameters"]["perks"]["icons_timeout"],
                timeout_search_kwargs={
                    "image": self.files["perks_clan_crate"] if not self.configuration["abyssal"] else self.files["perks_doom"],
                    "region": self.configurations["regions"]["perks"]["icons_area"],
                    "precision": self.configurations["parameters"]["perks"]["icons_precision"],
                },
            )
        except TimeoutError:
            self.logger.info(
                "Unable to find the \"%(search_perk)s\" perk in game, skipping perk functionality..." % {
                    "search_perk": "clan_crate" if not self.configuration["abyssal"] else "doom",
                }
            )
            return

        # We should be able to see all (or most) of the perks in game, clan crate is on the screen.
        # We'll search for each enabled perk, if it isn't found, we'll scroll up a bit.
        # Note: Reversing our list of enabled perks (bottom to top).
        for perk in [
            perk for perk, enabled in [
                ("clan_crate", self.configuration["perks_enable_clan_crate%(suffix)s" % {"suffix": perk_suffix}]),
                ("doom", self.configuration["perks_enable_doom%(suffix)s" % {"suffix": perk_suffix}]),
                ("mana_potion", self.configuration["perks_enable_mana_potion%(suffix)s" % {"suffix": perk_suffix}]),
                ("make_it_rain", self.configuration["perks_enable_make_it_rain%(suffix)s" % {"suffix": perk_suffix}]),
                ("adrenaline_rush", self.configuration["perks_enable_adrenaline_rush%(suffix)s" % {"suffix": perk_suffix}]),
                ("power_of_swiping", self.configuration["perks_enable_power_of_swiping%(suffix)s" % {"suffix": perk_suffix}]),
                ("mega_boost", self.configuration["perks_enable_mega_boost%(suffix)s" % {"suffix": perk_suffix}]),
            ] if enabled
        ]:
            self.logger.info(
                "Attempting to use \"%(perk)s\" perk..." % {
                    "perk": perk,
                }
            )
            timeout_perks_enabled_perk_cnt = 0
            timeout_perks_enabled_perk_max = self.configurations["parameters"]["perks"]["enabled_perk_timeout"]

            try:
                while not self.search(
                    image=self.files["perks_%(perk)s" % {"perk": perk}],
                    region=self.configurations["regions"]["perks"]["icons_area"],
                    precision=self.configurations["parameters"]["perks"]["icons_precision"],
                )[0]:
                    # Dragging up until the enabled perk
                    # is found.
                    self.drag(
                        start=self.configurations["points"]["travel"]["scroll"]["drag_top"],
                        end=self.configurations["points"]["travel"]["scroll"]["drag_bottom"],
                        pause=self.configurations["parameters"]["travel"]["drag_pause"],
                    )
                    timeout_perks_enabled_perk_cnt = self.handle_timeout(
                        count=timeout_perks_enabled_perk_cnt,
                        timeout=timeout_perks_enabled_perk_max,
                    )
                # Icon is found, we'll get the position so we can add proper
                # padding and attempt to use the perk.
                _, position, image = self.search(
                    image=self.files["perks_%(perk)s" % {"perk": perk}],
                    region=self.configurations["regions"]["perks"]["icons_area"],
                    precision=self.configurations["parameters"]["perks"]["icons_precision"],
                )
                # Dynamically calculate the location of the upgrade button
                # and perform a click.
                point = (
                    position[0] + self.configurations["parameters"]["perks"]["position_x_padding"],
                    position[1] + self.configurations["parameters"]["perks"]["position_y_padding"],
                )

                if perk == "mega_boost":
                    # If the free image can be found and clicked on (vip/pass), we can
                    # exit early and just assume that the perk was used successfully.
                    if self.find_and_click_image(
                        image=self.files["perks_free"],
                        region=self.configurations["regions"]["perks"]["free_area"],
                        precision=self.configurations["parameters"]["perks"]["free_precision"],
                        pause=self.configurations["parameters"]["perks"]["free_pause"],
                    ):
                        continue
                    # Should we try and use the ad blocking functionality to handle
                    # the collection of the mega boost perk?
                    if self.ad_blocking_enabled_func():
                        # Follow normal flow and try to watch the ad
                        # "Okay" button will begin the process.
                        self.click(
                            point=point,
                            pause=self.configurations["parameters"]["perks"]["use_perk_pause"],
                        )
                        while self.search(
                            image=self.files["perks_header"],
                            region=self.configurations["regions"]["perks"]["header_area"],
                            precision=self.configurations["parameters"]["perks"]["header_precision"],
                        )[0]:
                            # Looping until the perks header has disappeared, which represents
                            # the ad collection being finished.
                            self.find_and_click_image(
                                image=self.files["perks_okay"],
                                region=self.configurations["regions"]["perks"]["okay_area"],
                                precision=self.configurations["parameters"]["perks"]["okay_precision"],
                                pause=self.configurations["parameters"]["perks"]["okay_pause"],
                            )
                else:
                    self.click(
                        point=point,
                        pause=self.configurations["parameters"]["perks"]["use_perk_pause"],
                    )
                    # If the header is available, the perk is not already active.
                    if self.search(
                        image=self.files["perks_header"],
                        region=self.configurations["regions"]["perks"]["header_area"],
                        precision=self.configurations["parameters"]["perks"]["header_precision"]
                    )[0]:
                        # Does this perk require diamonds to actually use?
                        if self.search(
                            image=self.files["perks_diamond"],
                            region=self.configurations["regions"]["perks"]["diamond_area"],
                            precision=self.configurations["parameters"]["perks"]["diamond_precision"],
                        )[0]:
                            if not self.configuration["perks_spend_diamonds"]:
                                self.logger.info(
                                    "The \"%(perk)s\" requires spending diamonds to use but diamond spending "
                                    "is disabled, skipping..." % {
                                        "perk": perk,
                                    }
                                )
                                self.find_and_click_image(
                                    image=self.files["perks_cancel"],
                                    region=self.configurations["regions"]["perks"]["cancel_area"],
                                    precision=self.configurations["parameters"]["perks"]["cancel_precision"],
                                    pause=self.configurations["parameters"]["perks"]["cancel_pause"],
                                )
                                continue
                        # Perk can be used if we get to this point...
                        # Activating it now.
                        self.find_and_click_image(
                            image=self.files["perks_okay"],
                            region=self.configurations["regions"]["perks"]["okay_area"],
                            precision=self.configurations["parameters"]["perks"]["okay_precision"],
                            pause=self.configurations["parameters"]["perks"]["okay_pause"],
                        )
                        if perk == "mana_potion":
                            # Mana potion unfortunately actually closes our
                            # master panel, we'll need to open it back up.
                            self.click(
                                point=self.configurations["points"]["travel"]["tabs"]["master"],
                                pause=self.configurations["parameters"]["perks"]["post_use_open_master_pause"],
                            )
                    else:
                        self.logger.info(
                            "The \"%(perk)s\" perk is already active, skipping..." % {
                                "perk": perk,
                            }
                        )
            except TimeoutError:
                self.logger.info(
                    "The \"%(perk)s\" perk could not be found on the screen, skipping..." % {
                        "perk": perk,
                    }
                )
                continue

    def headgear_swap(self):
        """
        Perform all headgear related swapping functionality.
        """
        self.travel_to_equipment(collapsed=False, scroll=False)
        self.logger.info(
            "Attempting to swap headgear for %(powerful)s type hero damage..." % {
                "powerful": self.powerful_hero,
            }
        )

        # Ensure the headgear panel is also open...
        timeout_headgear_panel_click_cnt = 0
        timeout_headgear_panel_click_max = self.configurations["parameters"]["headgear_swap"]["timeout_headgear_panel_click"]

        try:
            while not self.point_is_color_range(
                point=self.configurations["points"]["headgear_swap"]["headgear_panel_color_check"],
                color_range=self.configurations["colors"]["headgear_swap"]["headgear_panel_range"],
            ):
                self.click(
                    point=self.configurations["points"]["headgear_swap"]["headgear_panel"],
                    pause=self.configurations["parameters"]["headgear_swap"]["headgear_panel_pause"],
                )
                timeout_headgear_panel_click_cnt = self.handle_timeout(
                    count=timeout_headgear_panel_click_cnt,
                    timeout=timeout_headgear_panel_click_max,
                )
        except TimeoutError:
            self.logger.info(
                "Unable to open headgear panel in game, skipping..."
            )
            return

        # At this point, the equipment panel is open,
        # and we should be on the headgear panel, we will
        # also perform a quick travel to scroll to the top.
        self.travel_to_equipment(collapsed=False)

        # Once we've reached the headgear panel, we need to begin
        # looking through each possible equipment location, checking
        # for the correct "type" damage effect.
        for region in self.configurations["regions"]["headgear_swap"]["equipment_regions"]:
            # We only parse and deal with locked gear.
            if self.search(
                image=self.files["equipment_locked"],
                region=region,
                precision=self.configurations["parameters"]["headgear_swap"]["equipment_locked_precision"]
            )[0]:
                if self.search(
                    image=self.files["%(powerful)s_damage" % {"powerful": self.powerful_hero}],
                    region=region,
                    precision=self.configurations["parameters"]["headgear_swap"]["powerful_damage_precision"],
                )[0]:
                    # This equipment is the correct damage type.
                    # Is it already equipped?
                    if self.search(
                        image=self.files["equipment_equipped"],
                        region=region,
                        precision=self.configurations["parameters"]["headgear_swap"]["equipment_equipped_precision"],
                    )[0]:
                        self.logger.info(
                            "Headgear of type %(powerful)s is already equipped..." % {
                                "powerful": self.powerful_hero,
                            }
                        )
                    else:
                        self.logger.info(
                            "Equipping %(powerful)s type headgear now..." % {
                                "powerful": self.powerful_hero,
                            }
                        )
                        try:
                            self.find_and_click_image(
                                image=self.files["equipment_equip"],
                                region=region,
                                precision=self.configurations["parameters"]["headgear_swap"]["equipment_equip_precision"],
                                pause=self.configurations["parameters"]["headgear_swap"]["equipment_equip_pause"],
                                pause_not_found=self.configurations["parameters"]["headgear_swap"]["equipment_equip_pause_not_found"],
                                timeout=self.configurations["parameters"]["headgear_swap"]["equipment_equip_timeout"],
                                timeout_search_kwargs={
                                    "image": self.files["equipment_equipped"],
                                    "region": region,
                                    "precision": self.configurations["parameters"]["headgear_swap"]["equipment_equipped_precision"],
                                },
                            )
                            self.logger.info(
                                "%(powerful)s headgear has been equipped..." % {
                                    "powerful": self.powerful_hero.capitalize(),
                                }
                            )
                            return
                        except TimeoutError:
                            self.logger.info(
                                "Unable to equip headgear, skipping..."
                            )
                    return
        self.logger.info(
            "No locked %(powerful)s headgear could be found to be equipped..." % {
                "powerful": self.powerful_hero,
            }
        )

    def _artifacts_ensure_multiplier(self, multiplier):
        """
        Ensure the artifacts tab is set to the specified multiplier.
        """
        self.logger.info(
            "Ensuring %(multiplier)s is active..." % {
                "multiplier": multiplier,
            }
        )
        self.click(
            point=self.configurations["points"]["artifacts"]["multiplier"],
            pause=self.configurations["parameters"]["artifacts"]["multiplier_pause"],
            timeout=self.configurations["parameters"]["artifacts"]["timeout_multiplier"],
            timeout_search_kwargs={
                "image": self.files["artifacts_%s" % multiplier],
                "region": self.configurations["regions"]["artifacts"]["%s_open_area" % multiplier],
                "precision": self.configurations["parameters"]["artifacts"]["multiplier_open_precision"],
            },
        )
        # At this point, we should be able to perform a simple find and click
        # on the buy max button, we'll pause after than and then our loop should
        # end above.
        self.find_and_click_image(
            image=self.files["artifacts_%s" % multiplier],
            region=self.configurations["regions"]["artifacts"]["%s_open_area" % multiplier],
            precision=self.configurations["parameters"]["artifacts"]["multiplier_open_precision"],
            pause=self.configurations["parameters"]["artifacts"]["multiplier_open_pause"],
            timeout=self.configurations["parameters"]["artifacts"]["timeout_multiplier_open"],
        )

    def _artifacts_upgrade(self, artifact, multiplier):
        """
        Search for and actually perform an upgrade on it in the artifacts panel.
        """
        # Upgrade a single artifact to it's maximum
        # one time...
        self.logger.info(
            "Attempting to upgrade %(artifact)s artifact..." % {
                "artifact": artifact,
            }
        )
        timeout_artifact_search_cnt = 0
        timeout_artifact_search_max = self.configurations["parameters"]["artifacts"]["timeout_search"]

        while not self.search(
            image=self.files["artifact_%(artifact)s" % {"artifact": artifact}],
            region=self.configurations["regions"]["artifacts"]["search_area"],
            precision=self.configurations["parameters"]["artifacts"]["search_precision"],
        )[0]:
            self.drag(
                start=self.configurations["points"]["travel"]["scroll"]["drag_bottom"],
                end=self.configurations["points"]["travel"]["scroll"]["drag_top"],
                pause=self.configurations["parameters"]["travel"]["drag_pause"],
            )
            timeout_artifact_search_cnt = self.handle_timeout(
                count=timeout_artifact_search_cnt,
                timeout=timeout_artifact_search_max,
            )
        # At this point, the artifact being upgraded should be visible on the screen,
        # we'll grab the position and perform a single upgrade click before continuing.
        _, position, image = self.search(
            image=self.files["artifact_%(artifact)s" % {"artifact": artifact}],
            region=self.configurations["regions"]["artifacts"]["search_area"],
            precision=self.configurations["parameters"]["artifacts"]["search_precision"],
        )
        # Dynamically calculate the location of the upgrade button
        # and perform a click.
        point = (
            position[0] + self.configurations["parameters"]["artifacts"]["position_x_padding"],
            position[1] + self.configurations["parameters"]["artifacts"]["position_y_padding"],
        )
        self.click(
            point=point,
            clicks=self.configurations["parameters"]["artifacts"]["upgrade_clicks"] if multiplier == "max" else 1,
            interval=self.configurations["parameters"]["artifacts"]["upgrade_interval"],
            pause=self.configurations["parameters"]["artifacts"]["upgrade_pause"],
        )

    def _prestige_enchant_artifacts(self):
        """
        Handle enchanting artifacts in game following a prestige.
        """
        self.travel_to_artifacts(collapsed=False)

        found, position, image = self.search(
            image=self.files["artifacts_enchant_icon"],
            region=self.configurations["regions"]["artifacts"]["enchant_icon_area"],
            precision=self.configurations["parameters"]["artifacts"]["enchant_icon_precision"],
        )
        # In case multiple artifacts can be enchanted, looping
        # until no more enchantments can be performed.
        if found:
            self.logger.info(
                "Attempting to enchant artifacts..."
            )
            while True:
                self.click_image(
                    image=image,
                    position=position,
                    pause=self.configurations["parameters"]["artifacts"]["enchant_click_pause"],
                )
                if self.search(
                        image=self.files["artifacts_enchant_confirm_header"],
                        region=self.configurations["regions"]["artifacts"]["enchant_confirm_header_area"],
                        precision=self.configurations["parameters"]["artifacts"]["enchant_confirm_header_precision"],
                )[0]:
                    self.logger.info(
                        "Enchanting artifact now..."
                    )
                    self.click(
                        point=self.configurations["points"]["artifacts"]["enchant_confirm_point"],
                        pause=self.configurations["parameters"]["artifacts"]["enchant_confirm_pause"],
                    )
                    # Perform some middle top clicks to close enchantment prompt.
                    self.click(
                        point=self.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.configurations["parameters"]["artifacts"]["post_collect_clicks"],
                        interval=self.configurations["parameters"]["artifacts"]["post_collect_interval"],
                        pause=self.configurations["parameters"]["artifacts"]["post_collect_pause"],
                    )
                # Break if no header is found, no more artifacts can
                # be enchanted at this point.
                else:
                    break

    def _prestige_discover_artifacts(self):
        """
         Handle discovering artifacts in game following a prestige.
         """
        self.travel_to_artifacts(collapsed=False)

        found, position, image = self.search(
            image=self.files["artifacts_discover_icon"],
            region=self.configurations["regions"]["artifacts"]["discover_icon_area"],
            precision=self.configurations["parameters"]["artifacts"]["discover_icon_precision"],
        )
        # In case multiple artifacts can be discovered, looping
        # until no more discoveries can be performed.
        if found:
            self.logger.info(
                "Attempting to discover artifacts..."
            )
            while True:
                self.click_image(
                    image=image,
                    position=position,
                    pause=self.configurations["parameters"]["artifacts"]["discover_click_pause"],
                )
                if self.search(
                        image=self.files["artifacts_discover_confirm_header"],
                        region=self.configurations["regions"]["artifacts"]["discover_confirm_header_area"],
                        precision=self.configurations["parameters"]["artifacts"]["discover_confirm_header_precision"],
                )[0]:
                    self.logger.info(
                        "Discovering artifact now..."
                    )
                    self.click(
                        point=self.configurations["points"]["artifacts"]["discover_confirm_point"],
                        pause=self.configurations["parameters"]["artifacts"]["discover_confirm_pause"],
                    )
                    # Perform some middle top clicks to close discovery prompt.
                    self.click(
                        point=self.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.configurations["parameters"]["artifacts"]["post_collect_clicks"],
                        interval=self.configurations["parameters"]["artifacts"]["post_collect_interval"],
                        pause=self.configurations["parameters"]["artifacts"]["post_collect_pause"],
                    )
                    # If the user has enabled the option to also upgrade the newly discovered
                    # artifact, we'll do that now as well.
                    if self.configuration["artifacts_discovery_upgrade"]:
                        self.logger.info(
                            "Artifact discovery upgrade is enabled, attempting to upgrade the new artifact using the "
                            "\"%(multiplier)s\" multiplier in game..." % {
                                "multiplier": self.configuration["artifacts_discovery_upgrade_multiplier"],
                            }
                        )
                        self._artifacts_ensure_multiplier(
                            multiplier=self.configuration["artifacts_discovery_upgrade_multiplier"],
                        )
                        # Just manually clicking on the point since a newly discovered
                        # artifact will always pop up in the same location.
                        self.click(
                            point=self.configurations["points"]["artifacts"]["discovered_artifact"],
                            pause=self.configurations["parameters"]["artifacts"]["discovered_artifact_pause"],
                        )
                # Break if no header is found, no more artifacts can
                # be discovered at this point.
                else:
                    break

    def _prestige_upgrade_artifacts(self):
        """
        Handle upgrading artifacts in game following a prestige.
        """
        self.logger.info(
            "Beginning artifacts functionality..."
        )
        if self.configuration["artifacts_upgrade_enabled"]:
            self.travel_to_artifacts(scroll=False, collapsed=False)
            # Determining if maps are even going to be used
            # for this artifact upgrade functionality.
            if not self.mapping_enabled and self.next_artifact_upgrade:
                self.logger.info(
                    "Artifact upgrade maps are disabled, attempting to upgrade single artifact with "
                    "the \"BUY Max\" multiplier once."
                )
                try:
                    self._artifacts_ensure_multiplier(
                        multiplier="max",
                    )
                    # Upgrade a single artifact to it's maximum
                    # one time...
                    self.travel_to_artifacts(
                        collapsed=False,
                        stop_image_kwargs={
                            "image": self.files["artifact_%(artifact)s" % {"artifact": self.next_artifact_upgrade}],
                            "region": self.configurations["regions"]["artifacts"]["search_area"],
                            "precision": self.configurations["parameters"]["artifacts"]["search_precision"],
                        },
                    )
                    self._artifacts_upgrade(
                        artifact=self.next_artifact_upgrade,
                        multiplier="max",
                    )
                    # Update the next artifact that will be upgraded.
                    # This is done regardless of upgrade state (success/fail).
                    self.next_artifact_upgrade = next(self.upgrade_artifacts) if self.upgrade_artifacts else None
                    # Exporting our prestige once it's finished and right before
                    # exporting session data (if enabled).
                    self.export_prestige(prestige_contents={
                        "upgradeArtifact": self.next_artifact_upgrade,
                    })
                except TimeoutError:
                    self.logger.info(
                        "Artifact: %(artifact)s could not be found on the screen, or the \"BUY Max\" option could not be enabled, "
                        "skipping upgrade..." % {
                            "artifact": self.next_artifact_upgrade,
                        }
                    )
                    self.export_prestige(prestige_contents={
                        "upgradeArtifact": None,
                    })
            else:
                upgraded_artifacts = []
                # Mappings are enabled... We'll begin all that functionality here.
                # We know maps are available, so we'll loop through all of our keys and
                # and handle the multiplier ordering as needed.
                for multiplier in self.upgrade_map[self.upgrade_map_key_ordering]:
                    multiplier = str(multiplier)
                    self.logger.info(
                        "Attempting to upgrade artifacts mapped to the %(multiplier)s multiplier..." % {
                            "multiplier": multiplier,
                        }
                    )
                    if self.upgrade_map[multiplier]:
                        count, limit = (
                            0,
                            self.upgrade_map[self.upgrade_map_key_limits][multiplier]
                        )
                        try:
                            self._artifacts_ensure_multiplier(
                                multiplier=multiplier,
                            )
                            for artifact in self.upgrade_map[multiplier]:
                                if limit:
                                    if count >= int(limit):
                                        self.logger.info(
                                            "Mapped artifact upgrade limit (%(limit)s) reached, ending mapped artifact "
                                            "upgrades early..." % {
                                                "limit": limit,
                                            }
                                        )
                                        break
                                try:
                                    self.travel_to_artifacts(
                                        collapsed=False,
                                        stop_image_kwargs={
                                            "image": self.files["artifact_%(artifact)s" % {"artifact": artifact}],
                                            "region": self.configurations["regions"]["artifacts"]["search_area"],
                                            "precision": self.configurations["parameters"]["artifacts"]["search_precision"],
                                        },
                                    )
                                    self._artifacts_upgrade(
                                        artifact=artifact,
                                        multiplier=multiplier,
                                    )
                                    upgraded_artifacts.append(
                                        artifact,
                                    )
                                    count += 1
                                except TimeoutError:
                                    self.logger.info(
                                        "Artifact: %(artifact)s could not be found on the screen, skipping upgrade..." % {
                                            "artifact": artifact,
                                        }
                                    )
                        except TimeoutError:
                            self.logger.info(
                                "The \"%(multiplier)s\" option could not be enabled, skipping upgrade..." % {
                                    "multiplier": multiplier,
                                }
                            )
                    else:
                        self.logger.info(
                            "No artifacts are currently mapped to the %(multiplier)s multiplier, skipping..." % {
                                "multiplier": multiplier,
                            }
                        )
                # After artifact upgrades are complete, we'll re shuffle the maps
                # if it's enabled...
                if self.configuration["artifacts_shuffle"]:
                    self.logger.info(
                        "Shuffling artifacts maps following upgrades..."
                    )
                    for key in self.upgrade_map_keys + [self.upgrade_map_key_unmapped]:
                        random.shuffle(self.upgrade_map[key])
                self.export_prestige(prestige_contents={
                    "upgradeArtifact": upgraded_artifacts,
                })
        else:
            self.export_prestige(prestige_contents={
                "upgradeArtifact": None,
            })

    def prestige(self):
        """
        Perform a prestige in game, upgrading a specified artifact afterwards if enabled.

        Some extra care is put into performing timeouts and looping until
        certain actions are finished to ensure the prestige takes place.
        """
        self.travel_to_master()
        self.leave_boss()

        self.logger.info(
            "Attempting to prestige in game now..."
        )

        tournament_prestige = False

        # Handle all tournament functionality within our final prestige
        # execution. If enabled, we can check that a tournament is even running,
        # check if one can be joined, or check that rewards can be collected.
        if self.configuration["tournaments_enabled"]:
            self.logger.info(
                "Tournaments are enabled, checking current status of in game tournament..."
            )
            # Tournament is in a "grey" state, one will be starting soon...
            # We do nothing here.
            if self.point_is_color_range(
                point=self.configurations["points"]["tournaments"]["tournaments_status"],
                color_range=self.configurations["colors"]["tournaments"]["tournaments_soon_range"],
            ):
                # Tournament is not ready yet at all. Doing nothing for tournament functionality.
                self.logger.info(
                    "Tournament is starting soon, skipping tournament functionality until ready..."
                )
            # Tournament is in a "blue" state, one is ready and can
            # be joined now, we join the tournament here.
            elif self.point_is_color_range(
                point=self.configurations["points"]["tournaments"]["tournaments_status"],
                color_range=self.configurations["colors"]["tournaments"]["tournaments_ready_range"],
            ):
                tournament_prestige = True
                # Tournament is available and ready to be joined... Attempting to join and skip
                # prestige functionality below.
                self.click(
                    point=self.configurations["points"]["tournaments"]["tournaments_icon"],
                    pause=self.configurations["parameters"]["tournaments"]["icon_pause"],
                )
                try:
                    self.logger.info(
                        "Performing tournament prestige now..."
                    )
                    self.find_and_click_image(
                        image=self.files["tournaments_join"],
                        region=self.configurations["regions"]["tournaments"]["join_area"],
                        precision=self.configurations["parameters"]["tournaments"]["join_precision"],
                        pause=self.configurations["parameters"]["tournaments"]["join_pause"],
                        timeout=self.configurations["parameters"]["tournaments"]["join_timeout"],
                    )
                    self.find_and_click_image(
                        image=self.files["prestige_confirm_confirm_icon"],
                        region=self.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                        precision=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                        pause=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_pause"],
                        timeout=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_timeout"],
                        timeout_search_while_not=False,
                        timeout_search_kwargs={
                            "image": self.files["prestige_confirm_confirm_icon"],
                            "region": self.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                            "precision": self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                        },
                    )
                except TimeoutError:
                    self.logger.info(
                        "Timeout was reached while trying to join tournament, skipping..."
                    )
            # Tournament is in a "red" state, one we joined is now
            # over and rewards are available.
            elif self.point_is_color_range(
                point=self.configurations["points"]["tournaments"]["tournaments_status"],
                color_range=self.configurations["colors"]["tournaments"]["tournaments_over_range"],
            ):
                self.click(
                    point=self.configurations["points"]["tournaments"]["tournaments_icon"],
                    pause=self.configurations["parameters"]["tournaments"]["icon_pause"],
                )
                if self.find_and_click_image(
                    image=self.files["tournaments_collect"],
                    region=self.configurations["regions"]["tournaments"]["collect_area"],
                    precision=self.configurations["parameters"]["tournaments"]["collect_precision"],
                    pause=self.configurations["parameters"]["tournaments"]["collect_pause"],
                ):
                    self.logger.info(
                        "Collecting tournament rewards now..."
                    )
                    self.click(
                        point=self.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.configurations["parameters"]["tournaments"]["post_collect_clicks"],
                        interval=self.configurations["parameters"]["tournaments"]["post_collect_interval"],
                        pause=self.configurations["parameters"]["tournaments"]["post_collect_pause"],
                    )

        if not tournament_prestige:
            try:
                self.logger.info(
                    "Performing prestige now..."
                )
                self.find_and_click_image(
                    image=self.files["prestige_icon"],
                    region=self.configurations["regions"]["prestige"]["prestige_icon_area"],
                    precision=self.configurations["parameters"]["prestige"]["prestige_icon_precision"],
                    pause=self.configurations["parameters"]["prestige"]["prestige_icon_pause"],
                    timeout=self.configurations["parameters"]["prestige"]["prestige_icon_timeout"],
                    timeout_search_while_not=False,
                    timeout_search_kwargs={
                        "image": self.files["prestige_icon"],
                        "region": self.configurations["regions"]["prestige"]["prestige_icon_area"],
                        "precision": self.configurations["parameters"]["prestige"]["prestige_icon_precision"],
                    },
                )
                self.find_and_click_image(
                    image=self.files["prestige_confirm_icon"],
                    region=self.configurations["regions"]["prestige"]["prestige_confirm_icon_area"],
                    precision=self.configurations["parameters"]["prestige"]["prestige_confirm_icon_precision"],
                    pause=self.configurations["parameters"]["prestige"]["prestige_confirm_icon_pause"],
                    timeout=self.configurations["parameters"]["prestige"]["prestige_confirm_icon_timeout"],
                )
                self.find_and_click_image(
                    image=self.files["prestige_confirm_confirm_icon"],
                    region=self.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                    precision=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                    pause=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_pause"],
                    timeout=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_timeout"],
                    timeout_search_while_not=False,
                    timeout_search_kwargs={
                        "image": self.files["prestige_confirm_confirm_icon"],
                        "region": self.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                        "precision": self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                    },
                )
            except TimeoutError:
                self.logger.info(
                    "Timeout was reached while trying to perform prestige, skipping..."
                )
            # Waiting here through the confirm_confirm_icon_pause for the prestige
            # animation to be finished before moving on...
        if self.configuration["artifacts_enabled"]:
            # Important to handle enchantments/discovery before upgrading
            # artifacts so we can make sure the upgrade doesn't spend all our relics.
            if self.configuration["artifacts_enchantment_enabled"]:
                self._prestige_enchant_artifacts()
            if self.configuration["artifacts_discovery_enabled"]:
                self._prestige_discover_artifacts()
            # Artifacts are enabled.
            self._prestige_upgrade_artifacts()
        else:
            self.export_prestige(prestige_contents={
                "upgradeArtifact": None,
            })

        # Reset the most powerful hero, first subsequent hero levelling
        # should handle this for us again.
        self.powerful_hero = None
        # Update the next artifact that will be upgraded.
        # This is done regardless of upgrade state (success/fail).
        self.next_artifact_upgrade = next(self.upgrade_artifacts) if self.upgrade_artifacts else None
        # Prestige specific variables can be reset now.
        self.close_to_max_ready = False
        self.master_levelled = False
        # Once the prestige has finished, we need to update our most upto date
        # set of exported data, from here, we can then figure out whats changed
        # and send a new session event. If this isn't enabled, we at least get
        # a prestige sent along above.
        if self.configuration["export_data_enabled"] and not self.configuration["abyssal"]:
            self.export_data()

        # Handle some forcing of certain functionality post prestige below.
        # We do this once to ensure the game is up and running efficiently
        # before beginning scheduled functionality again.
        self.logger.info(
            "Prestige is complete, forcing master, skills, heroes levelling before continuing..."
        )
        self.level_master()
        self.level_skills()
        self.activate_skills()
        self.level_heroes()

        # Reset schedule data post prestige.
        # This ensures all functionality is "reset"
        # once prestige is complete, this includes prestige
        # functionality.
        self.schedule_functions()

    def prestige_execute_or_schedule(self):
        """
        Execute, or schedule a prestige based on the current configured interval.
        """
        interval = self.configuration["prestige_wait_when_ready_interval"]

        if interval > 0:
            self.logger.info(
                "Scheduling prestige to take place in %(interval)s second(s)..." % {
                    "interval": interval,
                }
            )
            # Cancel the scheduled prestige functions
            # if it's present so the options don't clash.
            self.cancel_scheduled_function(tags=[
                self.prestige.__name__,
                self.prestige_close_to_max.__name__,
            ])
            self.schedule_function(
                function=self.prestige,
                interval=interval,
            )
        else:
            self.prestige()

    def prestige_close_to_max(self):
        """
        Perform a prestige in game when the user has reached the stage required that represents them
        being close to their "max stage".

        We do this through two methods:

        1. While an event is running, we can look at the users master panel to determine
        if the event's icon is currently displayed by the prestige button.

        2. While an event isn't running, we can open up the users skill tree and check
        for the "prestige to reset" button being present on screen.

        When either of these conditions are met, we can make the assumption that a prestige
        should take place.
        """
        self.travel_to_master()
        self.logger.info(
            "Checking if prestige should be performed due to being close to max stage..."
        )

        if not self.close_to_max_ready:
            if self.configurations["global"]["events"]["event_running"] and not self.configuration["abyssal"]:
                self.logger.info(
                    "Event is currently running, checking for event icon present on master panel..."
                )
                # Event is running, let's check the master panel for
                # the current event icon.
                if self.search(
                    image=self.files["prestige_close_to_max_event_icon"],
                    region=self.configurations["regions"]["prestige_close_to_max"]["event_icon_search_area"],
                    precision=self.configurations["parameters"]["prestige_close_to_max"]["event_icon_search_precision"],
                )[0]:
                    self.close_to_max_ready = True
            else:
                # No event is running, instead, we will open the skill tree,
                # and check that the reset icon is present.
                if self.configuration["abyssal"]:
                    self.logger.info(
                        "Abyssal tournament is enabled, checking for prestige reset on skill tree..."
                    )
                else:
                    self.logger.info(
                        "No event is currently running, checking for prestige reset on skill tree..."
                    )
                self.click(
                    point=self.configurations["points"]["prestige_close_to_max"]["skill_tree_icon"],
                    pause=self.configurations["parameters"]["prestige_close_to_max"]["skill_tree_click_pause"]
                )
                if self.search(
                    image=self.files["prestige_close_to_max_skill_tree_icon"],
                    region=self.configurations["regions"]["prestige_close_to_max"]["skill_tree_search_area"],
                    precision=self.configurations["parameters"]["prestige_close_to_max"]["skill_tree_search_precision"],
                )[0]:
                    self.close_to_max_ready = True
                # Closing the skill tree once finished.
                # "prestige" variable will determine next steps below.
                while self.search(
                    image=self.files["prestige_close_to_max_skill_tree_header"],
                    region=self.configurations["regions"]["prestige_close_to_max"]["skill_tree_header_area"],
                    precision=self.configurations["parameters"]["prestige_close_to_max"]["skill_tree_header_precision"],
                )[0]:
                    # Looping to exit, careful since not exiting could cause us
                    # to use a skill point, which makes it hard to leave the prompt.
                    self.find_and_click_image(
                        image=self.files["large_exit"],
                        region=self.configurations["regions"]["prestige_close_to_max"]["skill_tree_exit_area"],
                        precision=self.configurations["parameters"]["prestige_close_to_max"]["skill_tree_exit_precision"],
                        pause=self.configurations["parameters"]["prestige_close_to_max"]["skill_tree_exit_pause"],
                    )
        if self.close_to_max_ready:
            if self.configuration["prestige_close_to_max_fight_boss_enabled"]:
                self.logger.info(
                    "Prestige is ready, waiting for fight boss icon to appear..."
                )
                # We need to also make sure the fight boss function is no longer
                # scheduled to run for the rest of this prestige.
                self.cancel_scheduled_function(tags=self.fight_boss.__name__)
                # Instead of executing or scheduling our prestige right away,
                # we will check for the fight boss icon and if it's present,
                # then we will execute/schedule.
                if self.search(
                    image=self.files["fight_boss_icon"],
                    region=self.configurations["regions"]["fight_boss"]["search_area"],
                    precision=self.configurations["parameters"]["fight_boss"]["search_precision"]
                )[0]:
                    self.logger.info(
                        "Fight boss icon is present, prestige is ready..."
                    )
                    self.prestige()
            else:
                self.logger.info(
                    "Prestige is ready..."
                )
                self.prestige_execute_or_schedule()

    def tap(self):
        """
        Perform taps on main game screen.
        """
        try:
            self.collapse()
            self.collapse_event_panel()
        except TimeoutError:
            # Check for a timeout error directly while collapsing panels,
            # this allows us to skip tapping if collapsing failed.
            self.logger.info(
                "Unable to successfully collapse panels in game, skipping tap functionality..."
            )
        # To prevent many, many logs from appearing in relation
        # to the tapping functionality, we'll go ahead and only
        # log the swiping information if the last function wasn't
        # already the tapping function.
        if self.stream.last_message != "Tapping...":
            self.logger.info(
                "Tapping..."
            )
        tap = []
        maps = [
            "fairies",
            "heroes",
            "pet",
            "master",
        ]
        for key in maps:
            if key == "heroes":
                lst = copy.copy(self.configurations["points"]["tap"]["tap_map"][key])
                for i in range(self.configurations["parameters"]["tap"]["tap_heroes_loops"]):
                    # The "heroes" key will shuffle and reuse the map, this aids in the process
                    # of activating the astral awakening skills.
                    random.shuffle(lst)
                    # After a shuffle, we'll also remove some tap points if they dont surpass a certain
                    # percent threshold configured in the backend.
                    lst = [
                        point for point in lst if
                        random.random() > self.configurations["parameters"]["tap"]["tap_heroes_remove_percent"]
                    ]
                    tap.extend(lst)
            else:
                tap.extend(self.configurations["points"]["tap"]["tap_map"][key])

        # Remove any points that could open up the
        # one time offer prompt.
        if self.search(
            image=self.files["one_time_offer"],
            region=self.configurations["regions"]["tap"]["one_time_offer_area"],
            precision=self.configurations["parameters"]["tap"]["one_time_offer_precision"],
        )[0]:
            # A one time offer is on the screen, we'll filter out any tap points that fall
            # within this point, this prevents us from buying anything in the store.
            tap = [point for point in tap if not self.point_is_region(
                point=point,
                region=self.configurations["regions"]["tap"]["one_time_offer_prevent_area"],
            )]
        # Remove any points that could collect pieces
        # of available equipment in game.
        if not self.configuration["tapping_collect_equipment"]:
            tap = [point for point in tap if not self.point_is_region(
                point=point,
                region=self.configurations["regions"]["tap"]["collect_equipment_prevent_area"],
            )]

        for index, point in enumerate(tap):
            if index % self.configurations["parameters"]["tap"]["tap_fairies_modulo"] == 0:
                # Also handle the fact that fairies could appear
                # and be clicked on while tapping is taking place.
                self.fairies()
                if self.stream.last_message != "Tapping...":
                    self.logger.info(
                        "Tapping..."
                    )
            if index % self.configurations["parameters"]["tap"]["tap_collapse_prompts_modulo"] == 0:
                # Also handle the fact the tapping in general is sporadic
                # and the incorrect panel/window could be open.
                self.collapse_prompts()
                self.collapse()
            self.click(
                point=point,
                button=self.configurations["parameters"]["tap"]["button"],
                offset=random.randint(
                    self.configurations["parameters"]["tap"]["offset_min"],
                    self.configurations["parameters"]["tap"]["offset_max"],
                ),
            )
        # Only pausing after all clicks have been performed.
        time.sleep(self.configurations["parameters"]["tap"]["pause"])
        # Additionally, perform a final fairy check explicitly
        # when tapping is complete, in case of a fairy being clicked
        # on right at the end of tapping.
        self.fairies()

    def collapse(self):
        """
        Ensure the game screen is currently collapsed, regardless of the currently opened tab.
        """
        self.logger.debug(
            "Attempting to collapse any panels in game..."
        )
        if self.find_and_click_image(
            image=self.files["travel_collapse"],
            region=self.configurations["regions"]["travel"]["collapse_area"],
            precision=self.configurations["parameters"]["travel"]["uncollapse_precision"],
            pause=self.configurations["parameters"]["collapse"]["collapse_loop_pause"],
            pause_not_found=self.configurations["parameters"]["collapse"]["collapse_loop_pause_not_found"],
            timeout=self.configurations["parameters"]["collapse"]["timeout_collapse"],
            timeout_search_while_not=False,
            timeout_search_kwargs={
                "image": self.files["travel_collapse"],
                "region": self.configurations["regions"]["travel"]["collapse_area"],
                "precision": self.configurations["parameters"]["travel"]["uncollapse_precision"],
            },
        ):
            self.logger.debug(
                "Panel has been successfully collapsed..."
            )

    def collapse_prompts(self):
        """
        Attempt to collapse any open prompts in game.
        """
        self.find_and_click_image(
            image=[
                self.files["large_exit"],
                self.files["small_shop_exit"],
            ],
            region=self.configurations["regions"]["collapse_prompts"]["collapse_prompts_area"],
            precision=self.configurations["parameters"]["collapse_prompts"]["collapse_prompts_precision"],
            pause=self.configurations["parameters"]["collapse_prompts"]["collapse_prompts_pause"],
            pause_not_found=self.configurations["parameters"]["collapse_prompts"]["collapse_prompts_not_found_pause"],
            timeout=self.configurations["parameters"]["collapse_prompts"]["collapse_prompts_timeout"],
            timeout_search_while_not=False,
            timeout_search_kwargs={
                "image": [
                    self.files["large_exit"],
                    self.files["small_shop_exit"],
                ],
                "region": self.configurations["regions"]["collapse_prompts"]["collapse_prompts_area"],
                "precision": self.configurations["parameters"]["collapse_prompts"]["collapse_prompts_precision"],
            },
        )

    def collapse_event_panel(self):
        """
        Attempt to collapse the event panel in game if it is currently open.
        """
        self.logger.debug(
            "Attempting to collapse the event panel in game..."
        )
        # Early check in case the panel can not be expanded or collapsed
        # due to no event or abyssal tournament even being available in any way.
        if not self.search(
            image=[
                self.files["event_panel_collapse"],
                self.files["event_panel_expand"],
            ],
            region=self.configurations["regions"]["event_panel"]["event_area"],
            precision=self.configurations["parameters"]["event_panel"]["event_precision"],
        )[0]:
            self.logger.debug(
                "The event panel can not currently be collapsed or expanded, skipping..."
            )
            return

        if self.find_and_click_image(
            image=self.files["event_panel_collapse"],
            region=self.configurations["regions"]["event_panel"]["event_area"],
            precision=self.configurations["parameters"]["event_panel"]["event_precision"],
            pause=self.configurations["parameters"]["event_panel"]["collapse_loop_pause"],
            pause_not_found=self.configurations["parameters"]["event_panel"]["collapse_loop_pause_not_found"],
            timeout=self.configurations["parameters"]["event_panel"]["timeout_collapse"],
            timeout_search_kwargs={
                "image": self.files["event_panel_expand"],
                "region": self.configurations["regions"]["event_panel"]["event_area"],
                "precision": self.configurations["parameters"]["event_panel"]["event_precision"],
            },
        ):
            self.logger.info(
                "Event panel has been successfully collapsed..."
            )

    def expand_event_panel(self):
        """
        Attempt to expand the event panel in game if it is currently closed.
        """
        self.logger.debug(
            "Attempting to expand the event panel in game."
        )
        # Early check in case the panel can not be expanded or collapsed
        # due to no event or abyssal tournament even being available in any way.
        if not self.search(
            image=[
                self.files["event_panel_collapse"],
                self.files["event_panel_expand"],
            ],
            region=self.configurations["regions"]["event_panel"]["event_area"],
            precision=self.configurations["parameters"]["event_panel"]["event_precision"],
        )[0]:
            self.logger.debug(
                "The event panel can not currently be collapsed or expanded, skipping..."
            )
            return

        if self.find_and_click_image(
            image=self.files["event_panel_expand"],
            region=self.configurations["regions"]["event_panel"]["event_area"],
            precision=self.configurations["parameters"]["event_panel"]["event_precision"],
            pause=self.configurations["parameters"]["event_panel"]["expand_loop_pause"],
            pause_not_found=self.configurations["parameters"]["event_panel"]["expand_loop_pause_not_found"],
            timeout=self.configurations["parameters"]["event_panel"]["timeout_expand"],
            timeout_search_kwargs={
                "image": self.files["event_panel_collapse"],
                "region": self.configurations["regions"]["event_panel"]["event_area"],
                "precision": self.configurations["parameters"]["event_panel"]["event_precision"],
            },
        ):
            self.logger.info(
                "Event panel has been successfully expanded..."
            )

    def export_data(self):
        """
        Open up the settings in game and export user data.

        This information contains a lot of very useful information, the information
        is saved to the users clipboard which we can access and store.
        """
        self.travel_to_master()

        try:
            self.logger.info(
                "Opening master page to ensure exported data is up to date..."
            )
            self.click(
                point=self.configurations["points"]["export_data"]["master_screen"],
                pause=self.configurations["parameters"]["export_data"]["master_screen_pause"],
                timeout=self.configurations["parameters"]["export_data"]["timeout_master_click"],
                timeout_search_kwargs={
                    "image": self.files["master_header"],
                    "region": self.configurations["regions"]["export_data"]["master_header_area"],
                    "precision": self.configurations["parameters"]["export_data"]["master_header_precision"],
                },
            )
            self.find_and_click_image(
                image=self.files["large_exit"],
                region=self.configurations["regions"]["travel"]["exit_area"],
                precision=self.configurations["parameters"]["travel"]["exit_precision"],
                pause=self.configurations["parameters"]["export_data"]["exit_pause"],
            )
        except TimeoutError:
            self.logger.info(
                "Unable to open the master panel to handle data exports, timeout has been reached, "
                "skipping data export..."
            )
            return

        try:
            self.logger.info(
                "Attempting to export data now..."
            )
            self.click(
                point=self.configurations["points"]["export_data"]["options_icon"],
                pause=self.configurations["parameters"]["export_data"]["options_icon_pause"],
                timeout=self.configurations["parameters"]["export_data"]["timeout_options_click"],
                timeout_search_kwargs={
                    "image": self.files["options_header"],
                    "region": self.configurations["regions"]["export_data"]["options_header_area"],
                    "precision": self.configurations["parameters"]["export_data"]["options_header_precision"],
                },
            )
            self.find_and_click_image(
                image=self.files["options_export"],
                region=self.configurations["regions"]["export_data"]["options_export_area"],
                precision=self.configurations["parameters"]["export_data"]["options_export_precision"],
                pause=self.configurations["parameters"]["export_data"]["options_export_pause"],
                pause_not_found=self.configurations["parameters"]["export_data"]["options_export_pause_not_found"],
                timeout=self.configurations["parameters"]["export_data"]["timeout_export_click"],
            )
            # Ensuring that we attempt to close the options panel until the
            # master icon is on the screen again, since the master panel is
            # active here, this should work fine.
            self.find_and_click_image(
                image=self.files["large_exit"],
                region=self.configurations["regions"]["travel"]["exit_area"],
                precision=self.configurations["parameters"]["travel"]["exit_precision"],
                pause=self.configurations["parameters"]["travel"]["exit_pause"],
                timeout=self.configurations["parameters"]["export_data"]["timeout_options_exit"],
                timeout_search_kwargs={
                    "image": self.files["travel_master_icon"],
                    "region": self.configurations["regions"]["travel"]["search_area"],
                    "precision": self.configurations["parameters"]["travel"]["precision"],
                },
            )
            if self.search(
                image=self.files["language_header"],
                region=self.configurations["regions"]["export_data"]["language_header_area"],
                precision=self.configurations["parameters"]["export_data"]["language_header_precision"],
            )[0]:
                self.logger.info(
                    "Language prompt is open, attempting to close now..."
                )
                self.find_and_click_image(
                    image=self.files["large_exit"],
                    region=self.configurations["regions"]["travel"]["exit_area"],
                    precision=self.configurations["parameters"]["travel"]["exit_precision"],
                    pause=self.configurations["parameters"]["travel"]["exit_pause"],
                )
                self.find_and_click_image(
                    image=self.files["large_exit"],
                    region=self.configurations["regions"]["travel"]["exit_area"],
                    precision=self.configurations["parameters"]["travel"]["exit_precision"],
                    pause=self.configurations["parameters"]["travel"]["exit_pause"],
                )

        except TimeoutError:
            self.logger.info(
                "Unable to open the options panel to handle data exports, timeout has been reached, "
                "skipping data export..."
            )
        self.logger.info(
            "Export data has been copied to the clipboard..."
        )
        # Grab the current clipboard contents...
        # It should be in the proper json format.
        contents = pyperclip.paste()

        try:
            # Always setting our exported content on export.
            # We handle the "original" set of exported data below.
            contents = json.loads(pyperclip.paste())
            # "playerStats" - Important user data.
            # "artifacts" - Artifact information (useful per prestige).
            self.export_contents = {
                "playerStats": contents["playerStats"],
                "artifacts": contents["artifacts"],
            }
            self.logger.info(
                "Exported data has been loaded successfully..."
            )
        except json.JSONDecodeError:
            self.logger.info(
                "Exported contents could not be parsed, skipping data export..."
            )
            return

        if not self.export_orig_contents:
            self.export_orig_contents = copy.deepcopy(self.export_contents)
            # original_contents is left blank to ensure we're only sending
            # over the original set of export data.
            self.export_session(
                export_contents=self.export_contents,
            )
        # If the export contents have differed in some way,
        # we'll update our session and handle "changed" values.
        elif self.export_orig_contents != self.export_contents:
            self.export_session(
                export_contents=self.export_contents,
                original_contents=self.export_orig_contents,
            )

    def travel(
        self,
        tab,
        image,
        scroll=True,
        collapsed=True,
        top=True,
        stop_image_kwargs=None,
    ):
        """
        Travel to the specified tab in game.

        If a scrolling tab is being accessed, the tab specified will determine
        which points are used when determining points.

        We allow the user to travel to the top or bottom of a panel only currently.
        """
        if scroll:
            self.logger.info(
                "Attempting to travel to the %(collapsed)s %(top_bottom)s of %(tab)s tab..." % {
                    "collapsed": "collapsed" if collapsed else "un-collapsed",
                    "top_bottom": "top" if top else "bottom",
                    "tab": tab,
                }
            )
        else:
            self.logger.info(
                "Attempting to travel to %(collapsed)s %(tab)s tab..." % {
                    "collapsed": "collapsed" if collapsed else "un-collapsed",
                    "tab": tab,
                }
            )

        # Always performing a quick find and click on an open prompt
        # page exit icon (large exit).
        while True:
            if self.find_and_click_image(
                image=self.files["large_exit"],
                region=self.configurations["regions"]["travel"]["exit_area"],
                precision=self.configurations["parameters"]["travel"]["exit_precision"],
                pause=self.configurations["parameters"]["travel"]["exit_pause"],
            ):
                continue
            break
        try:
            self.click(
                point=self.configurations["points"]["travel"]["tabs"][tab],
                pause=self.configurations["parameters"]["travel"]["click_pause"],
                timeout=self.configurations["parameters"]["travel"]["timeout_click"],
                timeout_search_kwargs={
                    "image": image,
                    "region": self.configurations["regions"]["travel"]["search_area"],
                    "precision": self.configurations["parameters"]["travel"]["precision"],
                },
            )

            # Tab is open at this point. Perform the collapse, un-collapse functionality
            # before attempting to scroll to the top or bottom of a panel.
            if collapsed is not None:
                if collapsed:
                    # We want to "collapse" the panel, check if it's already
                    # collapsed at this point.
                    self.click(
                        point=self.configurations["points"]["travel"]["collapse"],
                        pause=self.configurations["parameters"]["travel"]["collapse_pause"],
                        timeout=self.configurations["parameters"]["travel"]["timeout_collapse"],
                        timeout_search_kwargs={
                            "image": self.files["travel_collapsed"],
                            "region": self.configurations["regions"]["travel"]["collapsed_area"],
                            "precision": self.configurations["parameters"]["travel"]["collapse_precision"],
                        },
                    )
                else:
                    self.click(
                        point=self.configurations["points"]["travel"]["uncollapse"],
                        pause=self.configurations["parameters"]["travel"]["uncollapse_pause"],
                        timeout=self.configurations["parameters"]["travel"]["timeout_collapse"],
                        timeout_search_kwargs={
                            "image": self.files["travel_collapse"],
                            "region": self.configurations["regions"]["travel"]["collapse_area"],
                            "precision": self.configurations["parameters"]["travel"]["uncollapse_precision"],
                        },
                    )

            if scroll:
                scroll_img = self.files.get("travel_%(tab)s_%(scroll_key)s" % {
                    "tab": tab,
                    "scroll_key": "scroll_top" if top else "scroll_bottom",
                })

                # If a scroll image is available, we can drag and check for the image
                # being present to determine the top or bottom state of a tab.
                if scroll_img:
                    self.drag(
                        start=self.configurations["points"]["travel"]["scroll"]["drag_top" if top else "drag_bottom"],
                        end=self.configurations["points"]["travel"]["scroll"]["drag_bottom" if top else "drag_top"],
                        pause=self.configurations["parameters"]["travel"]["drag_pause"],
                        timeout=self.configurations["parameters"]["travel"]["timeout_drag"],
                        timeout_search_kwargs={
                            "image": scroll_img,
                            "precision": self.configurations["parameters"]["travel"]["scroll_precision"],
                        },
                    )
                # If no scroll image is present for the tab, we fallback to handling the
                # top and bottom check through an image duplication check.
                else:
                    timeout_drag_cnt = 0
                    timeout_drag_max = self.configurations["parameters"]["travel"]["timeout_drag"]
                    img = None

                    while True:
                        if stop_image_kwargs:
                            # Breaking early if image stopping is enabled
                            # and the image kwargs are found on the screen.
                            if self.search(
                                **stop_image_kwargs
                            )[0]:
                                break
                        img, dupe = self.duplicates(
                            image=img,
                            region=self.configurations["regions"]["travel"]["duplicate_area"],
                        )
                        if dupe:
                            break
                        self.drag(
                            start=self.configurations["points"]["travel"]["scroll"]["drag_top" if top else "drag_bottom"],
                            end=self.configurations["points"]["travel"]["scroll"]["drag_bottom" if top else "drag_top"],
                            pause=self.configurations["parameters"]["travel"]["drag_pause"],
                        )
                        timeout_drag_cnt = self.handle_timeout(
                            count=timeout_drag_cnt,
                            timeout=timeout_drag_max,
                        )
            self.logger.info(
                "Successfully travelled to the %(tab)s tab..." % {
                    "tab": tab,
                }
            )
        except TimeoutError:
            self.logger.info(
                "Unable to travel to the %(tab)s tab... Timeout has been reached, ignoring and "
                "attempting to continue..." % {
                    "tab": tab,
                }
            )

    def travel_to_master(
        self,
        scroll=True,
        collapsed=True,
        top=True,
    ):
        """
        Travel to the master tab in game.
        """
        self.travel(
            tab="master",
            image=self.files["travel_master_icon"],
            scroll=scroll,
            collapsed=collapsed,
            top=top,
        )

    def travel_to_heroes(
        self,
        scroll=True,
        collapsed=True,
        top=True,
    ):
        """
        Travel to the heroes tab in game.
        """
        self.travel(
            tab="heroes",
            image=self.files["travel_heroes_icon"],
            scroll=scroll,
            collapsed=collapsed,
            top=top,
        )

    def travel_to_equipment(
        self,
        scroll=True,
        collapsed=True,
        top=True,
    ):
        """
        Travel to the equipment tab in game.
        """
        self.travel(
            tab="equipment",
            image=self.files["travel_equipment_icon"],
            scroll=scroll,
            collapsed=collapsed,
            top=top,
        )

    def travel_to_pets(
        self,
        scroll=True,
        collapsed=True,
        top=True,
    ):
        """
        Travel to the pets tab in game.
        """
        self.travel(
            tab="pets",
            image=self.files["travel_pets_icon"],
            scroll=scroll,
            collapsed=collapsed,
            top=top,
        )

    def travel_to_artifacts(
        self,
        scroll=True,
        collapsed=True,
        top=True,
        stop_image_kwargs=None,
    ):
        """
        Travel to the artifacts tab in game.
        """
        self.travel(
            tab="artifacts",
            image=[
                self.files["travel_artifacts_icon"],
                self.files["travel_artifacts_abyssal_icon"],
            ],
            scroll=scroll,
            collapsed=collapsed,
            top=top,
            stop_image_kwargs=stop_image_kwargs,
        )

    def travel_to_shop(
        self,
        scroll=True,
        collapsed=None,
        top=True,
        stop_image_kwargs=None,
    ):
        """
        Travel to the shop tab in game.
        """
        self.travel(
            tab="shop",
            image=self.files["travel_shop_icon"],
            scroll=scroll,
            collapsed=collapsed,
            top=top,
            stop_image_kwargs=stop_image_kwargs,
        )

    def travel_to_main_screen(self):
        """
        Travel to the main game screen (no tabs open) in game.
        """
        timeout_travel_to_main_screen_cnt = 0
        timeout_travel_to_main_screen_max = self.configurations["parameters"]["travel"]["timeout_travel_main_screen"]

        while True:
            try:
                timeout_travel_to_main_screen_cnt = self.handle_timeout(
                    count=timeout_travel_to_main_screen_cnt,
                    timeout=timeout_travel_to_main_screen_max
                )
                found, position, image = self.search(
                    image=[file for file in self.image_tabs.keys()],
                    region=self.configurations["regions"]["travel"]["search_area"],
                    precision=self.configurations["parameters"]["travel"]["precision"],
                )
                if found:
                    tab = self.image_tabs[image]
                    self.logger.debug(
                        "It looks like the %(tab)s tab is open, attempting to close..." % {
                            "tab": tab,
                        }
                    )
                    self.click(
                        point=self.configurations["points"]["travel"]["tabs"][tab],
                        pause=self.configurations["parameters"]["travel"]["click_pause"],
                    )
                else:
                    # If nothing is found now... We can safely just
                    # assume that no tabs are open, breaking!
                    break
            # If a timeout error does occur, we'll continue to run, whatever is blocking us here
            # will likely be caught later on.
            except TimeoutError:
                self.logger.info(
                    "Unable to travel to the main screen in game, skipping..."
                )
                break

    def export_session(self, export_contents=None, original_contents=None, extra={}):
        """
        Export a session to the users licence backend.
        """
        self.logger.info(
            "Attempting to export session now..."
        )
        self.license.export_session(
            export_contents=export_contents,
            original_contents=original_contents,
            extra={
                "version": self.application_version,
                "configuration": self.configuration["configuration_name"],
                "abyssal": self.configuration["abyssal"],
                "window": self.window.__str__(),
            }
        )

    def export_prestige(self, prestige_contents):
        self.logger.info(
            "Attempting to export prestige now..."
        )
        self.license.export_prestige(
            prestige_contents=prestige_contents,
        )

    def run_checks(self):
        """
        Helper method to run checks against current bot state, this is in its own method so it can be ran in the main loop,
        as well as in our startup execution functions...
        """
        while self.pause_func():
            if self.stop_func() or self.force_stop_func():
                raise StoppedException
            if not self.pause_date:
                self.pause_date = datetime.datetime.now()
                self.toast_func(
                    title="Session",
                    message="Session Paused Successfully...",
                    duration=5,
                )
            # Currently paused through the GUI.
            # Just wait and sleep slightly in between checks.
            if self.stream.last_message != "Paused...":
                self.logger.info(
                    "Paused..."
                )
            time.sleep(self.configurations["global"]["pause"]["pause_check_interval"])

        if self.pause_date:
            # We were paused before, fixup our schedule and then
            # we'll resume.
            self.schedule.pad_jobs(timedelta=datetime.datetime.now() - self.pause_date)
            self.pause_date = None
        # Check for explicit prestige force...
        if self.force_prestige_func():
            self.force_prestige_func(_set=True)
            self.prestige()
        if self.force_stop_func():
            self.force_stop_func(_set=True)
            # Just raise a stopped exception if we
            # are just exiting and it's found in between
            # function execution.
            raise StoppedException
        if self.stop_func():
            raise StoppedException

    def run(self):
        """
        Begin main runtime loop for bot functionality.
        """
        self.logger.info("===================================================================================")
        self.logger.info("%(application_name)s (v%(application_version)s) Initialized..." % {
            "application_name": self.application_name,
            "application_version": self.application_version,
        })
        self.logger.info("Configuration: %(configuration)s" % {
            "configuration": self.configuration["configuration_name"],
        })
        self.logger.info("Experimental Configurations: %(experimental_configurations)s" % {
            "experimental_configurations": self.license.license_data["experimental"],
        })
        self.logger.info("Window: %(window)s" % {
            "window": self.window,
        })
        self.logger.info("Session: %(session)s" % {
            "session": self.session,
        })
        self.logger.info("License: %(license)s - %(expiration)s" % {
            "license": self.license.license,
            "expiration": self.license.expiration,
        })
        self.logger.info("===================================================================================")
        self.toast_func(
            title="Session",
            message="Session Initialized Successfully..."
        )

        try:
            self.configure_additional()
            # Ensure that a session is still available even if data
            # exports are disabled.
            if not self.configuration["export_data_enabled"]:
                self.export_session()
            # Any functions that should be ran once on startup
            # can be handled at this point.
            self.execute_startup_functions()
            # Right before running, make sure any scheduled functions
            # are configured properly.
            self.schedule_functions()

            # Main catch all for our manual stops, fail-safes are caught within
            # actual api calls instead of here...
            while not self.stop_func() and not self.force_stop_func():
                try:
                    self.run_checks()
                    self.schedule.run_pending()
                except PausedException:
                    # Paused exception could be raised through the scheduler, in which
                    # case, we'll pass here but the next iteration should catch that and
                    # we wont keep running until resumed (or stopped).
                    pass
            self.toast_func(
                title="Session",
                message="Session Stopped Successfully...",
                duration=5,
            )
        # Catch any explicit exceptions, these are useful so that we can
        # log custom error messages or deal with certain cases before running
        # through our "finally" block below.
        except GameStateException:
            self.logger.info(
                "A game state exception was encountered, ending session now..."
            )
            self.toast_func(
                title="Game State Exception",
                message="Game State Exception Encountered, Ending Session Now...",
                duration=5
            )
        except FailSafeException:
            self.logger.info(
                "A failsafe exception was encountered, ending session now... You can disable this functionality by "
                "toggling the settings in your local settings. Note, disabling the failsafe may make it more difficult to shut down "
                "a session while it is in the middle of a function."
            )
            self.toast_func(
                title="Failsafe Exception",
                message="Failsafe Exception Encountered, Ending Session Now...",
                duration=5
            )
        except ExportContentsException:
            self.logger.info(
                "An error occurred while attempting to export data from the game."
            )
            self.toast_func(
                title="Export Contents Exception",
                message="Export Contents Exception Encountered, Ending Session Now...",
                duration=5
            )
        except KeyError as err:
            self.logger.info(
                "It looks like a required configuration key \"%(key)s\" is either malformed or missing... Please contact support "
                "or make sure to visit the discord to determine if any server maintenance is actively being performed." % {
                    "key": err,
                }
            )
            self.toast_func(
                title="Missing Key",
                message="KeyError Encountered, Ending Session Now...",
                duration=7,
            )
        except LicenseAuthenticationError:
            self.logger.info(
                "An authentication error has occurred. Ending session now..."
            )
            self.toast_func(
                title="License Authentication Error",
                message="Authentication Error Encountered. Ending Session Now...",
                duration=7
            )
        except StoppedException:
            # Pass when stopped exception is encountered, skip right to our
            # finally block to handle logging and cleanup.
            self.toast_func(
                title="Session",
                message="Session Stopped Successfully...",
                duration=5,
            )
        except Exception:
            self.logger.info(
                "An unknown exception was encountered... The error has been reported to the support team."
            )
            sentry_sdk.capture_exception()
        finally:
            # Log some additional information now that our session is ending. This
            # information should be displayed regardless of the reason that caused
            # our termination of this instance.
            self.logger.info("===================================================================================")
            self.logger.info(
                "Your session has ended, thank you for using the %(application_name)s, if you run into any issues "
                "or require additional support, please contact the support team, or join our discord server: "
                "%(application_discord)s." % {
                    "application_name": self.application_name.lower(),
                    "application_discord": self.application_discord,
                },
            )
            self.logger.info("License: %(license)s" % {
                "license": self.license.license,
            })
            self.logger.info("Session: %(session)s" % {
                "session": self.session,
            })
            self.logger.info("===================================================================================")
            # Ensure we set our license to an offline state.
            # This is done when the session is completely ended.
            self.license.offline()
