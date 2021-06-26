from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class DailyRewards(BotPlugin):
    """Collect daily rewards in game if they are currently available.
    """
    plugin_name = "daily_rewards"
    plugin_enabled = True
    plugin_interval = 60
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def execute(self, force=False):
        if self.bot.find_and_click_image(
            image=self.bot.files["daily_rewards_icon"],
            region=self.bot.configurations["regions"]["daily_rewards"]["search_area"],
            precision=self.bot.configurations["parameters"]["daily_rewards"]["search_precision"],
            pause=self.bot.configurations["parameters"]["daily_rewards"]["search_pause"],
        ):
            self.logger.info(
                "Daily rewards are available, collecting now..."
            )
            if self.bot.find_and_click_image(
                image=self.bot.files["daily_rewards_collect"],
                region=self.bot.configurations["regions"]["daily_rewards"]["collect_area"],
                precision=self.bot.configurations["parameters"]["daily_rewards"]["collect_precision"],
                pause=self.bot.configurations["parameters"]["daily_rewards"]["collect_pause"],
            ):
                # Successfully grabbed daily rewards, we'll perform some simple clicks
                # on the screen to skip some of the reward prompts.
                self.bot.click(
                    point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                    clicks=self.bot.configurations["parameters"]["daily_rewards"]["post_collect_clicks"],
                    interval=self.bot.configurations["parameters"]["daily_rewards"]["post_collect_interval"],
                    pause=self.bot.configurations["parameters"]["daily_rewards"]["post_collect_pause"],
                )


register_plugin(
    plugin=DailyRewards,
)
