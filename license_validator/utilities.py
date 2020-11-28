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


def set_files(
    files_directory,
    files,
    logger=None,
):
    """
    Update the available images in the directory specified with the images passed in.
    """
    for file in files:
        version_path = "%(files_directory)s/%(version)s" % {
            "files_directory": files_directory,
            "version": file["version"],
        }
        file_path = "%(version_path)s/%(name)s" % {
            "version_path": version_path,
            "name": file["name"],
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
            f.write(base64.b64decode(file["content"]))


def set_dependencies(
    dependencies_directory,
    dependencies,
    logger=None,
):
    for dependency in dependencies:
        file_path = "%(dependencies_directory)s/%(name)s" % {
            "dependencies_directory": dependencies_directory,
            "name": dependency["name"],
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
            f.write(base64.b64decode(dependency["content"]))
        # Ensure dependency is extracted properly
        # after the file is created.
        with zipfile.ZipFile(file_path, mode="r") as zip_ref:
            zip_ref.extractall(path=dependencies_directory)


def set_configurations(
    configurations_file,
    content,
    logger=None,
):
    """
    Update the specified configurations file with the content specified.
    """
    with open(configurations_file, mode="w") as file:
        if logger:
            logger.info(
                "Writing global configurations..."
            )
        file.write(content)
