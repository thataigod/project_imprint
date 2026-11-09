"""Tests for image discovery and overlapped decoding."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from imprint.engine.images import (
    ImageDecoder,
    discover_images,
    discover_reference_images,
)
from tests.engine.helpers import write_image


class TestDiscovery:
    def test_recursive_source_discovery(self, tmp_path: Path) -> None:
        write_image(tmp_path / "top.png", 1)
        write_image(tmp_path / "nested" / "child.png", 2)
        (tmp_path / "notes.txt").touch()

        images = discover_images(tmp_path)
        assert [path.name for path in images] == ["child.png", "top.png"]

    def test_reference_discovery_is_not_recursive(self, tmp_path: Path) -> None:
        write_image(tmp_path / "top.png", 1)
        write_image(tmp_path / "nested" / "child.png", 2)
        (tmp_path / "notes.txt").touch()

        images = discover_reference_images(tmp_path)
        assert [path.name for path in images] == ["top.png"]

    def test_empty_folders(self, tmp_path: Path) -> None:
        assert discover_images(tmp_path) == []
        assert discover_reference_images(tmp_path) == []


class TestImageDecoder:
    def test_decodes_in_order(self, tmp_path: Path) -> None:
        first = tmp_path / "first.png"
        second = tmp_path / "second.png"
        write_image(first, 11)
        write_image(second, 22)

        decoded = list(ImageDecoder([first, second]))
        assert [item.path for item in decoded] == [first, second]
        assert decoded[0].image is not None
        assert int(decoded[0].image[0, 0, 0]) == 11
        assert int(decoded[1].image[0, 0, 0]) == 22
        assert all(item.error is None for item in decoded)

    def test_reports_unreadable_images(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.jpg"
        bad.write_bytes(b"not an image")

        decoded = list(ImageDecoder([bad]))
        assert len(decoded) == 1
        assert decoded[0].image is None
        assert decoded[0].error is not None

    def test_empty_input(self) -> None:
        assert list(ImageDecoder([])) == []

    def test_worker_and_window_minimums(self, tmp_path: Path) -> None:
        image_path = tmp_path / "one.png"
        write_image(image_path, 5)
        decoded = list(ImageDecoder([image_path], max_workers=0, window=0))
        assert len(decoded) == 1
        assert decoded[0].image is not None

    def test_exception_during_decode_is_reported(self, tmp_path: Path, monkeypatch) -> None:
        image_path = tmp_path / "one.png"
        write_image(image_path, 5)

        def boom(path: str) -> np.ndarray:
            raise RuntimeError("decoder exploded")

        monkeypatch.setattr("imprint.engine.images.cv2.imread", boom)
        decoded = list(ImageDecoder([image_path]))
        assert decoded[0].image is None
        assert decoded[0].error == "decoder exploded"
