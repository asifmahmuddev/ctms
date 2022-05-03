"""Turns an uploaded picture into the square avatar stored against an account."""

from io import BytesIO

from PIL import Image, ImageOps
from django.core.files.base import ContentFile

from .models import DEFAULT_PROFILE_IMAGE

AVATAR_SIZE_PIXELS = 512
AVATAR_FORMAT = 'PNG'
AVATAR_FILENAME = 'profile.png'
AVATAR_MODE = 'RGBA'
AVATAR_RESAMPLING = Image.Resampling.LANCZOS

# The smallest square worth storing, in the picture's own pixels.
MINIMUM_CROP_PIXELS = 128


def centred_square(width, height):
    """Return the largest square that fits inside the given size, centred on it."""

    side = min(width, height)
    return ((width - side) // 2, (height - side) // 2, side, side)


def clamp_selection(selection, width, height):
    """Fit a requested crop inside the picture as a square of usable size.

    Cropper.js reports the picture's own pixels, but its box may run past an edge while dragging, so
    the square is grown to the minimum, capped by the picture, then moved inside rather than trimmed.
    """

    left, top, side_width, side_height = selection
    smallest = min(MINIMUM_CROP_PIXELS, width, height)
    side = min(max(min(side_width, side_height), smallest), width, height)
    return (max(0, min(left, width - side)), max(0, min(top, height - side)), side, side)


def build_avatar(upload, selection=None):
    """Return the upload cropped square and scaled down, ready to hand to the image field."""

    with Image.open(upload) as opened:
        # Phone cameras store a rotation flag the browser applied before the selection was made.
        picture = ImageOps.exif_transpose(opened)

    width, height = picture.size
    left, top, side, _ = clamp_selection(selection, width, height) if selection else centred_square(width, height)
    avatar = picture.convert(AVATAR_MODE).crop((left, top, left + side, top + side))
    if side > AVATAR_SIZE_PIXELS:
        avatar = avatar.resize((AVATAR_SIZE_PIXELS, AVATAR_SIZE_PIXELS), AVATAR_RESAMPLING)

    content = BytesIO()
    avatar.save(content, format=AVATAR_FORMAT)
    return ContentFile(content.getvalue())


def store_profile_image(user, upload, selection=None):
    """Replace the account's avatar with the cropped upload."""

    stored = user.profile_image

    # Storage renames rather than overwrites, so the old file goes first; the shared default stays.
    if stored and stored.name != DEFAULT_PROFILE_IMAGE:
        stored.delete(save=False)

    user.profile_image.save(AVATAR_FILENAME, build_avatar(upload, selection), save=True)
