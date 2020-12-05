from license_validator.exceptions import (
    LicenseRetrievalError,
    LicenseExpirationError,
    LicenseServerError,
    LicenseConnectionError,
    LicenseIntegrityError,
)

from bot.core.window import WindowHandler, WindowNotFoundError
from bot.core.imagesearch import image_search_area, click_image
from bot.core.decorators import event
from bot.core.exceptions import LicenseAuthenticationError, GameStateException
from bot.core.utilities import (
    create_logger,
    decrypt_secret,
    most_common_result,
    calculate_percent,
)

from itertools import cycle
from pyautogui import FailSafeException
from pytesseract import pytesseract
from PIL import Image

import sentry_sdk
import imagehash
import schedule
import random
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

        self.files = {}           # Program Files.
        self.configurations = {}  # Global Program Configurations
        self.configuration = {}   # Local Bot Configurations.

        # stop_func is used to correctly handle our threading functionality.
        # A ``bot`` is initialized through some method that invokes a new thread.
        # We require an argument that should represent a function to determine when to exit.
        self.stop_func = stop_func
        # pause_func is used to correctly handle pause/resume functionality.
        # Function is used to determine when pause and resume should take
        # place during runtime.
        self.pause_func = pause_func

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

        # Handle some of the local configuration functionality early (prior to license checks)
        # so that we can make sure the window is actually opened before doing anything else.
        self.configure_configuration()

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
            raise SystemExit

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
                self.license.retrieve(logger=self.logger)
                self.license.online()
                self.logger.info(
                    "Your license has been requested and validated successfully!"
                )
                self.logger.debug(
                    self.license.license_data
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
        self.configure_configurations()
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
        with open(self.license.program_configuration_file, mode="r") as file:
            self.configuration = json.loads(file.read())
        self.logger.debug(
            "Local Configuration: Loaded..."
        )

    def configure_dependencies(self):
        """
        Configure the dependencies used by the bot.
        """
        self.logger.info("Configuring dependencies...")
        # For our purposes, we definitely need our pytesseract to be initialized
        # using the correct directory, we can expect it to be present in the
        # dependencies directory for our application.
        pytesseract.tesseract_cmd = os.path.join(
            self.license.program_dependencies_directory,
            "tesseract",
            "tesseract.exe",
        )
        self.logger.debug(
            "Dependencies: Loaded..."
        )
        self.logger.debug("Tesseract CMD: %(tesseract_cmd)s" % {
            "tesseract_cmd": pytesseract.tesseract_cmd,
        })

    def configure_files(self):
        """
        Configure the files available and used by the bot.
        """
        self.logger.info("Configuring files...")
        # Our local license/application directory should contain a directory of images
        # with their versions, the bot does not care about the versions other than making
        # sure the most recent one is being used. We handle that logic here.
        with os.scandir(self.license.program_files_directory) as scan:
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
        with open(self.license.program_configurations_file, mode="r") as file:
            self.configurations = json.loads(decrypt_secret(file.read()))
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
        tiers = [tier for tier, enabled in self.configuration["artifacts_upgrade_tier"].items() if enabled]
        upgrade_artifacts = [art for key, val in self.configurations["artifacts"].items() for art in val if key in tiers]
        if self.configuration["artifacts_upgrade_artifact"]:
            for artifact in self.configuration["artifacts_upgrade_artifact"].split(","):
                if artifact not in upgrade_artifacts:
                    upgrade_artifacts.append(artifact)

        # ARTIFACTS INFO.
        self.upgrade_artifacts = cycle(upgrade_artifacts) if upgrade_artifacts else None
        self.next_artifact_upgrade = next(self.upgrade_artifacts) if upgrade_artifacts else None
        # SESSION LEVEL INFO.
        self.current_stage = None
        self.max_stage = None
        # PER PRESTIGE INFO.
        self.master_levelled = False

        # Log some information about the additional configurations
        # that have been parsed out.
        self.logger.info(
            "====================================================================="
        )
        self.logger.info(
            "Additional configurations initialized..."
        )
        self.logger.info(
            "---------------------------------------------------------------------"
        )
        self.logger.info(
            "Artifacts:"
        )
        self.logger.info(
            "upgrade_artifacts: %(upgrade_artifacts)s." % {
                "upgrade_artifacts": ", ".join(upgrade_artifacts) if upgrade_artifacts else None
            }
        )
        self.logger.info(
            "next_artifact_upgrade: %(next_artifact_upgrade)s." % {
                "next_artifact_upgrade": self.next_artifact_upgrade,
            }
        )
        self.logger.info(
            "---------------------------------------------------------------------"
        )
        self.logger.info(
            "Session:"
        )
        self.logger.info(
            "current_stage: %(current_stage)s" % {
                "current_stage": self.current_stage,
            }
        )
        self.logger.info(
            "max_stage: %(max_stage)s" % {
                "max_stage": self.max_stage,
            }
        )
        self.logger.info(
            "---------------------------------------------------------------------"
        )
        self.logger.info(
            "Per Prestige:"
        )
        self.logger.info(
            "master_levelled: %(master_levelled)s" % {
                "master_levelled": self.master_levelled,
            }
        )
        self.logger.info(
            "====================================================================="
        )

    def schedule_functions(self):
        """
        Loop through each available function used during runtime, setting up
        and configuring a scheduler for each one.
        """
        schedule.clear()

        for function, data in {
            self.check_game_state: {
                "enabled": self.configuration["crash_recovery_enabled"],
                "interval": self.configurations["global"]["check_game_state"]["check_game_state_interval"],
            },
            self.check_license: {
                "enabled": self.configurations["global"]["check_license"]["check_license_enabled"],
                "interval": self.configurations["global"]["check_license"]["check_license_interval"],
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
            self.prestige: {
                "enabled": self.configuration["prestige_time_enabled"],
                "interval": self.configuration["prestige_time_interval"],
            },
            self.prestige_stage: {
                "enabled": self.configuration["prestige_stage_enabled"],
                "interval": self.configurations["global"]["prestige_stage"]["prestige_stage_interval"],
            },
            self.prestige_close_to_max: {
                "enabled": self.configuration["prestige_close_to_max_enabled"],
                "interval": self.configurations["global"]["prestige_close_to_max"]["prestige_close_to_max_interval"],
            },
            self.prestige_percent_of_max_stage: {
                "enabled": self.configuration["prestige_percent_of_max_stage_enabled"],
                "interval": self.configurations["global"]["prestige_percent_of_max_stage"]["prestige_percent_of_max_stage_interval"]
            },
        }.items():
            if data["enabled"]:
                self.schedule_function(
                    function=function,
                    interval=data["interval"],
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
        schedule.every(interval=interval).seconds.do(job_func=function).tag(function.__name__)

    @staticmethod
    def cancel_scheduled_function(tags):
        """
        Cancel a scheduled function if currently scheduled to run.
        """
        if not isinstance(tags, list):
            tags = list(tags)
        for tag in tags:
            schedule.clear(tag)

    def execute_startup_functions(self):
        """
        Execute any functions that should be ran right away following a successful session start.
        """
        for function, data in {
            self.check_game_state: {
                "enabled": self.configuration["crash_recovery_enabled"],
                "execute": self.configurations["global"]["check_game_state"]["check_game_state_on_start"],
            },
            self.fight_boss: {
                "enabled": self.configurations["global"]["fight_boss"]["fight_boss_enabled"],
                "execute": self.configurations["global"]["fight_boss"]["fight_boss_on_start"],
            },
            self.eggs: {
                "enabled": self.configurations["global"]["eggs"]["eggs_enabled"],
                "execute": self.configurations["global"]["eggs"]["eggs_on_start"],
            },
            self.inbox: {
                "enabled": self.configurations["global"]["inbox"]["inbox_enabled"],
                "execute": self.configurations["global"]["inbox"]["inbox_on_start"],
            },
            self.parse_max_stage: {
                "enabled": self.configuration["prestige_percent_of_max_stage_enabled"],
                "execute": self.configuration["prestige_percent_of_max_stage_enabled"],
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

        # Attempting to travel to the main screen
        # in game. This will for sure have our
        # game state icons, and likely some of the
        # travel icons.
        self.travel_to_main_screen()

        while True:
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
                        self.files["game_state_coin"],
                        self.files["game_state_master"],
                        self.files["game_state_relics"],
                        self.files["game_state_settings"],
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
                if not self.window.form:
                    self.logger.info(
                        "Emulator \"form\" instance not found, terminating instance now... If you are not using a Nox emulator, "
                        "this is the most likely reason why this process did not work, if you are using Nox and still encountering "
                        "this error, contact the support team for additional help."
                    )
                else:
                    self.click(
                        window=self.window.form,
                        point=self.configurations["points"]["check_game_state"]["home_point"],
                        pause=self.configurations["parameters"]["check_game_state"]["home_pause"],
                        offset=self.configurations["parameters"]["check_game_state"]["home_offset"],
                    )
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
        cutoff=2,
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
        return latest, (
            imagehash.average_hash(image=image) -
            imagehash.average_hash(image=latest)
        ) < cutoff

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
        pause=0.0,
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
            offset=offset,
            pause=pause,
        )

    def parse_max_stage(self):
        """
        Attempt to retrieve the current max stage that a user has reached.
        """
        if self.configuration["prestige_percent_of_max_stage_percent_use_manual_ms"]:
            self.logger.info(
                "Prestige of max stage percent is set to use a manually set maximum stage, using "
                "this value instead of parsing the stage from game..."
            )
            self.max_stage = self.configuration["prestige_percent_of_max_stage_percent_use_manual_ms"]
        else:
            self.travel_to_master()
            self.logger.info(
                "Attempting to parse current max stage from game..."
            )
            self.find_and_click_image(
                image=self.files["travel_master_scroll_top"],
                region=self.configurations["regions"]["parse_max_stage"]["master_icon_area"],
                precision=self.configurations["parameters"]["parse_max_stage"]["master_icon_precision"],
                pause=self.configurations["parameters"]["parse_max_stage"]["master_icon_pause"],
            )
            results = []
            loops = self.configurations["parameters"]["parse_max_stage"]["result_loops"]
            # Loop and gather results about the max stage...
            # We do this multiple times to try and stave off any false
            # positives, we'll use the most common result as our final.
            for i in range(loops):
                result = pytesseract.image_to_string(
                    image=self.process(
                        region=self.configurations["regions"]["parse_max_stage"]["max_stage_area"],
                        scale=self.configurations["parameters"]["parse_max_stage"]["scale"],
                        threshold=self.configurations["parameters"]["parse_max_stage"]["threshold"],
                        invert=self.configurations["parameters"]["parse_max_stage"]["invert"],
                    ),
                    config="--psm 7 --oem 0 nobatch",
                )
                self.logger.debug(
                    "Result %(loop)s/%(loops)s: \"%(result)s\"..." % {
                        "loop": i,
                        "loops": loops,
                        "result": result
                    }
                )
                result = "".join(filter(str.isdigit, result))
                result = int(result) if result else None
                # Ensure result is a valid amount, based on hard configurations
                # and user configurations (if specified).
                parse_min = self.configuration["stage_parsing_minimum"] or -100000
                parse_max = self.configuration["stage_parsing_maximum"] or 9999999
                if (
                    result
                    and parse_min <= result <= parse_max
                    and result <= self.configurations["global"]["game"]["max_stage"]
                ):
                    results.append(result)
            self.max_stage = most_common_result(
                results=results,
            )
            self.logger.info(
                "Maximum Stage: %(maximum_stage)s..." % {
                    "maximum_stage": self.max_stage,
                }
            )
            self.find_and_click_image(
                image=self.files["large_exit"],
                region=self.configurations["regions"]["parse_max_stage"]["exit_area"],
                precision=self.configurations["parameters"]["parse_max_stage"]["exit_precision"],
                pause=self.configurations["parameters"]["parse_max_stage"]["exit_pause"],
            )

    def parse_current_stage(self):
        """
        Attempt to retrieve the current stage that the user is on in game.
        """
        self.collapse()
        self.logger.info(
            "Attempting to parse current stage from game..."
        )
        results = []
        loops = self.configurations["parameters"]["parse_current_stage"]["result_loops"]
        # Loop and gather results about the current stage...
        # We do this multiple times to try and stave off any false
        # positives, we'll use the most common result as our final.
        for i in range(loops):
            result = pytesseract.image_to_string(
                image=self.process(
                    region=self.configurations["regions"]["parse_current_stage"]["current_stage_area"],
                    scale=self.configurations["parameters"]["parse_current_stage"]["scale"],
                    threshold=self.configurations["parameters"]["parse_current_stage"]["threshold"],
                    invert=self.configurations["parameters"]["parse_current_stage"]["invert"],
                ),
                config="--psm 7 --oem 0 nobatch",
            )
            self.logger.debug(
                "Result %(loop)s/%(loops)s: \"%(result)s\"..." % {
                    "loop": i,
                    "loops": loops,
                    "result": result
                }
            )
            result = "".join(filter(str.isdigit, result))
            result = int(result) if result else None
            # Ensure result is a valid amount, based on hard configurations
            # and user configurations (if specified).
            parse_min = self.configuration["stage_parsing_minimum"] or -100000
            parse_max = self.configuration["stage_parsing_maximum"] or 9999999
            if (
                result
                and parse_min <= result <= parse_max
                and result <= self.configurations["global"]["game"]["max_stage"]
            ):
                results.append(result)
        self.current_stage = most_common_result(
            results=results,
        )
        self.logger.info(
            "Current Stage: %(current_stage)s..." % {
                "current_stage": self.current_stage,
            }
        )

    def fight_boss(self):
        """
        Ensure a boss is being fought currently if one is available.
        """
        self.collapse()
        # Using a higher than normal pause when the fight boss
        # button is clicked on, this makes sure we don't "un-click"
        # before the fight is initiated.
        if self.find_and_click_image(
            image=self.files["fight_boss_icon"],
            region=self.configurations["regions"]["fight_boss"]["search_area"],
            precision=self.configurations["parameters"]["fight_boss"]["search_precision"],
            pause=self.configurations["parameters"]["fight_boss"]["search_pause"],
        ):
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
                if self.configuration["fairies_pi_hole"]:
                    self.logger.info(
                        "Attempting to collect ad rewards through pi-hole disabled ads..."
                    )
                    try:
                        timeout_fairy_pi_hole_cnt = 0
                        timeout_fairy_pi_hole_max = self.configurations["parameters"]["fairies"]["pi_hole_timeout"]

                        while not self.search(
                            image=self.files["fairies_collect"],
                            region=self.configurations["regions"]["fairies"]["pi_hole_collect_area"],
                            precision=self.configurations["parameters"]["fairies"]["pi_hole_collect_precision"],
                        )[0]:
                            self.click(
                                point=self.configurations["points"]["fairies"]["collect_or_watch"],
                                pause=self.configurations["parameters"]["fairies"]["pi_hole_pause"],
                            )
                            timeout_fairy_pi_hole_cnt = self.handle_timeout(
                                count=timeout_fairy_pi_hole_cnt,
                                timeout=timeout_fairy_pi_hole_max,
                            )
                    except TimeoutError:
                        self.logger.info(
                            "Unable to handle fairy ad through pi hole mechanism... Skipping ad collection."
                        )
                        self.click_image(
                            image=image,
                            position=no_thanks_pos,
                        )
                        return
                    self.find_and_click_image(
                        image=self.files["fairies_collect"],
                        region=self.configurations["regions"]["fairies"]["pi_hole_collect_area"],
                        precision=self.configurations["parameters"]["fairies"]["pi_hole_collect_precision"],
                        pause=self.configurations["parameters"]["fairies"]["pi_hole_collect_pause"],
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
        self.find_and_click_image(
            image=self.files["achievements_icon"],
            region=self.configurations["regions"]["achievements"]["search_area"],
            precision=self.configurations["parameters"]["achievements"]["search_precision"],
            pause=self.configurations["parameters"]["achievements"]["search_pause"],
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
            skill for skill, enabled in self.configuration["activate_skills_enabled_skills"].items() if enabled
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
            self.logger.info(
                "Levelling heroes on screen now..."
            )
            for point in self.configurations["points"]["level_heroes"]["possible_hero_level_points"]:
                self.click(
                    point=point,
                    clicks=clicks,
                    interval=self.configurations["parameters"]["level_heroes"]["hero_level_clicks_interval"],
                    pause=self.configurations["parameters"]["level_heroes"]["hero_level_clicks_pause"],
                )
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

    @event(title="Prestige Performed")
    def prestige(self):
        """
        Perform a prestige in game, upgrading a specified artifact afterwards if enabled.
        """
        self.travel_to_master()
        self.leave_boss()
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

    def prestige_stage(self):
        """
        Perform a prestige in game when the current stage exceeds the configured limit.
        """
        self.collapse()
        self.logger.info(
            "Checking current stage to determine if prestige should be performed..."
        )

        self.parse_current_stage()
        current_stage = self.current_stage
        require_stage = self.configuration["prestige_stage_threshold"]

        if current_stage and current_stage >= require_stage:
            self.logger.info(
                "Current stage: \"%(current_stage)s\" exceeds the configured threshold: \"%(require_stage)s\"..." % {
                    "current_stage": current_stage,
                    "require_stage": require_stage,
                }
            )
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
        interval = self.configuration["prestige_close_to_max_post_interval"]
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
                    self.prestige_stage.__name__,
                    self.prestige_close_to_max.__name__,
                ])
                self.schedule_function(
                    function=self.prestige,
                    interval=interval,
                )
            else:
                self.logger.info(
                    "Executing prestige now..."
                )
                self.prestige()

    def prestige_percent_of_max_stage(self):
        """
        Perform a prestige in game when the user has reached the stage required that represents
        a certain percent of their current maximum stage.
        """
        self.collapse()
        self.logger.info(
            "Checking current stage to determine if percent prestige should be performed..."
        )

        self.parse_current_stage()
        current_stage = self.current_stage
        require_stage = calculate_percent(amount=self.max_stage, percent=self.configuration["prestige_percent_of_max_stage_percent"])

        if current_stage and require_stage and current_stage >= require_stage:
            self.logger.info(
                "Current stage: \"%(current_stage)s\" exceeds the configured percent threshold: \"%(percent)s - %(require_stage)s\"..." % {
                    "current_stage": current_stage,
                    "percent": self.configuration["prestige_percent_of_max_stage_percent"],
                    "require_stage": require_stage,
                }
            )
            self.prestige()

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
                for i in range(self.configurations["global"]["tap"]["heroes_tap_loops"]):
                    # The "heroes" key will shuffle and reuse the map, this aids in the process
                    # of activating the astral awakening skills.
                    random.shuffle(lst)
                    # After a shuffle, we'll also remove 30% of the tap keys, this speeds up
                    # the process so we don't tap way too many points.
                    lst = [point for point in lst if random.random() > 0.15]
                    tap.extend(lst)
            else:
                tap.extend(self.configurations["points"]["tap"]["tap_map"][key])

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
        for index, point in enumerate(tap):
            if index % 5 == 0:
                # Also handle the fact that fairies could appear
                # and be clicked on while tapping is taking place.
                self.fairies()
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

    @event(title="{application_name} Session Started", description="New Bot Session Started...")
    def run(self):
        """
        Begin main runtime loop for bot functionality.
        """
        self.logger.info("===================================================================================")
        self.logger.info("%(application_name)s (v%(application_version)s) Initialized..." % {
            "application_name": self.application_name,
            "application_version": self.application_version,
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
            # Right before running, make sure any scheduled functions
            # are configured properly.
            self.schedule_functions()
            # Any functions that should be ran once on startup
            # can be handled at this point.
            self.execute_startup_functions()

            while not self.stop_func():
                if self.pause_func():
                    # Currently paused through the GUI.
                    # Just wait and sleep slightly in between checks.
                    self.logger.info(
                        "Paused..."
                    )
                    time.sleep(self.configurations["global"]["pause"]["pause_check_interval"])
                else:
                    # Ensure any pending scheduled jobs are executed at the beginning
                    # of our loop, each time.
                    schedule.run_pending()
                    # We'll always perform our swipe function if nothing
                    # is currently scheduled or pending.
                    self.tap()

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
