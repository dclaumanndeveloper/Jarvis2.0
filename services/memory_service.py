import os
import json
import logging
import pickle
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MemoryService:
    """
    RAG Local Long-Term Memory Service using Sentence-Transformers and NumPy.
    Lightweight alternative to ChromaDB designed for high compatibility in Python 3.14.
    """
    def __init__(self, db_path="memory_db"):
        self.db_path = db_path
        os.makedirs(self.db_path, exist_ok=True)
        
        self.conversations_file = os.path.join(self.db_path, "conversations.pkl")
        self.facts_file = os.path.join(self.db_path, "facts.pkl")
        
        self.conversations = []
        self.facts = []
        self.conversations_embeddings = []
        self.facts_embeddings = []
        
        try:
            from sentence_transformers import SentenceTransformer
            # Load lightweight local embedding model
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            self._load_db()
            logger.info("MemoryService: Lightweight RAG initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MemoryService: {e}")
            self.embedder = None
            
    def _load_db(self):
        if os.path.exists(self.conversations_file):
            with open(self.conversations_file, 'rb') as f:
                data = pickle.load(f)
                self.conversations = data.get('docs', [])
                self.conversations_embeddings = data.get('embeddings', [])
                
        if os.path.exists(self.facts_file):
            with open(self.facts_file, 'rb') as f:
                data = pickle.load(f)
                self.facts = data.get('docs', [])
                self.facts_embeddings = data.get('embeddings', [])

    def _save_db(self):
        with open(self.conversations_file, 'wb') as f:
            pickle.dump({'docs': self.conversations, 'embeddings': self.conversations_embeddings}, f)
        with open(self.facts_file, 'wb') as f:
            pickle.dump({'docs': self.facts, 'embeddings': self.facts_embeddings}, f)

    def store_interaction(self, user_text: str, ai_response: str, intent: str, timestamp: str):
        if not self.embedder: return
        
        try:
            document = f"User asked: '{user_text}'. Jarvis responded: '{ai_response}'."
            metadata = {
                "type": "interaction",
                "intent": intent,
                "timestamp": timestamp,
                "user_text": user_text,
                "ai_response": ai_response,
                "document": document
            }
            
            embedding = self.embedder.encode(document)
            self.conversations.append(metadata)
            
            if len(self.conversations_embeddings) == 0:
                self.conversations_embeddings = np.array([embedding])
            else:
                self.conversations_embeddings = np.vstack([self.conversations_embeddings, embedding])
            
            self._save_db()
            logger.debug(f"MemoryService: Stored interaction at {timestamp}")
        except Exception as e:
            logger.error(f"MemoryService Error storing interaction: {e}")

    def store_fact(self, fact_text: str, category: str = "general"):
        if not self.embedder: return
        
        try:
            # Upsert logic - avoid exact duplicates
            if any(f['document'] == fact_text for f in self.facts):
                return
                
            metadata = {
                "type": "fact",
                "category": category,
                "document": fact_text
            }
            
            embedding = self.embedder.encode(fact_text)
            self.facts.append(metadata)
            
            if len(self.facts_embeddings) == 0:
                self.facts_embeddings = np.array([embedding])
            else:
                self.facts_embeddings = np.vstack([self.facts_embeddings, embedding])
                
            self._save_db()
            logger.info(f"MemoryService: Stored fact '{fact_text[:20]}...'")
        except Exception as e:
            logger.error(f"MemoryService Error storing fact: {e}")

    def retrieve_relevant_context(self, current_query: str, n_results: int = 3) -> str:
        if not self.embedder: return ""
        
        context_parts = []
        try:
            query_embedding = self.embedder.encode(current_query).reshape(1, -1)
            
            def get_top_k(query_emb, stored_embs, stored_docs, k=2):
                if len(stored_embs) == 0:
                    return []
                # Cosine similarity using inner product of normalized vectors
                norms = np.linalg.norm(stored_embs, axis=1)
                norms[norms == 0] = 1e-10 # prevent div by zero
                normalized_embs = stored_embs / norms[:, np.newaxis]
                
                query_norm = np.linalg.norm(query_emb)
                normalized_query = query_emb / (query_norm + 1e-10)
                
                similarities = np.dot(normalized_query, normalized_embs.T)[0]
                
                top_indices = np.argsort(similarities)[::-1][:k]
                return [stored_docs[i]['document'] for i in top_indices if similarities[i] > 0.3] # Threshold
            
            fact_results = get_top_k(query_embedding, self.facts_embeddings, self.facts, k=2)
            if fact_results:
                context_parts.append("Known Facts: " + " | ".join(fact_results))

            conv_results = get_top_k(query_embedding, self.conversations_embeddings, self.conversations, k=n_results)
            if conv_results:
                context_parts.append("Past Context: " + " | ".join(conv_results))
                
        except Exception as e:
            logger.error(f"MemoryService Error during retrieval: {e}")
            
        return "\n".join(context_parts)
