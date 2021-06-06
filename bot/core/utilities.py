from bot.core.constants import DECRYPT_MAP

import datetime
import logging


class LogStream(object):
    def __init__(
        self,
        ignore_records=None,
        disable_levels=None,
        max_logs=50,
    ):
        self.ignore_records = ignore_records or ["\n"]
        self.disable_levels = disable_levels or ["DEBUG"]
        self.max_logs = max_logs

        # String all captured records in a list. Clearing it if
        # needed later on while writing records.
        self.logs = []

    def write(self, record):
        # Ignoring records with certain content in them
        # and any levels we don't wish to retain.
        if record not in self.ignore_records and self.record_level(record=record) not in self.disable_levels:
            if len(self.logs) > self.max_logs:
                # Clear out some logs if we've exceeded
                # the allowed amount of logs...
                self.logs.pop(0)
            # Appending our record normally to the available logs.
            self.logs.append(
                self.record_message(record=record),
            )

    def flush(self):
        pass

    @property
    def last_message(self):
        """
        Return the last log message available.
        """
        return self.logs[-1] if self.logs else None

    def __str__(self):
        return "".join(self.logs)

    @staticmethod
    def record_level(record):
        """
        Return the record level from the record.
        """
        return record.split(":")[0]

    @staticmethod
    def record_message(record):
        """
        Return the record message from the record.
        """
        return record.split(":")[2]


class StreamHandler(logging.StreamHandler):
    """Custom StreamHandler to ensure we can handle only emitting logs when
    the active instance is being logged.
    """
    def __init__(self, instance_id, instance_func, stream=None):
        """Initialize a custom stream handler, the active instance and a function to retrieve
        the currently active instance should be available, these are used to determine whether
        or not a log is emitted to the stream.
        """
        self.instance_id = instance_id
        self.instance_func = instance_func
        # Handle super init following instance
        # information setup.
        super().__init__(stream=stream)

    def emit(self, record):
        if self.instance_func() == self.instance_id:
            super().emit(record=record)


# Instance of our stream available through runtime.
# We only ever want one...
_STREAM = LogStream()

# Configure logging to use custom stream.
# This lets us properly handle log records
# where needed.
logging.basicConfig(
    stream=_STREAM,
)


def create_logger(
    log_directory,
    instance_id,
    instance_name,
    instance_func,
    session_id,
):
    """
    Generate a new logger instance with the proper handlers associated.
    """
    log_name = "%(instance_name)s-%(uuid)s" % {
        "instance_name": instance_name.replace(" ", "-").lower(),
        "uuid": session_id,
    }
    log_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [{log_name}] - %(message)s".format(
            log_name=log_name,
        ),
    )
    logger = logging.getLogger(name=log_name)
    logger_file = "%(log_directory)s/%(log_name)s-%(log_date)s.log" % {
        "log_directory": log_directory,
        "log_name": log_name,
        "log_date": datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
    }

    # File handler should always use a debug level of logging
    # to ensure all important information is available.
    handler_file = logging.FileHandler(filename=logger_file)
    handler_file.setLevel(level=logging.DEBUG)
    handler_file.setFormatter(fmt=log_formatter)

    # Stream handler should default to our information level
    # of logging to ensure only relevant information is available.
    handler_stream = StreamHandler(
        instance_id=instance_id,
        instance_func=instance_func,
    )
    handler_stream.setLevel(level=logging.INFO)
    handler_stream.setFormatter(fmt=log_formatter)

    logger.addHandler(hdlr=handler_file)
    logger.addHandler(hdlr=handler_stream)
    logger.setLevel(level=logging.DEBUG)

    return logger, _STREAM


def decrypt_secret(secret):
    """
    Decrypt a given "secret" string.

    "Secrets" in this sense are just simply scrambled strings and are not meant to be
    "secure" or "safe" from un-obfuscation, this just acts as a layer between them to prevent
    easy local modification.
    """
    return "".join([
        DECRYPT_MAP[character] for character in secret
    ])
