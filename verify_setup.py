#!/usr/bin/env python3
"""
Verify Jarvis2.0 setup and dependencies
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Verify Python version compatibility"""
    version = sys.version_info
    print(f"[CHECK] Python: {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 10:
        print("[OK] Python version is compatible")
        return True
    else:
        print("[WARN] Python 3.10+ recommended")
        return False

def check_package(package_name: str, import_name: str = None) -> bool:
    """Check if a package is installed"""
    import_name = import_name or package_name
    try:
        __import__(import_name)
        print(f"[OK] {package_name} installed")
        return True
    except ImportError:
        print(f"[FAIL] {package_name} NOT installed - run: pip install {package_name}")
        return False

def check_directory(dir_path: str) -> bool:
    """Check if directory exists"""
    p = Path(dir_path)
    if p.exists() and p.is_dir():
        print(f"[OK] Directory exists: {dir_path}")
        return True
    else:
        print(f"[WARN] Directory missing: {dir_path}")
        return False

def check_models():
    """Check for downloaded models"""
    models = {
        "models/whisper_ov": "Whisper OpenVINO",
        "models/embedding_model": "Sentence Transformers",
        "models/mmproj-Qwen2-VL-7B-Instruct-f32.gguf": "Qwen2 VLM",
        "models/qwen2-0_5b-instruct-q4_k_m.gguf": "Qwen2 0.5B LLM",
    }

    print("\n[CHECK] AI Models Status:")
    downloaded = 0
    for path, name in models.items():
        p = Path(path)
        if p.exists():
            print(f"[OK] {name} - {path}")
            downloaded += 1
        else:
            print(f"[MISSING] {name} - {path}")

    return downloaded, len(models)

def main():
    print("""
    ========================================================
    Jarvis2.0 Setup Verification
    ========================================================
    """)

    checks_passed = 0
    total_checks = 0

    print("\n[CHECK] Python Environment:")
    total_checks += 1
    if check_python_version():
        checks_passed += 1

    print("\n[CHECK] Required Dependencies:")
    critical_packages = [
        ("PyQt6", "PyQt6"),
        ("google-generativeai", "google.generativeai"),
        ("huggingface_hub", "huggingface_hub"),
        ("numpy", "numpy"),
        ("librosa", "librosa"),
        ("requests", "requests"),
    ]

    for package, import_name in critical_packages:
        total_checks += 1
        if check_package(package, import_name):
            checks_passed += 1

    print("\n[CHECK] Project Structure:")
    essential_dirs = [
        "models",
        "services",
        "skills",
        "web",
    ]

    for directory in essential_dirs:
        total_checks += 1
        if check_directory(directory):
            checks_passed += 1

    # Check models
    downloaded, total = check_models()

    print(f"\n{'='*60}")
    print(f"Summary: {checks_passed}/{total_checks} environment checks passed")
    print(f"Models: {downloaded}/{total} models downloaded")

    if checks_passed >= total_checks * 0.8 and downloaded >= total * 0.8:
        print("\n[OK] System is ready to run Jarvis!")
        print("\nTo start Jarvis, run:")
        print("  python main.py")
        return 0
    elif checks_passed >= total_checks * 0.5:
        print("\n[WARN] Some components missing. Install dependencies:")
        print("  pip install -r requirements.txt")
        return 1
    else:
        print("\n[FAIL] Critical components missing!")
        return 2

if __name__ == "__main__":
    sys.exit(main())
