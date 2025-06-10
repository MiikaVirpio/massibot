import os
import pickle
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
import tiktoken
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer


# List of urls to pages and pdfs and possible files to load
from doclist import doclist

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_URI = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode=disable"

tokenizer = OpenAITokenizer(
     tokenizer=tiktoken.encoding_for_model("gpt-4o"),
     max_tokens=128 * 1024,  # context window length required for OpenAI tokenizers
)

docs = []

for doc_url in doclist:
    docloader = DoclingLoader(
        file_path=doc_url,
        export_type=ExportType.DOC_CHUNKS,
        chunker=HybridChunker(
            tokenizer=tokenizer,
            merge_peers=True
        )
    )
    try:
        doc = docloader.load()
        docs.extend(doc)
    except Exception as e:
        print(f"Error loading document {doc_url}: {e}")
        continue

len(docs)
vars(docs[1800])["page_content"][:1000]  # Preview content of a document

# Save documents to a pickle file for later use
with open("docs.pkl", "wb") as f:
    pickle.dump(docs, f)

# Create vector db and add documents
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
collection_name = "massi_docs2"
vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=DB_URI,
    use_jsonb=True,
)

# Splitted to batches to fit embedding window
doc_splits = [docs[i:i+300] for i in range(0, len(docs), 300)]
for doc_split in doc_splits:
    vector_store.add_documents(doc_split)

# A test query
vector_store.similarity_search("Onko asuntolaina liian kallis?", k=5)

# In case of oopsie
vector_store.delete_collection()
