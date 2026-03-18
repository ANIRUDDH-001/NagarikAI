import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from app.core.config import master_config
from app.core.database import db_client

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Handles chunking of raw scraped data, generating HuggingFace embeddings,
    and pushing the vector data to Supabase (pgvector).
    """
    def __init__(self):
        # Load embedding model defined in master_config
        model_name = master_config["ingestion"]["embedding_model_name"]
        self.encoder = SentenceTransformer(model_name)
        
        self.chunk_size = master_config["ingestion"]["chunk_size"]
        self.chunk_overlap = master_config["ingestion"]["chunk_overlap"]
        self.batch_size = master_config["ingestion"]["batch_size"]

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Convert a list of text strings into dense vector embeddings.
        Uses sentence-transformers locally or API if configured.
        """
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.encoder.encode(texts)
        return embeddings.tolist()

    def ingest_to_db(self, schemes_data: List[Dict[str, Any]]):
        """
        Takes raw scheme data, chunks it, embeds it, and saves to database.
        """
        table_name = master_config["supabase"]["tables"]["chunks"]
        logger.info(f"Ingesting data into Supabase table: {table_name}")
        pass
