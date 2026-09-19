"""Validates the face-count filter used to skip multi-child photos.

Downloads two real fixture images (one solo face, one two-person photo, both
from public test-image repos) and checks count_faces() gets the right count
for each, so the multi-child filter is exercised against real photos rather
than assumptions. Run with: pytest test_face_filter.py
"""

from pathlib import Path

import pytest
import requests

from tadpole_sync import count_faces

FIXTURE_DIR = Path(__file__).parent / "tests" / "fixtures"

ONE_FACE_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/lena.jpg"
TWO_FACES_URL = "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/two_people.jpg"


def _fetch(url, dest):
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


@pytest.fixture(scope="module")
def one_face_photo():
    return _fetch(ONE_FACE_URL, FIXTURE_DIR / "one_face.jpg")


@pytest.fixture(scope="module")
def two_face_photo():
    return _fetch(TWO_FACES_URL, FIXTURE_DIR / "two_faces.jpg")


def test_single_face_photo_counts_one(one_face_photo):
    assert count_faces(one_face_photo) == 1


def test_two_face_photo_counts_two(two_face_photo):
    assert count_faces(two_face_photo) == 2
