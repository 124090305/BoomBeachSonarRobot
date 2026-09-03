from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from sonar.board import CellState, SonarBoard
from sonar_config import SonarLevelConfig, get_level_config
from vision.board_alignment import cell_polygon, grid_transform, project
from vision.board_recognition import recognize_board, recognize_board_files, resolve_reference_path
from vision.board_types import BoardRecognitionConfig
from vision.board_materials import assess_board_material
from vision import read_image


def scene(n=5, submarines=(2, 3)):
    level = SonarLevelConfig(n, submarines, ((320, 60), (560, 245), (320, 450), (80, 245)))
    matrix = grid_transform(level.board_quad, n)
    image = np.full((510, 650, 3), (135, 85, 25), np.uint8)
    for row in range(n):
        for col in range(n):
            poly = np.int32(cell_polygon(row, col, matrix, .92))
            cv2.fillConvexPoly(image, poly, (155, 135, 105))
            cv2.polylines(image, [poly], True, (235, 230, 215), 2)
    return image, level


def opened(image, level, cell):
    matrix = grid_transform(level.board_quad, level.grid_size)
    cv2.fillConvexPoly(image, np.int32(cell_polygon(*cell, matrix, .97)), (130, 78, 24))


def hull(image, level, cells):
    matrix = grid_transform(level.board_quad, level.grid_size)
    points = project([[c+.5, r+.5] for r, c in cells], matrix).astype(int)
    for cell in cells:
        opened(image, level, cell)
    width = round(130 / level.grid_size)
    cv2.line(image, tuple(points[0]), tuple(points[-1]), (160, 165, 164), width)
    for point in points:
        cv2.circle(image, tuple(point), max(3, width//2), (160, 165, 164), -1)
        cv2.circle(image, tuple(point), max(2, width//5), (230, 230, 230), 1)


class BoardRecognitionTests(unittest.TestCase):
    def test_empty_reference(self):
        ref, level = scene()
        result = recognize_board(ref, ref, level_config=level)
        self.assertEqual(result.counts["UNKNOWN"], 25)
        self.assertTrue(result.alignment.success)
        self.assertFalse(result.review_cells)

    def test_translation(self):
        ref, level = scene()
        moved = cv2.warpAffine(ref, np.float32([[1, 0, 5], [0, 1, -4]]), ref.shape[1::-1], borderMode=cv2.BORDER_REFLECT)
        result = recognize_board(ref, moved, level_config=level)
        self.assertTrue(result.alignment.success)
        self.assertEqual(result.counts["UNKNOWN"], 25)
        self.assertAlmostEqual(result.alignment.current_to_reference[0][2], -5, delta=1)

    def test_small_projective_change(self):
        ref, level = scene()
        transform = np.float32([[1.003, .003, 2], [-.002, .997, -1], [.000003, -.000004, 1]])
        cur = cv2.warpPerspective(ref, transform, ref.shape[1::-1], borderMode=cv2.BORDER_REFLECT)
        result = recognize_board(ref, cur, level_config=level)
        self.assertTrue(result.alignment.success)
        self.assertEqual(result.counts["UNKNOWN"], 25)

    def test_brightness_and_noise(self):
        ref, level = scene()
        rng = np.random.default_rng(123)
        changed = np.clip(ref.astype(float)+12+rng.normal(0, 1.5, ref.shape), 0, 255).astype(np.uint8)
        result = recognize_board(ref, changed, level_config=level)
        self.assertEqual(result.counts["UNKNOWN"], 25)

    def test_single_miss(self):
        ref, level = scene()
        cur = ref.copy()
        opened(cur, level, (2, 2))
        result = recognize_board(ref, cur, level_config=level)
        self.assertEqual(result.cell_at(2, 2).state, CellState.MISS)
        self.assertEqual(result.counts["MISS"], 1)

    def test_single_hit(self):
        ref, level = scene()
        cur = ref.copy()
        hull(cur, level, [(2, 2)])
        result = recognize_board(ref, cur, level_config=level)
        self.assertEqual(result.cell_at(2, 2).state, CellState.HIT)
        self.assertFalse(result.sunk_submarines)

    def test_horizontal_and_vertical_sunk(self):
        for cells in ([(2, 1), (2, 2), (2, 3)], [(1, 2), (2, 2), (3, 2)]):
            with self.subTest(cells=cells):
                ref, level = scene()
                cur = ref.copy()
                hull(cur, level, cells)
                result = recognize_board(ref, cur, level_config=level)
                self.assertEqual(result.counts["SUNK"], 3)
                self.assertEqual(result.sunk_submarines[0].cells, tuple(cells))

    def test_adjacent_disconnected_hits_stay_hit(self):
        ref, level = scene()
        cur = ref.copy()
        for cell in [(2, 1), (2, 2)]:
            hull(cur, level, [cell])
        result = recognize_board(ref, cur, level_config=level)
        self.assertEqual(result.counts["HIT"], 2)
        self.assertFalse(result.sunk_submarines)

    def test_illegal_length_review(self):
        ref, level = scene(submarines=(2,))
        cur = ref.copy()
        hull(cur, level, [(2, 1), (2, 2), (2, 3)])
        result = recognize_board(ref, cur, level_config=level)
        self.assertFalse(result.sunk_submarines)
        self.assertTrue(result.cell_at(2, 2).needs_review)

    def test_fleet_capacity_conflict(self):
        ref, level = scene(submarines=(2,))
        cur = ref.copy()
        hull(cur, level, [(0, 0), (0, 1)])
        hull(cur, level, [(4, 3), (4, 4)])
        result = recognize_board(ref, cur, level_config=level)
        self.assertFalse(result.sunk_submarines)
        self.assertTrue(result.cell_at(0, 0).needs_review)

    def test_corners_edges_and_grid_sizes(self):
        for n in (3, 4, 7, 10):
            ref, level = scene(n)
            cur = ref.copy()
            opened(cur, level, (n-1, n-1))
            result = recognize_board(ref, cur, level_config=level)
            self.assertEqual(result.cell_at(n-1, n-1).state, CellState.MISS)
            self.assertEqual(len(result.cells), n*n)

    def test_occlusion_review(self):
        ref, level = scene()
        cur = ref.copy()
        matrix = grid_transform(level.board_quad, level.grid_size)
        cv2.fillConvexPoly(cur, np.int32(cell_polygon(2, 2, matrix)), (0, 0, 0))
        result = recognize_board(ref, cur, level_config=level)
        self.assertTrue(result.cell_at(2, 2).needs_review)
        self.assertLess(result.cell_at(2, 2).confidence, .3)

    def test_popup_preflight(self):
        ref, level = scene()
        cur = ref.copy()
        cv2.rectangle(cur, (180, 140), (470, 325), (70, 70, 70), -1)
        quality = assess_board_material(ref, cur, level)
        self.assertEqual(quality.category, "occluded")
        self.assertFalse(quality.suitable_for_tuning)
        result = recognize_board(ref, cur, level_config=level)
        self.assertTrue(result.cell_at(2, 2).needs_review)

    def test_bent_connected_hull_does_not_confirm(self):
        ref, level = scene()
        cur = ref.copy()
        hull(cur, level, [(1, 1), (2, 1)])
        hull(cur, level, [(2, 1), (2, 2)])
        result = recognize_board(ref, cur, level_config=level)
        self.assertFalse(result.sunk_submarines)

    def test_one_component_multiple_lanes_is_ambiguous(self):
        ref, level = scene(submarines=(3, 3))
        level = replace(level, use_safety_rule=False)
        cur = ref.copy()
        hull(cur, level, [(1, 1), (1, 2), (1, 3)])
        hull(cur, level, [(2, 1), (2, 2), (2, 3)])
        matrix = grid_transform(level.board_quad, level.grid_size)
        points = project([[2.5, 1.5], [2.5, 2.5]], matrix).astype(int)
        cv2.line(cur, tuple(points[0]), tuple(points[1]), (160, 165, 164), 18)
        result = recognize_board(ref, cur, level_config=level)
        self.assertFalse(result.sunk_submarines)
        self.assertTrue(result.review_cells)

    def test_global_result_does_not_access_board_or_strategy(self):
        ref, level = scene()
        with patch("sonar.board.SonarBoard.__init__", side_effect=AssertionError("禁止读取棋盘")), \
             patch("sonar.checkerboard_strategy.CheckerboardHuntStrategy.__init__", side_effect=AssertionError("禁止策略")):
            result = recognize_board(ref, ref, level_config=level)
        self.assertEqual(result.counts["UNKNOWN"], 25)

    def test_supplied_references_across_levels(self):
        for number in range(1, 12):
            with self.subTest(level=number):
                level = get_level_config(number)
                ref = read_image(resolve_reference_path(number))
                changed = np.clip(ref.astype(float)+10, 0, 255).astype(np.uint8)
                changed = cv2.warpAffine(changed, np.float32([[1, 0, 4], [0, 1, -3]]),
                                         ref.shape[1::-1], borderMode=cv2.BORDER_REFLECT)
                result = recognize_board(ref, changed, level_config=level)
                self.assertTrue(result.alignment.success)
                self.assertEqual(result.counts["UNKNOWN"], level.grid_size**2)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            BoardRecognitionConfig(inner_margin=.8)
        with self.assertRaises(ValueError):
            BoardRecognitionConfig(confidence_weights=(1, 1, 1))

    def test_manual_cli_interactive_and_missing_image(self):
        from tests.manual_global_board_recognition_test import main
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(StringIO()):
            with patch("builtins.input", side_effect=[str(resolve_reference_path(11)), "11", ""]):
                self.assertEqual(main(["--output", directory]), 0)
            self.assertTrue((Path(directory) / "result.json").is_file())
        with redirect_stderr(StringIO()):
            self.assertEqual(main(["--image", "missing_current.png", "--level", "11"]), 1)

    def test_manual_sunk_coordinates_are_one_based(self):
        from tests.manual_global_board_recognition_test import main
        ref, level = scene()
        cur = ref.copy()
        hull(cur, level, [(2, 1), (2, 2), (2, 3)])
        result = recognize_board(ref, cur, level_config=level)
        output = StringIO()
        with patch("tests.manual_global_board_recognition_test.recognize_board_files", return_value=result):
            with redirect_stdout(output):
                main(["--image", "unused.png"])
        self.assertIn("格子=[(3, 2), (3, 3), (3, 4)]", output.getvalue())

    def test_wrong_page_and_alignment_failure(self):
        ref, level = scene()
        result = recognize_board(ref, np.zeros_like(ref), level_config=level)
        self.assertFalse(result.alignment.success)
        self.assertFalse(result.valid)
        self.assertEqual(result.quality, "wrong_page")
        self.assertTrue(all(c.needs_review for c in result.cells))

    def test_large_translation_rejected(self):
        ref, level = scene()
        current = cv2.warpAffine(ref, np.float32([[1, 0, 36], [0, 1, 22]]), ref.shape[1::-1])
        result = recognize_board(ref, current, level_config=level)
        self.assertFalse(result.alignment.success)

    def test_missing_paths(self):
        with self.assertRaisesRegex(FileNotFoundError, "全空基准"):
            resolve_reference_path(11, "does_not_exist_empty.png")
        with self.assertRaisesRegex(FileNotFoundError, "图片不存在"):
            recognize_board_files("does_not_exist_current.png", level=11)

    def test_invalid_shape(self):
        ref, level = scene()
        with self.assertRaisesRegex(ValueError, "尺寸不同"):
            recognize_board(ref, ref[:50], level_config=level)

    def test_geometry_matches_existing_board(self):
        for level_number in range(1, 12):
            level = get_level_config(level_number)
            board = SonarBoard(level.grid_size, level.submarines)
            board.set_screen_quad(level.board_quad)
            matrix = grid_transform(level.board_quad, level.grid_size)
            for row in range(level.grid_size):
                for col in range(level.grid_size):
                    point = tuple(int(round(v)) for v in project([[col+.5, row+.5]], matrix)[0])
                    self.assertEqual(point, board.screen_point(row, col))

    def test_reference_reuse_after_level11(self):
        self.assertEqual(resolve_reference_path(12), resolve_reference_path(11))
        self.assertEqual(resolve_reference_path(99), resolve_reference_path(11))

    def test_debug_and_inputs_unchanged(self):
        ref, level = scene()
        original = ref.copy()
        with tempfile.TemporaryDirectory() as directory:
            result = recognize_board(ref, ref, level_config=level, output_dir=directory)
            self.assertTrue(Path(result.debug_paths["overlay"]).is_file())
            self.assertTrue(Path(result.debug_paths["result"]).is_file())
            with self.assertRaises(FileExistsError):
                recognize_board(ref, ref, level_config=level, output_dir=directory)
        np.testing.assert_array_equal(ref, original)

    def test_final_state_scores_and_confidence_are_bounded(self):
        ref, level = scene()
        cur = ref.copy()
        hull(cur, level, [(2, 1), (2, 2), (2, 3)])
        result = recognize_board(ref, cur, level_config=level)
        for cell in result.cells:
            self.assertGreaterEqual(cell.confidence, 0)
            self.assertLessEqual(cell.confidence, 1)
            self.assertEqual(cell.state.value, max(cell.state_scores, key=cell.state_scores.get))


if __name__ == "__main__":
    unittest.main()
