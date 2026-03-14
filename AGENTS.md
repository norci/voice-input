# AGENTS.md - Agent Coding Guidelines for voice-input

This document provides guidelines for AI agents working on the voice-input project.

## Project Overview

voice-input is a Linux desktop Chinese voice input method based on FunASR. It uses:
- **Python 3.11+** with asyncio for async operations
- **PyGObject/GTK** for GUI
- **sounddevice** for audio capture
- **WebSocket** for communication with FunASR server

## Build, Lint, and Test Commands

### Running Tests

```bash
# Run all tests
pytest

# Run all unit tests
pytest tests/unit/

# Run all integration tests
pytest tests/integration/

# Run a single test file
pytest tests/unit/test_event_queue.py

# Run a single test function
pytest tests/unit/test_event_queue.py::TestEventQueue::test_put_and_get

# Run tests matching a pattern
pytest -k "test_asr"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src.voice_input --cov-report=html
```

### Linting and Formatting

```bash
# Run ruff linter (auto-fix issues)
ruff check --fix src/

# Run ruff formatter
ruff format src/

# Run mypy type checker
mypy src/

# Run all checks (pre-commit)
pre-commit run --all-files
```

### Development Commands

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run the application
voice-input
```

## Code Style Guidelines

### General Principles

1. **Async-First**: Use `asyncio` for all I/O operations. Avoid threading unless absolutely necessary (e.g., wrapping synchronous sounddevice).
2. **Module Imports**: Use absolute imports from the package root.
   ```python
   # Good
   from voice_input.event_queue import EventQueue

   # Avoid
   from .event_queue import EventQueue  # Relative imports
   ```
3. **Line Length**: Maximum 100 characters per line.
4. **Python Version**: Target Python 3.11+ (uses | union syntax, dataclasses, etc.)

### Type Hints

Always use type hints for function signatures and variables:

```python
# Good
async def process_audio(data: bytes, timestamp: float) -> Optional[ResultEvent]:
    ...

# Class with types
class AudioManager:
    def __init__(self, event_queue: EventQueue) -> None:
        self._event_queue: EventQueue = event_queue
        self._is_recording: bool = False
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `EventQueue`, `AsrClient` |
| Functions/methods | snake_case | `get_event()`, `start_recording()` |
| Private methods | snake_case with underscore | `_internal_method()` |
| Constants | UPPER_SNAKE_CASE | `MAX_BUFFER_SIZE` |
| Modules | snake_case | `event_queue.py` |
| Variables | snake_case | `event_data`, `config` |

### Dataclasses

Use `@dataclass` for simple data containers:

```python
from dataclasses import dataclass

@dataclass
class AudioChunkEvent:
    """Audio chunk event"""
    data: bytes
    timestamp: float

@dataclass
class ResultEvent:
    """Recognition result event"""
    text: str
    result_type: str  # "interim" or "final"
```

### Enums

Use `@dataclass` with `Enum` for type-safe constants:

```python
from enum import Enum

class ConnectionState(Enum):
    """WebSocket connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
```

### Docstrings

Write docstrings in English (or Chinese if in Chinese context):

```python
async def connect(self) -> bool:
    """Connect to the ASR server (async method).

    This starts a worker coroutine that establishes the WebSocket connection.
    Audio sending begins when start_sending_audio() is called.

    Returns:
        True if successfully initialized
    """
```

### Error Handling

1. **Use specific exceptions**: Catch specific exceptions, not generic `Exception`.
2. **Log errors**: Always log errors with appropriate level.
3. **Reraise with context**: When reraising, use `raise ... from e` to preserve stack trace.
4. **Never swallow exceptions silently**: At minimum, log warnings.

```python
try:
    result = await self._ws.recv()
except asyncio.TimeoutError:
    continue
except websockets.exceptions.ConnectionClosed:
    logger.info("Connection closed by server")
except (OSError, ssl.SSLError) as e:
    logger.error(f"Network error: {e}")
    await self._send_error_event("NETWORK_ERROR", str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
```

### Async/Await Patterns

1. **Use `asyncio.create_task()`** for background tasks, not `threading.Thread`.
2. **Always await coroutines**: Never call async functions without await.
3. **Handle cancellation**: Catch `asyncio.CancelledError` for graceful shutdown.

```python
# Good - using asyncio.create_task
self._worker_task = asyncio.create_task(self._worker_async())

# Handle cancellation gracefully
try:
    await self._audio_task
except asyncio.CancelledError:
    logger.info("Task was cancelled")
```

### Import Ordering

Order imports in this sequence (use `ruff check --fix` to auto-sort):

1. Standard library
2. Third-party packages
3. Local application imports

```python
import asyncio
import json
import logging
from typing import Optional

import numpy as np
import sounddevice as sd
import websockets

from voice_input.event_queue import EventQueue, ResultEvent
```

### Testing Guidelines

1. **Use pytest-asyncio**: Mark async tests with `@pytest.mark.asyncio`.
2. **Use descriptive test names**: `test_<what_is_being_tested>`.
3. **Test one thing per test**: Each test should verify a single behavior.
4. **Use fixtures**: Create reusable test fixtures for common setup.

```python
import pytest

class TestEventQueue:
    """Unit tests for EventQueue"""

    @pytest.mark.asyncio
    async def test_put_and_get(self):
        """Test basic put and get operations"""
        queue = EventQueue()
        event = AudioChunkEvent(data=b"test", timestamp=1.0)

        await queue.put(event)
        result = await queue.get()

        assert result == event
```

### Configuration

- Configuration is stored in `config/config.toml`
- Use the `ConfigLoader` to load configuration
- Default values should be sensible

```python
from voice_input.config_loader import load_config, Config

config: Config = load_config()
window_opacity = config.window.opacity
```

### Logging

Use the module-level logger pattern:

```python
import logging

logger = logging.getLogger(__name__)

# Then use appropriate levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

## Project Structure

```
voice-input/
├── src/voice_input/
│   ├── __init__.py
│   ├── event_queue.py      # Async event queue
│   ├── audio_manager.py    # Audio capture
│   ├── asr_client.py       # ASR WebSocket client
│   ├── voice_gui.py        # Main GUI window
│   ├── config_loader.py    # Configuration loading
│   ├── error_handler.py    # Error handling
│   ├── toggle.py           # Toggle script
│   └── ui/
│       └── status_window.py
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── config/
│   └── config.toml
└── pyproject.toml
```

## Common Patterns

### Creating Async Tasks

```python
# Start a background task
self._task = asyncio.create_task(self._do_work())

# Cancel on shutdown
self._task.cancel()
try:
    await self._task
except asyncio.CancelledError:
    pass
```

### Using EventQueue

```python
# Send event
await self._event_queue.put(ResultEvent(text="hello", result_type="final"))

# Receive event with timeout
event = await self._event_queue.get(timeout=1.0)
if event:
    # Process event
    pass
```

### WebSocket Communication

```python
# Connect with SSL
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

self._ws = await websockets.connect(uri, ssl=ssl_context)

# Send binary data
await self._ws.send(audio_bytes)

# Receive with timeout
try:
    result = await asyncio.wait_for(self._ws.recv(), timeout=0.5)
except asyncio.TimeoutError:
    continue
```
