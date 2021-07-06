from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class Perks(BotPlugin):
    """Attempt to use perks in game.

    Perks are configured through a user configuration and each perk can be used upto a certain
    tier in game.
    """
    plugin_name = "perks"
    plugin_enabled = "perks_enabled"
    plugin_interval = "perks_interval"
    plugin_interval_reset = False
    plugin_execute_on_start = "perks_on_start"

    def execute(self, force=False):
        self.bot.travel_to_master(collapsed=False)
        self.logger.info(
            "Using perks in game..."
        )
        # Travel to the bottom (ish) of the master tab, we'll scroll until
        # we've found the correct perk, since that's the last one available.
        try:
            self.bot.drag(
                start=self.bot.configurations["points"]["travel"]["scroll"]["drag_bottom"],
                end=self.bot.configurations["points"]["travel"]["scroll"]["drag_top"],
                pause=self.bot.configurations["parameters"]["travel"]["drag_pause"],
                timeout=self.bot.configurations["parameters"]["perks"]["icons_timeout"],
                timeout_search_kwargs={
                    "image": self.bot.files["perks_clan_crate"] if not self.bot.configuration.abyssal else self.bot.files["perks_doom"],
                    "region": self.bot.configurations["regions"]["perks"]["icons_area"],
                    "precision": self.bot.configurations["parameters"]["perks"]["icons_precision"],
                },
            )
        except TimeoutError:
            self.logger.info(
                "Unable to find the \"%(search_perk)s\" perk in game, skipping perk functionality..." % {
                    "search_perk": "clan_crate" if not self.bot.configuration.abyssal else "doom",
                }
            )
            return

        # We should be able to see all (or most) of the perks in game, clan crate is on the screen.
        # We'll search for each enabled perk, if it isn't found, we'll scroll up a bit.
        for perk in self.bot.perks_lst:
            perk, enabled, tier = (
                perk[0],
                perk[1],
                perk[2],
            )
            if enabled:
                self.logger.info(
                    "Attempting to use \"%(perk)s\" perk..." % {
                        "perk": perk,
                    }
                )

                timeout_perks_enabled_perk_cnt = 0
                timeout_perks_enabled_perk_max = self.bot.configurations["parameters"]["perks"]["enabled_perk_timeout"]

                try:
                    while not self.bot.search(
                        image=self.bot.files["perks_%(perk)s" % {"perk": perk}],
                        region=self.bot.configurations["regions"]["perks"]["icons_area"],
                        precision=self.bot.configurations["parameters"]["perks"]["icons_precision"],
                    )[0]:
                        # Dragging up until the enabled perk
                        # is found.
                        self.bot.drag(
                            start=self.bot.configurations["points"]["travel"]["scroll"]["drag_top"],
                            end=self.bot.configurations["points"]["travel"]["scroll"]["drag_bottom"],
                            pause=self.bot.configurations["parameters"]["travel"]["drag_pause"],
                        )
                        timeout_perks_enabled_perk_cnt = self.bot.handle_timeout(
                            count=timeout_perks_enabled_perk_cnt,
                            timeout=timeout_perks_enabled_perk_max,
                        )
                    # Icon is found, we'll get the position so we can add proper
                    # padding and attempt to use the perk.
                    _, position, image = self.bot.search(
                        image=self.bot.files["perks_%(perk)s" % {"perk": perk}],
                        region=self.bot.configurations["regions"]["perks"]["icons_area"],
                        precision=self.bot.configurations["parameters"]["perks"]["icons_precision"],
                    )
                    # Dynamically calculate the location of the upgrade button
                    # and perform a click.
                    point = (
                        position[0] + self.bot.configurations["parameters"]["perks"]["position_x_padding"],
                        position[1] + self.bot.configurations["parameters"]["perks"]["position_y_padding"],
                    )
                    # We know the perk is on screen, we'll pad some points to generate a region
                    # that should contain the perk "button" on screen.
                    region = (
                        position[0] + 318,
                        position[1],
                        position[0] + 471,
                        position[1] + 60,
                    )

                    # First thing we need to do is determine if the perk is currently
                    # active and set to the specified tier.
                    if tier:
                        tier = str(tier)
                        # If the perk is already set to the correct tier,
                        # we can skip this perk altogether
                        if self.bot.search(
                            image=self.bot.files["perks_%(tier)s_tier" % {"tier": tier}],
                            region=region,
                            precision=self.bot.configurations["parameters"]["perks"]["tier_search_precision"],
                        )[0]:
                            self.logger.info(
                                "The \"%(perk)s\" perk is already active and set to tier \"%(tier)s\"..." % {
                                    "perk": perk,
                                    "tier": tier,
                                }
                            )
                            continue
                        else:
                            # Otherwise, let's determine what level the perk is currently at, so we can determine
                            # if we need to try and activate it multiple times.
                            perk_tier_map = {
                                self.bot.files["perks_no_tier"]: "none",
                                self.bot.files["perks_1_tier"]: "1",
                                self.bot.files["perks_2_tier"]: "2",
                                self.bot.files["perks_3_tier"]: "3",
                            }
                            perk_tier_int_map = {
                                "none": 0,
                                "1": 1,
                                "2": 2,
                                "3": 3,
                            }
                            found, position, image = self.bot.search(
                                image=[
                                    self.bot.files["perks_no_tier"],
                                    self.bot.files["perks_1_tier"],
                                    self.bot.files["perks_2_tier"],
                                    self.bot.files["perks_3_tier"],
                                ],
                                region=region,
                                precision=self.bot.configurations["parameters"]["perks"]["tier_search_precision"],
                            )
                            # None of the images could be found?
                            # Failsafe here, log and just go on to the next perk.
                            if not found:
                                self.logger.info(
                                    "None of the perks tier images could be found, skipping..."
                                )
                                continue

                            # Based on the tier found, determine if we need to try to actively
                            # activate the perk multiple times...
                            found = perk_tier_map[image]
                            found_int = perk_tier_int_map[found]
                            tier_int = perk_tier_int_map[tier]

                            if found_int > tier_int:
                                self.logger.info(
                                    "The \"%(perk)s\" perk is already above the tier \"%(tier)s\", skipping..." % {
                                        "perk": perk,
                                        "tier": tier,
                                    }
                                )
                                continue

                            loops = tier_int - found_int

                            self.logger.info(
                                "Attempting to activate the \"%(perk)s\" and set it to tier \"%(tier)s\"..." % {
                                    "perk": perk,
                                    "tier": tier,
                                }
                            )

                            # Loop through the differences integer so we can attempt to activate the perk
                            # X times...
                            for i in range(loops):
                                self.bot.click(
                                    point=point,
                                    pause=self.bot.configurations["parameters"]["perks"]["open_perk_prompt_pause"],
                                )
                                if perk == "mega_boost":
                                    # The mega boost perk is being activated, we'll check to see if
                                    # it can be activated for free, or it must have ads watched.
                                    found, position, image = self.bot.search(
                                        image=self.bot.files["perks_free"],
                                        region=self.bot.configurations["regions"]["perks"]["free_area"],
                                        precision=self.bot.configurations["parameters"]["perks"]["free_precision"],
                                    )

                                    # Free mega boost can be collected...
                                    if found:
                                        self.bot.click_image(
                                            image=image,
                                            position=position,
                                            pause=self.bot.configurations["parameters"]["perks"]["free_pause"],
                                        )
                                        continue
                                    # Maybe we can use ad blocking.
                                    else:
                                        if self.bot.get_settings_obj().ad_blocking:
                                            # Follow normal flow and try to watch the ad
                                            # "Okay" button will begin the process.
                                            while self.bot.search(
                                                image=self.bot.files["perks_mega_boost_header"],
                                                region=self.bot.configurations["regions"]["perks"]["header_area"],
                                                precision=self.bot.configurations["parameters"]["perks"]["header_precision"],
                                            )[0]:
                                                # Looping until the perks header has disappeared, which represents
                                                # the ad collection being finished.
                                                self.bot.find_and_click_image(
                                                    image=self.bot.files["perks_okay_tier"],
                                                    region=self.bot.configurations["regions"]["perks"]["okay_area"],
                                                    precision=self.bot.configurations["parameters"]["perks"]["okay_precision"],
                                                    pause=self.bot.configurations["parameters"]["perks"]["okay_pause"],
                                                )
                                else:
                                    # Otherwise, we can check to see if diamonds are required at this point.
                                    if self.bot.search(
                                        image=self.bot.files["perks_diamond"],
                                        region=self.bot.configurations["regions"]["perks"]["diamond_area"],
                                        precision=self.bot.configurations["parameters"]["perks"]["diamond_precision"],
                                    )[0]:
                                        # Diamonds must be used, is this enabled?
                                        if not self.bot.configuration.perks_spend_diamonds:
                                            self.logger.info(
                                                "The \"%(perk)s\" perk requires spending diamonds to use but diamond spending "
                                                "is disabled, skipping..." % {
                                                    "perk": perk,
                                                }
                                            )
                                            self.bot.find_and_click_image(
                                                image=self.bot.files["perks_cancel_tier"],
                                                region=self.bot.configurations["regions"]["perks"]["cancel_area"],
                                                precision=self.bot.configurations["parameters"]["perks"]["cancel_precision"],
                                                pause=self.bot.configurations["parameters"]["perks"]["cancel_pause"],
                                            )
                                            # We actually break here since we can move to the next perk at
                                            # this point since diamonds are required and disabled.
                                            break
                                    # Perk can be used if we get to this point...
                                    # Activating it now.
                                    self.bot.find_and_click_image(
                                        image=self.bot.files["perks_okay_tier"],
                                        region=self.bot.configurations["regions"]["perks"]["okay_area"],
                                        precision=self.bot.configurations["parameters"]["perks"]["okay_precision"],
                                        pause=self.bot.configurations["parameters"]["perks"]["okay_pause"],
                                    )
                                    if perk == "mana_potion":
                                        # Mana potion unfortunately actually closes our
                                        # master panel, we'll need to open it back up.
                                        self.bot.click(
                                            point=self.bot.configurations["points"]["travel"]["tabs"]["master"],
                                            pause=self.bot.configurations["parameters"]["perks"]["post_use_open_master_pause"],
                                        )
                                        continue
                    # If the skill doesn't support the option for a tier, we skip the tier functionality
                    # and just attempt to activate the skill proper.
                    else:
                        # Most common use case here is currently using the clan crate perk..
                        # Which still uses the older perks functionality.
                        self.bot.click(
                            point=point,
                            pause=self.bot.configurations["parameters"]["perks"]["open_perk_prompt_pause"],
                        )
                        if self.bot.search(
                            image=self.bot.files["perks_header"],
                            region=self.bot.configurations["regions"]["perks"]["header_area"],
                            precision=self.bot.configurations["parameters"]["perks"]["header_precision"]
                        )[0]:
                            # Does this perk require diamonds to actually use?
                            if self.bot.search(
                                image=self.bot.files["perks_diamond"],
                                region=self.bot.configurations["regions"]["perks"]["diamond_area"],
                                precision=self.bot.configurations["parameters"]["perks"]["diamond_precision"],
                            )[0]:
                                if not self.bot.configuration.perks_spend_diamonds:
                                    self.logger.info(
                                        "The \"%(perk)s\" perk requires spending diamonds to use but diamond spending "
                                        "is disabled, skipping..." % {
                                            "perk": perk,
                                        }
                                    )
                                    self.bot.find_and_click_image(
                                        image=self.bot.files["perks_cancel"],
                                        region=self.bot.configurations["regions"]["perks"]["cancel_area"],
                                        precision=self.bot.configurations["parameters"]["perks"]["cancel_precision"],
                                        pause=self.bot.configurations["parameters"]["perks"]["cancel_pause"],
                                    )
                                    continue
                            # Perk can be used if we get to this point...
                            # Activating it now.
                            self.bot.find_and_click_image(
                                image=self.bot.files["perks_okay"],
                                region=self.bot.configurations["regions"]["perks"]["okay_area"],
                                precision=self.bot.configurations["parameters"]["perks"]["okay_precision"],
                                pause=self.bot.configurations["parameters"]["perks"]["okay_pause"],
                            )
                except TimeoutError:
                    self.logger.info(
                        "Unable to use perks in game, skipping..."
                    )


register_plugin(
    plugin=Perks,
)
