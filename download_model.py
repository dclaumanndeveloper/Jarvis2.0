import requests
import os

url = "https://huggingface.co/Qwen/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0_5b-instruct-q4_k_m.gguf"
output_path = "models/qwen2-0_5b-instruct-q4_k_m.gguf"

print(f"Downloading model from {url}...")
try:
    response = requests.get(url, stream=True, allow_redirects=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    done = int(50 * downloaded / total_size)
                    print(f"\r[{'=' * done}{' ' * (50-done)}] {downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB", end='')
    print("\nDownload complete!")
except Exception as e:
    print(f"\nError downloading: {e}")
