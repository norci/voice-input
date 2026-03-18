"""GTK initialization module.

This module handles GTK version requirements and imports.
Import this first in any module that uses GTK.
"""

from __future__ import annotations

# GTK requires version check before import
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

__all__ = ["GLib", "Gtk"]
