import platform
import logging

logger = logging.getLogger("viperos.adapters")

class BaseAdapter:
    """
    Interface for all hardware adapters. 
    Defines the contract for OS-facing actions.
    """
    def execute_shell(self, command: str) -> str:
        raise NotImplementedError("HardwareAdapter must implement execute_shell")
    def launch_app(self, app_name: str) -> bool:
        raise NotImplementedError("HardwareAdapter must implement launch_app")
    def open_url(self, url: str) -> bool:
        raise NotImplementedError("HardwareAdapter must implement open_url")
    def open_file(self, path: str) -> bool:
        raise NotImplementedError("HardwareAdapter must implement open_file")
    def open_folder(self, path: str) -> bool:
        raise NotImplementedError("HardwareAdapter must implement open_folder")
    def run_command(self, command_text: str) -> bool:
        raise NotImplementedError("HardwareAdapter must implement run_command")
    def set_volume(self, volume: int) -> bool:
        raise NotImplementedError("HardwareAdapter must implement set_volume")
    def mute_volume(self) -> bool:
        raise NotImplementedError("HardwareAdapter must implement mute_volume")
    def set_tts_speed(self, speed: int) -> bool:
        raise NotImplementedError("HardwareAdapter must implement set_tts_speed")
    def speak(self, text: str) -> bool:
        raise NotImplementedError("HardwareAdapter must implement speak")
    def get_name(self) -> str:
        raise NotImplementedError("HardwareAdapter must implement get_name")

# Import implementations from platform_adapters
from .platform_adapters import (
    LinuxAdapter, 
    WindowsAdapter, 
    MacOSAdapter, 
    UnknownAdapter
)

def get_active_adapter() -> BaseAdapter:
    """
    Selects the appropriate HardwareAdapter based on the host operating system.
    If the platform is unknown or unsupported, returns the generic UnknownAdapter.
    
    Implementation detail: Raspberry Pi identifies as 'Linux' via platform.system()
    and is explicitly routed to the LinuxAdapter.
    """
    try:
        os_name = platform.system()
        logger.info(f"Detecting host platform for adapter selection: {os_name}")
        
        if os_name == "Windows":
            return WindowsAdapter()
        elif os_name == "Linux":
            # Requirement: Raspberry Pi should be treated as Linux.
            # platform.system() returns 'Linux' on Raspberry Pi OS.
            logger.debug("Linux/Raspberry Pi platform detected.")
            return LinuxAdapter()
        elif os_name == "Darwin":
            return MacOSAdapter()
        
        logger.warning(f"Unsupported platform '{os_name}' detected. Falling back to UnknownAdapter.")
        return UnknownAdapter()
    except Exception as e:
        logger.error(f"Critical error during adapter selection: {str(e)}")
        # Defensive fallback to ensure the system doesn't crash on selection
        return UnknownAdapter()