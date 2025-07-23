import argparse
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings, BedrockEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms import Bedrock
from langchain_community.chat_models import BedrockChat
from langchain_aws import ChatBedrock
import fitz  # PyMuPDF
#from fuzzywuzzy import fuzz
from rapidfuzz import fuzz
import re
import json
import shutil
import boto3

# Load API key từ file .env
load_dotenv()

client = boto3.client(service_name="bedrock-runtime",region_name="us-east-1")
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

def partial_highlight(pdt_path, output_path, text_to_highlight, page_number,file_exist, threshold=90):
    doc = fitz.open(pdt_path)
    page = doc[page_number]
    page_text = page.get_text()

    # Làm sạch text
    target_text = text_to_highlight.replace("\\n", "\n").strip()

    spans = find_spans_fuzzy(page, target_text, threshold)

    if not spans:
        print("--------------Failed to find highlight partial!")
        return
    else:
        for span in spans:
            highlight = page.add_highlight_annot(span)
            highlight.update()

    print("------------------Partial highlight checking---------------")

    
    if file_exist:
        temp_output = output_path + ".temp.pdf"
        doc.save(temp_output, garbage=4, deflate=True, clean=True)
        doc.close()
        shutil.move(temp_output, output_path)
    else:
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()

def find_spans_fuzzy(page, target, threshold=90, buffer=10):
    spans = []
    words = page.get_text("words")  # Mỗi từ là (x0, y0, x1, y1, word, block_no, line_no, word_no)
    words.sort(key=lambda w: (w[1], w[0]))  # Sắp xếp từ trên xuống dưới, trái sang phải

    word_texts = [w[4] for w in words]
    target_len = len(target.split())
    max_window = min(len(words), target_len + buffer)

    for i in range(len(words) - max_window + 1):
        for window in range(target_len, max_window + 1):
            window_words = word_texts[i:i+window]
            window_text = " ".join(window_words)
            score = fuzz.partial_ratio(window_text, target)
            if score >= threshold:
                rects = [fitz.Rect(w[:4]) for w in words[i:i+window]]
                span = rects[0]
                for r in rects[1:]:
                    span |= r  # union các vùng lại
                spans.append(span)
                break  # không cần kiểm tra các cửa sổ dài hơn nữa tại vị trí i

    return spans

def simple_highlight(pdf_path, output_path, text_to_highlight, page_number, threshold=90):
    print("-----------------------------------------------------CHEKING----------------------------------------------------------------------------")
    print(text_to_highlight)

    file_exist = os.path.isfile(output_path)

    print(file_exist)

    if file_exist:
        pdf_path = output_path

    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_number)
        rects = page.search_for(text_to_highlight)

        # print("CHECKING - ",text_to_highlight)
        # print(rects)


        if (len(rects) == 0):
            print("Failed to highlight from LLM. CHECKING the partial highlight!")
            partial_highlight(pdf_path,output_path,text_to_highlight,page_number,file_exist,threshold=90)
            return

        for rect in rects:
            page.add_highlight_annot(rect)

        if file_exist:
            temp_output = output_path + ".temp.pdf"
            doc.save(temp_output, garbage=0, deflate=True, clean=True)
            doc.close()
            shutil.move(temp_output, output_path)
        else:
            doc.save(output_path, garbage=0, deflate=True, clean=True)
            doc.close()
        print(f"✅ Highlighted PDF saved to: {output_path}")
        return
    except Exception as e:
        print("DANGBILOI@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        print(e)

def extract_info(resp: str):
    # Tìm phần danh sách JSON trong chuỗi
    match = re.search(r'\[\s*{.*?}\s*\]', resp, re.DOTALL)
    if not match:
        return resp,[]

    end_answer = match.span()[0]

    json_str = match.group(0)
    print(json_str)

    try:
        return resp[:end_answer], json.loads(json_str)
    except json.JSONDecodeError:
        # Nếu JSON bị lỗi do escape (\\n), xử lý tiếp
        cleaned_str = json_str.replace("\\n", "\n")
        return resp[:end_answer], json.loads(cleaned_str)
    
# ✅ HÀM CHÍNH
def main():
    # CLI
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Load vector DB
    # embedding_function = HuggingFaceEmbeddings(
    #     model_name="BAAI/bge-large-en-v1.5",
    #     model_kwargs={"device": "cpu"},
    #     encode_kwargs={"normalize_embeddings": True}
    # )

    embedding_function = BedrockEmbeddings(
        model_id="cohere.embed-english-v3",
        region_name="us-east-1"  # thay bằng region bạn dùng Bedrock
    )
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Chuyển truy vấn sang định dạng BGE
    bge_query = "Represent this sentence for searching relevant passages: " + query_text

    # Truy vấn vector DB
    initial_result = db.similarity_search_with_relevance_scores(bge_query, k=10)

    #results = [(doc,score) for doc,score in initial_result if score >= 0.65]

    # all_docs = db.get(include=['documents', 'metadatas'])
    # for i, (doc, meta) in enumerate(zip(all_docs['documents'], all_docs['metadatas'])):
    #     print(f"Document {i}")
    #     print("Text:", doc)  # In 200 ký tự đầu
    #     print("Metadata:", meta)
    #     print("-" * 40)

    #     if (i == 50):
    #         break

    #return

    results = initial_result

    # for i in initial_result:
    #     print(i)
    #     print("\n\n\n")

    if len(results) == 0:
        print("Error len == 0")

    # if len(results) == 0 or results[0][1] < 0.3:
    #     print("Unable to find matching results.")
    #     return

    #number = 1


    # for doc, score in results:
    #     source = doc.metadata.get("source", None)
    #     if source is None or not source.endswith(".pdf"):
    #         continue

    #     print(f"\n🔍 Highlighting evidence from: {source}")
        
    #     chunk_text = doc.page_content
    #     output_highlighted_pdf = source.replace(".pdf", f"highlighted_{number}.pdf")


        #output_highlighted_pdf = source.replace(".pdf", f"highlighted_{number}.pdf")
        #number += 1

        # ✅ Gọi hàm highlight mới
        # simple_highlight(
        #     pdf_path=source,
        #     output_path=output_highlighted_pdf,
        #     text_to_highlight=chunk_text,
        #     page_number=doc.metadata["page"]
        # )


    instruction = """
You will be given a set of document chunks.

Your task is to ANSWER the promt and EXTRACT *only* spans of text that are **exactly present** in the provided content (verbatim match). 
Do not invent, paraphrase, or reword. 
You must copy phrases directly from the context only.

The output will be used for string-matching highlights. So it must match *exactly* the content provided.
"""

    
    # Tạo prompt cho LLM từ context
    #context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
    context_text = "\n\n---\n\n".join(
    [f"[CHUNK {i}]\n{doc.page_content}" for i, (doc, _) in enumerate(results)]
)
    template = """You are given several document chunks.

Only extract exact text spans from the content. 
You MUST NOT paraphrase or generate new content.

Context:
{context}

Question:
{question}

Answer format:
"...............................(Must answer the promt based on the context given. If dont know answer that you dont have enought information)"

[
  {{ "chunk_id": ..., "highlight_text": "..." }},
  ...
]
"""
    prompt_template = ChatPromptTemplate.from_template(template)
    prompt_input = instruction + "\n\n" + context_text
    prompt = prompt_template.format(context=prompt_input, question=query_text)
    #print(f"\n===== PROMPT SENT TO GEMINI =====\n{prompt}\n")

    # LLM: Gemini
    print(prompt_input)
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=os.environ["GOOGLE_API_KEY"]
    )
    response_text = model.predict(prompt)

    # native_request = {
    # "anthropic_version": "bedrock-2023-05-31",
    # "max_tokens": 1594,
    # "temperature": 0,
    # "messages": [
    #         {
    #             "role": "user",
    #             "content": [{"type": "text", "text": prompt}],
    #         }
    #     ],
    # }

    # # Convert the native request to JSON.
    # request = json.dumps(native_request)
    # response = client.invoke_model(modelId=model_id, body=request)

    # model_response = json.loads(response["body"].read())

    # # Extract and print the response text.
    # response_text = model_response["content"][0]["text"]
    # print(response_text)


    #print(response_text)

    answer, highlight_doc_info = extract_info(response_text)
    

    for i,item in enumerate(highlight_doc_info):
        id_num = item["chunk_id"]
        text_highlight = item["highlight_text"]
        doc = results[id_num][0]

        source = doc.metadata["file_path"]
        file_name = doc.metadata["source"]
        page_num = doc.metadata["page"]
        
        print(f"🔍 Highlighting chunk {id_num} from {file_name} page {page_num}")
        print(source)
        
        # Tạo 1 file output duy nhất cho tất cả highlights
        output_path = f"highlight_evidence_{file_name}_combined.pdf"

        simple_highlight(
            pdf_path=source,
            output_path=output_path,
            text_to_highlight=text_highlight,
            page_number=page_num
        )

    print("------------------------------FULLCHECK------------------------------")
    print(response_text)

    print("------------------------------ANSWER------------------------------")
    if(answer == "```json"):
        print("The knowledge-base given did not contain enough information to answer this promt!!!")
    else:
        print(answer)
    print("------------------------------CHECKING---------------------------")
    print(highlight_doc_info)
    # sources = [doc.metadata.get("source", None) for doc, _ in results]
    # formatted_response = f"\n===== RESPONSE =====\n{response_text}\nSources: {sources}"
    # print(formatted_response)

# ✅ ENTRY POINT
if __name__ == "__main__":
    main()
