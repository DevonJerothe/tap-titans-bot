import base64
import zipfile
import os


def get_license(
    license_file,
    only_check_exists=False,
):
    """
    Grab the current license data available in the specified license file.
    """
    try:
        with open(file=license_file, mode="r") as file:
            # We need the content regardless of existence check or not.
            content = file.read()
            # Return a boolean if specified to only find
            # the existence of the license. An empty license file
            # could be present if this is the first time things
            # are being ran, OR, a user is messing with their local dir.
            if only_check_exists:
                return content != ""
            else:
                # Read all content and return.
                return content

    # If the file isn't found, we can return False/None based on whether
    # or not we're checking the existence instead of grabbing content.
    except FileNotFoundError:
        if only_check_exists:
            return False
        return None


def set_license(
    license_file,
    text,
):
    """
    Set the current license data available in the specified license file.
    """
    with open(file=license_file, mode="w") as file:
        # Simply just write our text to the file.
        file.write(text)


def set_file(
    instance,
    file_directory,
    logger=None,
):
    """
    Update the available images in the directory specified with the images passed in.
    """
    version_path = "%(files_directory)s/%(version)s" % {
        "files_directory": file_directory,
        "version": instance["version"],
    }
    file_path = "%(version_path)s/%(name)s" % {
        "version_path": version_path,
        "name": instance["name"],
    }
    if logger:
        logger.info(
            "Writing file: \"%(file_path)s\"..." % {
                "file_path": file_path,
            }
        )
        # Ensure the version directory is present for the image
        # that we will be setting up.
        if not os.path.exists(version_path):
            os.makedirs(version_path)

        # Write the actual image file to our directory.
        # Decoding our content back to base64 bytes.
        with open(file_path, mode="wb") as f:
            f.write(base64.b64decode(instance["content"]))


def sync_file(
    instance,
    instances,
    logger=None,
):
    """
    Sync the file instance so it's removed from any version directories if it's no longer within the actual set of
    program files available.
    """
    if instance.name not in instances:
        if logger:
            logger.info(
                "Deleting stale file: \"%(file_path)s\"..." % {
                    "file_path": instance.path,
                }
            )
            os.remove(instance)


def set_dependency(
    instance,
    dependency_directory,
    logger=None,
):
    file_path = "%(dependencies_directory)s/%(name)s" % {
        "dependencies_directory": dependency_directory,
        "name": instance["name"],
    }
    if logger:
        logger.info(
            "Writing dependency: \"%(file_path)s\"..." % {
                "file_path": file_path,
            }
        )
    # Generate the file itself that contains our dependency.
    # Dependencies are expected to come in a zip format.
    with open(file_path, mode="wb") as f:
        f.write(base64.b64decode(instance["content"]))
    # Ensure dependency is extracted properly
    # after the file is created.
    with zipfile.ZipFile(file_path, mode="r") as zip_ref:
        zip_ref.extractall(path=dependency_directory)


def changed_contents(
    export_contents,
    original_contents,
):
    """
    Given two dictionaries, create a new dictionary that only holds the set
    of dictionary keys/values that have changed between the two.
    """
    def calculate_difference(value, original_value):
        if value == "True" and original_value == "False":
            return value
        try:
            original_value, value = (
                float(original_value),
                float(value),
            )
        except ValueError:
            original_value, value = (
                0,
                0,
            )
        return "{:n}".format(float(int(value - original_value)))

    new_contents = {
        "playerStats": {},
        "artifacts": {},
    }

    for key in new_contents:
        for original_key, original_val in original_contents[key].items():
            export_key, export_val = (
                original_key,
                export_contents[key][original_key],
            )
            if isinstance(original_val, dict):
                for original_dict_key, original_dict_val in original_val.items():
                    export_dict_key, export_dict_val = (
                        original_dict_key,
                        export_contents[key][original_key][original_dict_key],
                    )
                    if original_dict_val != export_dict_val:
                        if not new_contents[key].get(original_key):
                            new_contents[key][original_key] = {}
                        new_contents[key][original_key].setdefault(original_dict_key, calculate_difference(
                            value=export_dict_val,
                            original_value=original_dict_val,
                        ))
            else:
                if original_val != export_val:
                    new_contents[key][original_key] = calculate_difference(
                        value=export_val,
                        original_value=original_val,
                    )
    return new_contents


def chunks(
    lst,
    n,
):
    """
    Yield successive "n" sized chunks from a given list.
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
