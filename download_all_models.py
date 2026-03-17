#!/usr/bin/env python3
"""
Download all AI models required for Jarvis2.0
Executes all model downloads in sequence with progress tracking
"""

import os
import sys
import subprocess
from pathlib import Path

def run_download_script(script_name: str, description: str) -> bool:
    """Execute a download script and report status"""
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f"[FAIL] {description}: Script not found ({script_name})")
        return False

    try:
        print(f"\n{'='*60}")
        print(f"[DOWNLOAD] {description}")
        print(f"{'='*60}")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            cwd=Path(__file__).parent
        )
        print(f"[OK] {description}: Complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {description}: Failed with error code {e.returncode}")
        return False
    except Exception as e:
        print(f"[FAIL] {description}: {e}")
        return False

def main():
    print("""
    ========================================================
    J.A.R.V.I.S. 2.0 - Model Downloader

    This will download all required AI models (~8-10GB)
    Models will be saved to: ./models/
    ========================================================
    """)

    # Create models directory
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    results = {}

    # Download models in order of importance/size
    models_to_download = [
        ("download_whisper_ov.py", "Whisper OpenVINO (Speech-to-Text) [~500MB]"),
        ("download_embeddings.py", "Sentence Transformers Embedding Model [~150MB]"),
        ("download_vlm.py", "Qwen2 Vision Language Model [~5-7GB]"),
        ("download_model.py", "Qwen2 0.5B Instruct LLM [~350MB]"),
    ]

    total = len(models_to_download)
    completed = 0

    for script, description in models_to_download:
        if run_download_script(script, description):
            results[description] = "[OK]"
            completed += 1
        else:
            results[description] = "[FAIL]"

    # Summary
    print(f"\n{'='*60}")
    print("DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    for model, status in results.items():
        print(f"{status} {model}")

    print(f"\nProgress: {completed}/{total} models downloaded successfully")

    if completed == total:
        print("\n[SUCCESS] All models downloaded successfully! Jarvis is ready to run.")
        sys.exit(0)
    elif completed > 0:
        print(f"\n[WARNING] Partial success: {completed}/{total} models ready")
        print("    Some features may be unavailable.")
        sys.exit(1)
    else:
        print("\n[FAIL] No models were downloaded. Please check your internet connection.")
        sys.exit(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[WARNING] Download interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        sys.exit(1)
