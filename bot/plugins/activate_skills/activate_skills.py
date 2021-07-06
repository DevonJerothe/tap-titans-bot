from bot.plugins.activate_skills.configure_skills import (
    ConfigureSkills,
)
from bot.plugins.plugin import (
    register_plugin,
)

import datetime


class ActivateSkills(ConfigureSkills):
    """Activate skills in game.

    Activated skills are dependant on the users configuration, each skill can have it's own
    interval set, as well as number of clicks to perform when it's activated.
    """
    plugin_name = "activate_skills"
    plugin_enabled = "activate_skills_enabled"
    plugin_interval = "activate_skills_interval"
    plugin_interval_reset = True
    plugin_execute_on_start = "activate_skills_on_start"
    plugin_force_on_start = True

    def execute(self, force=False):
        # We'll only travel if we have a skill ready to be activated...
        # Determine that here.
        ready = []
        now = datetime.datetime.now()

        for skill, interval in (
            ("heavenly_strike", self.bot.skills_heavenly_strike_next_run),
            ("deadly_strike", self.bot.skills_deadly_strike_next_run),
            ("hand_of_midas", self.bot.skills_hand_of_midas_next_run),
            ("fire_sword", self.bot.skills_fire_sword_next_run),
            ("war_cry", self.bot.skills_war_cry_next_run),
            ("shadow_clone", self.bot.skills_shadow_clone_next_run),
        ):
            if interval and (interval <= now or force):
                ready.append(
                    skill,
                )

        if ready:
            self.bot.travel_to_main_screen()
            self.logger.info(
                "Activating skills in game now..."
            )
            # Ensure we loop through the ordered skills to retain the proper
            # activation order for each ready skill.
            for skill in self.bot.skills_lst:
                skill, interval, clicks = (
                    skill[0],
                    skill[2],
                    skill[4],
                )
                if skill in ready:
                    self.logger.info(
                        "Activating %(skill)s %(clicks)s time(s) now..." % {
                            "skill": skill,
                            "clicks": clicks,
                        }
                    )
                    self.bot.click(
                        point=self.bot.configurations["points"]["activate_skills"]["skill_points"][skill],
                        clicks=clicks,
                        interval=self.bot.configurations["parameters"]["activate_skills"]["activate_interval"],
                        pause=self.bot.configurations["parameters"]["activate_skills"]["activate_pause"],
                    )
                    self._configure_skill(
                        skill=skill,
                        interval=interval,
                    )


register_plugin(
    plugin=ActivateSkills,
)
