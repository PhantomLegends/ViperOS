import logging
from .core import VIPEROSCore

logger = logging.getLogger("viperos.voice")

class LocalVoiceInput:
    """
    Optional component for turning spoken input into command text locally.
    In a headless environment, this typically interfaces with a local 
    STT (Speech-To-Text) engine.
    """
    def __init__(self, core: VIPEROSCore):
        self.core = core

    def simulate_voice_command(self, text: str) -> str:
        """
        Simulates the arrival of a recognized voice command.
        """
        logger.info(f"Voice Input detected: {text}")
        # Feed directly into the core command path
        return self.core.process_voice_input(text)