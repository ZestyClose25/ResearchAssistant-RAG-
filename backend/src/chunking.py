from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class Chunker:
    def __init__(self):
        print("[DEBUG] Initializing Recursive text splitter....")
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=['\n\n', '\n', ' ', '']
        )

    def chunk(self, documents: List[Document]) -> List[Dict[str, Any]]:
        print("[DEBUG] Chunking documents...")
        chunks = []

        split_docs = self.splitter.split_documents(documents)

        for doc in split_docs:
            chunks.append({
                "chunk": doc.page_content,
                "metadata": doc.metadata
            })
        print(f"[DEBUG] Sucessfully generated {len(chunks)} chunks....")
        return chunks