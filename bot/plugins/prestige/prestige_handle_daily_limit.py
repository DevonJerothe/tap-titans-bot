from bot.plugins.prestige.prestige import (
    Prestige,
)
from bot.plugins.plugin import (
    register_plugin,
)


class PrestigeHandleDailyLimit(Prestige):
    """Perform the required check to determine if the daily prestige limit has been reached,
    this is useful so we can determine if the "event" icon "close to max" checks will work in game.
    """
    plugin_name = "prestige_handle_daily_limit"
    plugin_enabled = True
    plugin_interval = 0
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def execute(self, force=False):
        self.logger.debug(
            "Checking prestige daily limit now..."
        )

        self.bot.travel_to_master()
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
        self._prestige_check_daily_limit()


register_plugin(
    plugin=PrestigeHandleDailyLimit,
)
