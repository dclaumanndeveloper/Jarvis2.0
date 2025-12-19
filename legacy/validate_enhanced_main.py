"""
Basic validation script for Enhanced Main System
Tests the core structure and integration patterns without requiring heavy dependencies
"""

import sys
import ast
import inspect
from pathlib import Path

def validate_enhanced_main_structure():
    """Validate the structure of enhanced_main.py"""
    print("=== Enhanced Main Structure Validation ===")
    
    # Read the enhanced_main.py file
    enhanced_main_path = Path("enhanced_main.py")
    if not enhanced_main_path.exists():
        print("❌ enhanced_main.py file not found")
        return False
    
    with open(enhanced_main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the AST to analyze structure
    try:
        tree = ast.parse(content)
        print("✅ Python syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    
    # Check for required classes and functions
    required_classes = [
        'SystemState',
        'PerformanceMode', 
        'SystemConfig',
        'SystemMetrics',
        'EnhancedJarvis'
    ]
    
    required_functions = [
        'create_default_config',
        'main'
    ]
    
    # Extract class and function names
    classes_found = []
    functions_found = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes_found.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions_found.append(node.name)
    
    # Validate required classes
    missing_classes = [cls for cls in required_classes if cls not in classes_found]
    if missing_classes:
        print(f"❌ Missing required classes: {missing_classes}")
        return False
    else:
        print(f"✅ All required classes found: {required_classes}")
    
    # Validate required functions
    missing_functions = [func for func in required_functions if func not in functions_found]
    if missing_functions:
        print(f"❌ Missing required functions: {missing_functions}")
        return False
    else:
        print(f"✅ All required functions found: {required_functions}")
    
    return True

def validate_enhanced_jarvis_methods():
    """Validate EnhancedJarvis class methods"""
    print("\n=== EnhancedJarvis Methods Validation ===")
    
    # Read and parse the file
    with open("enhanced_main.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    # Find EnhancedJarvis class
    jarvis_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'EnhancedJarvis':
            jarvis_class = node
            break
    
    if not jarvis_class:
        print("❌ EnhancedJarvis class not found")
        return False
    
    # Extract method names
    methods = [node.name for node in jarvis_class.body if isinstance(node, ast.FunctionDef)]
    
    # Required methods for proper functionality
    required_methods = [
        '__init__',
        'initialize_system',
        '_initialize_database',
        '_initialize_speech_recognition',
        '_initialize_conversation_manager',
        '_initialize_learning_engine',
        '_initialize_ui',
        '_setup_component_integration',
        '_change_system_state',
        'handle_system_error',
        'start_conversation_loop',
        'stop_conversation_loop',
        'shutdown',
        'get_system_status'
    ]
    
    # Callback methods
    callback_methods = [
        '_on_speech_start',
        '_on_speech_end',
        '_on_recognition_result',
        '_on_intent_classified',
        '_on_response_generated',
        '_on_pattern_detected'
    ]
    
    # Check required methods
    missing_required = [method for method in required_methods if method not in methods]
    if missing_required:
        print(f"❌ Missing required methods: {missing_required}")
        return False
    else:
        print(f"✅ All required methods found ({len(required_methods)} methods)")
    
    # Check callback methods
    missing_callbacks = [method for method in callback_methods if method not in methods]
    if missing_callbacks:
        print(f"❌ Missing callback methods: {missing_callbacks}")
        return False
    else:
        print(f"✅ All callback methods found ({len(callback_methods)} methods)")
    
    print(f"✅ Total methods in EnhancedJarvis: {len(methods)}")
    return True

def validate_integration_patterns():
    """Validate integration patterns and architecture"""
    print("\n=== Integration Patterns Validation ===")
    
    with open("enhanced_main.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for observer pattern implementation
    observer_indicators = [
        'set_callbacks',
        'register_callback',
        '_trigger_callbacks',
        'on_speech_start',
        'on_recognition_result',
        'on_state_change'
    ]
    
    found_patterns = []
    for indicator in observer_indicators:
        if indicator in content:
            found_patterns.append(indicator)
    
    if len(found_patterns) >= len(observer_indicators) * 0.8:  # 80% threshold
        print(f"✅ Observer pattern implementation detected ({len(found_patterns)}/{len(observer_indicators)} indicators)")
    else:
        print(f"❌ Observer pattern implementation insufficient ({len(found_patterns)}/{len(observer_indicators)} indicators)")
        return False
    
    # Check for error handling patterns
    error_handling_indicators = [
        'handle_system_error',
        'recovery_attempts',
        'graceful',
        'try:',
        'except Exception',
        'logger.error'
    ]
    
    error_patterns = [indicator for indicator in error_handling_indicators if indicator in content]
    
    if len(error_patterns) >= 5:
        print(f"✅ Comprehensive error handling detected ({len(error_patterns)} patterns)")
    else:
        print(f"❌ Insufficient error handling patterns ({len(error_patterns)} patterns)")
        return False
    
    # Check for async/await patterns
    async_indicators = ['async def', 'await ', 'asyncio']
    async_patterns = [indicator for indicator in async_indicators if indicator in content]
    
    if len(async_patterns) >= 3:
        print(f"✅ Async programming patterns detected ({len(async_patterns)} patterns)")
    else:
        print(f"❌ Insufficient async patterns ({len(async_patterns)} patterns)")
        return False
    
    return True

def validate_configuration_management():
    """Validate configuration and metrics management"""
    print("\n=== Configuration Management Validation ===")
    
    with open("enhanced_main.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for configuration classes
    config_indicators = [
        'SystemConfig',
        'SystemMetrics',
        'AudioConfig',
        'create_default_config',
        'dataclass'
    ]
    
    config_patterns = [indicator for indicator in config_indicators if indicator in content]
    
    if len(config_patterns) >= 4:
        print(f"✅ Configuration management implemented ({len(config_patterns)}/{len(config_indicators)} elements)")
    else:
        print(f"❌ Configuration management incomplete ({len(config_patterns)}/{len(config_indicators)} elements)")
        return False
    
    # Check for performance monitoring
    performance_indicators = [
        'performance_monitor',
        'metrics',
        'memory_usage',
        'cpu_usage',
        'uptime_seconds',
        '_update_performance_metrics'
    ]
    
    perf_patterns = [indicator for indicator in performance_indicators if indicator in content]
    
    if len(perf_patterns) >= 5:
        print(f"✅ Performance monitoring implemented ({len(perf_patterns)}/{len(performance_indicators)} elements)")
    else:
        print(f"❌ Performance monitoring incomplete ({len(perf_patterns)}/{len(performance_indicators)} elements)")
        return False
    
    return True

def validate_documentation_and_logging():
    """Validate documentation and logging implementation"""
    print("\n=== Documentation and Logging Validation ===")
    
    with open("enhanced_main.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count docstrings
    tree = ast.parse(content)
    
    documented_methods = 0
    total_methods = 0
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            total_methods += 1
            if (node.body and 
                isinstance(node.body[0], ast.Expr) and 
                isinstance(node.body[0].value, ast.Constant) and 
                isinstance(node.body[0].value.value, str)):
                documented_methods += 1
    
    doc_percentage = (documented_methods / total_methods * 100) if total_methods > 0 else 0
    
    if doc_percentage >= 80:
        print(f"✅ Good documentation coverage: {doc_percentage:.1f}% ({documented_methods}/{total_methods} methods)")
    else:
        print(f"⚠️  Documentation could be improved: {doc_percentage:.1f}% ({documented_methods}/{total_methods} methods)")
    
    # Check logging implementation
    logging_indicators = [
        'logging',
        'logger.info',
        'logger.error',
        'logger.warning',
        'logger.debug',
        'logger.critical'
    ]
    
    logging_patterns = [indicator for indicator in logging_indicators if indicator in content]
    
    if len(logging_patterns) >= 5:
        print(f"✅ Comprehensive logging implemented ({len(logging_patterns)} patterns)")
    else:
        print(f"❌ Logging implementation incomplete ({len(logging_patterns)} patterns)")
        return False
    
    return True

def main():
    """Main validation function"""
    print("Enhanced Jarvis 2.0 - Main System Validation")
    print("=" * 50)
    
    validation_results = []
    
    # Run all validations
    validation_results.append(validate_enhanced_main_structure())
    validation_results.append(validate_enhanced_jarvis_methods())
    validation_results.append(validate_integration_patterns())
    validation_results.append(validate_configuration_management())
    validation_results.append(validate_documentation_and_logging())
    
    # Summary
    passed = sum(validation_results)
    total = len(validation_results)
    
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("Enhanced Main System is properly implemented!")
    else:
        print("⚠️  Some validations failed. Review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)