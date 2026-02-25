import os
from huggingface_hub import snapshot_download

def download_model():
    model_id = "OpenVINO/whisper-tiny-fp16-ov"
    local_dir = "models/whisper_ov"
    
    print(f"Downloading {model_id} to {local_dir}...")
    os.makedirs(local_dir, exist_ok=True)
    
    snapshot_download(
        repo_id=model_id,
        local_dir=local_dir,
        ignore_patterns=["*.md", "*.txt"]
    )
    print("Download complete.")

if __name__ == "__main__":
    download_model()
