from bot.plugins.plugin import (
    register_plugin,
    BotPlugin,
)

import datetime


class ConfigureSkills(BotPlugin):
    """Configure skills in game, ensuring that if skill activation is enabled, proper date-times
    are configured for each enabled skill and its execution time.
    """
    plugin_name = "configure_skills"
    plugin_enabled = True
    plugin_interval = 0
    plugin_interval_reset = True
    plugin_execute_on_start = True
    plugin_force_on_start = True

    def _configure_skill(self, skill, interval):
        """Utility function to handle a specific skill and setup it's next run date.
        """
        setattr(
            self.bot,
            "skills_%(skill)s_next_run" % {"skill": skill},
            datetime.datetime.now() + datetime.timedelta(seconds=interval)
        )

    def execute(self, force=False):
        if self.plugin_enabled:
            # [skill, enabled, weight, interval, clicks].
            for skill in self.bot.skills_lst:
                skill, enabled, interval = (
                    skill[0],
                    skill[1],
                    skill[3],
                )
                if enabled:
                    self._configure_skill(
                        skill=skill,
                        interval=interval,
                    )


register_plugin(
    plugin=ConfigureSkills,
)
