from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class FightBoss(BotPlugin):
    """Attempt to initiate the boss fight in game if it isn't already.
    """
    plugin_name = "fight_boss"
    plugin_enabled = True
    plugin_interval = 5
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def execute(self, force=False):
        if not self.bot.search(
            image=[
                self.bot.files["fight_boss_icon"],
                self.bot.files["reconnect_icon"],
            ],
            region=self.bot.configurations["regions"]["fight_boss"]["search_area"],
            precision=self.bot.configurations["parameters"]["fight_boss"]["search_precision"]
        )[0]:
            # Return early, boss fight is already in progress.
            # or, we're almost at another fight.
            self.logger.debug(
                "Boss fight is already initiated or a non boss encounter is active..."
            )
        else:
            try:
                # Handle reconnection before trying to start a normal boss fight...
                # We'll use a longer graceful pause period here for reconnecting.
                if self.bot.find_and_click_image(
                    image=self.bot.files["reconnect_icon"],
                    region=self.bot.configurations["regions"]["fight_boss"]["search_area"],
                    precision=self.bot.configurations["parameters"]["fight_boss"]["search_precision"],
                    pause=self.bot.configurations["parameters"]["fight_boss"]["reconnect_pause"],
                ):
                    self.logger.info(
                        "Attempting to reconnect and initiate boss fight..."
                    )
                    return
                self.logger.info(
                    "Attempting to initiate boss fight..."
                )
                self.bot.find_and_click_image(
                    image=self.bot.files["fight_boss_icon"],
                    region=self.bot.configurations["regions"]["fight_boss"]["search_area"],
                    precision=self.bot.configurations["parameters"]["fight_boss"]["search_precision"],
                    pause=self.bot.configurations["parameters"]["fight_boss"]["search_pause"],
                    pause_not_found=self.bot.configurations["parameters"]["fight_boss"]["search_pause_not_found"],
                    timeout=self.bot.configurations["parameters"]["fight_boss"]["fight_boss_timeout"],
                    timeout_search_while_not=False,
                    timeout_search_kwargs={
                        "image": self.bot.files["fight_boss_icon"],
                        "region": self.bot.configurations["regions"]["fight_boss"]["search_area"],
                        "precision": self.bot.configurations["parameters"]["fight_boss"]["search_precision"],
                    },
                )
            except TimeoutError:
                self.logger.info(
                    "Boss fight could not be initiated, skipping..."
                )
            self.logger.info(
                "Boss fight initiated..."
            )


register_plugin(
    plugin=FightBoss,
)
