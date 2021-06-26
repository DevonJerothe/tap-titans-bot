from bot.plugins.level_heroes.level_heroes import (
    LevelHeroes,
)
from bot.plugins.plugin import (
    register_plugin,
)


class LevelHeroesQuick(LevelHeroes):
    """Level heroes in game quickly without dragging the panel or searching for max level heroes,
    we simply just travel to the heroes panel, scroll to the top and try to level heroes.
    """
    plugin_name = "level_heroes_quick"
    plugin_enabled = "level_heroes_quick_enabled"
    plugin_interval = "level_heroes_quick_interval"
    plugin_interval_reset = True
    plugin_execute_on_start = "level_heroes_quick_on_start"

    def execute(self, force=False):
        self.bot.travel_to_heroes(scroll=False)
        self.logger.info(
            "Attempting to level the heroes in game quickly..."
        )

        # If auto hero levelling is currently enabled and on in game,
        # we'll use that instead and skip quick levelling completely.
        if not self._level_heroes_autobuy_on():
            self.bot.travel_to_heroes(collapsed=False)
            self._level_heroes_ensure_max()

            # Loop through the specified amount of level loops for quick
            # levelling...
            for i in range(self.bot.configuration.level_heroes_quick_loops):
                self.logger.info(
                    "Levelling heroes quickly..."
                )
                self._level_heroes_on_screen()
        # If headgear swapping is turned on, we always check once heroes
        # are done being levelled quickly.
        else:
            self.logger.info(
                "Hero autobuy is currently enabled and on in game, skipping quick hero levelling..."
            )
        if self.bot.configuration.headgear_swap_enabled:
            self._check_headgear()


register_plugin(
    plugin=LevelHeroesQuick,
)
