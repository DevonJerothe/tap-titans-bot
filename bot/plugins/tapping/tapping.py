from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)

import copy
import random
import time


class Tapping(BotPlugin):
    """Initiate the tapping process in game. This handles the activation of mini-games on the screen
    and fairy collection.
    """
    plugin_name = "tapping"
    plugin_enabled = "tapping_enabled"
    plugin_interval = "tapping_interval"
    plugin_interval_reset = True
    plugin_execute_on_start = True

    def fairies(self):
        """Check for any fairy prompts on screen, and deal with them accordingly.
        """
        # Attempt to just collect the ad rewards...
        # If the "collect" text is present, then the
        # user must have VIP status or a season pass.
        collected = self.bot.find_and_click_image(
            image=self.bot.files["fairies_collect"],
            region=self.bot.configurations["regions"]["fairies"]["collect_area"],
            precision=self.bot.configurations["parameters"]["fairies"]["collect_precision"],
            pause=self.bot.configurations["parameters"]["fairies"]["collect_pause"],
        )
        if collected:
            self.logger.info(
                "Fairy ad has been collected..."
            )
        if not collected:
            # Is there even ad ad on the screen?
            found, no_thanks_pos, image = self.bot.search(
                image=self.bot.files["fairies_no_thanks"],
                region=self.bot.configurations["regions"]["fairies"]["no_thanks_area"],
                precision=self.bot.configurations["parameters"]["fairies"]["no_thanks_precision"],
            )
            if found:
                # No ad can be collected without watching an ad.
                # We can loop and wait for a disabled ad to be blocked.
                # (This is done through ad blocking, unrelated to our code here).
                if self.bot.get_settings_obj().ad_blocking:
                    self.logger.info(
                        "Attempting to collect ad rewards through ad blocking..."
                    )
                    try:
                        self.bot.find_and_click_image(
                            image=self.bot.files["fairies_watch"],
                            region=self.bot.configurations["regions"]["fairies"]["ad_block_collect_area"],
                            precision=self.bot.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                            pause=self.bot.configurations["parameters"]["fairies"]["ad_block_pause"],
                            pause_not_found=self.bot.configurations["parameters"]["fairies"]["ad_block_pause_not_found"],
                            timeout=self.bot.configurations["parameters"]["fairies"]["ad_block_timeout"],
                            timeout_search_kwargs={
                                "image": self.bot.files["fairies_collect"],
                                "region": self.bot.configurations["regions"]["fairies"]["ad_block_collect_area"],
                                "precision": self.bot.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                            },
                        )
                    except TimeoutError:
                        self.logger.info(
                            "Unable to handle fairy ad through ad blocking, skipping..."
                        )
                        self.bot.click_image(
                            image=image,
                            position=no_thanks_pos,
                            pause=self.bot.configurations["parameters"]["fairies"]["no_thanks_pause"],
                        )
                        return
                    # At this point, the collect options is available
                    # to the user, attempt to collect the fairy reward.
                    self.bot.find_and_click_image(
                        image=self.bot.files["fairies_collect"],
                        region=self.bot.configurations["regions"]["fairies"]["ad_block_collect_area"],
                        precision=self.bot.configurations["parameters"]["fairies"]["ad_block_collect_precision"],
                        pause=self.bot.configurations["parameters"]["fairies"]["ad_block_pause"],
                        timeout=self.bot.configurations["parameters"]["fairies"]["ad_block_timeout"],
                    )
                    self.logger.info(
                        "Fairy ad has been collected through ad blocking..."
                    )
                else:
                    # Ads can not be collected for the user.
                    # Let's just press our no thanks button.
                    self.logger.info(
                        "Fairy ad could not be collected, skipping..."
                    )
                    self.bot.click_image(
                        image=image,
                        position=no_thanks_pos,
                        pause=self.bot.configurations["parameters"]["fairies"]["no_thanks_pause"],
                    )

    def execute(self, force=False):
        try:
            self.bot.collapse()
            self.bot.collapse_event_panel()
        except TimeoutError:
            # Check for a timeout error directly while collapsing panels,
            # this allows us to skip tapping if collapsing failed.
            self.logger.info(
                "Unable to successfully collapse panels in game, skipping tap functionality..."
            )
        # To prevent many, many logs from appearing in relation
        # to the tapping functionality, we'll go ahead and only
        # log the swiping information if the last function wasn't
        # already the tapping function.
        if self.bot.stream.last_message != "Tapping...":
            self.logger.info(
                "Tapping..."
            )
        tap = []
        maps = [
            "fairies",
            "heroes",
            "pet",
            "master",
        ]
        for key in maps:
            if key == "heroes":
                lst = copy.copy(self.bot.configurations["points"]["tap"]["tap_map"][key])
                for i in range(self.bot.configurations["parameters"]["tap"]["tap_heroes_loops"]):
                    # The "heroes" key will shuffle and reuse the map, this aids in the process
                    # of activating the astral awakening skills.
                    random.shuffle(lst)
                    # After a shuffle, we'll also remove some tap points if they dont surpass a certain
                    # percent threshold configured in the backend.
                    lst = [
                        point for point in lst if
                        random.random() > self.bot.configurations["parameters"]["tap"]["tap_heroes_remove_percent"]
                    ]
                    tap.extend(lst)
            else:
                tap.extend(self.bot.configurations["points"]["tap"]["tap_map"][key])

        # Remove any points that could open up the
        # one time offer prompt.
        if self.bot.search(
            image=self.bot.files["one_time_offer"],
            region=self.bot.configurations["regions"]["tap"]["one_time_offer_area"],
            precision=self.bot.configurations["parameters"]["tap"]["one_time_offer_precision"],
        )[0]:
            # A one time offer is on the screen, we'll filter out any tap points that fall
            # within this point, this prevents us from buying anything in the store.
            tap = [point for point in tap if not self.bot.point_is_region(
                point=point,
                region=self.bot.configurations["regions"]["tap"]["one_time_offer_prevent_area"],
            )]

        for index, point in enumerate(tap):
            if index % self.bot.configurations["parameters"]["tap"]["tap_fairies_modulo"] == 0:
                # Also handle the fact that fairies could appear
                # and be clicked on while tapping is taking place.
                self.fairies()
                if self.bot.stream.last_message != "Tapping...":
                    self.logger.info(
                        "Tapping..."
                    )
            if index % self.bot.configurations["parameters"]["tap"]["tap_collapse_prompts_modulo"] == 0:
                # Also handle the fact the tapping in general is sporadic
                # and the incorrect panel/window could be open.
                try:
                    self.bot.collapse()
                    self.bot.collapse_event_panel()
                except TimeoutError:
                    # This might be a one off issue, in which case, just continue even though
                    # we aren't able to collapse.
                    continue
            self.bot.click(
                point=point,
                button=self.bot.configurations["parameters"]["tap"]["button"],
                offset=random.randint(
                    self.bot.configurations["parameters"]["tap"]["offset_min"],
                    self.bot.configurations["parameters"]["tap"]["offset_max"],
                ),
            )
        # Only pausing after all clicks have been performed.
        time.sleep(self.bot.configurations["parameters"]["tap"]["pause"])
        # Additionally, perform a final fairy check explicitly
        # when tapping is complete, in case of a fairy being clicked
        # on right at the end of tapping.
        self.fairies()


register_plugin(
    plugin=Tapping,
)
