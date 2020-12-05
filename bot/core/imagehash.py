from PIL import Image


def d_hash(image, hash_size=8):
    """
    Computer the hash of a given image.
    """
    # Grayscale and shrink the image in one step.
    image = image.convert("L").resize((hash_size + 1, hash_size), Image.ANTIALIAS)

    # Compare adjacent pixels.
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left, pixel_right = (
                image.getpixel((col, row)),
                image.getpixel((col + 1, row))
            )
            difference.append(
                pixel_left > pixel_right
            )

    # Convert the binary array to a hexadecimal string.
    decimal_value = 0
    hex_string = []

    for index, value in enumerate(difference):
        if value:
            decimal_value += 2 ** (index % 8)
        if (index % 8) == 7:
            hex_string.append(
                hex(decimal_value)[2:].rjust(2, "0")
            )
            decimal_value = 0

    return "".join(hex_string)


def compare_images(image_one, image_two):
    """
    Compare two given images, determine if they are the same images.
    """
    return d_hash(image=image_one) == d_hash(image=image_two)
