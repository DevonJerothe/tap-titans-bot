from bot.settings import (
    CONFIGURATION_DEFAULT_FILE,
)

import json


def get_default_configuration(
    default_configuration_file=None,
):
    """
    Retrieve the default configuration.

    The default configuration should contain a list
    of dictionaries that contain our specific configuration
    keys -> values along with a specific comment that should
    be associated with each configuration.
    """
    if not default_configuration_file:
        default_configuration_file = CONFIGURATION_DEFAULT_FILE

    with open(file=default_configuration_file, mode="r") as file:
        return json.loads(file.read())


def get_local_configuration(
    local_configuration_file,
):
    """
    Retrieve the local configuration.

    The local configuration should contain sets of key -> value
    pairs, we ignore the comments in this utility for now, since
    we re-write our comments whenever the local configuration is "set".
    """
    with open(file=local_configuration_file, mode="r") as file:
        # Default to a string representation of a dictionary ({}).
        # We do this to ensure the getter always returns something usable.
        return json.loads(file.read() or "{}")


def set_local_configuration(
    local_configuration_file,
    default_configuration_file=None,
    defaults=False
):
    """
    Set the local configuration.

    The local configuration file is in a .json format and

    We can re-write the file, ensuring that any keys in the default
    configuration that are missing from our local configuration are
    added in the correct order.
    """
    if not default_configuration_file:
        default_configuration_file = CONFIGURATION_DEFAULT_FILE

    default_configuration = get_default_configuration(default_configuration_file=default_configuration_file)
    local_configuration = get_local_configuration(local_configuration_file=local_configuration_file)

    # Return early if defaults and locals are already the same.
    if default_configuration == local_configuration:
        return

    # Create a dictionary to store all of the new configurations
    # and ordering for them that will be written back to the local file.
    local_new = {}

    if defaults:
        local_new = default_configuration
    else:
        # Begin looping through all of our defaults, ensure that each key -> value is present,
        # if a key is not present, we'll add it in the correct location.
        for configuration, value in default_configuration.items():
            if configuration in local_configuration:
                local_new[configuration] = local_configuration[configuration]
            else:
                local_new[configuration] = value

    with open(file=local_configuration_file, mode="w") as file:
        file.write(json.dumps(
            local_new,
            indent=4,
        ))
