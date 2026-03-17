from huggingface_hub import hf_hub_download
import os

repo_id = "bartowski/Qwen2-VL-7B-Instruct-GGUF"
filename = "mmproj-Qwen2-VL-7B-Instruct-f32.gguf"
local_dir = "models"

print(f"Downloading {filename} from {repo_id}...")
try:
    hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=local_dir
    )
    print("Download successful!")
except Exception as e:
    print(f"Error during download: {e}")
