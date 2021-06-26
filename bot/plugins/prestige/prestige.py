from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class Prestige(BotPlugin):
    """Perform a prestige in game.

    During this process, tournament functionality is handled and if a tournament is available, it will
    be joined, if rewards are available, they will be collected.
    """
    plugin_name = "prestige"
    plugin_enabled = "prestige_time_enabled"
    plugin_interval = "prestige_time_interval"
    plugin_interval_reset = True
    plugin_execute_on_start = False

    def _artifacts_ensure_multiplier(self, multiplier):
        """Ensure the artifacts tab is set to the specified multiplier.
        """
        self.logger.info(
            "Ensuring %(multiplier)s is active..." % {
                "multiplier": multiplier,
            }
        )
        self.bot.click(
            point=self.bot.configurations["points"]["artifacts"]["multiplier"],
            pause=self.bot.configurations["parameters"]["artifacts"]["multiplier_pause"],
            timeout=self.bot.configurations["parameters"]["artifacts"]["timeout_multiplier"],
            timeout_search_kwargs={
                "image": self.bot.files["artifacts_%s" % multiplier],
                "region": self.bot.configurations["regions"]["artifacts"]["%s_open_area" % multiplier],
                "precision": self.bot.configurations["parameters"]["artifacts"]["multiplier_open_precision"],
            },
        )
        # At this point, we should be able to perform a simple find and click
        # on the buy max button, we'll pause after than and then our loop should
        # end above.
        self.bot.find_and_click_image(
            image=self.bot.files["artifacts_%s" % multiplier],
            region=self.bot.configurations["regions"]["artifacts"]["%s_open_area" % multiplier],
            precision=self.bot.configurations["parameters"]["artifacts"]["multiplier_open_precision"],
            pause=self.bot.configurations["parameters"]["artifacts"]["multiplier_open_pause"],
            timeout=self.bot.configurations["parameters"]["artifacts"]["timeout_multiplier_open"],
        )

    def _artifacts_upgrade(self, artifact, multiplier):
        """Search for and actually perform an upgrade on it in the artifacts panel.
        """
        # Upgrade a single artifact to it's maximum
        # one time...
        self.logger.info(
            "Attempting to upgrade %(artifact)s artifact..." % {
                "artifact": artifact,
            }
        )
        timeout_artifact_search_cnt = 0
        timeout_artifact_search_max = self.bot.configurations["parameters"]["artifacts"]["timeout_search"]

        while not self.bot.search(
            image=self.bot.files["artifact_%(artifact)s" % {"artifact": artifact}],
            region=self.bot.configurations["regions"]["artifacts"]["search_area"],
            precision=self.bot.configurations["parameters"]["artifacts"]["search_precision"],
        )[0]:
            self.bot.drag(
                start=self.bot.configurations["points"]["travel"]["scroll"]["drag_bottom"],
                end=self.bot.configurations["points"]["travel"]["scroll"]["drag_top"],
                pause=self.bot.configurations["parameters"]["travel"]["drag_pause"],
            )
            timeout_artifact_search_cnt = self.bot.handle_timeout(
                count=timeout_artifact_search_cnt,
                timeout=timeout_artifact_search_max,
            )
        # At this point, the artifact being upgraded should be visible on the screen,
        # we'll grab the position and perform a single upgrade click before continuing.
        _, position, image = self.bot.search(
            image=self.bot.files["artifact_%(artifact)s" % {"artifact": artifact}],
            region=self.bot.configurations["regions"]["artifacts"]["search_area"],
            precision=self.bot.configurations["parameters"]["artifacts"]["search_precision"],
        )
        # Dynamically calculate the location of the upgrade button
        # and perform a click.
        point = (
            position[0] + self.bot.configurations["parameters"]["artifacts"]["position_x_padding"],
            position[1] + self.bot.configurations["parameters"]["artifacts"]["position_y_padding"],
        )
        self.bot.click(
            point=point,
            clicks=self.bot.configurations["parameters"]["artifacts"]["upgrade_clicks"] if multiplier == "max" else 1,
            interval=self.bot.configurations["parameters"]["artifacts"]["upgrade_interval"],
            pause=self.bot.configurations["parameters"]["artifacts"]["upgrade_pause"],
        )
        self.bot.generate_event(event="Upgraded Artifact: %(artifact)s..." % {
                "artifact": artifact.replace("_", " ").title(),
            },
        )

    def _prestige_enchant_artifacts(self):
        """Handle enchanting artifacts in game following a prestige.
        """
        self.bot.travel_to_artifacts(collapsed=False)

        found, position, image = self.bot.search(
            image=self.bot.files["artifacts_enchant_icon"],
            region=self.bot.configurations["regions"]["artifacts"]["enchant_icon_area"],
            precision=self.bot.configurations["parameters"]["artifacts"]["enchant_icon_precision"],
        )
        # In case multiple artifacts can be enchanted, looping
        # until no more enchantments can be performed.
        if found:
            self.logger.info(
                "Attempting to enchant artifacts..."
            )
            while True:
                self.bot.click_image(
                    image=image,
                    position=position,
                    pause=self.bot.configurations["parameters"]["artifacts"]["enchant_click_pause"],
                )
                if self.bot.search(
                    image=self.bot.files["artifacts_enchant_confirm_header"],
                    region=self.bot.configurations["regions"]["artifacts"]["enchant_confirm_header_area"],
                    precision=self.bot.configurations["parameters"]["artifacts"]["enchant_confirm_header_precision"],
                )[0]:
                    self.logger.info(
                        "Enchanting artifact now..."
                    )
                    self.bot.click(
                        point=self.bot.configurations["points"]["artifacts"]["enchant_confirm_point"],
                        pause=self.bot.configurations["parameters"]["artifacts"]["enchant_confirm_pause"],
                    )
                    # Perform some middle top clicks to close enchantment prompt.
                    self.bot.click(
                        point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.bot.configurations["parameters"]["artifacts"]["post_collect_clicks"],
                        interval=self.bot.configurations["parameters"]["artifacts"]["post_collect_interval"],
                        pause=self.bot.configurations["parameters"]["artifacts"]["post_collect_pause"],
                    )
                    self.bot.generate_event(
                        event="Enchanted Artifact...",
                    )
                # Break if no header is found, no more artifacts can
                # be enchanted at this point.
                else:
                    break

    def _prestige_discover_artifacts(self):
        """Handle discovering artifacts in game following a prestige.
         """
        self.bot.travel_to_artifacts(collapsed=False)

        found, position, image = self.bot.search(
            image=self.bot.files["artifacts_discover_icon"],
            region=self.bot.configurations["regions"]["artifacts"]["discover_icon_area"],
            precision=self.bot.configurations["parameters"]["artifacts"]["discover_icon_precision"],
        )
        # In case multiple artifacts can be discovered, looping
        # until no more discoveries can be performed.
        if found:
            self.logger.info(
                "Attempting to discover artifacts..."
            )
            while True:
                self.bot.click_image(
                    image=image,
                    position=position,
                    pause=self.bot.configurations["parameters"]["artifacts"]["discover_click_pause"],
                )
                if self.bot.search(
                    image=self.bot.files["artifacts_discover_confirm_header"],
                    region=self.bot.configurations["regions"]["artifacts"]["discover_confirm_header_area"],
                    precision=self.bot.configurations["parameters"]["artifacts"]["discover_confirm_header_precision"],
                )[0]:
                    self.logger.info(
                        "Discovering artifact now..."
                    )
                    self.bot.click(
                        point=self.bot.configurations["points"]["artifacts"]["discover_confirm_point"],
                        pause=self.bot.configurations["parameters"]["artifacts"]["discover_confirm_pause"],
                    )
                    # Perform some middle top clicks to close discovery prompt.
                    self.bot.click(
                        point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.bot.configurations["parameters"]["artifacts"]["post_collect_clicks"],
                        interval=self.bot.configurations["parameters"]["artifacts"]["post_collect_interval"],
                        pause=self.bot.configurations["parameters"]["artifacts"]["post_collect_pause"],
                    )
                    self.bot.generate_event(
                        event="Discovered Artifact...",
                    )
                    # If the user has enabled the option to also upgrade the newly discovered
                    # artifact, we'll do that now as well.
                    if self.bot.configuration.artifacts_discovery_upgrade_enabled:
                        self.logger.info(
                            "Artifact discovery upgrade is enabled, attempting to upgrade the new artifact using the "
                            "\"%(multiplier)s\" multiplier in game..." % {
                                "multiplier": self.bot.configuration.artifacts_discovery_upgrade_multiplier,
                            }
                        )
                        self._artifacts_ensure_multiplier(
                            multiplier=self.bot.configuration.artifacts_discovery_upgrade_multiplier,
                        )
                        # Just manually clicking on the point since a newly discovered
                        # artifact will always pop up in the same location.
                        self.bot.click(
                            point=self.bot.configurations["points"]["artifacts"]["discovered_artifact"],
                            pause=self.bot.configurations["parameters"]["artifacts"]["discovered_artifact_pause"],
                        )
                        self.bot.generate_event(event=(
                            "Upgraded Discovered Artifact (%(multiplier)s)..." % {
                                "multiplier": self.bot.configuration.artifacts_discovery_upgrade_multiplier.upper(),
                            }
                        ))
                # Break if no header is found, no more artifacts can
                # be discovered at this point.
                else:
                    break

    def _prestige_upgrade_artifacts(self):
        """Handle upgrading artifacts in game following a prestige.
        """
        self.logger.info(
            "Beginning artifacts functionality..."
        )
        if self.bot.configuration.artifacts_upgrade_enabled:
            self.bot.travel_to_artifacts(scroll=False, collapsed=False)
            try:
                self._artifacts_ensure_multiplier(
                    multiplier="max",
                )
                # Upgrade a single artifact to it's maximum
                # one time...
                self.bot.travel_to_artifacts(
                    collapsed=False,
                    stop_image_kwargs={
                        "image": self.bot.files["artifact_%(artifact)s" % {"artifact": self.bot.next_artifact_upgrade}],
                        "region": self.bot.configurations["regions"]["artifacts"]["search_area"],
                        "precision": self.bot.configurations["parameters"]["artifacts"]["search_precision"],
                    },
                )
                self._artifacts_upgrade(
                    artifact=self.bot.next_artifact_upgrade,
                    multiplier="max",
                )
                # Update the next artifact that will be upgraded.
                # This is done regardless of upgrade state (success/fail).
                self.bot.next_artifact_upgrade = next(self.bot.upgrade_artifacts) if self.bot.upgrade_artifacts else None
            except TimeoutError:
                self.logger.info(
                    "Artifact: %(artifact)s could not be found on the screen, or the \"BUY Max\" option could not be enabled, "
                    "skipping upgrade..." % {
                        "artifact": self.bot.next_artifact_upgrade,
                    }
                )

    def _prestige_check_daily_limit(self):
        """Check to see if the daily limit has been reached in game, this helps determine if the "close to max"
        functionality should use the event icon method or the skill tree method.
        """
        self.logger.debug(
            "Checking prestige daily limit now..."
        )

        if self.bot.search(
            image=self.bot.files["prestige_daily_limit_reached"],
            region=self.bot.configurations["regions"]["prestige"]["prestige_daily_limit_area"],
            precision=self.bot.configurations["parameters"]["prestige"]["prestige_daily_limit_precision"],
        )[0]:
            self.logger.debug(
                "Daily prestige limit reached, disabling event icon checks..."
            )
            self.bot.daily_limit_reached = True
        else:
            self.logger.debug(
                "Daily prestige limit has not been reached, enabling event icon checks..."
            )
            self.bot.daily_limit_reached = False

    def _leave_boss(self):
        """Ensure a boss is not being fought currently.
        """
        if self.bot.search(
            image=self.bot.files["fight_boss_icon"],
            region=self.bot.configurations["regions"]["fight_boss"]["search_area"],
            precision=self.bot.configurations["parameters"]["fight_boss"]["search_precision"]
        )[0]:
            # Return early, a boss fight is not already in progress,
            # or, we're almost at another boss fight.
            self.logger.info(
                "Boss fight is already not active..."
            )
        else:
            try:
                self.bot.find_and_click_image(
                    image=self.bot.files["leave_boss_icon"],
                    region=self.bot.configurations["regions"]["leave_boss"]["search_area"],
                    precision=self.bot.configurations["parameters"]["leave_boss"]["search_precision"],
                    pause=self.bot.configurations["parameters"]["leave_boss"]["search_pause"],
                    pause_not_found=self.bot.configurations["parameters"]["leave_boss"]["search_pause_not_found"],
                    timeout=self.bot.configurations["parameters"]["leave_boss"]["leave_boss_timeout"],
                    timeout_search_kwargs={
                        "image": self.bot.files["fight_boss_icon"],
                        "region": self.bot.configurations["regions"]["fight_boss"]["search_area"],
                        "precision": self.bot.configurations["parameters"]["fight_boss"]["search_precision"],
                    },
                )
            except TimeoutError:
                self.logger.info(
                    "Boss fight is not currently in progress, continuing..."
                )

    def execute(self, force=False):
        self.bot.travel_to_master()
        self._leave_boss()

        self.bot.logger.info(
            "Attempting to prestige in game now..."
        )

        tournament_prestige = False

        # Handle all tournament functionality within our final prestige
        # execution. If enabled, we can check that a tournament is even running,
        # check if one can be joined, or check that rewards can be collected.
        if self.bot.configuration.tournaments_enabled:
            self.logger.info(
                "Tournaments are enabled, checking current status of in game tournament..."
            )
            # Tournament is in a "grey" state, one will be starting soon...
            # We do nothing here.
            if self.bot.point_is_color_range(
                point=self.bot.configurations["points"]["tournaments"]["tournaments_status"],
                color_range=self.bot.configurations["colors"]["tournaments"]["tournaments_soon_range"],
            ):
                # Tournament is not ready yet at all. Doing nothing for tournament functionality.
                self.logger.info(
                    "Tournament is starting soon, skipping tournament functionality until ready..."
                )
            # Tournament is in a "blue" state, one is ready and can
            # be joined now, we join the tournament here.
            elif self.bot.point_is_color_range(
                point=self.bot.configurations["points"]["tournaments"]["tournaments_status"],
                color_range=self.bot.configurations["colors"]["tournaments"]["tournaments_ready_range"],
            ):
                tournament_prestige = True
                # Tournament is available and ready to be joined... Attempting to join and skip
                # prestige functionality below.
                self.bot.click(
                    point=self.bot.configurations["points"]["tournaments"]["tournaments_icon"],
                    pause=self.bot.configurations["parameters"]["tournaments"]["icon_pause"],
                )
                try:
                    self.logger.info(
                        "Performing tournament prestige now..."
                    )
                    self.bot.find_and_click_image(
                        image=self.bot.files["tournaments_join"],
                        region=self.bot.configurations["regions"]["tournaments"]["join_area"],
                        precision=self.bot.configurations["parameters"]["tournaments"]["join_precision"],
                        pause=self.bot.configurations["parameters"]["tournaments"]["join_pause"],
                        timeout=self.bot.configurations["parameters"]["tournaments"]["join_timeout"],
                    )
                    self.bot.find_and_click_image(
                        image=self.bot.files["prestige_confirm_confirm_icon"],
                        region=self.bot.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                        precision=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                        pause=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_pause"],
                        timeout=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_timeout"],
                        timeout_search_while_not=False,
                        timeout_search_kwargs={
                            "image": self.bot.files["prestige_confirm_confirm_icon"],
                            "region": self.bot.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                            "precision": self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                        },
                    )
                    self.bot.generate_event(
                        event="Tournament Prestige Performed...",
                    )
                except TimeoutError:
                    self.logger.info(
                        "Timeout was reached while trying to join tournament, skipping..."
                    )
            # Tournament is in a "red" state, one we joined is now
            # over and rewards are available.
            elif self.bot.point_is_color_range(
                point=self.bot.configurations["points"]["tournaments"]["tournaments_status"],
                color_range=self.bot.configurations["colors"]["tournaments"]["tournaments_over_range"],
            ):
                self.bot.click(
                    point=self.bot.configurations["points"]["tournaments"]["tournaments_icon"],
                    pause=self.bot.configurations["parameters"]["tournaments"]["icon_pause"],
                )
                if self.bot.find_and_click_image(
                    image=self.bot.files["tournaments_collect"],
                    region=self.bot.configurations["regions"]["tournaments"]["collect_area"],
                    precision=self.bot.configurations["parameters"]["tournaments"]["collect_precision"],
                    pause=self.bot.configurations["parameters"]["tournaments"]["collect_pause"],
                ):
                    self.logger.info(
                        "Collecting tournament rewards now..."
                    )
                    self.bot.click(
                        point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.bot.configurations["parameters"]["tournaments"]["post_collect_clicks"],
                        interval=self.bot.configurations["parameters"]["tournaments"]["post_collect_interval"],
                        pause=self.bot.configurations["parameters"]["tournaments"]["post_collect_pause"],
                    )
                    self.bot.generate_event(
                        event="Collected Tournament Rewards...",
                    )

        if not tournament_prestige:
            try:
                self.logger.info(
                    "Performing prestige now..."
                )
                self.bot.find_and_click_image(
                    image=self.bot.files["prestige_icon"],
                    region=self.bot.configurations["regions"]["prestige"]["prestige_icon_area"],
                    precision=self.bot.configurations["parameters"]["prestige"]["prestige_icon_precision"],
                    pause=self.bot.configurations["parameters"]["prestige"]["prestige_icon_pause"],
                    timeout=self.bot.configurations["parameters"]["prestige"]["prestige_icon_timeout"],
                    timeout_search_while_not=False,
                    timeout_search_kwargs={
                        "image": self.bot.files["prestige_icon"],
                        "region": self.bot.configurations["regions"]["prestige"]["prestige_icon_area"],
                        "precision": self.bot.configurations["parameters"]["prestige"]["prestige_icon_precision"],
                    },
                )
                # Check for the daily limit here in case it's been reached...
                # In which case we'll update our internal value to handle this.
                self._prestige_check_daily_limit()
                # Continue prestige post this check...
                self.bot.find_and_click_image(
                    image=self.bot.files["prestige_confirm_icon"],
                    region=self.bot.configurations["regions"]["prestige"]["prestige_confirm_icon_area"],
                    precision=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_icon_precision"],
                    pause=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_icon_pause"],
                    timeout=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_icon_timeout"],
                )
                self.bot.find_and_click_image(
                    image=self.bot.files["prestige_confirm_confirm_icon"],
                    region=self.bot.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                    precision=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                    pause=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_pause"],
                    timeout=self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_timeout"],
                    timeout_search_while_not=False,
                    timeout_search_kwargs={
                        "image": self.bot.files["prestige_confirm_confirm_icon"],
                        "region": self.bot.configurations["regions"]["prestige"]["prestige_confirm_confirm_icon_area"],
                        "precision": self.bot.configurations["parameters"]["prestige"]["prestige_confirm_confirm_icon_precision"],
                    },
                )
                self.bot.generate_event(
                    event="Prestige Performed...",
                )
            except TimeoutError:
                self.logger.info(
                    "Timeout was reached while trying to perform prestige, skipping..."
                )
            # Waiting here through the confirm_confirm_icon_pause for the prestige
            # animation to be finished before moving on...
        if self.bot.configuration.artifacts_enabled:
            # Important to handle enchantments/discovery before upgrading
            # artifacts so we can make sure the upgrade doesn't spend all our relics.
            if self.bot.configuration.artifacts_enchantment_enabled:
                self._prestige_enchant_artifacts()
            if self.bot.configuration.artifacts_discovery_enabled:
                self._prestige_discover_artifacts()
            # Artifacts are enabled.
            self._prestige_upgrade_artifacts()

        # Reset the most powerful hero, first subsequent hero levelling
        # should handle this for us again.
        self.bot.powerful_hero = None
        # Update the next artifact that will be upgraded.
        # This is done regardless of upgrade state (success/fail).
        self.bot.next_artifact_upgrade = next(self.bot.upgrade_artifacts) if self.bot.upgrade_artifacts else None
        # Prestige specific variables can be reset now.
        self.bot.close_to_max_ready = False
        self.bot.master_levelled = False

        # Handle some forcing of certain functionality post prestige below.
        # We do this once to ensure the game is up and running efficiently
        # before beginning scheduled functionality again.
        self.logger.info(
            "Prestige is complete, forcing master, skills, heroes levelling before continuing..."
        )
        for run_after in [
            "level_master",
            "level_skills",
            "activate_skills",
            "level_heroes",
        ]:
            self.bot.plugins[run_after].execute(
                force=self.bot.plugins[run_after].force_on_start,
            )
        # Reset schedule data post prestige.
        # This ensures all functionality is "reset"
        # once prestige is complete, this includes prestige
        # functionality.
        self.bot.schedule_plugins()


register_plugin(
    plugin=Prestige,
)
