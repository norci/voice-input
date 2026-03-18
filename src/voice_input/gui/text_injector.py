"""Text injection utility."""

import logging
import subprocess
import threading

logger = logging.getLogger(__name__)


class TextInjector:
    """Text injector - inserts text at cursor position."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_injected_text = ""

    def inject(self, text: str) -> bool:
        """Inject text into active window."""
        if not text or not isinstance(text, str) or not text.strip():
            return False

        if text == self._last_injected_text:
            return False

        with self._lock:
            try:
                result = subprocess.run(
                    ["wtype", f"{text}"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
            except Exception:
                return False
            else:
                if result.returncode == 0:
                    self._last_injected_text = text
                    return True
                return False
