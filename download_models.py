import os
from huggingface_hub import snapshot_download

def download_models():
    """
    Downloads models from Hugging Face Hub to the local models/ directory.
    You need to update REPO_ID with your actual Hugging Face repository.
    """
    # TODO: Substitute with your actual repo ID after creating it on Hugging Face
    REPO_ID = "YOUR_USERNAME/jarvis-models" 
    LOCAL_DIR = "models"

    print(f"📥 Checking for models in {LOCAL_DIR}...")
    
    if not os.path.exists(LOCAL_DIR):
        os.makedirs(LOCAL_DIR)

    try:
        snapshot_download(
            repo_id=REPO_ID,
            local_dir=LOCAL_DIR,
            local_dir_use_symlinks=False,
            # allow_patterns=['*'], # Download all files
        )
        print("✅ Models synchronized successfully!")
    except Exception as e:
        print(f"❌ Error downloading models: {e}")
        print("\n💡 Tip: Make sure you created the repo on Hugging Face and uploaded the files.")
        print("💡 If the repo is private, run: huggingface-cli login")

if __name__ == "__main__":
    download_models()
