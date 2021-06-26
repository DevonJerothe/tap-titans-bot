from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)
from bot.core.exceptions import (
    GameStateException,
)

import time


class CheckGameState(BotPlugin):
    """Check the current game state within the sessions emulator, attempting to reboot
    the game if the game state can not be read.
    """
    plugin_name = "check_game_state"
    plugin_enabled = True
    plugin_interval = 45
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def _check_game_state_reboot(self):
        """
        Reboot the emulator if possible, raising a game state exception if it is not possible.
        """
        self.logger.info(
            "Unable to handle current game state, attempting to recover and restart application..."
        )
        # Attempting to drag the screen and use the emulator screen
        # directly to travel to the home screen to recover.
        self.bot.drag(
            start=self.bot.configurations["points"]["check_game_state"]["emulator_drag_start"],
            end=self.bot.configurations["points"]["check_game_state"]["emulator_drag_end"],
            pause=self.bot.configurations["parameters"]["check_game_state"]["emulator_drag_pause"],
        )
        self.bot.click(
            point=self.bot.configurations["points"]["check_game_state"]["emulator_home_point"],
            clicks=self.bot.configurations["parameters"]["check_game_state"]["emulator_home_clicks"],
            interval=self.bot.configurations["parameters"]["check_game_state"]["emulator_home_interval"],
            pause=self.bot.configurations["parameters"]["check_game_state"]["emulator_home_pause"],
            offset=self.bot.configurations["parameters"]["check_game_state"]["emulator_home_offset"],
        )
        # The home screen should be active and the icon present on screen.
        found, position, image = self.bot.search(
            image=self.bot.files["application_icon"],
            region=self.bot.configurations["regions"]["check_game_state"]["application_icon_search_area"],
            precision=self.bot.configurations["parameters"]["check_game_state"]["application_icon_search_precision"],
        )
        if found:
            self.logger.info(
                "Application icon found, attempting to open game now..."
            )
            self.bot.click_image(
                image=image,
                position=position,
                pause=self.bot.configurations["parameters"]["check_game_state"]["application_icon_click_pause"],
            )
            return
        else:
            self.logger.info(
                "Unable to find the application icon to handle crash recovery, if your emulator is currently on the "
                "home screen, crash recovery is working as intended, please ensure the tap titans icon is available "
                "and visible."
            )
            self.logger.info(
                "If your game crashed and the home screen wasn't reached through this function, you may need to enable "
                "the \"Virtual button on the bottom\" setting in your emulator, this will enable the option for the bot "
                "to travel to the home screen."
            )
        raise GameStateException()

    def _check_game_state_misc(self):
        """Handle the miscellaneous game state check,
        """
        # Handle the skill prompt in game causing the bot
        # to be stuck...
        if self.bot.search(
            image=self.bot.files["warning_header"],
            precision=self.bot.configurations["parameters"]["check_game_state"]["misc_warning_header_precision"],
        )[0]:
            self.bot.click(
                point=self.bot.configurations["points"]["check_game_state"]["misc_warning_header_yes"],
                pause=self.bot.configurations["parameters"]["check_game_state"]["misc_warning_header_yes_pause"],
            )

        # Handle the server maintenance prompt showing up which should
        # just shut the bot down.
        if self.bot.search(
            image=self.bot.files["server_maintenance_header"],
            precision=self.bot.configurations["parameters"]["check_game_state"]["misc_server_maintenance_precision"],
        )[0]:
            self.bot.logger.info(
                "It looks like server maintenance is currently active, exiting..."
            )
            raise GameStateException()

    def _check_game_state_fairies(self):
        """
        Handle the fairies based game state check.
        """
        timeout_check_game_state_fairies_cnt = 0
        timeout_check_game_state_fairies_max = self.bot.configurations["parameters"]["check_game_state"]["check_game_state_fairies_timeout"]

        try:
            while self.bot.search(
                image=self.bot.files["fairies_no_thanks"],
                region=self.bot.configurations["regions"]["fairies"]["no_thanks_area"],
                precision=self.bot.configurations["parameters"]["fairies"]["no_thanks_precision"],
            )[0]:
                timeout_check_game_state_fairies_cnt = self.bot.handle_timeout(
                    count=timeout_check_game_state_fairies_cnt,
                    timeout=timeout_check_game_state_fairies_max,
                )
                # A fairy is on the screen, since this is a game state check, we're going to
                # actually decline the ad in this case after clicking on the middle of the screen.
                self.bot.click(
                    point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                    clicks=self.bot.configurations["parameters"]["check_game_state"]["fairies_pre_clicks"],
                    interval=self.bot.configurations["parameters"]["check_game_state"]["fairies_pre_interval"],
                    pause=self.bot.configurations["parameters"]["check_game_state"]["fairies_pre_pause"],
                )
                self.bot.find_and_click_image(
                    image=self.bot.files["fairies_no_thanks"],
                    region=self.bot.configurations["regions"]["fairies"]["no_thanks_area"],
                    precision=self.bot.configurations["parameters"]["fairies"]["no_thanks_precision"],
                    pause=self.bot.configurations["parameters"]["fairies"]["no_thanks_pause"],
                )
        except TimeoutError:
            # Reboot if the ad is unable to be closed for some reason
            # in game, the reboot lets us get a fresh start...
            self._check_game_state_reboot()

    def _check_game_state_frozen(self):
        """
        Handle the frozen emulator based game state check.
        """
        # We'll travel to the main screen whenever handling a frozen check,
        # this will have the most movement *if* the game isn't currently frozen.
        self.bot.travel_to_main_screen()

        if not self.bot.last_screenshot:
            self.bot.last_screenshot = self.bot.snapshot(
                region=self.bot.configurations["regions"]["check_game_state"]["frozen_screenshot_area"],
                pause=self.bot.configurations["parameters"]["check_game_state"]["frozen_screenshot_pause"],
            )
        # Comparing the last screenshot available with the current
        # screenshot of the emulator screen.
        self.bot.last_screenshot, duplicates = self.bot.duplicates(
            image=self.bot.last_screenshot,
            region=self.bot.configurations["regions"]["check_game_state"]["frozen_screenshot_area"],
            pause_before_check=self.bot.configurations["parameters"]["check_game_state"]["frozen_screenshot_before_pause"],
        )
        if duplicates:
            self._check_game_state_reboot()

    def _check_game_state_generic(self):
        """
        Handle the generic game state check.
        """
        timeout_check_game_state_generic_cnt = 0
        timeout_check_game_state_generic_max = self.bot.configurations["parameters"]["check_game_state"]["check_game_state_generic_timeout"]

        while True:
            # Attempting to travel to the main screen
            # in game. This will for sure have our
            # game state icons, and likely some of the
            # travel icons.
            self.bot.travel_to_main_screen()

            try:
                if not self.bot.search(
                    image=[
                        # Exit.
                        self.bot.files["large_exit"],
                        # Main Screen.
                        self.bot.files["attack_damage_icon"],
                        self.bot.files["current_damage_icon"],
                        self.bot.files["heroes_damage_icon"],
                        # Misc.
                        self.bot.files["no_boss_icon"],
                        self.bot.files["fight_boss_icon"],
                        self.bot.files["leave_boss_icon"],
                        # Travel Tabs.
                        self.bot.files["travel_master_icon"],
                        self.bot.files["travel_heroes_icon"],
                        self.bot.files["travel_equipment_icon"],
                        self.bot.files["travel_pets_icon"],
                        self.bot.files["travel_artifacts_icon"],
                        # Explicit Game State Images.
                        self.bot.files["coin_icon"],
                        self.bot.files["master_icon"],
                        self.bot.files["relics_icon"],
                        self.bot.files["options_icon"],
                    ],
                    precision=self.bot.configurations["parameters"]["check_game_state"]["state_precision"],
                )[0]:
                    timeout_check_game_state_generic_cnt = self.bot.handle_timeout(
                        count=timeout_check_game_state_generic_cnt,
                        timeout=timeout_check_game_state_generic_max,
                    )
                    # Pause slightly in between our checks...
                    # We don't wanna check too quickly.
                    time.sleep(self.bot.configurations["parameters"]["check_game_state"]["check_game_state_pause"])
                else:
                    # Game state is fine, exit with no errors.
                    break
            except TimeoutError:
                # Rebooting whenever the generic checks fail
                # for whatever reason...
                self._check_game_state_reboot()

    def execute(self, force=False):
        self.logger.debug(
            "Checking game state..."
        )

        # A couple of different methods are used to determine a game state...
        # Different odd use cases occur within the game that we check for here
        # and solve through this method.

        # 1. Checking for some of the miscellaneous game state checks, this currently includes
        #    things like the skill tree stuck open.
        self._check_game_state_misc()
        # 2. A fairy ad is stuck on the screen...
        #    This one is odd, but can be solved by clicking on the middle
        #    of the screen and then trying to collect the ad.
        self._check_game_state_fairies()
        # 3. The game has frozen completely, we track this by taking a screenshot of the entire
        #    screen when we're in here and comparing it to the last one taken each time, if the
        #    images are the same, we should reboot the game.
        self._check_game_state_frozen()
        # 4. The generic game state check, we try to travel to the main game screen
        #    and then we look for some key images that would mean we are still in the game.
        self._check_game_state_generic()


register_plugin(
    plugin=CheckGameState,
)
