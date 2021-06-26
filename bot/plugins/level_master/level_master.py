from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class LevelMaster(BotPlugin):
    """Attempt to level the sword master in game, ignoring the functionality if the users configuration
    specified to only level the master once per prestige, and a prestige hasn't taken place since the
    last execution.
    """
    plugin_name = "level_master"
    plugin_enabled = "level_master_enabled"
    plugin_interval = "level_master_interval"
    plugin_interval_reset = True
    plugin_execute_on_start = "level_master_on_start"

    def execute(self, force=False):
        if not self.bot.master_levelled:
            self.bot.travel_to_master()
            self.logger.info(
                "Attempting to level the sword master in game..."
            )
            self.bot.click(
                point=self.bot.configurations["points"]["level_master"]["level"],
                clicks=self.bot.configurations["parameters"]["level_master"]["level_clicks"],
                interval=self.bot.configurations["parameters"]["level_master"]["level_interval"],
            )
            if self.bot.configuration.level_master_once_per_prestige:
                self.bot.master_levelled = True


register_plugin(
    plugin=LevelMaster,
)
