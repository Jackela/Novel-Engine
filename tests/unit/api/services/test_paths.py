"""Unit tests for services/paths module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

from src.api.services.paths import find_project_root, get_characters_directory_path


@pytest.mark.unit
class TestFindProjectRoot:
    """Tests for find_project_root function."""

    def test_find_project_root_with_pyproject_toml(self, tmp_path: Path) -> None:
        """Test finding project root with pyproject.toml marker."""
        # Create a temporary project structure
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()

        # Create subdirectory
        subdir = project_dir / "src" / "api"
        subdir.mkdir(parents=True)

        result = find_project_root(str(subdir))

        assert result == project_dir

    def test_find_project_root_with_src(self, tmp_path: Path) -> None:
        """Test finding project root with src directory marker."""
        project_dir = tmp_path / "test_project"
        src_dir = project_dir / "src"
        src_dir.mkdir(parents=True)

        subdir = src_dir / "api" / "services"
        subdir.mkdir(parents=True)

        result = find_project_root(str(subdir))

        assert result == project_dir

    def test_find_project_root_with_git(self, tmp_path: Path) -> None:
        """Test finding project root with .git directory marker."""
        project_dir = tmp_path / "test_project"
        git_dir = project_dir / ".git"
        git_dir.mkdir(parents=True)

        subdir = project_dir / "some" / "deep" / "path"
        subdir.mkdir(parents=True)

        result = find_project_root(str(subdir))

        assert result == project_dir

    def test_find_project_root_from_cwd(self, tmp_path: Path) -> None:
        """Test finding project root from current working directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()

        with patch("os.getcwd", return_value=str(project_dir)):
            result = find_project_root()

        assert result == project_dir

    def test_find_project_root_returns_cwd_when_no_markers(
        self, tmp_path: Path
    ) -> None:
        """Test that current directory is returned when no markers found."""
        # Create a directory without any markers
        no_marker_dir = tmp_path / "no_markers"
        no_marker_dir.mkdir()

        with patch("os.getcwd", return_value=str(no_marker_dir)):
            result = find_project_root(str(no_marker_dir))

        assert result == no_marker_dir.resolve()

    def test_find_project_root_with_explicit_start_path(self, tmp_path: Path) -> None:
        """Test find_project_root with explicit start_path parameter."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()

        start_dir = project_dir / "level1" / "level2"
        start_dir.mkdir(parents=True)

        result = find_project_root(start_path=str(start_dir))

        assert result == project_dir


@pytest.mark.unit
class TestGetCharactersDirectoryPath:
    """Tests for get_characters_directory_path function."""

    def test_get_characters_directory_relative_path(self, tmp_path: Path) -> None:
        """Test getting characters directory with relative path."""
        # Create project structure
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()

        with patch("os.getcwd", return_value=str(project_dir)):
            result = get_characters_directory_path()

        expected = str(project_dir / "characters")
        assert result == expected

    def test_get_characters_directory_absolute_path(self, tmp_path: Path) -> None:
        """Test getting characters directory when already absolute."""
        with patch("os.path.isabs", return_value=True):
            result = get_characters_directory_path()

        assert result == "characters"

    def test_get_characters_directory_with_os_path_isabs_true(self) -> None:
        """Test that absolute paths are returned as-is."""
        with patch("os.path.isabs", return_value=True):
            result = get_characters_directory_path()

        # When isabs returns True, the function returns base_character_path directly
        assert result == "characters"

    def test_get_characters_directory_integration(self, tmp_path: Path) -> None:
        """Integration test for get_characters_directory_path."""
        # Create a realistic project structure
        project_dir = tmp_path / "novel_engine"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()
        (project_dir / "characters").mkdir(exist_ok=True)

        # Change to a subdirectory
        subdir = project_dir / "src" / "api"
        subdir.mkdir(parents=True)

        # Mock cwd to be the subdir
        with patch("os.getcwd", return_value=str(subdir)):
            with patch("os.path.isabs", return_value=False):
                result = get_characters_directory_path()

        expected = str(project_dir / "characters")
        assert result == expected


@pytest.mark.unit
class TestPathUtilitiesEdgeCases:
    """Edge case tests for path utilities."""

    def test_find_project_root_with_symlinks(self, tmp_path: Path) -> None:
        """Test finding project root with symlinked directories."""
        # Skip on Windows
        if os.name == "nt":
            pytest.skip("Symlinks not always supported on Windows")

        project_dir = tmp_path / "real_project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()

        # Create a symlink to the project
        symlink_dir = tmp_path / "symlink_project"
        symlink_dir.symlink_to(project_dir)

        subdir = symlink_dir / "src"
        subdir.mkdir()

        result = find_project_root(str(subdir))

        # Result should be the resolved path
        assert result == project_dir.resolve()

    def test_find_project_root_parent_is_self(self, tmp_path: Path) -> None:
        """Test find_project_root stops at filesystem root."""
        # This tests the boundary condition where current == current.parent
        root = Path("/")

        with patch.object(Path, "resolve", return_value=root):
            with patch.object(Path, "parent", root):  # parent of root is root
                result = find_project_root("/")

        # Should return root when at filesystem boundary
        assert result == root
