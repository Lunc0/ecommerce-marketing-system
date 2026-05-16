import json
import logging
import uuid
import requests
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHROMA_URL = "http://localhost:8000/api/v1"
COLLECTION_NAME = "marketing_scripts"
MODEL_NAME = "BAAI/bge-m3"

def get_or_create_collection(name):
    try:
        # Check if exists
        response = requests.get(f"{CHROMA_URL}/collections/{name}")
        if response.status_code == 200:
            return response.json()['id']
        
        # Create
        payload = {
            "name": name,
            "metadata": {"hnsw:space": "cosine"}
        }
        response = requests.post(f"{CHROMA_URL}/collections", json=payload)
        if response.status_code == 200:
            return response.json()['id']
        else:
            logger.error(f"Failed to create collection: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error accessing ChromaDB: {e}")
        return None

def ingest_scripts():
    try:
        # 1. Load scripts
        with open('marketing_scripts.json', 'r', encoding='utf-8') as f:
            scripts = json.load(f)
        
        if not scripts:
            logger.warning("No scripts found in JSON file.")
            return

        logger.info(f"Loaded {len(scripts)} scripts.")

        # 2. Generate embeddings
        logger.info(f"Loading model {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME)
        
        texts = []
        ids = []
        metadatas = []
        
        for script in scripts:
            scenario = script.get('scenario', 'general')
            content = script.get('content', '')
            tags = script.get('tags', '')
            
            # Format text for embedding: [Scenario] Content
            text_to_embed = f"场景: {scenario}. 内容: {content}"
            
            texts.append(text_to_embed)
            ids.append(str(uuid.uuid4()))
            metadatas.append({
                "scenario": scenario,
                "tags": tags
            })
            
        logger.info("Generating embeddings...")
        embeddings = model.encode(texts, normalize_embeddings=True).tolist()
        
        # 3. Ingest to ChromaDB
        col_id = get_or_create_collection(COLLECTION_NAME)
        if not col_id:
            return
            
        payload = {
            "ids": ids,
            "embeddings": embeddings,
            "metadatas": metadatas,
            "documents": texts
        }
        
        logger.info(f"Upserting to collection {col_id}...")
        response = requests.post(f"{CHROMA_URL}/collections/{col_id}/upsert", json=payload)
        
        if response.status_code == 200:
            logger.info("Successfully ingested scripts into ChromaDB.")
        else:
            logger.error(f"Failed to upsert: {response.text}")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")

if __name__ == "__main__":
    ingest_scripts()
