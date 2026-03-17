from sentence_transformers import SentenceTransformer
import os

model_path = "models/embedding_model"
os.makedirs(model_path, exist_ok=True)

print(f"Downloading and saving model to {model_path}...")
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save(model_path)
print("Done!")
