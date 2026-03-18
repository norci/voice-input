"""IEventBus implementation using observer pattern."""

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from voice_input.interfaces import EventType, IEventBus

logger = logging.getLogger(__name__)


class EventBus(IEventBus):
    """Event bus implementation using observer pattern."""

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._subscribers: dict[EventType, list[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event_type: EventType, callback: Callable[..., Any]) -> None:
        """Subscribe to an event type.

        Args:
            event_type: The type of event to subscribe to
            callback: The callback function to invoke when the event is published
        """
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type}: {callback}")

    def unsubscribe(self, event_type: EventType, callback: Callable[..., Any]) -> None:
        """Unsubscribe from an event type.

        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback function to remove
        """
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from {event_type}: {callback}")

    def publish(self, event_type: EventType, data: dict[str, Any]) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: The type of event being published
            data: The event data
        """
        subscribers = self._subscribers.get(event_type, [])
        logger.debug(f"Publishing {event_type} to {len(subscribers)} subscribers")
        for callback in subscribers:
            try:
                callback(event_type, data)
            except Exception:
                logger.exception("Error in event callback for %s", event_type)
