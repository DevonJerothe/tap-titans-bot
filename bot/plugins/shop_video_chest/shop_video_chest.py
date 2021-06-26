from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class ShopVideoChest(BotPlugin):
    """Attempt to watch/collect the video chest from the in game shop if it is available.
    """
    plugin_name = "shop_video_chest"
    plugin_enabled = "shop_video_chest_enabled"
    plugin_interval = "shop_video_chest_interval"
    plugin_interval_reset = False
    plugin_execute_on_start = "shop_video_chest_on_start"

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
                "image": self.bot.files["shop_watch_video_header"],
                "precision": self.bot.configurations["parameters"]["shop_video_chest"]["watch_video_precision"],
            },
        )
        self.logger.info(
            "Attempting to collect the video chest from the shop..."
        )

        timeout_shop_video_chest_cnt = 0
        timeout_shop_video_chest_max = self.bot.configurations["parameters"]["shop_video_chest"]["timeout_search_watch_video"]

        try:
            while not (
                self.bot.search(
                    image=self.bot.files["shop_watch_video_header"],
                    precision=self.bot.configurations["parameters"]["shop_video_chest"]["watch_video_precision"],
                )[0] and
                self.bot.search(
                    image=self.bot.files["shop_diamonds_header"],
                    precision=self.bot.configurations["parameters"]["shop_video_chest"]["diamonds_precision"],
                )[0]
            ):
                # Looping until both the watch video header and diamonds header
                # are present, since at that point, video chest is on the screen to search.
                timeout_shop_video_chest_cnt = self.bot.handle_timeout(
                    count=timeout_shop_video_chest_cnt,
                    timeout=timeout_shop_video_chest_max,
                )
                self.bot.drag(
                    start=self.bot.configurations["points"]["shop"]["scroll"]["slow_drag_bottom"],
                    end=self.bot.configurations["points"]["shop"]["scroll"]["slow_drag_top"],
                    pause=self.bot.configurations["parameters"]["shop"]["slow_drag_pause"],
                )
                self._shop_ensure_prompts_closed()
        except TimeoutError:
            self.logger.info(
                "Unable to travel to the video chest in the shop, skipping..."
            )
            # Always travel to the main screen following execution
            # so we don't linger on this panel.
            self.bot.travel_to_main_screen()
            return

        # At this point we can be sure that the video chest panel is open
        # and can be parsed.
        collect_found, collect_position, collect_image = self.bot.search(
            image=self.bot.files["shop_collect_video_icon"],
            precision=self.bot.configurations["parameters"]["shop_video_chest"]["collect_video_icon_precision"],
        )
        if collect_found:
            self.bot.click(
                point=collect_position,
                pause=self.bot.configurations["parameters"]["shop_video_chest"]["collect_pause"],
            )
            if not self.bot.point_is_color_range(
                    point=self.bot.configurations["points"]["shop_video_chest"]["collect_color_point"],
                    color_range=self.bot.configurations["colors"]["shop_video_chest"]["collect_disabled_range"],
            ):
                collect_found, collect_position, collect_image = self.bot.search(
                    image=self.bot.files["shop_collect_video_icon"],
                    precision=self.bot.configurations["parameters"]["shop_video_chest"]["collect_video_icon_precision"],
                )
                if collect_found:
                    # Only trying to collect if the collection button isn't in
                    # a disabled state...
                    if not self.bot.point_is_color_range(
                        point=self.bot.configurations["points"]["shop_video_chest"]["collect_color_point"],
                        color_range=self.bot.configurations["colors"]["shop_video_chest"]["collect_disabled_range"],
                    ):
                        self.logger.info(
                            "Video chest collection is available, collecting now..."
                        )
                        # Collection happens here.
                        self.bot.click(
                            point=self.bot.configurations["points"]["shop_video_chest"]["collect_point"],
                            pause=self.bot.configurations["parameters"]["shop_video_chest"]["collect_point_pause"],
                        )
                        # After collecting the chest, we will click on the middle of the screen
                        # TWICE, we don't want to accidentally click on anything in the shop.
                        self.bot.click(
                            point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                            clicks=self.bot.configurations["parameters"]["shop"]["post_purchase_clicks"],
                            interval=self.bot.configurations["parameters"]["shop"]["post_purchase_interval"],
                            pause=self.bot.configurations["parameters"]["shop"]["post_purchase_pause"],
                        )
                watch_found, watch_position, watch_image = self.bot.search(
                    image=self.bot.files["shop_watch_video_icon"],
                    precision=self.bot.configurations["parameters"]["shop_video_chest"]["watch_video_icon_precision"],
                )
                if watch_found:
                    if self.bot.get_settings_obj().ad_blocking:
                        # Watch is available, we'll only do this if ad blocking is enabled.
                        self.logger.info(
                            "Video chest watch is available, collecting now..."
                        )
                        self.bot.click(
                            point=watch_position,
                            pause=self.bot.configurations["parameters"]["shop_video_chest"]["watch_pause"],
                        )
                        while self.bot.search(
                            image=self.bot.files["shop_video_chest_header"],
                            region=self.bot.configurations["regions"]["shop_video_chest"]["video_chest_header_area"],
                            precision=self.bot.configurations["parameters"]["shop_video_chest"]["video_chest_header_precision"],
                        )[0]:
                            # Looping until the header has disappeared so we properly support the ad blocking
                            # video chest watch.
                            self.bot.click(
                                point=self.bot.configurations["points"]["shop_video_chest"]["collect_point"],
                                pause=self.bot.configurations["parameters"]["shop_video_chest"]["collect_pause"],
                            )
                        # After collecting the chest, we will click on the middle of the screen
                        # TWICE, we don't want to accidentally click on anything in the shop.
                        self.bot.click(
                            point=self.bot.configurations["points"]["main_screen"]["top_middle"],
                            clicks=self.bot.configurations["parameters"]["shop"]["post_purchase_clicks"],
                            interval=self.bot.configurations["parameters"]["shop"]["post_purchase_interval"],
                            pause=self.bot.configurations["parameters"]["shop"]["post_purchase_pause"],
                        )
                    else:
                        self.logger.info(
                            "Video chest watch is available but ad blocking is disabled, skipping..."
                        )
                if not collect_found and not watch_found:
                    self.logger.info(
                        "No video chest is available to collect, skipping..."
                    )
            else:
                self.logger.info(
                    "Video chest collection is not available, skipping..."
                )

        self._shop_ensure_prompts_closed()
        # Always travel to the main screen following execution
        # so we don't linger on this panel.
        self.bot.travel_to_main_screen()


register_plugin(
    plugin=ShopVideoChest,
)
