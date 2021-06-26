from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class Achievements(BotPlugin):
    """Collect achievements in game if they are available.

    Achievements are available in game if the achievements icon is missing from the screen, since this
    most likely means that the "new" or "X" number of achievements are available to collect in game.
    """
    plugin_name = "achievements"
    plugin_enabled = True
    plugin_interval = 600
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def execute(self, force=False):
        self.bot.travel_to_master()
        self.logger.info(
            "Checking if achievements are available to collect..."
        )
        if not self.bot.search(
            image=self.bot.files["achievements_icon"],
            region=self.bot.configurations["regions"]["achievements"]["search_area"],
            precision=self.bot.configurations["parameters"]["achievements"]["search_precision"],
        )[0]:
            self.bot.click(
                point=self.bot.configurations["points"]["achievements"]["achievements_icon"],
                pause=self.bot.configurations["parameters"]["achievements"]["icon_pause"],
            )
            # Also ensure the daily tab is opened.
            self.bot.find_and_click_image(
                image=self.bot.files["achievements_daily_header"],
                region=self.bot.configurations["regions"]["achievements"]["daily_header_area"],
                precision=self.bot.configurations["parameters"]["achievements"]["daily_header_precision"],
                pause=self.bot.configurations["parameters"]["achievements"]["daily_header_pause"],
            )
            while True:
                found, position, image = self.bot.search(
                    image=self.bot.files["achievements_collect"],
                    region=self.bot.configurations["regions"]["achievements"]["collect_area"],
                    precision=self.bot.configurations["parameters"]["achievements"]["collect_precision"],
                )
                if found:
                    self.logger.info(
                        "Collecting achievement..."
                    )
                    self.bot.click_image(
                        image=image,
                        position=position,
                        pause=self.bot.configurations["parameters"]["achievements"]["collect_pause"],
                    )
                else:
                    self.bot.find_and_click_image(
                        image=self.bot.files["large_exit"],
                        region=self.bot.configurations["regions"]["achievements"]["exit_area"],
                        precision=self.bot.configurations["parameters"]["achievements"]["exit_precision"],
                        pause=self.bot.configurations["parameters"]["achievements"]["exit_pause"],
                    )
                    break


register_plugin(
    plugin=Achievements,
)
