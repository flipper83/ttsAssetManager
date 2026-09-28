from pathlib import Path

from PIL import Image

from tts_manager.optimizer import optimize_image, resize_to_fit


def make_image(path: Path, size: tuple[int, int], fmt: str = "PNG") -> Path:
    if fmt == "PNG":
        Image.new("RGBA", size, (255, 0, 0, 255)).save(path, fmt)
    else:
        Image.new("RGB", size, (255, 0, 0)).save(path, fmt)
    return path


def test_resize_to_fit_leaves_small_image_unchanged() -> None:
    img = Image.new("RGBA", (100, 50))
    resized = resize_to_fit(img, 2048)
    assert resized.size == (100, 50)


def test_resize_to_fit_downscales_oversized_image() -> None:
    img = Image.new("RGBA", (4000, 2000))
    resized = resize_to_fit(img, 2048)
    assert resized.size == (2048, 1024)


def test_optimize_image_resizes_oversized_png(tmp_path: Path) -> None:
    src = make_image(tmp_path / "big.png", (3000, 1000))
    dest = tmp_path / "processed" / "big.png"
    result = optimize_image(src, dest, max_dimension=1500)
    assert result == dest
    with Image.open(dest) as img:
        assert img.size == (1500, 500)


def test_optimize_image_keeps_small_image_size(tmp_path: Path) -> None:
    src = make_image(tmp_path / "small.png", (10, 10))
    dest = tmp_path / "processed" / "small.png"
    optimize_image(src, dest, max_dimension=2048)
    with Image.open(dest) as img:
        assert img.size == (10, 10)


def test_optimize_image_preserves_format(tmp_path: Path) -> None:
    src = make_image(tmp_path / "photo.jpg", (20, 20), fmt="JPEG")
    dest = tmp_path / "processed" / "photo.jpg"
    optimize_image(src, dest, max_dimension=2048)
    with Image.open(dest) as img:
        assert img.format == "JPEG"
