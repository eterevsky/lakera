import datetime
import flask
from flask import Response, request
import json
import logging
import os
import os.path
from PIL import Image
from queue import Queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


IMAGES = []
NEW_IMAGE_QUEUE = Queue()


def load_images(images_dir):
    images = []
    for file in os.listdir(images_dir):
        image = Image.open(os.path.join(images_dir, file))
        width, height = image.size
        images.append({
            "name": file,
            "size": f"{width} x {height}"
        })

    return images


logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)


app = flask.Flask(__name__)


@app.route("/thumbs/<path:filename>")
def static_thumbs(filename):
    return flask.send_from_directory("thumbs", filename)


@app.route("/images/<path:filename>")
def static_images(filename):
    return flask.send_from_directory("images", filename)


def build_navigation(ifrom, count, total_images):
    params = {}

    prev = {"show": False}
    first = {"show": False}
    if ifrom > 0:
        assert ifrom >= count
        prev = {
            "show": True,
            "ifrom": ifrom - count,
        }
        first = {"show": True}

    next = {"show": False}
    last = {"show": False}
    if ifrom + count < len(IMAGES):
        next = {
            "show": True,
            "ifrom": ifrom + count,
        }
        last = {
            "show": True,
            "ifrom": ((len(IMAGES) - 1) // count) * count,
        }

    return {'prev': prev, 'next': next, 'first': first, 'last': last}


@app.route("/show", methods=["GET"])
def index():
    while not NEW_IMAGE_QUEUE.empty():
        image = NEW_IMAGE_QUEUE.get()
        print("Got a new image from the queue:", image)
        IMAGES.append(image)

    try:
        ifrom = int(request.args.get("ifrom", 0))
    except ValueError:
        ifrom = 0
    try:
        count = int(request.args.get("count", 50))
    except ValueError:
        count = 0

    ifrom = ifrom // count * count
    images = []
    for im in IMAGES[ifrom : ifrom + count]:
        images.append({"name": im["name"], "size": im["size"]})

    count_per_page = []
    for c in (10, 50, 100, 500):
        cpp = {
            "current": c == count,
            "count": c
        }
        count_per_page.append(cpp)

    navigation = build_navigation(ifrom, count, len(IMAGES))
    print(navigation)

    return flask.render_template(
        "images.html",
        images=images,
        current_ifrom=ifrom,
        current_count=count,
        count_per_page=count_per_page,
        **navigation,
    )

MAX_HEIGHT = 128
MAX_WIDTH = 640
THUMBS_DIR = "thumbs"

def new_dimensions(dims):
    width, height = dims
    new_width, new_height = width * MAX_HEIGHT / height, MAX_HEIGHT
    if new_width > MAX_WIDTH:
        new_width, new_height = MAX_WIDTH, height * MAX_WIDTH / width
    return round(new_width), round(new_height)


def create_thumbnail(path):
    """Returns the filename and a tuple with dimensions"""
    image = Image.open(path)
    file = os.path.basename(path)
    new_width, new_height = new_dimensions(image.size)
    thumb = image.resize((new_width, new_height), resample=Image.LANCZOS)
    new_path = os.path.join(THUMBS_DIR, file)
    logging.info(f"Writing resized image with dimensions ({new_width}, {new_height}) to {new_path}")
    thumb.save(new_path)

    return (file, image.size)


class UpdateHandler(FileSystemEventHandler):
    def on_created(self, event):
        print("on_created", event, event.src_path)
        name, size = create_thumbnail(event.src_path)
        NEW_IMAGE_QUEUE.put({
            "name": name,
            "size": f"{size[0]} x {size[1]}"
        })



if __name__ == "__main__":
    IMAGES = load_images("images")
    handler = UpdateHandler()
    observer = Observer()
    observer.schedule(handler, "images")
    observer.start()
    try:
        app.run(port=5000, debug=True)
    finally:
        observer.stop()
        observer.join()
