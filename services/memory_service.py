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
        self.doc_embeddings = []   # New: For larger documents
        self.documents = []        # New: metadata for documents
        self.knowledge_graph = {} # {entity: {relation: [targets]}}
        
        self.docs_file = os.path.join(self.db_path, "docs_rag.pkl")
        
        try:
            from sentence_transformers import SentenceTransformer
            # Load lightweight local embedding model (local path in models/)
            model_path = os.path.join(self.db_path.parent if hasattr(self.db_path, 'parent') else "models", "embedding_model")
            if not os.path.exists(model_path):
                # Fallback to download if local folder doesn't exist yet
                model_path = 'all-MiniLM-L6-v2'
                
            self.embedder = SentenceTransformer(model_path)
            self._load_db()
            self._dirty = False # Track if we need to save
            logger.info("MemoryService: Optimized RAG initialized successfully.")
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
                # Backward compatibility: ensure norms
                if len(self.facts_embeddings) > 0:
                    norms = np.linalg.norm(self.facts_embeddings, axis=1)
                    norms[norms == 0] = 1.0
                    self.facts_embeddings = self.facts_embeddings / norms[:, np.newaxis]

        if os.path.exists(self.docs_file):
            with open(self.docs_file, 'rb') as f:
                data = pickle.load(f)
                self.documents = data.get('documents', []) # Changed from 'docs' to 'documents' for consistency
                self.doc_embeddings = data.get('embeddings', [])
                self.knowledge_graph = data.get('knowledge_graph', {})

    def _save_db(self):
        with open(self.conversations_file, 'wb') as f:
            pickle.dump({'docs': self.conversations, 'embeddings': self.conversations_embeddings}, f)
        with open(self.facts_file, 'wb') as f:
            pickle.dump({'docs': self.facts, 'embeddings': self.facts_embeddings}, f)
        with open(self.docs_file, 'wb') as f:
            pickle.dump({
                'documents': self.documents, # Changed from 'docs' to 'documents' for consistency
                'embeddings': self.doc_embeddings,
                'knowledge_graph': self.knowledge_graph
            }, f)

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
            # Pre-normalize
            norm = np.linalg.norm(embedding)
            if norm > 0: embedding = embedding / norm

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
            # Pre-normalize for instant search later
            norm = np.linalg.norm(embedding)
            if norm > 0: embedding = embedding / norm

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
                
                # Normalize query once
                query_norm = np.linalg.norm(query_emb)
                normalized_query = query_emb / (query_norm + 1e-10)
                
                # Stored embeddings are now pre-normalized (see store methods)
                similarities = np.dot(normalized_query, stored_embs.T)[0]
                
                top_indices = np.argsort(similarities)[::-1][:k]
                return [stored_docs[i]['document'] for i in top_indices if similarities[i] > 0.35]
            
            # 1. Facts
            fact_results = get_top_k(query_embedding, self.facts_embeddings, self.facts, k=2)
            if fact_results:
                context_parts.append("Known Facts: " + " | ".join(fact_results))

            # 2. Documents (RAG)
            doc_results = get_top_k(query_embedding, self.doc_embeddings, self.documents, k=2)
            if doc_results:
                context_parts.append("Document Knowledge: " + " | ".join(doc_results))

            # 3. Interactions
            conv_results = get_top_k(query_embedding, self.conversations_embeddings, self.conversations, k=n_results)
            if conv_results:
                context_parts.append("Past Context: " + " | ".join(conv_results))
                
        except Exception as e:
            logger.error(f"MemoryService Error during retrieval: {e}")
            
        return "\n".join(context_parts)

    def ingest_document(self, file_path: str):
        """Read a file, chunk it, and store in vector DB"""
        if not self.embedder: return
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Simple chunking by paragraph or fixed size
            chunks = [content[i:i+800] for i in range(0, len(content), 600)] # Overlap of 200
            
            for i, chunk in enumerate(chunks):
                metadata = {
                    "type": "doc_chunk",
                    "source": os.path.basename(file_path),
                    "chunk_id": i,
                    "document": chunk.strip()
                }
                
                embedding = self.embedder.encode(chunk)
                norm = np.linalg.norm(embedding)
                if norm > 0: embedding = embedding / norm

                self.documents.append(metadata)
                if len(self.doc_embeddings) == 0:
                    self.doc_embeddings = np.array([embedding])
                else:
                    self.doc_embeddings = np.vstack([self.doc_embeddings, embedding])
            
            self._save_db()
            logger.info(f"MemoryService: Ingested {len(chunks)} chunks from {file_path}")
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")

    def ingest_directory(self, dir_path: str):
        """Ingest all text-based files in a directory"""
        valid_exts = ['.txt', '.md', '.py', '.js', '.html', '.css']
        for root, _, files in os.walk(dir_path):
            for file in files:
                if any(file.endswith(ext) for ext in valid_exts):
                    self.ingest_document(os.path.join(root, file))

    def add_relation(self, entity: str, relation: str, target: str):
        """Add a relationship to the knowledge graph"""
        if entity not in self.knowledge_graph:
            self.knowledge_graph[entity] = {}
        if relation not in self.knowledge_graph[entity]:
            self.knowledge_graph[entity][relation] = []
        
        if target not in self.knowledge_graph[entity][relation]:
            self.knowledge_graph[entity][relation].append(target)
            self._save_db()
            logger.info(f"MemoryService: Added relation {entity} -> {relation} -> {target}")

    def query_relations(self, entity: str) -> Dict[str, List[str]]:
        """Query all relations for a given entity"""
        return self.knowledge_graph.get(entity, {})
