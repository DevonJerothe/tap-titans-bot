from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class Eggs(BotPlugin):
    """Collect eggs in game if they are currently available.
    """
    plugin_name = "eggs"
    plugin_enabled = True
    plugin_interval = 600
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def execute(self, force=False):
        if self.bot.find_and_click_image(
            image=self.bot.files["eggs_icon"],
            region=self.bot.configurations["regions"]["eggs"]["search_area"],
            precision=self.bot.configurations["parameters"]["eggs"]["search_precision"],
            pause=self.bot.configurations["parameters"]["eggs"]["search_pause"],
        ):
            self.logger.info(
                "Eggs are available, collecting now..."
            )
            # Eggs are collected automatically, we'll just need to perform
            # some taps on the screen to speed up the process.
            self.bot.click(
                point=self.bot.configurations["points"]["main_screen"]["middle"],
                clicks=self.bot.configurations["parameters"]["eggs"]["post_collect_clicks"],
                interval=self.bot.configurations["parameters"]["eggs"]["post_collect_interval"],
                pause=self.bot.configurations["parameters"]["eggs"]["post_collect_pause"],
            )


register_plugin(
    plugin=Eggs,
)
