import pytest
from app.entities.page import BoundingBox
from app.ocr.openthai import _axis_aligned_box


def test_model_polygon_maps_to_axis_aligned_image_coordinates() -> None:
    box = _axis_aligned_box(
        [[10.0, 20.0], [80.0, 10.0], [90.0, 45.0], [15.0, 55.0]],
        100,
        60,
    )

    assert box == BoundingBox(10.0, 10.0, 90.0, 55.0)


def test_model_polygon_is_clipped_to_displayed_image() -> None:
    box = _axis_aligned_box(
        [[-2.0, 5.0], [30.0, 5.0], [32.0, 20.0], [-1.0, 22.0]],
        30,
        20,
    )

    assert box == BoundingBox(0.0, 5.0, 30.0, 20.0)


def test_model_polygon_rejects_non_finite_coordinates() -> None:
    with pytest.raises(ValueError, match="invalid line polygon"):
        _axis_aligned_box(
            [[0.0, 0.0], [1.0, 0.0], [1.0, float("nan")], [0.0, 1.0]],
            2,
            2,
        )
