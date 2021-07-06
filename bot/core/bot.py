from settings import (
    BOT_DATA_IMAGES_DIRECTORY,
    BOT_DATA_SCHEMA_CONFIGURATION_FILE,
    LOCAL_DATA_LOGS_DIRECTORY,
)

from bot.core.window import WindowHandler
from bot.core.scheduler import TitanScheduler
from bot.core.imagesearch import image_search_area, click_image
from bot.core.imagecompare import compare_images
from bot.core.exceptions import (
    GameStateException,
    StoppedException,
    PausedException,
)
from bot.core.utilities import (
    create_logger,
)

from bot.plugins.plugin import (
    PLUGINS,
)

from itertools import cycle
from pyautogui import FailSafeException

from PIL import Image

import datetime
import numpy
import time
import json
import cv2
import os


class Bot(object):
    """Core Bot Instance.
    """
    def __init__(
        self,
        application_name,
        application_version,
        event,
        instance,
        instance_obj,
        instance_name,
        instance_func,
        window,
        configuration,
        session,
        get_settings_obj,
        force_prestige_func,
        force_stop_func,
        stop_func,
        pause_func,
    ):
        self.application_name = application_name
        self.application_version = application_version

        self.files = {}           # Program Files.
        self.configurations = {}  # Global Program Configurations
        self.configuration = {}   # Local Bot Configurations.
        self.plugins = {}         # Local Bot Plugins.

        self.session = session

        # get_settings_obj is a callable that retrieved the current settings
        # instance, refreshing it if it's changed since we've last grabbed it.
        self.get_settings_obj = get_settings_obj
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

        # The "event" object should be the Event model
        # instance that we can use in our plugins and
        # right in the bot to generate events.
        self.event = event

        # This instance can be passed back to the gui whenever a
        # bot session needs to interact with a running bot.
        self.instance = instance
        self.instance_obj = instance_obj
        self.instance_name = instance_name
        self.instance_func = instance_func

        # Selected window and configuration, notable here that we expect a window hwnd,
        # and a configuration primary key for the bot to correctly process data and start.
        self.window = window
        self.configuration = configuration

        # Custom scheduler is used currently to handle
        # stop_func functionality when running pending
        # jobs, this avoids large delays when waiting
        # to pause/stop
        self.schedule = TitanScheduler(
            instance=self.instance,
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

        self.logger, self.stream = create_logger(
            log_directory=LOCAL_DATA_LOGS_DIRECTORY,
            instance_id=self.instance,
            instance_name=self.instance_name,
            instance_func=self.instance_func,
            session_id=self.session,
            get_settings_obj=self.get_settings_obj,
        )

        self.configure_images()
        self.configure_schema()
        self.configure_plugins()

        self.handle = WindowHandler()
        self.window = self.handle.filter_first(
            filter_title=self.window,
        )
        self.window.configure(
            instance=self.instance,
            get_settings_obj=self.get_settings_obj,
            force_stop_func=self.force_stop_func,
        )

        # Begin running the bot once all dependency/configuration/files/variables
        # have been handled and are ready to go.
        self.run()

    def configure_images(self):
        """Configure the images available and used by the bot.
        """
        self.logger.info("Configuring images...")

        with os.scandir(BOT_DATA_IMAGES_DIRECTORY) as scan:
            for file in scan:
                self.files[file.name.split(".")[0]] = file.path
        self.logger.debug(self.files)

    def configure_schema(self):
        """Configure the schema available and used by the bot.
        """
        self.logger.info("Configuring schemas...")

        with open(BOT_DATA_SCHEMA_CONFIGURATION_FILE, "r") as schema:
            self.configurations = json.loads(schema.read())
        self.logger.debug(self.configurations)

    def configure_additional(self):
        """Configure any additional variables or values that can be used throughout session runtime.
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

        # Skills Data.
        # ------------------
        self.skills_lst = sorted([s for s in [
            self.configuration.activate_skills_heavenly_strike,
            self.configuration.activate_skills_deadly_strike,
            self.configuration.activate_skills_hand_of_midas,
            self.configuration.activate_skills_fire_sword,
            self.configuration.activate_skills_war_cry,
            self.configuration.activate_skills_shadow_clone,
        ]], key=lambda skill: skill[0])
        # Configure some skills interval information so we can store
        # when each skill should be activated. These may not all be used depending
        # on if they're enabled through the configuration.
        self.skills_heavenly_strike_next_run = None
        self.skills_deadly_strike_next_run = None
        self.skills_hand_of_midas_next_run = None
        self.skills_fire_sword_next_run = None
        self.skills_war_cry_next_run = None
        self.skills_shadow_clone_next_run = None

        # Perks Data.
        # ------------------
        self.perks_lst = [p for p in [
            self.configuration.perks_clan_crate,
            self.configuration.perks_doom,
            self.configuration.perks_mana_potion,
            self.configuration.perks_make_it_rain,
            self.configuration.perks_adrenaline_rush,
            self.configuration.perks_power_of_swiping,
            self.configuration.perks_mega_boost,
        ]]

        # Artifacts Data.
        # ------------------
        self.upgrade_artifacts = cycle(self.configuration.artifacts_upgrade_artifacts) if self.configuration.artifacts_upgrade_artifacts else None
        self.next_artifact_upgrade = next(self.upgrade_artifacts) if self.upgrade_artifacts else None

        # Session Data.
        # ------------------
        # "powerful_hero" - Most powerful hero currently in game.
        # "daily_limit_reached" - Store a flag to determine if the prestige daily limit is reached.
        self.powerful_hero = None
        self.daily_limit_reached = False

        # Per Prestige Data.
        # ------------------
        # "close_to_max_ready" - Store a flag to denote that a close to max prestige is ready.
        # "master_levelled" - Store a flag to denote the master being levelled.
        self.close_to_max_ready = False
        self.master_levelled = False

    def configure_plugins(self):
        """Configure the available plugins used by the bot.
        """
        self.logger.info(
            "Configuring plugins..."
        )

        for plugin_name, plugin in PLUGINS.items():
            self.logger.debug(
                "Configuring plugin: %(plugin)s..." % {
                    "plugin": plugin_name,
                }
            )
            self.plugins[plugin_name] = plugin(
                bot=self,
                logger=self.logger,
            )

    def schedule_plugins(self):
        """Schedule all interval based plugins used by the bot.
        """
        schedule_first_time = False

        if not self.scheduled:
            schedule_first_time = True
        else:
            # If scheduling has already taken place at least once, we'll only clear
            # the plugins that are reset safe, others are ignored and are left as-is.
            self.cancel_scheduled_plugin(tags=[
                plugin.name for plugin in self.plugins.values() if plugin.interval_reset
            ])

        for plugin in self.plugins.values():
            if not schedule_first_time and self.scheduled and not plugin.interval_reset:
                continue
            if plugin.enabled:
                # We wont schedule any functions that also
                # have an interval of zero.
                if plugin.interval > 0:
                    self.schedule_plugin(
                        plugin=plugin,
                    )
                else:
                    self.logger.debug(
                        "Plugin: \"%(plugin)s\" is scheduled to run but the interval is set to zero, skipping..." % {
                            "plugin": plugin.name,
                        }
                    )
        if schedule_first_time:
            # If were scheduling for the first time, we flip this flag once
            # after initial scheduling, this lets us reschedule and respect reset
            # flags on each subsequent reschedule.
            self.scheduled = True

    def schedule_plugin(self, plugin, interval=None):
        """Schedule a given plugin to run periodically.
        """
        if isinstance(plugin, str):
            # Ensure plugin "names" can be passed along.
            # This allows us to pass in a plugin object, or string.
            plugin = self.plugins[plugin]
        if not interval:
            interval = plugin.interval

        self.logger.debug(
            "Plugin: \"%(plugin)s\" is scheduled to run every %(interval)s second(s)..." % {
                "plugin": plugin.name,
                "interval": plugin.interval,
            }
        )
        self.schedule.every(interval=interval).seconds.do(job_func=plugin.execute).tag(plugin.name)

    def cancel_scheduled_plugin(self, tags):
        """
        Cancel a scheduled plugin if currently scheduled to run.
        """
        if not isinstance(tags, list):
            tags = [tags]
        for tag in tags:
            self.schedule.clear(tag)

    def execute_startup_plugins(self):
        """Execute any plugins that should be ran right away following a successful session start.
        """
        for plugin in self.plugins.values():
            if plugin.enabled and plugin.execute_on_start:
                self.logger.debug(
                    "Plugin: \"%(plugin)s\" is enabled and set to run on startup, executing now..." % {
                        "plugin": plugin.name,
                    }
                )
                # Startup functions should still have the run checks
                # executed... Since a manual pause or stop while these
                # are running should be respected by the bot.
                self.run_checks()
                # Execute the given plugin with our force flag
                # properly passed along.
                plugin.execute(
                    force=plugin.force_on_start,
                )

    def handle_timeout(
        self,
        count,
        timeout,
    ):
        """Handle function timeouts throughout bot execution.

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

    def snapshot(
        self,
        region=None,
        scale=None,
        pause=0.0
    ):
        """Take a snapshot of the current windows screen.

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
        """Attempt to process a specified image or screenshot region.
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
        """Search for the specified image(s) on the current window.

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
        """Check that a given snapshot is the exact same as the current snapshot available.
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
        """Check that a specific point is currently a certain color.
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
        """Check that a specific point is currently within a color range.
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
        """Check that a specific point is currently within a region.
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
        """Perform a click on the current window.
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
        """Attempt to find and click on the specified image on the current window.

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
        """Perform a drag on the current window.
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
        """Perform a click on a particular image on the current window.
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

    def collapse(self):
        """Ensure the game screen is currently collapsed, regardless of the currently opened tab.
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
        """Attempt to collapse any open prompts in game.
        """
        try:
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
        except TimeoutError:
            # In rare cases, perhaps something else is on the screen, like a fairy or prompt
            # that requires some care. This will be handled in a next iteration most likely.
            pass

    def collapse_event_panel(self):
        """Attempt to collapse the event panel in game if it is currently open.
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
        """Attempt to expand the event panel in game if it is currently closed.
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

    def travel(
        self,
        tab,
        image,
        scroll=True,
        collapsed=True,
        top=True,
        stop_image_kwargs=None,
    ):
        """Travel to the specified tab in game.

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
        """Travel to the master tab in game.
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
        """Travel to the heroes tab in game.
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
        """Travel to the equipment tab in game.
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
        """Travel to the pets tab in game.
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
        """Travel to the artifacts tab in game.
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
        """Travel to the shop tab in game.
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
        """Travel to the main game screen (no tabs open) in game.
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

    def run_checks(self):
        """Helper method to run checks against current bot state, this is in its own method so it can be ran in the main loop,
        as well as in our startup execution functions...
        """
        while self.pause_func(instance=self.instance):
            if self.stop_func(instance=self.instance) or self.force_stop_func(instance=self.instance):
                raise StoppedException
            if not self.pause_date:
                self.pause_date = datetime.datetime.now()
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
        if self.force_prestige_func(instance=self.instance):
            self.force_prestige_func(instance=self.instance, _set=True,)
            self.plugins["prestige"].execute()
        if self.force_stop_func(instance=self.instance):
            self.force_stop_func(instance=self.instance, _set=True)
            # Just raise a stopped exception if we
            # are just exiting and it's found in between
            # function execution.
            raise StoppedException
        if self.stop_func(instance=self.instance):
            raise StoppedException

    def generate_event(self, event, timestamp=None):
        """Generate a new event instance, an optional explicit timestamp can be specified, the current
        datetime is used by default.

        The event should be a string descriptor of the event.
        """
        event_kwargs = {
            "instance": self.instance_obj,
            "event": event,
        }
        if timestamp:
            event_kwargs.update({
                "timestamp": timestamp,
            })

        self.event.objects.create(
            **event_kwargs,
        )

    def run(self):
        """Begin main runtime loop for bot functionality.
        """
        self.logger.info("===================================================================================")
        self.logger.info("%(application_name)s (v%(application_version)s) Initialized..." % {
            "application_name": self.application_name,
            "application_version": self.application_version,
        })
        self.logger.info("Configuration: %(configuration)s" % {
            "configuration": self.configuration.name,
        })
        self.logger.info("Window: %(window)s" % {
            "window": self.window,
        })
        self.logger.info("Instance: %(instance)s" % {
            "instance": self.instance_name,
        })
        self.logger.info("Session: %(session)s" % {
            "session": self.session,
        })
        self.logger.info("===================================================================================")

        # Generate a new "session started" event on successful startup.
        self.generate_event(
            event="Session %(session)s Initialized..." % {
                "session": self.session,
            },
        )

        try:
            self.configure_additional()
            # Any functions that should be ran once on startup
            # can be handled at this point.
            self.execute_startup_plugins()
            # Right before running, make sure any scheduled functions
            # are configured properly.
            self.schedule_plugins()

            # Main catch all for our manual stops, fail-safes are caught within
            # actual api calls instead of here...
            while not self.stop_func(instance=self.instance) and not self.force_stop_func(instance=self.instance):
                try:
                    self.run_checks()
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
                "toggling the settings in your local settings. Note, disabling the failsafe may make it more difficult to shut down "
                "a session while it is in the middle of a function."
            )
        except StoppedException:
            # Pass when stopped exception is encountered, skip right to our
            # finally block to handle logging and cleanup.
            pass
        except Exception as exc:
            self.logger.info(
                "An unknown exception was encountered... %(exception)s" % {
                    "exception": exc,
                }
            )
            self.logger.debug(
                "Exception information:",
                exc_info=exc,
            )
        finally:
            # Log some additional information now that our session is ending. This
            # information should be displayed regardless of the reason that caused
            # our termination of this instance.
            self.logger.info("===================================================================================")
            self.logger.info(
                "Your session has ended, thank you for using the %(application_name)s" % {
                    "application_name": self.application_name.lower(),
                },
            )
            self.logger.info("Session: %(session)s" % {
                "session": self.session,
            })
            self.logger.info("===================================================================================")
