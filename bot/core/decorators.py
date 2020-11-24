from string import Formatter

import functools
import datetime
import asyncio


class event(object):
    """
    Decorator function to ensure certain functions log "events" to the backend authentication server.

    An "event" should just represent something that happens while a bot session is running. An event should
    contain a readable timestamp, a title, and an optional description.
    """
    def __init__(self, title, description=None):
        self.title = title
        self.description = description

    def __call__(self, function):
        @functools.wraps(function)
        def wrapped(bot, *args, **kwargs):
            """
            Wrapping the bot function itself, we'll fire the event before the function is executed, this
            ensures that we dont run into any issues with long running functions or even "forever" running, ie:
            our main run function runs until we're done a session.
            """
            # The bot instance should always have access to the license
            # validation utility instance to handle events.
            bot.license.event(
                event={
                    "timestamp": str(datetime.datetime.now()),
                    "title": self.title.format(**self.format_dict(template=self.title, bot=bot)),
                    "description": self.description.format(**self.format_dict(template=self.title, bot=bot)) if self.description else None,
                },
            )
            return function(bot, *args, **kwargs)
        return wrapped

    def format_dict(self, template, bot):
        """
        Generate a format dictionary for a given template and bot instance. As long as a bot instance
        has access to a given template key on it's self instance, we can include those values in templates.
        """
        return {
            key: getattr(bot, key) for key in self.template_keys(template=template)
        }

    @staticmethod
    def template_keys(template):
        """
        Parse a given string template, returning any instances of template keys.
        """
        return [
            key[1] for key in Formatter().parse(format_string=template) if key[1] is not None
        ]
