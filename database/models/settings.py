from django.db.models import (
    Model,
    Manager,
    CharField,
    BooleanField,
    IntegerField,
)


class SettingsManager(Manager):
    def get(self):
        """When retrieving our settings instance, we only ever want to return the first one if it exists,
        we treat this model like a "Singleton" in the sense that we only ever want one row.
        """
        if self.count() == 0:
            self.create()

        # Always grabbing the first available settings row.
        # Create happens above if none exist.
        return self.first()


class Settings(Model):
    """Settings instance should expose a singular row that contains all application settings.
    """
    editable_fields = [
        "failsafe",
        "ad_blocking",
        "log_level",
        "log_purge_days",
    ]

    log_level_choices = (
        ("DEBUG", "DEBUG"),
        ("ERROR", "ERROR"),
        ("WARNING", "WARNING"),
        ("INFO", "INFO"),
    )

    objects = SettingsManager()

    failsafe = BooleanField(
        default=True,
        verbose_name="Failsafe",
        help_text=(
            "Enable/disable the \"failsafe\" functionality while a bot is actively running. A failsafe exception will be\n"
            "encountered if this is enabled and your mouse cursor is in the TOP LEFT corner of your primary monitor. Note that\n"
            "running other windows or tasks in fullscreen mode may also raise failsafe exceptions if you're using the bot in\n"
            "the background. Defaults to \"True\"."
        ),
    )
    ad_blocking = BooleanField(
        default=False,
        verbose_name="Ad Blocking",
        help_text=(
            "Enable/disable the functionality that controls whether or not the \"watch\" button is clicked on when encountered\n"
            "in game. This function will only work if you have an external ad blocker actively running while playing the game.\n"
            "Defaults to \"False\"."
        ),
    )
    log_level = CharField(
        max_length=255,
        default="INFO",
        choices=log_level_choices,
        verbose_name="Log Level",
        help_text=(
            "Determine the log level used when displaying logs while a bot session is running. This setting is only applied\n"
            "on session startup, if this is changed while a session is running, you'll need to restart your session for the\n"
            "log level to be changed.\n"
            "Defaults to \"INFO\"."
        ),
    )
    log_purge_days = IntegerField(
        default=3,
        verbose_name="Log Purge (Days)",
        help_text=(
            "Specify the number of (days) to retain any logs, \"stale\" logs are purged once their modification date has surpassed\n"
            "the number of days specified here. Defaults to \"3\"."
        ),
    )
    # Unconfigurable settings. These are handled implicitly by the application
    # and we do not need to expose these to the gui for modification by the user.
    console_size = CharField(
        max_length=255,
        default="mode con: cols=140 lines=200",
    )
    last_window = CharField(
        max_length=255,
        default=None,
        null=True,
    )
    last_configuration = CharField(
        max_length=255,
        default=None,
        null=True,
    )
