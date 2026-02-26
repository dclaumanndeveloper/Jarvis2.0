import os
import pkgutil
import importlib
import logging

logger = logging.getLogger(__name__)

def load_all_skills():
    """
    Dynamically discovers and loads all valid Python modules within the 'skills' directory.
    This automatically triggers their @registry.register decorators to hook them into the ActionController.
    """
    skills_dir = os.path.dirname(__file__)
    loaded_skills = []

    # Iterate over all modules in the current package
    for module_info in pkgutil.iter_modules([skills_dir]):
        module_name = module_info.name
        
        # Prevent importing __init__ itself or private modules
        if module_name.startswith('_'):
            continue
            
        try:
            full_module_name = f"skills.{module_name}"
            importlib.import_module(full_module_name)
            loaded_skills.append(module_name)
            logger.info(f"Skill loaded successfully: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load skill '{module_name}': {e}")
            
    return loaded_skills

# Auto-execute upon import skills
load_all_skills()
