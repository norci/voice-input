"""
Pytest configuration for voice_input tests.

This file mocks GTK and other system-level dependencies before they are imported.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path BEFORE any imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def _create_mock_glib():
    """Create mock GLib module."""
    mock_glib = MagicMock()
    mock_glib.idle_add = MagicMock(return_value=False)
    mock_glib.timeout_add = MagicMock(return_value=0)
    return mock_glib


def _create_mock_box():
    """Create mock Box class."""

    class MockBox:
        def __init__(self, *args, **kwargs):
            pass

        def set_margin_start(self, v):
            pass

        def set_margin_end(self, v):
            pass

        def set_margin_top(self, v):
            pass

        def set_margin_bottom(self, v):
            pass

        def set_halign(self, v):
            pass

        def append(self, w):
            pass

    return MockBox


def _create_mock_label():
    """Create mock Label class."""

    class MockLabel:
        def __init__(self, *args, **kwargs):
            self._label = kwargs.get("label", "")

        def set_label(self, text):
            self._label = text

        def get_label(self):
            return self._label

        def set_markup(self, text):
            pass

        def set_halign(self, v):
            pass

        def set_wrap(self, v):
            pass

        def set_max_width_chars(self, v):
            pass

    return MockLabel


def _create_mock_button():
    """Create mock Button class."""

    class MockButton:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self, sig, callback):
            pass

        def set_label(self, text):
            pass

    return MockButton


def _create_mock_gtk():
    """Create mock Gtk module with all required classes."""
    mock_gtk = MagicMock()
    mock_gtk.ApplicationWindow = type("MockApplicationWindow", (), {})
    mock_gtk.Application = type("MockApplication", (), {})
    mock_gtk.Box = _create_mock_box()
    mock_gtk.Label = _create_mock_label()
    mock_gtk.Button = _create_mock_button()
    mock_gtk.Orientation = MagicMock()
    mock_gtk.Align = MagicMock()
    return mock_gtk


def pytest_configure(config):
    """Configure pytest - run before any tests."""
    mock_gi = MagicMock()
    mock_glib = _create_mock_glib()
    mock_gtk = _create_mock_gtk()
    mock_gobject = MagicMock()

    sys.modules["gi"] = mock_gi
    sys.modules["gi.repository"] = MagicMock()
    sys.modules["gi.repository.Gtk"] = mock_gtk
    sys.modules["gi.repository.GLib"] = mock_glib
    sys.modules["gi.repository.GObject"] = mock_gobject
