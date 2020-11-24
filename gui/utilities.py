import datetime
import logging
import glob
import os


def get_most_recent_log_file(
    log_directory,
):
    """
    Grab the most recent log file path.
    """
    pathname = "%(log_directory)s/*.log" % {
        "log_directory": log_directory,
    }
    try:
        return max(
            glob.iglob(
                pathname=pathname,
            ),
            key=os.path.getctime,
        )
    except ValueError:
        return None


def create_gui_logger(
    log_directory,
    log_name,
):
    """
    Generate a new logger instance with the proper handlers associated.
    """
    log_name = "%(log_name)s-gui" % {
        "log_name": log_name,
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
    handler_stream = logging.StreamHandler()
    handler_stream.setLevel(level=logging.INFO)
    handler_stream.setFormatter(fmt=log_formatter)

    logger.addHandler(hdlr=handler_file)
    logger.addHandler(hdlr=handler_stream)
    logger.setLevel(level=logging.DEBUG)

    return logger
