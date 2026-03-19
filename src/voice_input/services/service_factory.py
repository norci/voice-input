"""IServiceFactory implementation."""

from __future__ import annotations

import logging

from voice_input.asr_config import AsrClientConfig
from voice_input.audio_engine import AudioEngine
from voice_input.interfaces import IAudioEngine, IConnectionManager, IServiceFactory
from voice_input.network.connection_manager import ConnectionManager
from voice_input.services.voice_service import VoiceService

logger = logging.getLogger(__name__)


class ServiceFactory(IServiceFactory):
    """Service factory implementation."""

    def create_voice_service(self: ServiceFactory, config: AsrClientConfig) -> VoiceService:
        """Create a voice service instance.

        Args:
            config: ASR client configuration

        Returns:
            VoiceService instance
        """
        logger.info("Creating VoiceService")
        return VoiceService(config)

    def create_audio_engine(self: ServiceFactory, config: AsrClientConfig) -> IAudioEngine:
        """Create an audio engine instance.

        Args:
            config: ASR client configuration

        Returns:
            AudioEngine instance
        """
        logger.info("Creating AudioEngine")
        return AudioEngine(config)

    def create_connection_manager(
        self: ServiceFactory, config: AsrClientConfig
    ) -> IConnectionManager:
        """Create a connection manager instance.

        Args:
            config: ASR client configuration

        Returns:
            ConnectionManager instance
        """
        logger.info("Creating ConnectionManager")

        return ConnectionManager(config)
