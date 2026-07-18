from pathlib import Path
import urllib.request as urlrequest
import arxiv

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.document_loaders import UnstructuredFileLoader

from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader

from langchain_community.document_loaders import WebBaseLoader

from langchain_community.document_loaders import UnstructuredCSVLoader
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.document_loaders import JSONLoader


def load_documents(data_dir: str):
    # Use project root data folder
    data_path = Path(data_dir).resolve()
    print(f"[DEBUG] Data path: {data_path}")
    documents = []

    # Map known extensions to their optimized loaders
    loader_mapping = {
        ".pdf": PyMuPDFLoader,
        ".txt": TextLoader,
        ".docx": Docx2txtLoader,
        ".csv": UnstructuredCSVLoader,
        ".xlsx": UnstructuredExcelLoader,
        ".md": UnstructuredMarkdownLoader,
    }

    # Recursively find ALL files in the directory regardless of extension
    for file_path in data_path.rglob('*'):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        print(f"[DEBUG] Processing file: {file_path}")

        try:
            if ext == '.json':
                loader = JSONLoader(str(file_path), jq_schema=".", text_content=False)
            elif ext in loader_mapping:
                # Use the predefined loader class for known types
                loader_class = loader_mapping[ext]
                loader = loader_class(str(file_path))
            else:
                # Catch-All fallback for unknown types (PPTX, HTML, EPUB, RTF, EML, etc.)
                print(f"[DEBUG] Unknown extension '{ext}', falling back to UnstructuredFileLoader")
                loader = UnstructuredFileLoader(str(file_path))

            loaded = loader.load()
            print(f"[DEBUG] Loaded {len(loaded)} docs from {file_path}")
            documents.extend(loaded)
        except Exception as e:
            print(f"[ERROR] Failed to load {file_path}: {e}")

    print(f"[INFO] Total documents loaded: {len(documents)}")
    return documents

def load_web_urls(urls:list):
    documents = []
    for url in urls:
        print(f"[DEBUG] Processing url: {url}")
        try:
            loader = WebBaseLoader(url)
            loaded = loader.load()
            print(f"[DEBUG] Loaded {len(loaded)} docs from {url}")
            documents.extend(loaded)
        except Exception as e:
            print(f"[ERROR] Failed to load {url}: {e}")
    print(f"[INFO] Total documents loaded from web URLs: {len(documents)}")
    return documents

def search_arxiv(query: str, max_results: int = 10):
    # Fetching paper metadata
    print(f"[DEBUG] Searching arxiv for : {query}")
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    results = []
    for paper in client.results(search):
        results.append({
            "id" : paper.get_short_id(),
            "title" : paper.title,
            "summary" : paper.summary,
            "authors" : [author.name for author in paper.authors],
            "published" : paper.published.strftime("%Y-%m-%d"),
            "pdf_url" : paper.pdf_url,
        })
    return results

def load_selected_arxivs(paper_ids: list):
    documents = []
    client = arxiv.Client()
    Path('../data').mkdir(parents=True, exist_ok=True)
    for paper_id in paper_ids:
        print(f"[DEBUG] Downloading and Loading arxiv paper-ID: {paper_id}")
        try:
            DATA_PATH='../data'
            DATA_URL=f'https://arxiv.org/pdf/{paper_id}.pdf'
            urlrequest.urlretrieve(DATA_URL, f'{DATA_PATH}/{paper_id}.pdf')
            print(f"[DEBUG] Successfully downloaded arxiv paper-ID: {paper_id}")
            loader = PyMuPDFLoader(f'{DATA_PATH}/{paper_id}.pdf')
            loaded = loader.load()
            print(f"[DEBUG] Loaded {len(loaded)} docs from {DATA_URL}")
            documents.extend(loaded)
        except Exception as e:
            print(f"[ERROR] Failed to load arxiv paper-ID {paper_id}: {e}")
    return documents

if __name__=="__main__":
    keyword = "Transformers"
    results = search_arxiv(keyword, max_results=10)
    print(results)

if __name__=="__main__":
    for result in results:
        print(f"""ID : {result["id"]}
                Title : {result["title"]}""")

if __name__=="__main__":
    paper_ids = [result["id"] for result in results]
    docs = load_selected_arxivs(paper_ids)
    print(f"Loaded {len(docs)} documents from arxiv")
    print("docs:", docs)

if __name__ == "__main__":
    docs = load_documents('../data')
    print(f"Loaded {len(docs)} documents")
    print(f"First document content: {docs[0].page_content if docs else 'No documents loaded'}")

if __name__=="__main__":
    urls= ['https://medium.com/the-ai-forum/semantic-chunking-for-rag-f4733025d5f5', 'https://medium.com/@awaldeep/understanding-the-essentials-nlp-text-preprocessing-steps-b5d1fd58c11a']
    web_docs = load_web_urls(urls)
    print(f"Loaded {len(web_docs)} documents from web URLs")
    print(web_docs)