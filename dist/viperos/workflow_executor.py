import logging
import time
from sqlalchemy.orm import Session
from .models import Workflow, WorkflowAction, Setting

logger = logging.getLogger("viperos.workflow_executor")

class WorkflowExecutor:
    def __init__(self, db: Session, adapter):
        self.db = db
        self.adapter = adapter

    def run(self, workflow: Workflow) -> str:
        """
        Executes a workflow by running its actions in order.
        Honors retry_count and failure_policy (stop vs continue).
        """
        actions = (
            self.db.query(WorkflowAction)
            .filter_by(workflow_id=workflow.id)
            .order_by(WorkflowAction.order.asc())
            .all()
        )
        
        if not actions:
            return f"Workflow '{workflow.name}' has no actions."

        executed_successfully_count = 0
        errors = []
        
        # Mapping logic: stop_on_failure usually corresponds to 'stop' policy
        # continue_on_failure corresponds to 'continue' policy.
        policy = workflow.failure_policy or "stop"

        for action in actions:
            success = False
            attempts = 0
            # retry_count = 0 means 1 attempt. retry_count = 2 means 3 attempts.
            max_attempts = max(0, workflow.retry_count) + 1

            while attempts < max_attempts and not success:
                attempts += 1
                try:
                    success = self._execute_step(action)
                except Exception as e:
                    logger.error(
                        f"Exception in action {action.id} (Order {action.order}) "
                        f"during workflow '{workflow.name}': {e}", 
                        exc_info=True
                    )
                    success = False
                
                if not success and attempts < max_attempts:
                    # Brief pause between retries
                    time.sleep(0.1)

            if success:
                executed_successfully_count += 1
            else:
                error_detail = f"Action {action.order} ({action.type}) failed after {attempts} attempt(s)."
                errors.append(error_detail)
                
                if policy == "stop":
                    return (
                        f"Workflow failed at step {action.order}: {error_detail}. "
                        f"Total steps successfully completed: {executed_successfully_count}."
                    )

        # Final report for completed (or partially completed with 'continue') workflows
        result_msg = (
            f"Workflow '{workflow.name}' completed. "
            f"Actions executed: {executed_successfully_count}/{len(actions)}."
        )
        if errors:
            result_msg += " Errors encountered: " + "; ".join(errors)
        
        return result_msg

    def _execute_step(self, action: WorkflowAction) -> bool:
        t = action.type
        v = action.value
        
        try:
            if t == "launch_app": return bool(self.adapter.launch_app(v))
            if t == "open_url": return bool(self.adapter.open_url(v))
            if t == "open_file": return bool(self.adapter.open_file(v))
            if t == "open_folder": return bool(self.adapter.open_folder(v))
            if t == "run_command": return bool(self.adapter.run_command(v))
            if t == "start_timer":
                time.sleep(float(v))
                return True
            if t == "set_volume":
                return bool(self.adapter.set_volume(int(v)))
            if t == "mute_volume": 
                return bool(self.adapter.mute_volume())
            if t == "enable_tts": 
                return self._toggle_tts_db(True)
            if t == "disable_tts": 
                return self._toggle_tts_db(False)
            if t == "set_tts_speed":
                speed = int(v)
                db_success = self._set_tts_speed_db(speed)
                adapter_success = self.adapter.set_tts_speed(speed)
                return bool(db_success and adapter_success)
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Validation or execution error in step '{t}' with value '{v}': {e}")
            return False
        
        logger.warning(f"Unknown workflow action type: {t}")
        return False

    def _toggle_tts_db(self, enabled: bool) -> bool:
        try:
            val = "true" if enabled else "false"
            s = self.db.query(Setting).filter_by(key="tts_enabled").first()
            if s: 
                s.value = val
            else: 
                self.db.add(Setting(key="tts_enabled", value=val))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to toggle TTS in DB: {e}")
            self.db.rollback()
            return False

    def _set_tts_speed_db(self, speed: int) -> bool:
        try:
            s = self.db.query(Setting).filter_by(key="tts_speed").first()
            if s: 
                s.value = str(speed)
            else: 
                self.db.add(Setting(key="tts_speed", value=str(speed)))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to set TTS speed in DB: {e}")
            self.db.rollback()
            return False