
# Global dictionary of registered plugins, we use a dictionary here to avoid issues
# with imports registering a plugin multiple times. Dict ordering is retained here
# so we can loop through this dictionary and retain our registered order.
PLUGINS = {}


def register_plugin(plugin):
    """Register the given plugin, ensure a plugin can only be present
    once in our list of available plugins.
    """
    if plugin.plugin_name not in PLUGINS:
        PLUGINS[plugin.plugin_name] = plugin


class BotPlugin(object):
    """A ``BotPlugin`` works by implementing the following patterns:

    - Ensure a dot separated key is used to derive the location of the plugins
      enabled key as well as the interval key used to schedule the plugins execution
      in the main bot runtime loop.

    - Follow the commented rules below for defining plugin settings/attributes.

    - Ensure a ``execute`` method is available that actually "runs" the plugin's
      main logic/functionality.

    """
    # The ``name`` of the plugin, this is just used for logging purposes
    # and for organizing plugins, has no bearing on functionality at the moment.
    plugin_name = None

    # Is this plugin enabled? This can be a hard-coded boolean value, or a dot
    # separated key that contains a value taken from the user configuration, or
    # the global schema that is defined.
    plugin_enabled = None

    # How often should this function be executed through the scheduler, this can be
    # a hard-coded integer value, or a dot separated key that contains a value taken
    # from the user configuration or the global schema that is defined.
    plugin_interval = None

    # Is this plugin's interval "reset" upon an in game prestige? This is a boolean
    # value that handles the following:
    #
    # If True: Upon prestige, this function has it's next execution time reset to the
    # current time + the interval defined.
    #
    # If False: Upon prestige, this function retains it's existing next execution time
    # and runs as it normally would.
    plugin_interval_reset = None

    # Should this plugin be executed once on session startup? This can be a hard-coded
    # boolean value, or a dot separated key that contains a value taken from the user
    # configuration or the global schema that is defined.
    plugin_execute_on_start = None

    # Should this plugin "force" itself on on session startup. This defaults to false,
    # and if it's true, the execute function will use it to handle any "initial" functionality
    # that may be required to make this work.
    plugin_force_on_start = False

    def __init__(self, bot, logger):
        self.bot = bot
        self.logger = logger

        for req in [
            "plugin_name",
            "plugin_enabled",
            "plugin_interval",
            "plugin_interval_reset",
            "plugin_execute_on_start",
        ]:
            if getattr(self, req) is None:
                raise ValueError(
                    "``%(req)s`` must be set on any ``BotPlugin`` instances. Modify the plugin: \"%(plugin)s\" to meet "
                    "this requirement and try again." % {
                        "req": req,
                        "plugin": self.__class__.__name__
                    },
                )
        if self.plugin_force_on_start is None:
            raise ValueError(
                "``plugin_force_on_start`` should be ``True`` or ``False`` when defined on any "
                "``BotPlugin`` instances. Modify the plugin: \"%(plugin)s\" to meet this requirement "
                "and try again." % {
                    "plugin": self.__class__.__name__,
                }
            )

        self._default_schemas = [
            self.bot.configuration,
            self.bot.configurations,
        ]

        self.enabled = self._parse_key(
            schemas=self._default_schemas,
            key=self.plugin_enabled,
        )
        self.interval = self._parse_key(
            schemas=self._default_schemas,
            key=self.plugin_interval,
        )
        self.execute_on_start = self._parse_key(
            schemas=self._default_schemas,
            key=self.plugin_execute_on_start,
        )
        self.name = self.plugin_name
        self.interval_reset = self.plugin_interval_reset
        self.force_on_start = self.plugin_force_on_start

    def _parse_key(self, schemas, key, separator="."):
        """Parse a given key, checking to see if the given key is present in any of the schemas
        passed along.

        The default separator of ``.`` is used so that dot separated keys can be used
        when initializing new plugins for ease of access of configurations/values.
        """
        if not isinstance(key, str):
            # Early return out if the key isn't a string, this means it's likely
            # a hard-coded value that we can just use out of the box.
            return key

        key_parsed = None
        key = key.split(separator) if separator in key else [key]

        for schema in schemas:
            # If the schema isn't a dictionary, it must be a model (current impl).
            # so we can use getattr proper.
            if not isinstance(schema, dict):
                # Bit of a hack, but gets us our normalized dict.
                schema = schema.__dict__["__data__"]

            for val in key:
                if not key_parsed and val in schema:
                    key_parsed = schema.get(val)
                if key_parsed and isinstance(key_parsed, dict) and val in key_parsed:
                    key_parsed = key_parsed.get(val)

        return key_parsed

    def execute(self, force=False):
        raise NotImplementedError(
            "The ``execute`` function must be implemented on any subclasses of the "
            "``BotPlugin`` class."
        )


