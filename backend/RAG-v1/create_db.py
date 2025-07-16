from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

# Đường dẫn
CHROMA_PATH = "chroma"
DATA_PATH = "data/ppl"


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
            print("HIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII")
            print(loader)
            all_docs.extend(docs)
    print(all_docs)
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

    document = chunks[10]
    print(document.page_content)
    print(document.metadata)

    # for i, chunk in enumerate(chunks[:5]):
    #     print(f"Chunk {i}")
    #     print("Text:", chunk.page_content)
    #     print("Metadata:", chunk.metadata)

    return chunks


def save_to_chroma(chunks: list[Document]):
    # Xóa vector DB cũ nếu có
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

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
