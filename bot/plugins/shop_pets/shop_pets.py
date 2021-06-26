from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class ShopPets(BotPlugin):
    """Attempt to purchase any of the selected pets in game from the shop if they are available.
    """
    plugin_name = "shop_pets"
    plugin_enabled = "shop_pets_purchase_enabled"
    plugin_interval = "shop_pets_purchase_interval"
    plugin_interval_reset = False
    plugin_execute_on_start = "shop_pets_purchase_on_start"

    def _shop_ensure_prompts_closed(self):
        """Ensure any prompts or panels open in the shop panel are closed.

        This is important so we don't have any bundles open for extended time.
        """
        self.bot.find_and_click_image(
            image=self.bot.files["small_shop_exit"],
            region=self.bot.configurations["regions"]["shop"]["small_shop_exit_area"],
            precision=self.bot.configurations["parameters"]["shop"]["small_shop_exit_precision"],
            pause=self.bot.configurations["parameters"]["shop"]["small_shop_exit_pause"],
        )

    def execute(self, force=False):
        self.bot.travel_to_shop(
            stop_image_kwargs={
                "image": self.bot.files["shop_daily_deals_header"],
                "precision": self.bot.configurations["parameters"]["shop_pets"]["daily_deals_precision"],
            },
        )
        self.logger.info(
            "Attempting to purchase pets from the shop..."
        )

        timeout_shop_pets_search_cnt = 0
        timeout_shop_pets_search_max = self.bot.configurations["parameters"]["shop_pets"]["timeout_search_daily_deals"]

        try:
            while not (
                self.bot.search(
                    image=self.bot.files["shop_daily_deals_header"],
                    precision=self.bot.configurations["parameters"]["shop_pets"]["daily_deals_precision"],
                )[0] and
                self.bot.search(
                    image=self.bot.files["shop_chests_header"],
                    precision=self.bot.configurations["parameters"]["shop_pets"]["chests_precision"],
                )[0]
            ):
                # Looping until both the daily deals and chests headers
                # are present, since at that point, daily deals are on the screen
                # to search through.
                timeout_shop_pets_search_cnt = self.bot.handle_timeout(
                    count=timeout_shop_pets_search_cnt,
                    timeout=timeout_shop_pets_search_max,
                )
                self.bot.drag(
                    start=self.bot.configurations["points"]["shop"]["scroll"]["slow_drag_bottom"],
                    end=self.bot.configurations["points"]["shop"]["scroll"]["slow_drag_top"],
                    pause=self.bot.configurations["parameters"]["shop"]["slow_drag_pause"],
                )
                self._shop_ensure_prompts_closed()
        except TimeoutError:
            self.logger.info(
                "Unable to travel to the daily deals panel in the shop, skipping..."
            )
            # Always travel to the main screen following execution
            # so we don't linger on this panel.
            self.bot.travel_to_main_screen()
            return

        # At this point we can be sure that the daily deals
        # panel is open and can be parsed.
        for pet in self.bot.configuration.shop_pets_purchase_pets:
            found, position, image = self.bot.search(
                image=self.bot.files["pet_%(pet)s" % {"pet": pet}],
                precision=self.bot.configurations["parameters"]["shop_pets"]["pet_precision"],
            )
            if found:
                self.logger.info(
                    "Pet: \"%(pet)s\" found on screen, checking if purchase is possible..." % {
                        "pet": pet,
                    }
                )
                # Click on the pet, if it hasn't already been purchased, the correct header should
                # be present on the screen that we can use to purchase.
                self.bot.click(
                    point=position,
                    pause=self.bot.configurations["parameters"]["shop_pets"]["check_purchase_pause"],
                )
                # Check for the purchase header now...
                if self.bot.search(
                    image=self.bot.files["shop_pet_header"],
                    region=self.bot.configurations["regions"]["shop_pets"]["shop_pet_header_area"],
                    precision=self.bot.configurations["parameters"]["shop_pets"]["shop_pet_header_precision"],
                )[0]:
                    self.logger.info(
                        "Pet: \"%(pet)s\" can be purchased, purchasing now..." % {
                            "pet": pet,
                        }
                    )
                    self.bot.click(
                        point=self.bot.configurations["points"]["shop_pets"]["purchase_pet"],
                        pause=self.bot.configurations["parameters"]["shop_pets"]["purchase_pet_pause"],
                    )
                    # After buying the pet, we will click on the middle of the screen
                    # TWICE, we don't want to accidentally click on anything in the shop.
                    self.bot.click(
                        point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                        clicks=self.bot.configurations["parameters"]["shop"]["post_purchase_clicks"],
                        interval=self.bot.configurations["parameters"]["shop"]["post_purchase_interval"],
                        pause=self.bot.configurations["parameters"]["shop"]["post_purchase_pause"],
                    )
                else:
                    self.logger.info(
                        "Pet: \"%(pet)s\" can not be purchased, it's likely already been bought, skipping..." % {
                            "pet": pet,
                        }
                    )
                    self._shop_ensure_prompts_closed()
        self._shop_ensure_prompts_closed()
        # Always travel to the main screen following execution
        # so we don't linger on this panel.
        self.bot.travel_to_main_screen()


register_plugin(
    plugin=ShopPets,
)
