from bot.plugins.prestige.prestige import (
    Prestige,
)
from bot.plugins.plugin import (
    register_plugin,
)


class PrestigeCloseToMax(Prestige):
    """Perform a prestige in game if the "close to max" threshold has been reached.

    Close to max can be determined two ways:

    1. The "event" icon is available for the event that is currently running.
    2. The "skills" page "Prestige To Reset" icon is available in game.

    Once either of these are met, the close to max has been reached and the prestige
    functionality will be executed, or scheduled.

    One caveat here is the "close to max fight boss" behaviour that will wait for
    the "fight boss" icon to appear in game after the threshold is reached before
    beginning the prestige functionality.
    """
    plugin_name = "prestige_close_to_max"
    plugin_enabled = "prestige_close_to_max_enabled"
    plugin_interval = 30
    plugin_interval_reset = True
    plugin_execute_on_start = False

    def _prestige_execute_or_schedule(self):
        """
        Execute, or schedule a prestige based on the current configured interval.
        """
        interval = self.bot.configuration.prestige_wait_when_ready_interval

        if interval > 0:
            self.logger.info(
                "Scheduling prestige to take place in %(interval)s second(s)..." % {
                    "interval": interval,
                }
            )
            # Cancel the scheduled prestige functions
            # if it's present so the options don't clash.
            self.bot.cancel_scheduled_plugin(tags=[
                "prestige",
                "prestige_close_to_max",
            ])
            self.bot.schedule_plugin(
                plugin="prestige",
                interval=interval,
            )
        else:
            self.bot.plugins["prestige"].execute()

    def execute(self, force=False):
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
        self.bot.travel_to_master()
        self.logger.info(
            "Checking if prestige should be performed due to being close to max stage..."
        )

        if not self.bot.close_to_max_ready:
            if (
                self.bot.configurations["global"]["events"]["event_running"]
                and not self.bot.configuration.abyssal
                and not self.bot.daily_limit_reached
            ):
                self.logger.info(
                    "Checking for event icon present on master panel..."
                )
                # Event is running, let's check the master panel for
                # the current event icon.
                if self.bot.search(
                    image=self.bot.files["prestige_close_to_max_event_icon"],
                    region=self.bot.configurations["regions"]["prestige_close_to_max"]["event_icon_search_area"],
                    precision=self.bot.configurations["parameters"]["prestige_close_to_max"]["event_icon_search_precision"],
                )[0]:
                    self.bot.close_to_max_ready = True
            else:
                # No event is running, instead, we will open the skill tree,
                # and check that the reset icon is present.
                self.logger.info(
                    "Checking for prestige reset on skill tree..."
                )
                self.bot.click(
                    point=self.bot.configurations["points"]["prestige_close_to_max"]["skill_tree_icon"],
                    pause=self.bot.configurations["parameters"]["prestige_close_to_max"]["skill_tree_click_pause"]
                )
                if self.bot.search(
                    image=self.bot.files["prestige_close_to_max_skill_tree_icon"],
                    region=self.bot.configurations["regions"]["prestige_close_to_max"]["skill_tree_search_area"],
                    precision=self.bot.configurations["parameters"]["prestige_close_to_max"]["skill_tree_search_precision"],
                )[0]:
                    self.bot.close_to_max_ready = True
                # Closing the skill tree once finished.
                # "prestige" variable will determine next steps below.
                while self.bot.search(
                    image=self.bot.files["prestige_close_to_max_skill_tree_header"],
                    region=self.bot.configurations["regions"]["prestige_close_to_max"]["skill_tree_header_area"],
                    precision=self.bot.configurations["parameters"]["prestige_close_to_max"]["skill_tree_header_precision"],
                )[0]:
                    # Looping to exit, careful since not exiting could cause us
                    # to use a skill point, which makes it hard to leave the prompt.
                    self.bot.find_and_click_image(
                        image=self.bot.files["large_exit"],
                        region=self.bot.configurations["regions"]["prestige_close_to_max"]["skill_tree_exit_area"],
                        precision=self.bot.configurations["parameters"]["prestige_close_to_max"]["skill_tree_exit_precision"],
                        pause=self.bot.configurations["parameters"]["prestige_close_to_max"]["skill_tree_exit_pause"],
                    )
        if self.bot.close_to_max_ready:
            if self.bot.configuration.prestige_close_to_max_fight_boss_enabled:
                self.logger.info(
                    "Prestige is ready, waiting for fight boss icon to appear..."
                )
                # We need to also make sure the fight boss function is no longer
                # scheduled to run for the rest of this prestige.
                self.bot.cancel_scheduled_function(tags="fight_boss")
                # Instead of executing or scheduling our prestige right away,
                # we will check for the fight boss icon and if it's present,
                # then we will execute/schedule.
                if self.bot.search(
                    image=self.bot.files["fight_boss_icon"],
                    region=self.bot.configurations["regions"]["fight_boss"]["search_area"],
                    precision=self.bot.configurations["parameters"]["fight_boss"]["search_precision"]
                )[0]:
                    self.logger.info(
                        "Fight boss icon is present, prestige is ready..."
                    )
                    self.bot.plugins["prestige"].execute()
            else:
                self.logger.info(
                    "Prestige is ready..."
                )
                self._prestige_execute_or_schedule()


register_plugin(
    plugin=PrestigeCloseToMax,
)