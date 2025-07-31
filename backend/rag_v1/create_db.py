from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings, BedrockEmbeddings
from langchain_community.vectorstores import Chroma
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

# Đường dẫn
BASE_DIR = os.path.dirname(__file__)
CHROMA_PATH = os.path.join(BASE_DIR, "chroma")
DATA_PATH   = os.path.join(BASE_DIR, "data")

def main():
    generate_data_store()


def generate_data_store():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)


def load_documents():
    # loader = DirectoryLoader(DATA_PATH, glob="*.pdf")
    # documents = loader.load()
    # return documents
    all_docs = []
    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".pdf"):
            path = os.path.join(DATA_PATH, filename)
            loader = PyMuPDFLoader(path)
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = filename  # thêm tên file nếu cần
                doc.metadata["file_path"] = path  # thêm full path để query.py sử dụng
                # Đảm bảo page metadata được set đúng
                if "page" not in doc.metadata:
                    doc.metadata["page"] = 0  # default page nếu không có
                print(f"📄 Loaded {filename} page {doc.metadata.get('page', 'unknown')}")
            print(f"✅ Loaded {len(docs)} pages from {filename}")
            all_docs.extend(docs)
    
    print(f"📚 Total documents loaded: {len(all_docs)}")
    # Print some metadata examples for debugging
    for i, doc in enumerate(all_docs[:3]):
        print(f"Sample doc {i}: page={doc.metadata.get('page')}, source={doc.metadata.get('source')}")
    
    return all_docs


def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=300,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    if len(chunks) > 10:
        document = chunks[10]
        print(document.page_content[:300])
        print(document.page_content)
        print(document.metadata)
    else:
        print("⚠️ Không có đủ chunks để preview.")

    return chunks


def save_to_chroma(chunks: list[Document]):
    # Xóa vector DB cũ nếu có
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
    os.makedirs(CHROMA_PATH, exist_ok=True)

    # Tạo vector store mới với AWS Bedrock embeddings
    # embedding_model = HuggingFaceEmbeddings(
    #     model_name="sentence-transformers/all-MiniLM-L6-v2",
    #     model_kwargs={"device": "cpu"},  # Nếu có GPU thì dùng "cuda"
    #     encode_kwargs={"normalize_embeddings": True}
    # )

    embedding_model = BedrockEmbeddings(
        model_id="cohere.embed-english-v3",
        region_name="us-east-1"  # thay bằng region bạn dùng Bedrock
    )
    db = Chroma.from_documents(
        chunks, embedding_model, persist_directory=CHROMA_PATH
    )
    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")


if __name__ == "__main__":
    main()
