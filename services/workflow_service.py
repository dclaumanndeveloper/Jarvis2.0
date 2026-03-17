import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class WorkflowService:
    """
    Service to manage and execute multi-step macros or workflows.
    Allows Jarvis to orchestrate complex sequences of actions.
    """
    def __init__(self, storage_path="web/data/workflows.json"):
        self.storage_path = Path(storage_path)
        self.workflows = self._load_workflows()
        self.is_recording = False
        self.current_recording = []
        logger.info("WorkflowService: Initialized.")

    def _load_workflows(self) -> Dict[str, List[str]]:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"WorkflowService: Load error: {e}")
        return {}

    def _save_workflows(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.workflows, f, indent=4)

    def start_recording(self, name: str):
        self.is_recording = True
        self.current_workflow_name = name
        self.current_recording = []
        logger.info(f"WorkflowService: Recording started for '{name}'")

    def add_to_recording(self, command: str):
        if self.is_recording:
            self.current_recording.append(command)
            logger.info(f"WorkflowService: Added command to record: {command}")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.workflows[self.current_workflow_name] = self.current_recording
            self._save_workflows()
            logger.info(f"WorkflowService: Workflow '{self.current_workflow_name}' saved.")
            return self.current_workflow_name
        return None

    async def run_workflow(self, name: str, ai_service):
        """Execute a sequence of commands via AIService"""
        if name in self.workflows:
            commands = self.workflows[name]
            logger.info(f"WorkflowService: Running workflow '{name}' ({len(commands)} steps)")
            
            for cmd in commands:
                logger.info(f"WorkflowService: Executing step: {cmd}")
                # We reuse the AI Service command processing logic
                ai_service.process_command(cmd)
                # Wait a bit between steps for stability
                await asyncio.sleep(2.0)
            
            return True
        return False

    def list_workflows(self) -> List[str]:
        return list(self.workflows.keys())
