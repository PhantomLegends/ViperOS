import logging
import re
from sqlalchemy.orm import Session
from .models import Setting

logger = logging.getLogger("viperos.system_actions")

class SystemManager:
    def __init__(self, db: Session, adapter):
        self.db = db
        self.adapter = adapter

    def provide_tts_feedback(self, text: str):
        """Optionally speaks the result if TTS is enabled in settings."""
        try:
            setting = self.db.query(Setting).filter_by(key="tts_enabled").first()
            if setting and setting.value.lower() == "true":
                self.adapter.speak(text)
        except Exception as e:
            logger.error(f"Failed to provide TTS feedback: {e}")

    def handle_toggle_tts(self, enabled: bool) -> str:
        try:
            state_str = "true" if enabled else "false"
            setting = self.db.query(Setting).filter_by(key="tts_enabled").first()
            if setting:
                setting.value = state_str
            else:
                setting = Setting(key="tts_enabled", value=state_str)
                self.db.add(setting)
            self.db.commit()
            status = "enabled" if enabled else "disabled"
            return f"TTS has been {status}."
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            error_msg = f"Failed to update TTS setting: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

    def handle_set_tts_speed(self, command_text: str) -> str:
        match = re.match(r"set tts speed to (\d+)", command_text, re.IGNORECASE)
        if not match:
            return "Error: Invalid syntax. Use 'set tts speed to <number>'."
        try:
            speed = int(match.group(1))
            if not (50 <= speed <= 400):
                return "Error: TTS speed must be between 50 and 400 WPM."

            setting = self.db.query(Setting).filter_by(key="tts_speed").first()
            if setting:
                setting.value = str(speed)
            else:
                self.db.add(Setting(key="tts_speed", value=str(speed)))
            self.db.commit()
            self.adapter.set_tts_speed(speed)
            return f"TTS speed set to {speed}."
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            return f"Error: {str(e)}"

    def handle_mute_volume(self) -> str:
        try:
            success = self.adapter.mute_volume()
            if success:
                return "System volume muted."
            else:
                return "Error: Failed to mute system volume."
        except Exception as e:
            logger.error(f"Mute control error: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def handle_set_volume(self, command_text: str) -> str:
        match = re.match(r"set volume to (-?\d+)", command_text, re.IGNORECASE)
        if not match:
            return "Error: Invalid volume format. Use 'set volume to <number>'."
        
        try:
            volume_level = int(match.group(1))
            if not (0 <= volume_level <= 100):
                return "Error: Volume must be between 0 and 100."
            
            success = self.adapter.set_volume(volume_level)
            if success:
                return f"Volume set to {volume_level}%."
            else:
                return "Error: Failed to set system volume."
        except ValueError:
            return "Error: Volume must be a valid integer."
        except Exception as e:
            logger.error(f"Volume control error: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def handle_system_info(self) -> str:
        try:
            platform_name = self.adapter.get_name()
            adapter_type = self.adapter.__class__.__name__
            return f"System Info: Platform={platform_name}, Adapter={adapter_type}, Status=Ready"
        except Exception as e:
            error_msg = f"Failed to retrieve system info: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg