import subprocess
import logging
from .adapters import BaseAdapter

logger = logging.getLogger("viperos.adapters")

class WindowsAdapter(BaseAdapter):
    """
    Hardware adapter for Windows-based systems.
    """
    def execute_shell(self, command: str) -> str:
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            return result.strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"

    def launch_app(self, app_name: str) -> bool:
        try:
            # Using start command for Windows
            subprocess.Popen(["start", app_name], shell=True)
            return True
        except Exception as e:
            logger.error(f"WindowsAdapter: Failed to launch {app_name}: {e}")
            return False

    def open_url(self, url: str) -> bool:
        try:
            subprocess.Popen(["start", url], shell=True)
            return True
        except Exception as e:
            logger.error(f"WindowsAdapter: Failed to open URL {url}: {e}")
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
            logger.error(f"WindowsAdapter: Failed to run command: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        try:
            # Defensive check for volume range 0-100
            target_vol = max(0, min(100, volume))
            ps_cmd = f"(new-object -com wscript.shell).SendKeys([char]174)*50; (new-object -com wscript.shell).SendKeys([char]175)*{target_vol // 2}"
            subprocess.run(["powershell", "-Command", ps_cmd], check=True, capture_output=True)
            return True
        except Exception as e:
            logger.error(f"WindowsAdapter: Failed to set volume to {volume}: {e}")
            return False

    def mute_volume(self) -> bool:
        try:
            ps_cmd = "(new-object -com wscript.shell).SendKeys([char]173)"
            subprocess.run(["powershell", "-Command", ps_cmd], check=True, capture_output=True)
            return True
        except Exception as e:
            logger.error(f"WindowsAdapter: Failed to toggle mute: {e}")
            return False

    def set_tts_speed(self, speed: int) -> bool:
        logger.info(f"WindowsAdapter: TTS Speed set to {speed}")
        return True

    def speak(self, text: str) -> bool:
        try:
            logger.info(f"WindowsAdapter Speaking: {text}")
            # Escape single quotes for PowerShell
            escaped_text = text.replace("'", "''")
            ps_cmd = (
                "Add-Type -AssemblyName System.Speech; "
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.Speak('{escaped_text}')"
            )
            subprocess.Popen(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logger.error(f"WindowsAdapter: Speech failed for text '{text}': {e}")
            return False

    def get_name(self) -> str:
        return "Windows"