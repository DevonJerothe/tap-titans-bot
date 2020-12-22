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
        stop_func,
        pause_func,
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

        # stop_func is used to correctly handle our threading functionality.
        # A ``bot`` is initialized through some method that invokes a new thread.
        # We require an argument that should represent a function to determine when to exit.
        self.stop_func = stop_func
        # pause_func is used to correctly handle pause/resume functionality.
        # Function is used to determine when pause and resume should take
        # place during runtime.
        self.pause_func = pause_func
        self.pause_date = None

        # Custom scheduler is used currently to handle
        # stop_func functionality when running pending
        # jobs, this avoids large delays when waiting
        # to pause/stop
        self.schedule = TitanScheduler()

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
                    "Invalid license entered. Double check your license and please try again."
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
                enable_failsafe=self.configuration["failsafe_enabled"],
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
        }

        tiers = [
            tier for tier, enabled in [
                ("s", self.configuration["artifacts_upgrade_tier_s"]),
                ("a", self.configuration["artifacts_upgrade_tier_a"]),
                ("b", self.configuration["artifacts_upgrade_tier_b"]),
                ("c", self.configuration["artifacts_upgrade_tier_c"]),
            ] if enabled
        ]

        upgrade_artifacts = [art for key, val in self.configurations["artifacts"].items() for art in val if key in tiers]
        if self.configuration["artifacts_upgrade_artifact"]:
            for artifact in self.configuration["artifacts_upgrade_artifact"].split(","):
                if artifact not in upgrade_artifacts:
                    upgrade_artifacts.append(artifact)
        if self.configuration["artifacts_ignore_artifact"]:
            for artifact in self.configuration["artifacts_ignore_artifact"].split(","):
                if artifact in upgrade_artifacts:
                    upgrade_artifacts.pop(upgrade_artifacts.index(artifact))
        if self.configuration["artifacts_remove_max_level"]:
            upgrade_artifacts = [art for art in upgrade_artifacts if art not in self.configurations["artifacts_max"]]
        if self.configuration["artifacts_shuffle"]:
            random.shuffle(upgrade_artifacts)

        # Artifacts Data.
        # ------------------
        # "upgrade_artifacts" - cycled (iter) if available.
        # "next_artifact_upgrade" - first available from "upgrade_artifacts" if available.
        self.upgrade_artifacts = cycle(upgrade_artifacts) if upgrade_artifacts else None
        self.next_artifact_upgrade = next(self.upgrade_artifacts) if upgrade_artifacts else None

        # Per Prestige Data.
        # ------------------
        # "master_levelled" - Store a flag to denote the master being levelled.
        self.master_levelled = False

        self.logger.debug(
            "Additional Configurations: Loaded..."
        )
        self.logger.debug("\"upgrade_artifacts\": %s" % upgrade_artifacts)
        self.logger.debug("\"next_artifact_upgrade\": %s" % self.next_artifact_upgrade)
        self.logger.debug("\"master_levelled\": %s" % self.master_levelled)

    def schedule_functions(self):
        """
        Loop through each available function used during runtime, setting up
        and configuring a scheduler for each one.
        """
        self.schedule.clear()

        for function, data in {
            self.check_game_state: {
                "enabled": self.configuration["crash_recovery_enabled"],
                "interval": self.configurations["global"]["check_game_state"]["check_game_state_interval"],
            },
            self.check_license: {
                "enabled": self.configurations["global"]["check_license"]["check_license_enabled"],
                "interval": self.configurations["global"]["check_license"]["check_license_interval"],
            },
            self.export_data: {
                "enabled": self.configuration["export_data_enabled"],
                "interval": self.configuration["export_data_interval"],
            },
            self.tap: {
                "enabled": self.configuration["tapping_enabled"],
                "interval": self.configuration["tapping_interval"],
            },
            self.fight_boss: {
                "enabled": self.configurations["global"]["fight_boss"]["fight_boss_enabled"],
                "interval": self.configurations["global"]["fight_boss"]["fight_boss_interval"],
            },
            self.eggs: {
                "enabled": self.configurations["global"]["eggs"]["eggs_enabled"],
                "interval": self.configurations["global"]["eggs"]["eggs_interval"],
            },
            self.inbox: {
                "enabled": self.configurations["global"]["inbox"]["inbox_enabled"],
                "interval": self.configurations["global"]["inbox"]["inbox_interval"],
            },
            self.daily_rewards: {
                "enabled": self.configurations["global"]["daily_rewards"]["daily_rewards_enabled"],
                "interval": self.configurations["global"]["daily_rewards"]["daily_rewards_interval"],
            },
            self.achievements: {
                "enabled": self.configurations["global"]["achievements"]["achievements_enabled"],
                "interval": self.configurations["global"]["achievements"]["achievements_interval"],
            },
            self.level_master: {
                "enabled": self.configuration["level_master_enabled"],
                "interval": self.configuration["level_master_interval"],
            },
            self.level_skills: {
                "enabled": self.configuration["level_skills_enabled"],
                "interval": self.configuration["level_skills_interval"],
            },
            self.activate_skills: {
                "enabled": self.configuration["activate_skills_enabled"],
                "interval": self.configuration["activate_skills_interval"],
            },
            self.level_heroes: {
                "enabled": self.configuration["level_heroes_enabled"],
                "interval": self.configuration["level_heroes_interval"],
            },
            self.perks: {
                "enabled": self.configuration["perks_enabled"],
                "interval": self.configuration["perks_interval"],
            },
            self.prestige: {
                "enabled": self.configuration["prestige_time_enabled"],
                "interval": self.configuration["prestige_time_interval"],
            },
            self.prestige_close_to_max: {
                "enabled": self.configuration["prestige_close_to_max_enabled"],
                "interval": self.configurations["global"]["prestige_close_to_max"]["prestige_close_to_max_interval"],
            },
        }.items():
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
            tags = list(tags)
        for tag in tags:
            self.schedule.clear(tag)

    def execute_startup_functions(self):
        """
        Execute any functions that should be ran right away following a successful session start.
        """
        for function, data in {
            self.check_game_state: {
                "enabled": self.configuration["crash_recovery_enabled"],
                "execute": self.configurations["global"]["check_game_state"]["check_game_state_on_start"],
            },
            self.export_data: {
                "enabled": self.configuration["export_data_enabled"],
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
            self.level_heroes: {
                "enabled": self.configuration["level_heroes_enabled"],
                "execute": self.configuration["level_heroes_on_start"],
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
                function()

    @staticmethod
    def handle_timeout(
        count,
        timeout,
    ):
        """
        Handle function timeouts throughout bot execution.

        The given count is incremented by one and checked to see
        if we have exceeded the specified dynamic timeout.
        """
        count += 1

        if count <= timeout:
            return count

        # Raising a timeout error if the specified count is over
        # our timeout after incrementing it by one.
        raise TimeoutError()

    def check_game_state(self):
        """
        Perform a check on the emulator to determine whether or not the game state is no longer
        in a valid place to derive that the game is still running. The emulator may crash
        during runtime, we can at least attempt to recover.
        """
        timeout_check_game_state_cnt = 0
        timeout_check_game_state_max = self.configurations["parameters"]["check_game_state"]["check_game_state_timeout"]

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
                    timeout_check_game_state_cnt = self.handle_timeout(
                        count=timeout_check_game_state_cnt,
                        timeout=timeout_check_game_state_max,
                    )
                    # Pause slightly in between our checks...
                    # We don't wanna check too quickly.
                    time.sleep(self.configurations["parameters"]["check_game_state"]["check_game_state_pause"])
                else:
                    # Game state is fine, exit with no errors.
                    break
            except TimeoutError:
                self.logger.info(
                    "Unable to derive current game state, attempting to recover and restart application..."
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
            self.license.retrieve()
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
                    self.logger.debug(
                        "Image: \"%(image)s\" was found." % {
                            "image": i,
                        }
                    )
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
        latest = self.snapshot(region=region)
        return latest, compare_images(
            image_one=image,
            image_two=latest,
        )

    def point_is_color(
        self,
        point,
        color,
    ):
        """
        Check that a specific point is currently a certain color.
        """
        return self.snapshot().getpixel(
            xy=tuple(point),
        ) == tuple(color)

    def point_is_color_range(
        self,
        point,
        color_range,
    ):
        """
        Check that a specific point is currently within a color range.
        """
        pixel = self.snapshot().getpixel(
            xy=tuple(point),
        )
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

    def click(
        self,
        point,
        window=None,
        clicks=1,
        interval=0.0,
        button="left",
        offset=5,
        pause=0.001,
    ):
        """
        Perform a click on the current window.
        """
        if not window:
            window = self.window
        window.click(
            point=point,
            clicks=clicks,
            interval=interval,
            button=button,
            offset=offset,
            pause=pause,
        )

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
    ):
        """
        Attempt to find and click on the specified image on the current window.
        """
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
        return found

    def drag(
        self,
        start,
        end,
        button="left",
        pause=0.0,
    ):
        """
        Perform a drag on the current window.
        """
        self.window.drag(
            start=start,
            end=end,
            button=button,
            pause=pause,
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
        timeout_fight_boss_cnt = 0
        timeout_fight_boss_max = self.configurations["parameters"]["fight_boss"]["fight_boss_timeout"]

        if not self.search(
            image=self.files["fight_boss_icon"],
            region=self.configurations["regions"]["fight_boss"]["search_area"],
            precision=self.configurations["parameters"]["fight_boss"]["search_precision"]
        )[0]:
            # Return early, boss fight is already in progress.
            # or, we're almost at another fight, in which case,
            # we can just keep going.
            return
        else:
            while self.search(
                image=self.files["fight_boss_icon"],
                region=self.configurations["regions"]["fight_boss"]["search_area"],
                precision=self.configurations["parameters"]["fight_boss"]["search_precision"],
            )[0]:
                try:
                    self.logger.info(
                        "Attempting to initiate boss fight..."
                    )
                    self.find_and_click_image(
                        image=self.files["fight_boss_icon"],
                        region=self.configurations["regions"]["fight_boss"]["search_area"],
                        precision=self.configurations["parameters"]["fight_boss"]["search_precision"],
                    )
                    time.sleep(self.configurations["parameters"]["fight_boss"]["search_not_found_pause"])
                    timeout_fight_boss_cnt = self.handle_timeout(
                        count=timeout_fight_boss_cnt,
                        timeout=timeout_fight_boss_max,
                    )
                except TimeoutError:
                    self.logger.info(
                        "Boss fight could not be initiated, skipping..."
                    )
                    return
            self.logger.info(
                "Boss fight initiated..."
            )

    def leave_boss(self):
        """
        Ensure a boss is not being fought currently.
        """
        timeout_leave_boss_cnt = 0
        timeout_leave_boss_max = self.configurations["parameters"]["leave_boss"]["leave_boss_timeout"]

        while not self.search(
            image=self.files["fight_boss_icon"],
            region=self.configurations["regions"]["fight_boss"]["search_area"],
            precision=self.configurations["parameters"]["fight_boss"]["search_precision"],
        )[0]:
            try:
                self.find_and_click_image(
                    image=self.files["leave_boss_icon"],
                    region=self.configurations["regions"]["leave_boss"]["search_area"],
                    precision=self.configurations["parameters"]["leave_boss"]["search_precision"],
                )
                # Always perform the pause sleep, regardless of the image being found.
                time.sleep(self.configurations["parameters"]["leave_boss"]["search_pause"])
                timeout_leave_boss_cnt = self.handle_timeout(
                    count=timeout_leave_boss_cnt,
                    timeout=timeout_leave_boss_max,
                )
            except TimeoutError:
                self.logger.info(
                    "Boss fight is not currently in progress, continuing..."
                )
                return
        self.logger.info(
            "Boss fight is now not active..."
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
                # (This is done through pi-hole, unrelated to our code here).
                if self.configuration["ad_blocking_enabled"]:
                    self.logger.info(
                        "Attempting to collect ad rewards through pi-hole disabled ads..."
                    )
                    try:
                        timeout_fairy_ad_block_cnt = 0
                        timeout_fairy_ad_block_max = self.configurations["parameters"]["fairies"]["ad_block_timeout"]

                        while not self.search(
                            image=self.files["fairies_collect"],
                            region=self.configurations["regions"]["fairies"]["ad_block_collect_area"],
                            precision=self.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                        )[0]:
                            self.click(
                                point=self.configurations["points"]["fairies"]["collect_or_watch"],
                                pause=self.configurations["parameters"]["fairies"]["ad_block_pause"],
                            )
                            timeout_fairy_ad_block_cnt = self.handle_timeout(
                                count=timeout_fairy_ad_block_cnt,
                                timeout=timeout_fairy_ad_block_max,
                            )
                    except TimeoutError:
                        self.logger.info(
                            "Unable to handle fairy ad through ad blocking mechanism, skipping..."
                        )
                        self.click_image(
                            image=image,
                            position=no_thanks_pos,
                        )
                        return
                    self.find_and_click_image(
                        image=self.files["fairies_collect"],
                        region=self.configurations["regions"]["fairies"]["ad_block_collect_area"],
                        precision=self.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                        pause=self.configurations["parameters"]["fairies"]["ad_block_pause"],
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
                    else:
                        # Max level option isn't available,
                        # we'll go ahead and just try to level the skill
                        # to max.
                        self.click(
                            point=point,
                            clicks=self.configurations["parameters"]["level_skills"]["skills_max_level"],
                            interval=self.configurations["parameters"]["level_skills"]["level_clicks_interval"],
                            pause=self.configurations["parameters"]["level_skills"]["level_clicks_pause"],
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

    def level_heroes(self):
        """
        Level the heroes in game.
        """
        def level_heroes_on_screen():
            """
            Level all current heroes on the game screen.
            """
            # Make sure we're still on the heroes screen...
            self.travel_to_heroes(scroll=False, collapsed=False)
            self.logger.info(
                "Levelling heroes on screen now..."
            )
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

        clicks = self.configurations["parameters"]["level_heroes"]["hero_level_clicks"] if (
            not self.configuration["level_heroes_masteries_unlocked"]
        ) else 1

        found, position, image = self.search(
            image=self.files["heroes_max_level"],
            region=self.configurations["regions"]["level_heroes"]["max_level_search_area"],
            precision=self.configurations["parameters"]["level_heroes"]["max_level_search_precision"],
        )
        if found:
            self.logger.info(
                "Max levelled hero found, levelling first set of heroes only..."
            )
            level_heroes_on_screen()
        else:
            # Otherwise, we'll scroll and look for a max level hero,
            # or we will find a duplicate (bottom of tab) and just begin
            # levelling heroes.
            drag_heroes_panel(
                top=False,
                stop_on_max=True,
            )
            drag_heroes_panel(
                callback=level_heroes_on_screen,
            )

    def perks(self):
        """
        Perform all perk related functionality in game, using/purchasing perks if enabled.
        """
        self.travel_to_master(collapsed=False)
        self.logger.info(
            "Using perks in game..."
        )
        timeout_perks_search_cnt = 0
        timeout_perks_search_max = self.configurations["parameters"]["perks"]["icons_timeout"]

        # Travel to the bottom (ish) of the master tab, we'll scroll until
        # we've found the "clan crate" perk, since that's the last one available.
        try:
            while not self.search(
                image=self.files["perks_clan_crate"],
                region=self.configurations["regions"]["perks"]["icons_area"],
                precision=self.configurations["parameters"]["perks"]["icons_precision"],
            )[0]:
                self.drag(
                    start=self.configurations["points"]["travel"]["scroll"]["drag_bottom"],
                    end=self.configurations["points"]["travel"]["scroll"]["drag_top"],
                    pause=self.configurations["parameters"]["travel"]["drag_pause"],
                )
                timeout_perks_search_cnt = self.handle_timeout(
                    count=timeout_perks_search_cnt,
                    timeout=timeout_perks_search_max,
                )
        except TimeoutError:
            self.logger.info(
                "Unable to find the \"clan_crate\" perk in game, skipping perk functionality..."
            )
            return

        # We should be able to see all (or most) of the perks in game, clan crate is on the screen.
        # We'll search for each enabled perk, if it isn't found, we'll scroll up a bit.
        # Note: Reversing our list of enabled perks (bottom to top).
        for perk in [
            perk for perk, enabled in [
                ("clan_crate", self.configuration["perks_enable_clan_crate"]),
                ("doom", self.configuration["perks_enable_doom"]),
                ("mana_potion", self.configuration["perks_enable_mana_potion"]),
                ("make_it_rain", self.configuration["perks_enable_make_it_rain"]),
                ("adrenaline_rush", self.configuration["perks_enable_adrenaline_rush"]),
                ("power_of_swiping", self.configuration["perks_enable_power_of_swiping"]),
                ("mega_boost", self.configuration["perks_enable_mega_boost"]),
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
                    if self.configuration["ad_blocking_enabled"]:
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

    def prestige(self):
        """
        Perform a prestige in game, upgrading a specified artifact afterwards if enabled.
        """
        self.travel_to_master()
        self.leave_boss()

        self.logger.info(
            "Attempting to prestige in game now..."
        )
        self.export_prestige(prestige_contents={
            "upgradeArtifact": self.next_artifact_upgrade,
        })

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
                # Tournament is available and to be joined... Attempting to join and skip
                # prestige functionality below.
                self.click(
                    point=self.configurations["points"]["tournaments"]["tournaments_icon"],
                    pause=self.configurations["parameters"]["tournaments"]["icon_pause"],
                )
                if self.find_and_click_image(
                    image=self.files["tournaments_join"],
                    region=self.configurations["regions"]["tournaments"]["join_area"],
                    precision=self.configurations["parameters"]["tournaments"]["join_precision"],
                    pause=self.configurations["parameters"]["tournaments"]["join_pause"],
                ):
                    self.logger.info(
                        "Performing tournament prestige now..."
                    )
                    self.find_and_click_image(
                        image=self.files["prestige_confirm_confirm_icon"],
                        region=self.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                        precision=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                        clicks=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_clicks"],
                        interval=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_interval"],
                        pause=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_pause"],
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
            self.logger.info(
                "Performing prestige now..."
            )
            self.find_and_click_image(
                image=self.files["prestige_icon"],
                region=self.configurations["regions"]["prestige"]["prestige_icon_area"],
                precision=self.configurations["parameters"]["prestige"]["prestige_icon_precision"],
                pause=self.configurations["parameters"]["prestige"]["prestige_icon_pause"],
            )
            self.find_and_click_image(
                image=self.files["prestige_confirm_icon"],
                region=self.configurations["regions"]["prestige"]["prestige_confirm_icon_area"],
                precision=self.configurations["parameters"]["prestige"]["prestige_confirm_icon_precision"],
                pause=self.configurations["parameters"]["prestige"]["prestige_confirm_icon_pause"],
            )
            self.find_and_click_image(
                image=self.files["prestige_confirm_confirm_icon"],
                region=self.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                precision=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                clicks=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_clicks"],
                interval=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_interval"],
                pause=self.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_pause"],
            )
            # Waiting here through the confirm_confirm_icon_pause for the prestige
            # animation to be finished before moving on...
        if self.configuration["artifacts_enabled"]:
            self.travel_to_artifacts(collapsed=False)
            # Artifacts are enabled, we'll check for a couple of things,
            # enchantment/discovery followed by the actual upgrade of
            # a specified artifact.
            self.logger.info(
                "Beginning artifacts functionality..."
            )
            if self.configuration["artifacts_enchantment_enabled"]:
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
            if self.configuration["artifacts_discovery_enabled"]:
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
                        # Break if no header is found, no more artifacts can
                        # be discovered at this point.
                        else:
                            break
            if self.configuration["artifacts_upgrade_enabled"]:
                self.logger.info(
                    "Attempting to upgrade %(artifact)s artifact..." % {
                        "artifact": self.next_artifact_upgrade,
                    }
                )
                timeout_artifact_search_cnt = 0
                timeout_artifact_search_max = self.configurations["parameters"]["artifacts"]["timeout_search"]
                try:
                    while not self.search(
                        image=self.files["artifact_%(artifact)s" % {"artifact": self.next_artifact_upgrade}],
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
                        image=self.files["artifact_%(artifact)s" % {"artifact": self.next_artifact_upgrade}],
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
                        clicks=self.configurations["parameters"]["artifacts"]["upgrade_clicks"],
                        interval=self.configurations["parameters"]["artifacts"]["upgrade_interval"],
                        pause=self.configurations["parameters"]["artifacts"]["upgrade_pause"],
                    )
                except TimeoutError:
                    self.logger.info(
                        "Artifact: %(artifact)s could not be found on the screen, skipping upgrade..." % {
                            "artifact": self.next_artifact_upgrade,
                        }
                    )
        # Update the next artifact that will be upgraded.
        # This is done regardless of upgrade state (success/fail).
        self.next_artifact_upgrade = next(self.upgrade_artifacts) if self.upgrade_artifacts else None
        self.master_levelled = False

        # Once the prestige has finished, we need to update our most upto date
        # set of exported data, from here, we can then figure out whats changed
        # and send a new session event. If this isn't enabled, we at least get
        # a prestige sent along above.
        if self.configuration["export_data_enabled"]:
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
        prestige = False

        if self.configurations["global"]["events"]["event_running"]:
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
                prestige = True
        else:
            # No event is running, instead, we will open the skill tree,
            # and check that the reset icon is present.
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
                prestige = True
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
        if prestige:
            self.logger.info(
                "Prestige is ready..."
            )
            self.prestige_execute_or_schedule()

    def tap(self):
        """
        Perform taps on main game screen.
        """
        self.collapse()
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
        timeout_collapse_cnt = 0
        timeout_collapse_max = self.configurations["parameters"]["collapse"]["timeout_collapse"]

        while True:
            try:
                if self.find_and_click_image(
                    image=self.files["travel_collapse"],
                    region=self.configurations["regions"]["travel"]["collapse_area"],
                    precision=self.configurations["parameters"]["travel"]["uncollapse_precision"],
                ):
                    self.logger.debug(
                        "Panel has been successfully collapsed..."
                    )
                timeout_collapse_cnt = self.handle_timeout(
                    count=timeout_collapse_cnt,
                    timeout=timeout_collapse_max,
                )
                # Perform a very slight sleep in between checks.
                # Collapsing can be important and we don't want
                # any false positives to occur.
                time.sleep(self.configurations["parameters"]["collapse"]["collapse_loop_pause"])
            except TimeoutError:
                # Timeout error is used here to derive that no
                # panel is available to be collapsed at all.
                self.logger.debug(
                    "No panels could be found to collapse..."
                )
                break

    def export_data(self):
        """
        Open up the settings in game and export user data.

        This information contains a lot of very useful information, the information
        is saved to the users clipboard which we can access and store.
        """
        self.travel_to_master()

        # Opening up the master screen will make sure the export data
        # function has the most up to date information.
        self.logger.info(
            "Opening master page to ensure exported data is up to date..."
        )
        self.click(
            point=self.configurations["points"]["export_data"]["master_screen"],
            pause=self.configurations["parameters"]["export_data"]["master_screen_pause"],
        )
        while not self.find_and_click_image(
            image=self.files["large_exit"],
            region=self.configurations["regions"]["travel"]["exit_area"],
            precision=self.configurations["parameters"]["travel"]["exit_precision"],
            pause=self.configurations["parameters"]["travel"]["exit_pause"],
        ):
            time.sleep(self.configurations["parameters"]["travel"]["exit_pause"])

        self.logger.info(
            "Attempting to export data now..."
        )
        while not self.search(
            image=self.files["options_header"],
            region=self.configurations["regions"]["export_data"]["options_header_area"],
            precision=self.configurations["parameters"]["export_data"]["options_header_precision"],
        )[0]:
            self.click(
                point=self.configurations["points"]["export_data"]["options_icon"],
                pause=self.configurations["parameters"]["export_data"]["options_icon_pause"],
            )

        while not self.find_and_click_image(
            image=self.files["options_export"],
            region=self.configurations["regions"]["export_data"]["options_export_area"],
            precision=self.configurations["parameters"]["export_data"]["options_export_precision"],
            pause=self.configurations["parameters"]["export_data"]["options_export_pause"],
        ):
            time.sleep(self.configurations["parameters"]["export_data"]["options_export_pause"])
        while not self.find_and_click_image(
            image=self.files["large_exit"],
            region=self.configurations["regions"]["travel"]["exit_area"],
            precision=self.configurations["parameters"]["travel"]["exit_precision"],
            pause=self.configurations["parameters"]["travel"]["exit_pause"],
        ):
            time.sleep(self.configurations["parameters"]["travel"]["exit_pause"])

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
            self.export_contents = {
                "playerStats": contents["playerStats"],
                "artifacts": contents["artifacts"],
            }
            self.logger.info(
                "Exported data has been loaded successfully..."
            )
        except json.JSONDecodeError:
            raise ExportContentsException()

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

        timeout_click_cnt = 0
        timeout_click_max = self.configurations["parameters"]["travel"]["timeout_click"]
        timeout_collapse_cnt = 0
        timeout_collapse_max = self.configurations["parameters"]["travel"]["timeout_collapse"]
        timeout_drag_cnt = 0
        timeout_drag_max = self.configurations["parameters"]["travel"]["timeout_drag"]

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
            while not self.search(
                image=image,
                region=self.configurations["regions"]["travel"]["search_area"],
                precision=self.configurations["parameters"]["travel"]["precision"],
            )[0]:
                self.logger.debug(
                    "Could not find image: '%(image)s', attempting to click on tab and trying again..." % {
                        "image": image,
                    }
                )
                self.click(
                    point=self.configurations["points"]["travel"]["tabs"][tab],
                    pause=self.configurations["parameters"]["travel"]["click_pause"],
                )
                timeout_click_cnt = self.handle_timeout(
                    count=timeout_click_cnt,
                    timeout=timeout_click_max,
                )

            # Tab is open at this point. Perform the collapse, un-collapse functionality
            # before attempting to scroll to the top or bottom of a panel.
            if collapsed:
                # We want to "collapse" the panel, check if it's already
                # collapsed at this point.
                while not self.search(
                    image=self.files["travel_collapsed"],
                    region=self.configurations["regions"]["travel"]["collapsed_area"],
                    precision=self.configurations["parameters"]["travel"]["collapse_precision"],
                )[0]:
                    self.click(
                        point=self.configurations["points"]["travel"]["collapse"],
                        pause=self.configurations["parameters"]["travel"]["collapse_pause"],
                    )
                    timeout_collapse_cnt = self.handle_timeout(
                        count=timeout_collapse_cnt,
                        timeout=timeout_collapse_max,
                    )
            else:
                # We want to "uncollapse" the panel, check if it's already
                # uncollapsed at this point.
                while not self.search(
                    image=self.files["travel_collapse"],
                    region=self.configurations["regions"]["travel"]["collapse_area"],
                    precision=self.configurations["parameters"]["travel"]["uncollapse_precision"],
                )[0]:
                    self.click(
                        point=self.configurations["points"]["travel"]["uncollapse"],
                        pause=self.configurations["parameters"]["travel"]["uncollapse_pause"],
                    )
                    timeout_collapse_cnt = self.handle_timeout(
                        count=timeout_collapse_cnt,
                        timeout=timeout_collapse_max,
                    )

            if scroll:
                scroll_img = self.files.get("travel_%(tab)s_%(scroll_key)s" % {
                    "tab": tab,
                    "scroll_key": "scroll_top" if top else "scroll_bottom",
                })

                # If a scroll image is available, we can drag and check for the image
                # being present to determine the top or bottom state of a tab.
                if scroll_img:
                    while not self.search(
                        image=scroll_img,
                        precision=self.configurations["parameters"]["travel"]["scroll_precision"],
                    )[0]:
                        self.drag(
                            start=self.configurations["points"]["travel"]["scroll"]["drag_top" if top else "drag_bottom"],
                            end=self.configurations["points"]["travel"]["scroll"]["drag_bottom" if top else "drag_top"],
                            pause=self.configurations["parameters"]["travel"]["drag_pause"],
                        )
                        timeout_drag_cnt = self.handle_timeout(
                            count=timeout_drag_cnt,
                            timeout=timeout_drag_max,
                        )
                # If no scroll image is present for the tab, we fallback to handling the
                # top and bottom check through an image duplication check.
                else:
                    img = None
                    while True:
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
    ):
        """
        Travel to the artifacts tab in game.
        """
        self.travel(
            tab="artifacts",
            image=self.files["travel_artifacts_icon"],
            scroll=scroll,
            collapsed=collapsed,
            top=top,
        )

    def travel_to_main_screen(self):
        """
        Travel to the main game screen (no tabs open) in game.
        """
        while True:
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

            while not self.stop_func():
                try:
                    if self.pause_func():
                        if not self.pause_date:
                            self.pause_date = datetime.datetime.now()
                        # Currently paused through the GUI.
                        # Just wait and sleep slightly in between checks.
                        if self.stream.last_message != "Paused...":
                            self.logger.info(
                                "Paused..."
                            )
                        time.sleep(self.configurations["global"]["pause"]["pause_check_interval"])
                    else:
                        if self.pause_date:
                            # We were paused before, fixup our schedule and then
                            # we'll resume.
                            self.schedule.pad_jobs(timedelta=datetime.datetime.now() - self.pause_date)
                            self.pause_date = None
                        # Ensure any pending scheduled jobs are executed at the beginning
                        # of our loop, each time.
                        self.schedule.run_pending()
                except PausedException:
                    # Paused exception could be raised through the scheduler, in which
                    # case, we'll pass here but the next iteration should catch that and
                    # we wont keep running until resumed (or stopped).
                    pass

        # Catch any explicit exceptions, these are useful so that we can
        # log custom error messages or deal with certain cases before running
        # through our "finally" block below.
        except GameStateException:
            self.logger.info(
                "A game state exception was encountered, ending session now..."
            )
        except FailSafeException:
            self.logger.info(
                "A failsafe exception was encountered, ending session now... You can disable this functionality by "
                "updating your configuration. Note, disabling the failsafe may make it more difficult to shut down "
                "a session while it is in the middle of a function."
            )
        except ExportContentsException:
            self.logger.info(
                "An error occurred while attempting to export data from the game."
            )
        except KeyError as err:
            self.logger.info(
                "It looks like a required configuration key (%(key)s) is either malformed or missing... "
                "Please contact support or make sure to visit the discord to determine if any server maintenance "
                "is actively being performed." % {
                    "key": err,
                }
            )
        except LicenseAuthenticationError:
            self.logger.info(
                "An authentication error has occurred. Ending session now..."
            )
        except StoppedException:
            # Pass when stopped exception is encountered, skip right to our
            # finally block to handle logging and cleanup.
            pass
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
