import uuid
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams,SparseVectorParams, Modifier, SparseVector
from qdrant_client.http.models import Distance, PointStruct, Filter, FieldCondition, MatchAny
from qdrant_client.http.models import Modifier, Prefetch, Fusion, FusionQuery
from fastembed import SparseTextEmbedding

class QDrantStore:
    def __init__(self, persist_dir:str = '../db', collection_name:str="docs", vector_size:int = 384):
        print(f"[DEBUG] Initializing QDrant Vector Database at {persist_dir}")

        self.client = QdrantClient(path=persist_dir)
        self.collection_name = collection_name

        print("[DEBUG] Loading BM25 Sparse model....")
        self.sparse_model = SparseTextEmbedding(model_name='Qdrant/bm25')

        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            # For dense vectors - query vector search
            vectors_config={
                "dense": VectorParams(size=vector_size, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    modifier=Modifier.IDF
                )
            }
        )

    def save_chunks(self, embedded_chunks: List[Dict[str, Any]]):
        if not embedded_chunks:
            print("[DEBUG] No chunks to save.")
            return

        print("Generating BM25 sparse vectors for chunks....")
        chunk_texts = [chunk_data['chunk'] for chunk_data in embedded_chunks]
        sparse_embeddings = list(self.sparse_model.embed(chunk_texts))

        points = []
        for idx, chunk_data in enumerate(embedded_chunks):
            chunk_text = chunk_data['chunk']
            sparse_vec = sparse_embeddings[idx]


            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_text))

            payload = chunk_data.get("metadata", {}).copy()
            payload["text_content"] = chunk_text

            point = PointStruct(
                id=chunk_id,
                payload=payload,
                vector={
                    "dense": chunk_data["embedding"],
                    "sparse": SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist()
                    )
                }
            )

            points.append(point)
        print(f"[DEBUG] Uploading {len(points)} chunks into QDrant.....")

        self.client.upload_points(
            collection_name=self.collection_name,
            points=points
        )

        print("[DEBUG] Saved...")

    # Hybrid search
    def search(self, query_vector: List[float], bm25_query_text: str = None, top_k: int = 5, file_types: List[str] = None):
        search_filter = None
        if file_types:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="file_type",
                        match=MatchAny(any=file_types)
                    )
                ]
            )

        if bm25_query_text:
            sparse_query_vec = list(self.sparse_model.embed([bm25_query_text]))[0]

            search_results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=query_vector,
                        using="dense",
                        limit=20,
                        filter=search_filter
                    ),
                    Prefetch(
                        query=SparseVector(
                            indices=sparse_query_vec.indices.tolist(),
                            values=sparse_query_vec.values.tolist()
                        ),
                        using="sparse",
                        limit=20,
                        filter=search_filter
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
                with_payload=True
            )

        else : # Dense only path (fallback)
            search_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                limit=top_k,
                query_filter=search_filter,
                with_payload=True
            )

        # Formatting results
        formatted_results = []
        for point in search_results.points:
            payload = point.payload.copy()
            text_content = payload.pop("text_content", "")

            formatted_results.append({
                "chunk": text_content,
                "score": point.score,
                "metadata": payload
            })

        return formatted_results