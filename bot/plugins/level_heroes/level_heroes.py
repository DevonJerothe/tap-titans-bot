from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)

import time


class LevelHeroes(BotPlugin):
    """Level heroes in game using the "drag" method, dragging the heroes panel down until the first
    "max level" hero is found, and then levelling and scrolling up until the top is reached.
    """
    plugin_name = "level_heroes"
    plugin_enabled = "level_heroes_enabled"
    plugin_interval = "level_heroes_interval"
    plugin_interval_reset = True
    plugin_execute_on_start = "level_heroes_on_start"

    def _level_heroes_ensure_max(self):
        """Ensure the "BUY Max" option is selected for the hero levelling process.
        """
        if not self.bot.search(
            image=self.bot.files["heroes_level_buy_max"],
            region=self.bot.configurations["regions"]["level_heroes"]["buy_max_area"],
            precision=self.bot.configurations["parameters"]["level_heroes"]["buy_max_precision"],
        )[0]:
            # The buy max option isn't currently set, we'll set it and then
            # continue...
            self.logger.info(
                "Heroes \"BUY Max\" option not found, attempting to set now..."
            )
            try:
                self.bot.click(
                    point=self.bot.configurations["points"]["level_heroes"]["buy_max"],
                    pause=self.bot.configurations["parameters"]["level_heroes"]["buy_max_pause"],
                    timeout=self.bot.configurations["parameters"]["level_heroes"]["timeout_buy_max"],
                    timeout_search_kwargs={
                        "image": self.bot.files["heroes_level_buy_max_open"],
                        "region": self.bot.configurations["regions"]["level_heroes"]["buy_max_open_area"],
                        "precision": self.bot.configurations["parameters"]["level_heroes"]["buy_max_open_precision"],
                    },
                )
                # At this point, we should be able to perform a simple find and click
                # on the buy max button, we'll pause after than and then our loop should
                # end above.
                self.bot.find_and_click_image(
                    image=self.bot.files["heroes_level_buy_max_open"],
                    region=self.bot.configurations["regions"]["level_heroes"]["buy_max_open_area"],
                    precision=self.bot.configurations["parameters"]["level_heroes"]["buy_max_open_precision"],
                    pause=self.bot.configurations["parameters"]["level_heroes"]["buy_max_open_pause"],
                    timeout=self.bot.configurations["parameters"]["level_heroes"]["timeout_buy_max_open"],
                    timeout_search_kwargs={
                        "image": self.bot.files["heroes_level_buy_max"],
                        "region": self.bot.configurations["regions"]["level_heroes"]["buy_max_area"],
                        "precision": self.bot.configurations["parameters"]["level_heroes"]["buy_max_precision"],
                    },
                )
            except TimeoutError:
                self.logger.info(
                    "Unable to set heroes levelling to \"BUY Max\", skipping..."
                )

    def _level_heroes_on_screen(self):
        """Level all current heroes on the game screen.
        """
        # Make sure we're still on the heroes screen...
        self.bot.travel_to_heroes(scroll=False, collapsed=False)
        self.bot.collapse_prompts()
        self.logger.info(
            "Levelling heroes on screen now..."
        )

        clicks = self.bot.configurations["parameters"]["level_heroes"]["hero_level_clicks"] if (
            not self.bot.configuration.level_heroes_masteries_unlocked
        ) else 1

        for point in self.bot.configurations["points"]["level_heroes"]["possible_hero_level_points"]:
            # Looping through possible clicks so we can check if we should level, if not, we can early
            # break and move to the next point.
            for i in range(clicks):
                # Only ever actually clicking on the hero if we know for sure a "level" is available.
                # We do this by checking the color of the point.
                if not self.bot.point_is_color_range(
                    point=(
                        point[0] + self.bot.configurations["parameters"]["level_heroes"]["check_possible_point_x_padding"],
                        point[1],
                    ),
                    color_range=self.bot.configurations["colors"]["level_heroes"]["level_heroes_click_range"],
                ):
                    self.bot.click(
                        point=point,
                        interval=self.bot.configurations["parameters"]["level_heroes"]["hero_level_clicks_interval"],
                        pause=self.bot.configurations["parameters"]["level_heroes"]["hero_level_clicks_pause"],
                    )
                else:
                    break
        # Perform an additional sleep once levelling is totally
        # complete, this helps avoid issues with clicks causing
        # a hero detail sheet to pop up.
        time.sleep(self.bot.configurations["parameters"]["level_heroes"]["hero_level_post_pause"])

    def _level_heroes_autobuy_on(self):
        """Perform a check to determine if the autobuy functionality is currently enabled for this session and in game.
        """
        if self.bot.configuration.level_heroes_skip_if_autobuy_enabled:
            # First thing here, turn on autobuy if it's currently off.
            # If this is the case, we can also just return early since we
            # know that it's on.
            if self.bot.point_is_color_range(
                point=self.bot.configurations["points"]["level_heroes"]["level_heroes_autobuy_color_check"],
                color_range=self.bot.configurations["colors"]["level_heroes"]["level_heroes_autobuy_disabled_range"],
            ):
                # Enable autobuy at this point.
                # (If the user does not have the required perk on, we can chalk it up to
                # a part of the configuration process, since there isn't much we can do at this point
                # to remedy that edge case).
                self.bot.click(
                    point=self.bot.configurations["points"]["level_heroes"]["level_heroes_autobuy"],
                    pause=self.bot.configurations["parameters"]["level_heroes"]["level_heroes_autobuy_pause"],
                )

            autobuy = False

            # We'll now check for the proper red/blue arrows being present, these being available
            # means that the autobuy functionality is enabled and running.
            for i in range(self.bot.configurations["parameters"]["level_heroes"]["level_heroes_autobuy_check_range"]):
                if (
                    self.bot.point_is_color_range(
                        point=self.bot.configurations["points"]["level_heroes"]["level_heroes_autobuy_color_check"],
                        color_range=self.bot.configurations["colors"]["level_heroes"]["level_heroes_autobuy_enabled_red_range"],
                    )
                    or self.bot.point_is_color_range(
                        point=self.bot.configurations["points"]["level_heroes"]["level_heroes_autobuy_color_check"],
                        color_range=self.bot.configurations["colors"]["level_heroes"]["level_heroes_autobuy_enabled_blue_range"],
                    )
                ):
                    autobuy = True
                    break
                # Sleeping no matter what here unless we break above to try and weed
                # out any false positives or incorrect readings.
                time.sleep(self.bot.configurations["parameters"]["level_heroes"]["level_heroes_autobuy_check_pause"])
            return autobuy
        return False

    def _check_headgear(self):
        """Check the headgear in game currently, performing a swap if one is ready to take place.
        """
        self.bot.travel_to_heroes(collapsed=False)

        while self.bot.point_is_color_range(
            point=self.bot.configurations["points"]["headgear_swap"]["skill_upgrade_wait"],
            color_range=self.bot.configurations["colors"]["headgear_swap"]["skill_upgrade_wait_range"]
        ):
            # Sleep slightly before checking again that the skill
            # notification has disappeared.
            time.sleep(self.bot.configurations["parameters"]["headgear_swap"]["headgear_swap_wait_pause"])

        check_index = str(self.bot.configuration.headgear_swap_check_hero_index)

        for typ in [
            "ranger", "warrior", "mage",
        ]:
            if self.bot.search(
                image=self.bot.files["%(typ)s_icon" % {"typ": typ}],
                region=self.bot.configurations["regions"]["headgear_swap"]["type_icon_areas"][check_index],
                precision=self.bot.configurations["parameters"]["headgear_swap"]["type_icon_precision"],
            )[0]:
                if self.bot.powerful_hero == typ:
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
                    self.bot.powerful_hero = typ
                    self._headgear_swap()

    def _headgear_swap(self):
        """Perform all headgear related swapping functionality.
        """
        self.bot.travel_to_equipment(collapsed=False, scroll=False)
        self.logger.info(
            "Attempting to swap headgear for %(powerful)s type hero damage..." % {
                "powerful": self.bot.powerful_hero,
            }
        )

        # Ensure the headgear panel is also open...
        timeout_headgear_panel_click_cnt = 0
        timeout_headgear_panel_click_max = self.bot.configurations["parameters"]["headgear_swap"]["timeout_headgear_panel_click"]

        try:
            while not self.bot.point_is_color_range(
                point=self.bot.configurations["points"]["headgear_swap"]["headgear_panel_color_check"],
                color_range=self.bot.configurations["colors"]["headgear_swap"]["headgear_panel_range"],
            ):
                self.bot.click(
                    point=self.bot.configurations["points"]["headgear_swap"]["headgear_panel"],
                    pause=self.bot.configurations["parameters"]["headgear_swap"]["headgear_panel_pause"],
                )
                timeout_headgear_panel_click_cnt = self.bot.handle_timeout(
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
        self.bot.travel_to_equipment(collapsed=False)

        # Once we've reached the headgear panel, we need to begin
        # looking through each possible equipment location, checking
        # for the correct "type" damage effect.
        for region in self.bot.configurations["regions"]["headgear_swap"]["equipment_regions"]:
            # We only parse and deal with locked gear.
            if self.bot.search(
                image=self.bot.files["equipment_locked"],
                region=region,
                precision=self.bot.configurations["parameters"]["headgear_swap"]["equipment_locked_precision"]
            )[0]:
                if self.bot.search(
                    image=self.bot.files["%(powerful)s_damage" % {"powerful": self.bot.powerful_hero}],
                    region=region,
                    precision=self.bot.configurations["parameters"]["headgear_swap"]["powerful_damage_precision"],
                )[0]:
                    # This equipment is the correct damage type.
                    # Is it already equipped?
                    if self.bot.search(
                        image=self.bot.files["equipment_equipped"],
                        region=region,
                        precision=self.bot.configurations["parameters"]["headgear_swap"]["equipment_equipped_precision"],
                    )[0]:
                        self.logger.info(
                            "Headgear of type %(powerful)s is already equipped..." % {
                                "powerful": self.bot.powerful_hero,
                            }
                        )
                    else:
                        self.logger.info(
                            "Equipping %(powerful)s type headgear now..." % {
                                "powerful": self.bot.powerful_hero,
                            }
                        )
                        try:
                            self.bot.find_and_click_image(
                                image=self.bot.files["equipment_equip"],
                                region=region,
                                precision=self.bot.configurations["parameters"]["headgear_swap"]["equipment_equip_precision"],
                                pause=self.bot.configurations["parameters"]["headgear_swap"]["equipment_equip_pause"],
                                pause_not_found=self.bot.configurations["parameters"]["headgear_swap"]["equipment_equip_pause_not_found"],
                                timeout=self.bot.configurations["parameters"]["headgear_swap"]["equipment_equip_timeout"],
                                timeout_search_kwargs={
                                    "image": self.bot.files["equipment_equipped"],
                                    "region": region,
                                    "precision": self.bot.configurations["parameters"]["headgear_swap"]["equipment_equipped_precision"],
                                },
                            )
                            self.logger.info(
                                "%(powerful)s headgear has been equipped..." % {
                                    "powerful": self.bot.powerful_hero.capitalize(),
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
                "powerful": self.bot.powerful_hero,
            }
        )

    def execute(self, force=False):
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
            timeout_heroes_dupe_max = self.bot.configurations["parameters"]["level_heroes"]["timeout_heroes_dupe"]

            while not dupe:
                try:
                    if callback:
                        callback()
                    self.bot.drag(
                        start=self.bot.configurations["points"]["travel"]["scroll"]["drag_top" if top else "drag_bottom"],
                        end=self.bot.configurations["points"]["travel"]["scroll"]["drag_bottom" if top else "drag_top"],
                        pause=self.bot.configurations["parameters"]["travel"]["drag_pause"],
                    )
                    if stop_on_max and self.bot.search(
                        image=self.bot.files["heroes_max_level"],
                        region=self.bot.configurations["regions"]["level_heroes"]["max_level_search_area"],
                        precision=self.bot.configurations["parameters"]["level_heroes"]["max_level_search_precision"],
                    )[0]:
                        # Breaking early since if we stop early, we can skip
                        # directly to the callbacks (if passed in).
                        break
                    img, dupe = self.bot.duplicates(
                        image=img,
                        region=self.bot.configurations["regions"]["travel"]["duplicate_area"],
                    )
                    timeout_heroes_dupe_cnt = self.bot.handle_timeout(
                        count=timeout_heroes_dupe_cnt,
                        timeout=timeout_heroes_dupe_max,
                    )
                except TimeoutError:
                    self.logger.info(
                        "Max level hero could not be found, ending check now..."
                    )
                    break

        self.bot.travel_to_heroes(scroll=False)
        # If auto hero levelling is currently enabled and on in game,
        # we'll use that instead and skip quick levelling completely.
        if not self._level_heroes_autobuy_on():
            self.bot.travel_to_heroes(collapsed=False)
            self.logger.info(
                "Attempting to level the heroes in game..."
            )

            self._level_heroes_ensure_max()

            found, position, image = self.bot.search(
                image=self.bot.files["heroes_max_level"],
                region=self.bot.configurations["regions"]["level_heroes"]["max_level_search_area"],
                precision=self.bot.configurations["parameters"]["level_heroes"]["max_level_search_precision"],
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
        else:
            self.logger.info(
                "Hero autobuy is currently enabled and on in game, skipping hero levelling..."
            )
        # If headgear swapping is turned on, we always check once heroes
        # are done being levelled.
        if self.bot.configuration.headgear_swap_enabled:
            self._check_headgear()


register_plugin(
    plugin=LevelHeroes,
)
