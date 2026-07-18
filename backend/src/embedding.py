from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', shared_model=None):
        if shared_model:
            print("[DEBUG] Using shared model....")
            self.model = shared_model
        else:
            print(f"Loading model: {model_name}")
            self.model = SentenceTransformer(model_name)

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            print("no chunks provided")
            return []

        print(f"processing {len(chunks)} chunks")
        texts_to_embed = [chunk_data["chunk"] for chunk_data in chunks]
        metadatas = [chunk_data["metadata"] for chunk_data in chunks]

        embeddings = self.model.encode(texts_to_embed, show_progress_bar=True)

        for i, (_, _) in enumerate(zip(texts_to_embed, metadatas)):
            chunks[i]["embedding"] = embeddings[i].tolist()
            if "metadata" not in chunks[i]:
                chunks[i]["metadata"] = {}
            chunks[i]["metadata"]["embedding"] = self.model.get_embedding_dimension()

        return chunks

if __name__ == "__main__":
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embedder = Embedder(model_name="all-MiniLM-L6-v2", shared_model=model)
    test_chunks = [
        {'chunk': 'The\nproposed method can match the performance of classic Q-\nlearning on control environments while showing potential on\nsome selected Atari benchmarks.', 'metadata': {'producer': '', 'creator': '', 'creationdate': '', 'source': 'D:\\Deep learning\\ResearchAssistant\\backend\\src\\sample\\2010.12698v2.pdf', 'file_path': 'D:\\Deep learning\\ResearchAssistant\\backend\\src\\sample\\2010.12698v2.pdf', 'total_pages': 8, 'format': 'PDF 1.5', 'title': '', 'author': '', 'subject': '', 'keywords': '', 'moddate': '', 'trapped': '', 'modDate': '', 'creationDate': '', 'page': 0}}, {'chunk': '2017) reported random performance\nfor their Transformer-based approaches.', 'metadata': {'producer': '', 'creator': '', 'creationdate': '', 'source': 'D:\\Deep learning\\ResearchAssistant\\backend\\src\\sample\\2010.12698v2.pdf', 'file_path': 'D:\\Deep learning\\ResearchAssistant\\backend\\src\\sample\\2010.12698v2.pdf', 'total_pages': 8, 'format': 'PDF 1.5', 'title': '', 'author': '', 'subject': '', 'keywords': '', 'moddate': '', 'trapped': '', 'modDate': '', 'creationDate': '', 'page': 0}}
    ]
    embedded_chunks = embedder.embed_chunks(test_chunks)
    print(embedded_chunks)
