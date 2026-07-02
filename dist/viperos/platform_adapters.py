import subprocess
import logging
import os
from .adapters import BaseAdapter
# Task 1 & 2: Moved WindowsAdapter to separate file to reduce size
from .windows_adapter import WindowsAdapter

logger = logging.getLogger("viperos.adapters")

class LinuxAdapter(BaseAdapter):
    """
    Hardware adapter for Linux-based systems.
    """
    def get_name(self) -> str:
        return "Linux"
    
    def execute_shell(self, command: str) -> str:
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            return result.strip()
        except subprocess.CalledProcessError as e:
            return f"Error executing Linux command: {e.output}"

    def launch_app(self, app_name: str) -> bool:
        return False

    def open_url(self, url: str) -> bool:
        return False

    def open_file(self, path: str) -> bool:
        return False

    def open_folder(self, path: str) -> bool:
        return False

    def run_command(self, command_text: str) -> bool:
        return False

    def set_volume(self, volume: int) -> bool:
        return False

    def mute_volume(self) -> bool:
        return False

    def set_tts_speed(self, speed: int) -> bool:
        return False

    def speak(self, text: str) -> bool:
        return False

class MacOSAdapter(BaseAdapter):
    """
    Hardware adapter for macOS systems.
    """
    def get_name(self) -> str:
        return "macOS"

    def execute_shell(self, command: str) -> str:
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            return result.strip()
        except subprocess.CalledProcessError as e:
            return f"Error executing macOS command: {e.output}"

    def launch_app(self, app_name: str) -> bool:
        try:
            subprocess.Popen(["open", "-a", app_name])
            return True
        except Exception as e:
            logger.error(f"MacOSAdapter: Failed to launch {app_name}: {e}")
            return False

    def open_url(self, url: str) -> bool:
        try:
            subprocess.Popen(["open", url])
            return True
        except Exception as e:
            logger.error(f"MacOSAdapter: Failed to open URL {url}: {e}")
            return False

    def open_file(self, path: str) -> bool:
        return self.open_url(path)

    def open_folder(self, path: str) -> bool:
        return self.open_url(path)

    def run_command(self, command_text: str) -> bool:
        try:
            subprocess.Popen(command_text, shell=True)
            return True
        except Exception as e:
            logger.error(f"MacOSAdapter: Failed to run command: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        try:
            # macOS volume via AppleScript handles 0-100
            cmd = ["osascript", "-e", f"set volume output volume {volume}"]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception as e:
            logger.error(f"MacOSAdapter: Failed to set volume to {volume}: {e}")
            return False

    def mute_volume(self) -> bool:
        try:
            cmd = ["osascript", "-e", "set volume with output muted"]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception as e:
            logger.error(f"MacOSAdapter: Failed to mute: {e}")
            return False

    def set_tts_speed(self, speed: int) -> bool:
        logger.info(f"MacOSAdapter: TTS Speed set to {speed} (Native 'say' uses default rate)")
        return True

    def speak(self, text: str) -> bool:
        try:
            logger.info(f"MacOSAdapter Speaking: {text}")
            subprocess.Popen(["say", text])
            return True
        except Exception as e:
            logger.error(f"MacOSAdapter: Speech failed for text '{text}': {e}")
            return False

class UnknownAdapter(BaseAdapter):
    """
    Fallback adapter for unsupported platforms.
    """
    def get_name(self) -> str:
        return "Unknown"

    def execute_shell(self, command: str) -> str:
        return "Error: Unsupported platform"

    def launch_app(self, app_name: str) -> bool:
        return False

    def open_url(self, url: str) -> bool:
        return False

    def open_file(self, path: str) -> bool:
        return False

    def open_folder(self, path: str) -> bool:
        return False

    def run_command(self, command_text: str) -> bool:
        return False

    def set_volume(self, volume: int) -> bool:
        return False

    def mute_volume(self) -> bool:
        return False

    def set_tts_speed(self, speed: int) -> bool:
        return False

    def speak(self, text: str) -> bool:
        return False