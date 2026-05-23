import pytest
from pathlib import Path
from PIL import Image


def make_png(directory: Path, name: str, size: tuple[int, int] = (10, 10), color: tuple = (255, 0, 0, 255)) -> Path:
    path = directory / name
    Image.new("RGBA", size, color).save(path)
    return path


@pytest.fixture
def input_dir(tmp_path: Path) -> Path:
    d = tmp_path / "input"
    d.mkdir()

    make_png(d, "to_gem.png", color=(255, 0, 0, 255))

    make_png(d, "c_hero_a.png", color=(0, 255, 0, 255))
    make_png(d, "c_hero_b.png", color=(0, 0, 255, 255))

    make_png(d, "t_forest_a.png", color=(0, 128, 0, 255))
    make_png(d, "t_forest_b.png", color=(0, 64, 0, 255))

    make_png(d, "d_spells_fireball.png", color=(255, 100, 0, 255))
    make_png(d, "d_spells_icebolt.png", color=(0, 100, 255, 255))
    make_png(d, "d_spells_back.png", color=(50, 50, 50, 255))

    return d
