import datetime
import logging
import re
from sqlalchemy.orm import Session
from .models import Workflow, WorkflowAction
from .workflow_executor import WorkflowExecutor

logger = logging.getLogger("viperos.workflow_manager")

class WorkflowManager:
    def __init__(self, db: Session, adapter):
        self.db = db
        self._adapter = adapter
        self.executor = WorkflowExecutor(self.db, self._adapter)

    @property
    def adapter(self):
        return self._adapter

    @adapter.setter
    def adapter(self, value):
        self._adapter = value
        # Ensure the executor uses the updated adapter if changed via core
        self.executor.adapter = value

    def handle_list_workflows(self) -> str:
        try:
            workflows = self.db.query(Workflow).all()
            if not workflows:
                return "No workflows found."
            names = [w.name for w in workflows if w.name]
            return "Workflows: " + ", ".join(names)
        except Exception as e:
            error_msg = f"Failed to list workflows: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

    def create_workflow(self, name: str, description: str = "", failure_policy: str = "stop", retry_count: int = 0) -> Workflow:
        if not name or not name.strip():
            raise ValueError("Workflow name cannot be empty.")
        
        existing = self.db.query(Workflow).filter_by(name=name).first()
        if existing:
            raise ValueError(f"Workflow with name '{name}' already exists.")
            
        try:
            new_workflow = Workflow(
                name=name,
                description=description,
                failure_policy=failure_policy,
                retry_count=retry_count,
                created_at=datetime.datetime.utcnow()
            )
            self.db.add(new_workflow)
            self.db.commit()
            self.db.refresh(new_workflow)
            return new_workflow
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error during workflow creation: {e}", exc_info=True)
            raise RuntimeError(f"Could not persist workflow: {str(e)}")

    def handle_create_workflow(self, command_text: str) -> str:
        workflow_name = command_text[16:].strip()
        try:
            workflow = self.create_workflow(name=workflow_name)
            return f"Workflow '{workflow.name}' created successfully."
        except ValueError as ve:
            return f"Error: {str(ve)}"
        except Exception as e:
            return f"Failed to create workflow: {str(e)}"

    def handle_add_app(self, command_text: str) -> str:
        match = re.match(r"add app (.+) to (.+)", command_text, re.IGNORECASE)
        if not match: 
            return "Error: Invalid syntax. Use 'add app <name> to <workflow>'."
        return self._add_action(match.group(2).strip(), "launch_app", match.group(1).strip(), "app")

    def handle_add_url(self, command_text: str) -> str:
        match = re.match(r"add url (.+) to (.+)", command_text, re.IGNORECASE)
        if not match: 
            return "Error: Invalid syntax. Use 'add url <url> to <workflow>'."
        return self._add_action(match.group(2).strip(), "open_url", match.group(1).strip(), "URL")

    def _add_action(self, workflow_name: str, action_type: str, action_value: str, type_label: str) -> str:
        try:
            workflow = self.db.query(Workflow).filter_by(name=workflow_name).first()
            if not workflow: 
                return f"Error: Workflow '{workflow_name}' not found."
            
            last_action = (
                self.db.query(WorkflowAction)
                .filter_by(workflow_id=workflow.id)
                .order_by(WorkflowAction.order.desc())
                .first()
            )
            next_order = (last_action.order + 1) if last_action else 0
            
            new_action = WorkflowAction(
                workflow_id=workflow.id, 
                order=next_order, 
                type=action_type, 
                value=action_value
            )
            self.db.add(new_action)
            self.db.commit()
            return f"Added {type_label} '{action_value}' to workflow '{workflow_name}'."
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add action to workflow '{workflow_name}': {e}", exc_info=True)
            return f"Error: {str(e)}"

    def handle_run_workflow(self, command_text: str) -> str:
        workflow_name = command_text[4:].strip()
        if not workflow_name:
            return "Error: Please specify a workflow name to run."
        
        workflow = self.db.query(Workflow).filter_by(name=workflow_name).first()
        if not workflow:
            return f"Error: Workflow '{workflow_name}' not found."
        
        try:
            return self.executor.run(workflow)
        except Exception as e:
            logger.error(f"Execution engine error for workflow '{workflow_name}': {e}", exc_info=True)
            return f"Error: Workflow execution failed due to an internal error: {str(e)}"