import subprocess
import os
import logging
import sys

logger = logging.getLogger(__name__)

class CodingAgentService:
    """
    Allows Jarvis to write and execute its own Python scripts.
    Used for complex tasks like file conversions, data processing, etc.
    """
    def __init__(self, workspace_dir="tmp/jarvis_coder"):
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

    async def execute_task(self, prompt, llm_processor):
        """
        1. Ask LLM to generate Python code for the prompt.
        2. Save to a temporary file.
        3. Execute and capture output.
        """
        logger.info(f"CodingAgent: Resolvendo tarefa complexa: {prompt}")
        
        # Generation Prompt
        gen_prompt = (
            f"Escreva um script Python autônomo para resolver esta tarefa: '{prompt}'. "
            "O script deve ser completo, importar todas as bibliotecas necessárias "
            "e imprimir o resultado final claramente. Responda APENAS com o código Python, "
            "sem explicações ou blocos de markdown."
        )
        
        # Request code from LLM
        code = await llm_processor.process_complex_query(gen_prompt)
        
        # Clean code (remove markdown if LLM ignored instructions)
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
            
        script_path = os.path.join(self.workspace_dir, "generated_solution.py")
        
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            logger.info(f"CodingAgent: Executando script gerado em {script_path}")
            
            # Execute script
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("CodingAgent: Tarefa concluída com sucesso.")
                return f"Tarefa concluída. Resultado: {result.stdout}"
            else:
                logger.error(f"CodingAgent: Falha na execução: {result.stderr}")
                return f"Ocorreu um erro ao executar a solução: {result.stderr}"
                
        except Exception as e:
            logger.error(f"CodingAgent: Erro inesperado: {e}")
            return f"Erro ao processar a tarefa de codificação: {e}"
