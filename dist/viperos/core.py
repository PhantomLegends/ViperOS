import logging
import datetime
from typing import List
from sqlalchemy.orm import Session
from .models import CommandLog, Setting, PendingConfirmation
from .adapters import get_active_adapter
from .workflow_manager import WorkflowManager
from .system_actions import SystemManager

logger = logging.getLogger("viperos.core")

class VIPEROSCore:
    def __init__(self, db: Session):
        self.db = db
        self._adapter = get_active_adapter()
        self.workflow_manager = WorkflowManager(self.db, self._adapter)
        self.system_manager = SystemManager(self.db, self._adapter)

    @property
    def adapter(self):
        return self._adapter

    @adapter.setter
    def adapter(self, value):
        self._adapter = value
        if hasattr(self, 'workflow_manager'):
            self.workflow_manager.adapter = value
        if hasattr(self, 'system_manager'):
            self.system_manager.adapter = value

    def create_pending_confirmation(self, action: str, payload: str, timeout_minutes: int = 15) -> PendingConfirmation:
        """
        Stores a pending confirmation locally in SQLite with an expiration time.
        """
        try:
            now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
            expiration = now + datetime.timedelta(minutes=timeout_minutes)
            
            confirmation = PendingConfirmation(
                action=action,
                payload=payload,
                expiration_time=expiration
            )
            self.db.add(confirmation)
            self.db.commit()
            self.db.refresh(confirmation)
            logger.info(f"Created pending confirmation id={confirmation.id} for action='{action}'")
            return confirmation
        except Exception as e:
            self.db.rollback()
            error_info = f"Database error while saving confirmation for action '{action}': {str(e)}"
            logger.error(error_info, exc_info=True)
            raise RuntimeError(error_info)

    def get_active_confirmations(self) -> List[PendingConfirmation]:
        """
        Retrieves all pending confirmations that have not yet expired.
        """
        try:
            now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
            active = self.db.query(PendingConfirmation).filter(
                PendingConfirmation.expiration_time > now
            ).all()
            return active
        except Exception as e:
            logger.error(f"Failed to retrieve active confirmations from SQLite: {e}", exc_info=True)
            return []

    def cleanup_expired_confirmations(self) -> int:
        """
        Removes expired confirmations from the database.
        """
        try:
            now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
            deleted_count = self.db.query(PendingConfirmation).filter(
                PendingConfirmation.expiration_time <= now
            ).delete()
            self.db.commit()
            logger.info(f"Purged {deleted_count} expired confirmations.")
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cleanup expired confirmations: {e}", exc_info=True)
            return 0

    def parse_and_execute(self, command_text: str) -> str:
        """
        Interprets and routes CLI and API commands.
        """
        cmd = command_text.strip()
        if not cmd:
            return "Error: Empty command."

        low_cmd = cmd.lower()
        result = ""

        try:
            # Workflow Commands
            if low_cmd.startswith("create workflow"):
                result = self.workflow_manager.handle_create_workflow(cmd)
            elif low_cmd.startswith("add app"):
                result = self.workflow_manager.handle_add_app(cmd)
            elif low_cmd.startswith("add url"):
                result = self.workflow_manager.handle_add_url(cmd)
            elif low_cmd.startswith("run "):
                result = self.workflow_manager.handle_run_workflow(cmd)
            elif low_cmd == "list workflows":
                result = self.workflow_manager.handle_list_workflows()
            
            # System Commands
            elif low_cmd == "system info":
                result = self.system_manager.handle_system_info()
            elif low_cmd == "status":
                result = "System online. All local services ready."
            elif low_cmd.startswith("set volume to"):
                result = self.system_manager.handle_set_volume(cmd)
            elif low_cmd == "mute volume":
                result = self.system_manager.handle_mute_volume()
            elif low_cmd == "enable tts":
                result = self.system_manager.handle_toggle_tts(True)
            elif low_cmd == "disable tts":
                result = self.system_manager.handle_toggle_tts(False)
            elif low_cmd.startswith("set tts speed to"):
                result = self.system_manager.handle_set_tts_speed(cmd)
            
            # Hardware Adapter Direct (Shell)
            elif low_cmd.startswith("shell "):
                shell_cmd = cmd[6:].strip()
                # Use execute_shell to capture the output string as expected by tests
                result = self.adapter.execute_shell(shell_cmd)
            
            else:
                result = f"Unknown command: {cmd}"

        except Exception as e:
            logger.error(f"Command execution error: {e}", exc_info=True)
            result = f"Error: {str(e)}"

        # Requirement: Write one CommandLog entry for each request
        self.log_command(cmd, result)
        
        # Requirement: Provide optional TTS feedback
        self.system_manager.provide_tts_feedback(result)
        
        return result

    def process_voice_input(self, text: str) -> str:
        """
        Feeds recognized voice text into the standard command path.
        """
        return self.parse_and_execute(text)

    def log_command(self, command: str, result: str):
        """Persists a command outcome in the local SQLite CommandLog."""
        try:
            log_entry = CommandLog(command=command, result=result)
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            logger.critical(f"Failed to persist CommandLog in SQLite: {e}", exc_info=True)
            self.db.rollback()