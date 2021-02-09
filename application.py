from gui.main import (
    GUI,
)

import sentry_sdk
import traceback


__APPLICATION_NAME__ = "Tap Titans Bot"
__APPLICATION_VERSION__ = "1.0.1.1"
__APPLICATION_DISCORD__ = "https://discord.gg/HRfuw6HY5n"

__SENTRY_DSN__ = "https://bb8849b87d42407d9127fe6a7a1fd42c@o467351.ingest.sentry.io/5517455"
__SENTRY_RELEASE__ = "%(application_name)s@%(version)s" % {
    "application_name": __APPLICATION_NAME__.lower().replace(" ", "-"),
    "version": __APPLICATION_VERSION__,
}


def before_send(event, hint):
    """
    A frozen pyinstaller application currently does not support proper
    exception lines and information... This shim at least let's us place
    the formatted exception into our extra information.

    See: https://github.com/getsentry/sentry-python/issues/812

    If this is amended, this can be removed and the normal
    behaviour should be fine.
    """
    event["extra"]["exception"] = ["".join(
        traceback.format_exception(*hint["exc_info"])
    )]
    return event


if __name__ == "__main__":
    # Sentry is used to ensure any errors are caught and successfully
    # sent along for auditing and analyzing.
    sentry_sdk.init(
        dsn=__SENTRY_DSN__,
        release=__SENTRY_RELEASE__,
        before_send=before_send,
    )
    # Initializing a new GUI instance. Most business logic
    # and validation type work is handled inside of the instance
    # itself. This is done to ensure we can display messages or
    # notifications to the user about errors, etc.
    gui = GUI(
        application_name=__APPLICATION_NAME__,
        application_version=__APPLICATION_VERSION__,
        application_discord=__APPLICATION_DISCORD__,
    )
    gui.run()
