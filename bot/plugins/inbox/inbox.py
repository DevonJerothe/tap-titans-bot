from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class Inbox(BotPlugin):
    """Attempt to open and dismiss any inbox notifications in game if they are available.
    """
    plugin_name = "inbox"
    plugin_enabled = True
    plugin_interval = 600
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def execute(self, force=False):
        if self.bot.find_and_click_image(
            image=self.bot.files["inbox_icon"],
            region=self.bot.configurations["regions"]["inbox"]["search_area"],
            precision=self.bot.configurations["parameters"]["inbox"]["search_precision"],
            pause=self.bot.configurations["parameters"]["inbox"]["search_pause"],
        ):
            self.logger.info(
                "Inbox is present, attempting to collect any gifts/rewards..."
            )
            self.bot.click(
                point=self.bot.configurations["points"]["inbox"]["clan_header"],
                pause=self.bot.configurations["parameters"]["inbox"]["click_pause"],
            )
            if self.bot.find_and_click_image(
                image=self.bot.files["inbox_collect_all"],
                region=self.bot.configurations["regions"]["inbox"]["collect_all_area"],
                precision=self.bot.configurations["parameters"]["inbox"]["collect_all_precision"],
                pause=self.bot.configurations["parameters"]["inbox"]["collect_all_pause"],
            ):
                # Also clicking on the screen in the middle a couple
                # of times, ensuring rewards are collected...
                self.bot.click(
                    point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                    clicks=self.bot.configurations["parameters"]["inbox"]["collect_all_wait_clicks"],
                    interval=self.bot.configurations["parameters"]["inbox"]["collect_all_wait_interval"],
                    pause=self.bot.configurations["parameters"]["inbox"]["collect_all_wait_pause"],
                )
                self.logger.info(
                    "Inbox rewards collected successfully..."
                )
            self.bot.find_and_click_image(
                image=self.bot.files["large_exit"],
                region=self.bot.configurations["regions"]["inbox"]["exit_area"],
                precision=self.bot.configurations["parameters"]["inbox"]["exit_precision"],
                pause=self.bot.configurations["parameters"]["inbox"]["exit_pause"],
            )


register_plugin(
    plugin=Inbox,
)
