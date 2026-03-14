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


def pytest_configure(config):
    """Configure pytest - run before any tests."""
    # Create mock GTK modules
    mock_gi = MagicMock()
    mock_glib = MagicMock()
    mock_gtk = MagicMock()
    mock_gobject = MagicMock()

    # Configure GLib
    mock_glib.idle_add = MagicMock(return_value=False)
    mock_glib.timeout_add = MagicMock(return_value=0)

    # Create mock classes for Gtk
    class MockApplicationWindow:
        def __init__(self, *args, **kwargs):
            pass

    class MockApplication:
        def __init__(self, *args, **kwargs):
            pass

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

    class MockButton:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self, sig, callback):
            pass

        def set_label(self, text):
            pass

    # Set mock classes to Gtk module
    mock_gtk.ApplicationWindow = MockApplicationWindow
    mock_gtk.Application = MockApplication
    mock_gtk.Box = MockBox
    mock_gtk.Label = MockLabel
    mock_gtk.Button = MockButton
    mock_gtk.Orientation = MagicMock()
    mock_gtk.Align = MagicMock()

    # Install mocks BEFORE any imports
    sys.modules["gi"] = mock_gi
    sys.modules["gi.repository"] = MagicMock()
    sys.modules["gi.repository.Gtk"] = mock_gtk
    sys.modules["gi.repository.GLib"] = mock_glib
    sys.modules["gi.repository.GObject"] = mock_gobject
