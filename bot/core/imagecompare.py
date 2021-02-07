from numpy import (
    array,
    sum,
)


def mse(image_one, image_two):
    # Calculate the "Mean Squared Error" between both images, this number
    # represents how similar they are.
    err = sum((image_one.astype("float") - image_two.astype("float")) ** 2)
    err /= float(image_one.shape[0] * image_two.shape[1])

    # Returning the mse, lower the error, the more similar
    # the images are compared to each other.
    return err


def compare_images(image_one, image_two, threshold):
    """
    Compare two given images, determine if they are the same images.
    """
    return mse(
        image_one=array(image_one),
        image_two=array(image_two),
    ) < threshold
