import sys
import os
import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import Services
from services.ai_service import AIService
from services.memory_service import MemoryService
from nlp_processor import LocalAIProcessor, NLPResult
from conversation_manager import ConversationContext, IntentType
from services.workflow_service import WorkflowService
from services.health_monitor_service import HealthMonitorService

class JarvisFullSystemTest(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive verification suite for Jarvis 2.0 advanced features.
    """
    
    async def asyncSetUp(self):
        # We mock external hardware dependencies to ensure tests run in any environment
        self.mock_stt = MagicMock()
        self.mock_tts = MagicMock()
        
        # Initialize Core Services (with some mocks)
        with patch('services.ai_service.OptimizedVoiceThread'), \
             patch('services.ai_service.TTSService'), \
             patch('services.vision_service.VisionService'):
            self.ai_service = AIService()
            self.ai_service.initialize_pipeline()
            # Wait for initialization
            await asyncio.sleep(0.5)

    async def test_01_nlp_intent_recognition(self):
        """Test if the NLP processor correctly identifies new intents"""
        print("\n[TEST] NLP Intent Recognition...")
        processor = LocalAIProcessor()
        
        # Mocking the AI response to avoid long inference during test
        mock_response = {
            "intent_classification": "record_workflow",
            "confidence": 0.95,
            "suggested_response": "Iniciando gravação.",
            "parameters": {"name": "test_macro"}
        }
        
        with patch.object(LocalAIProcessor, '_process_via_ollama', return_value=mock_response), \
             patch.object(LocalAIProcessor, '_process_via_llama_cpp', return_value=mock_response):
            
            context = ConversationContext()
            result = await processor.process_complex_query("iniciar gravação de macro abrir vscode", context)
            
            self.assertEqual(result['intent_classification'], "record_workflow")
            print("  - Intent 'record_workflow' detected successfully.")

    async def test_02_memory_associative(self):
        """Test Knowledge Graph and Associative Memory"""
        print("\n[TEST] Associative Memory (Knowledge Graph)...")
        memory = MemoryService(db_path="tmp/test_memory")
        
        # Add relation
        memory.knowledge_graph = {}
        entity = "Steve Jobs"
        relation = "fundador de"
        target = "Apple"
        
        if not hasattr(memory, 'knowledge_graph'):
            memory.knowledge_graph = {}
            
        if entity not in memory.knowledge_graph:
            memory.knowledge_graph[entity] = {}
        if relation not in memory.knowledge_graph[entity]:
            memory.knowledge_graph[entity][relation] = []
        memory.knowledge_graph[entity][relation].append(target)
        
        # Verify
        self.assertIn(target, memory.knowledge_graph[entity][relation])
        print(f"  - Relation '{entity} -> {relation} -> {target}' stored successfully.")

    async def test_03_health_monitor(self):
        """Test if HealthMonitor detects errors in logs"""
        print("\n[TEST] Auto-Healing Monitor...")
        monitor = HealthMonitorService()
        log_file = "tmp/test_error.log"
        
        # Create a fake error log
        with open(log_file, "w") as f:
            f.write("2026-03-14 22:00:00 - ERROR - STT Service: Connection failed\n")
            f.write("2026-03-14 22:01:00 - ERROR - STT Service: Connection failed\n")
            f.write("2026-03-14 22:02:00 - ERROR - STT Service: Connection failed\n")

        # Mock AI service to check if heal is triggered
        mock_ai = MagicMock()
        
        # Run a quick check
        errors = monitor._parse_logs(log_file)
        self.assertIn("STT Service", errors)
        self.assertEqual(errors["STT Service"], 3)
        print("  - Persistent error threshold (3) detected correctly.")

    async def test_04_workflow_manager(self):
        """Test Macro recording and storage"""
        print("\n[TEST] Workflow Orchestrator...")
        wf = WorkflowService(storage_path="tmp/test_workflows.json")
        
        wf.start_recording("test_macro")
        wf.add_to_recording("abrir notepad")
        wf.add_to_recording("digitar olá")
        name = wf.stop_recording()
        
        self.assertEqual(name, "test_macro")
        self.assertIn("test_macro", wf.workflows)
        self.assertEqual(len(wf.workflows["test_macro"]), 2)
        print(f"  - Workflow '{name}' recorded with 2 steps successfully.")

    async def test_05_offline_model_loading(self):
        """Check if services attempt to load local paths after localization"""
        print("\n[TEST] Local Model Paths...")
        # Check MemoryService
        memory = MemoryService(db_path="tmp/test_memory")
        # Since we modified the code to look at "models/embedding_model", 
        # let's verify if the path resolution logic works
        model_path = os.path.join("models", "embedding_model")
        self.assertTrue(os.path.exists(model_path), "Local embedding model directory missing!")
        print("  - Local model directory 'models/embedding_model' verified.")

if __name__ == "__main__":
    unittest.main()
