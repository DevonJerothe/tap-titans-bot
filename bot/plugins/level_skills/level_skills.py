from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)


class LevelSkills(BotPlugin):
    """Attempt to level skills in game.

    Each skill is configured by the user and can be enabled/disabled and set to a specified level,
    or the "max" level available in game.
    """
    plugin_name = "level_skills"
    plugin_enabled = "level_skills_enabled"
    plugin_interval = "level_skills_interval"
    plugin_interval_reset = True
    plugin_execute_on_start = "level_skills_on_start"

    def execute(self, force=False):
        self.bot.travel_to_master(collapsed=False)
        self.logger.info(
            "Attempting to level all skills in game..."
        )
        for skill, region, point, max_point, clicks in zip(
            self.bot.configurations["global"]["skills"]["skills"],
            self.bot.configurations["regions"]["level_skills"]["skill_regions"],
            self.bot.configurations["points"]["level_skills"]["skill_points"],
            self.bot.configurations["points"]["level_skills"]["max_points"],
            [
                level for level in [
                    getattr(self.bot.configuration, "level_skills_%(skill)s_amount" % {
                        "skill": skill,
                    }) for skill in self.bot.configurations["global"]["skills"]["skills"]
                ]
            ],
        ):
            if clicks != "disable" and not self.bot.search(
                image=[
                    self.bot.files["level_skills_max_level"],
                    self.bot.files["level_skills_cancel_active_spell"],
                ],
                region=region,
                precision=self.bot.configurations["parameters"]["level_skills"]["max_level_precision"],
            )[0]:
                # Actually level the skill in question.
                # Regardless of max or amount specification.
                self.logger.info(
                    "Levelling %(skill)s now..." % {
                        "skill": skill,
                    }
                )
                if clicks != "max":
                    # Just level the skill the specified amount of clicks.
                    # 1-35 most likely if frontend enforces values proper.
                    self.bot.click(
                        point=point,
                        clicks=int(clicks),
                        interval=self.bot.configurations["parameters"]["level_skills"]["level_clicks_interval"],
                        pause=self.bot.configurations["parameters"]["level_skills"]["level_clicks_pause"],
                    )
                else:
                    # Attempt to max the skill out using the "level X"
                    # option that pops up when a user levels a skill.
                    timeout_level_max_cnt = 0
                    timeout_level_max_max = self.bot.configurations["parameters"]["level_skills"]["timeout_level_max"]

                    try:
                        while not self.bot.search(
                            image=[
                                self.bot.files["level_skills_max_level"],
                                self.bot.files["level_skills_cancel_active_spell"],
                            ],
                            region=region,
                            precision=self.bot.configurations["parameters"]["level_skills"]["max_level_precision"],
                        )[0]:
                            self.bot.click(
                                point=point,
                                pause=self.bot.configurations["parameters"]["level_skills"]["level_max_click_pause"]
                            )
                            if self.bot.point_is_color_range(
                                point=max_point,
                                color_range=self.bot.configurations["colors"]["level_skills"]["max_level_range"],
                            ):
                                self.bot.click(
                                    point=max_point,
                                    pause=self.bot.configurations["parameters"]["level_skills"]["level_max_pause"],
                                )
                            timeout_level_max_cnt = self.bot.handle_timeout(
                                count=timeout_level_max_cnt,
                                timeout=timeout_level_max_max,
                            )
                    except TimeoutError:
                        self.logger.info(
                            "%(skill)s could not be maxed, skipping..." % {
                                "skill": skill,
                            }
                        )


register_plugin(
    plugin=LevelSkills,
)
