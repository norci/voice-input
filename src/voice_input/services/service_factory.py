"""IServiceFactory implementation."""

import logging
from typing import TYPE_CHECKING, Any

from voice_input.audio_engine import AudioEngine
from voice_input.connection_manager import ConnectionManager
from voice_input.interfaces import IAudioEngine, IConnectionManager, IServiceFactory

if TYPE_CHECKING:
    from voice_input.services.voice_service import VoiceService

logger = logging.getLogger(__name__)


class ServiceFactory(IServiceFactory):
    """Service factory implementation."""

    def create_voice_service(self, config: Any) -> "VoiceService":
        """Create a voice service instance.

        Args:
            config: ASR client configuration

        Returns:
            VoiceService instance
        """
        # Lazy import to avoid circular dependency
        from voice_input.services.voice_service import VoiceService

        logger.info("Creating VoiceService")
        return VoiceService(config)

    def create_audio_engine(self, config: Any) -> IAudioEngine:
        """Create an audio engine instance.

        Args:
            config: ASR client configuration

        Returns:
            AudioEngine instance
        """
        logger.info("Creating AudioEngine")
        return AudioEngine(config)

    def create_connection_manager(self, config: Any) -> IConnectionManager:
        """Create a connection manager instance.

        Args:
            config: ASR client configuration

        Returns:
            ConnectionManager instance
        """
        logger.info("Creating ConnectionManager")
        return ConnectionManager(config)
