import os
from PIL import Image
import sys


MAX_HEIGHT = 128
MAX_WIDTH = 640


def new_dimensions(dims):
    width, height = dims
    new_width, new_height = width * MAX_HEIGHT / height, MAX_HEIGHT
    if new_width > MAX_WIDTH:
        new_width, new_height = MAX_WIDTH, height * MAX_WIDTH / width
    return round(new_width), round(new_height)


def main(images_dir, thumbs_dir):
    for file in os.listdir(images_dir):
        image = Image.open(os.path.join(images_dir, file))
        new_width, new_height = new_dimensions(image.size)
        thumb = image.resize((new_width, new_height), resample=Image.LANCZOS)
        thumb.save(os.path.join(thumbs_dir, file))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])