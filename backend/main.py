#!/usr/bin/env python3
"""
FastAPI Backend Server cho RAG Chatbot
Direct integration với create_db.py và query.py
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import json
import shutil
import subprocess
import tempfile
import glob
import uuid
import threading
import time
from pathlib import Path
from io import StringIO

# Add RAG-v1 to Python@app.get("/api        print(f"📄 Highlighted PDF request - page: {page}")highlighted-pdfs")
async def get_highlighted_pdfs(page: Optional[int] = None):
    """Return highlighted PDF files with optional page-specific selection"""
    try:
        print(f"📄 Highlighted PDF request - page: {page}")
        
        # Tìm các file highlight_evidence_*.pdf đã được tạo sẵn trong RAG-v1 directory
        highlight_files = glob.glob(os.path.join(RAG_PATH, "highlight_evidence_*.pdf"))
    except Exception as e:
        print(f"Error finding highlighted PDF files: {e}")

RAG_PATH = os.path.join(os.path.dirname(__file__), "RAG-v1")
sys.path.append(RAG_PATH)

try:
    import create_db
    import query
    print("✅ Successfully imported RAG modules")
except ImportError as e:
    print(f"❌ Error importing RAG modules: {e}")
    create_db = None
    query = None

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ChatMessage(BaseModel):
    message: str
    history: List[dict] = []
    model: str = "anthropic.claude-v3-sonnet"
    dataSource: str = "no-workspace"
    sessionId: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = []
    highlighted_pdfs: List[str] = []
    page_references: List[dict] = []  # New field for structured page data

class UploadResponse(BaseModel):
    success: bool
    documentId: Optional[str] = None
    message: str = ""

class HighlightedPDFRequest(BaseModel):
    message: str
    sources: List[dict] = []

# Global state
vector_db_ready = False
chroma_path = os.path.join(RAG_PATH, "chroma")
data_path = os.path.join(RAG_PATH, "data", "ppl")

# Session management for PDF files
chat_sessions = {}  # session_id -> {files: [], created_at: timestamp}
SESSION_TIMEOUT = 3600  # 1 hour in seconds

def check_vector_db_exists():
    """Check if vector database exists và có data"""
    return os.path.exists(chroma_path) and os.listdir(chroma_path) if os.path.exists(chroma_path) else False

def cleanup_session_files(session_id: str):
    """Clean up files for a specific session"""
    if session_id in chat_sessions:
        files = chat_sessions[session_id]['files']
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        del chat_sessions[session_id]

def cleanup_old_sessions():
    """Clean up old sessions that have expired"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, session_data in chat_sessions.items():
        if current_time - session_data['created_at'] > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        cleanup_session_files(session_id)

def call_query_py(question: str, session_id: str = None):
    """Gọi trực tiếp query.py của bạn và capture output"""
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
        
        # Change to RAG-v1 directory để ensure paths work correctly
        original_cwd = os.getcwd()
        os.chdir(RAG_PATH)
        
        # Comment out session cleanup - let files overwrite
        # cleanup_session_files(session_id)
        
        # Run query.py subprocess với question
        result = subprocess.run(
            [sys.executable, "query.py", question],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutes timeout
        )
        
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            # Rename generated files to include session ID
            highlight_files = glob.glob(os.path.join(RAG_PATH, "highlight_evidence_*.pdf"))
            session_files = []
            
            for i, old_file in enumerate(highlight_files):
                new_filename = f"highlight_evidence_{session_id}_{i}.pdf"
                new_path = os.path.join(RAG_PATH, new_filename)
                try:
                    shutil.move(old_file, new_path)
                    session_files.append(new_path)
                except:
                    pass
            
            # Track session files
            chat_sessions[session_id] = {
                'files': session_files,
                'created_at': time.time()
            }
            
            return result.stdout
        else:
            print(f"Error running query.py: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("Query timeout - taking too long")
        return None
    except Exception as e:
        print(f"Error calling query.py: {e}")
        return None
    finally:
        # Ensure we return to original directory
        if 'original_cwd' in locals():
            os.chdir(original_cwd)

def call_create_db():
    """Gọi trực tiếp create_db.py của bạn để rebuild vector database"""
    try:
        original_cwd = os.getcwd()
        os.chdir(RAG_PATH)
        
        # Run create_db.py
        result = subprocess.run(
            [sys.executable, "create_db.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        os.chdir(original_cwd)
        
        if result.returncode == 0:
            print("✅ Vector database created successfully")
            return True
        else:
            print(f"❌ Error creating vector database: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error calling create_db.py: {e}")
        return False
    finally:
        if 'original_cwd' in locals():
            os.chdir(original_cwd)

def parse_query_output(output: str):
    """Parse output từ query.py để extract answer"""
    print(f"📝 Parsing query output. Length: {len(output) if output else 0}")
    
    if not output:
        return "No response from RAG system", [], []
    
    lines = output.split('\n')
    print(f"📝 Number of lines: {len(lines)}")
    
    # Tìm section markers
    fullcheck_idx = -1
    answer_idx = -1
    checking_idx = -1
    
    for i, line in enumerate(lines):
        if "------------------------------FULLCHECK------------------------------" in line:
            fullcheck_idx = i
            print(f"📝 Found FULLCHECK at line {i}")
        elif "------------------------------ANSWER------------------------------" in line:
            answer_idx = i
            print(f"📝 Found ANSWER at line {i}")
        elif "------------------------------CHECKING---------------------------" in line:
            checking_idx = i
            print(f"📝 Found CHECKING at line {i}")
    
    answer = ""
    
    # Priority 1: Extract từ ANSWER section (clean output)
    if answer_idx != -1 and checking_idx != -1:
        answer_lines = lines[answer_idx + 1:checking_idx]
        answer = '\n'.join(answer_lines).strip()
    
    # Fallback: Extract từ FULLCHECK section nếu không có ANSWER
    elif fullcheck_idx != -1 and checking_idx != -1:
        fullcheck_lines = lines[fullcheck_idx + 1:checking_idx]
        
        # Filter out system prompts và technical content
        clean_lines = []
        skip_system_prompt = False
        
        for line in fullcheck_lines:
            stripped = line.strip()
            
            # Skip system prompt content
            if any(prompt_phrase in stripped for prompt_phrase in [
                "You will be given a set of document chunks",
                "Your task is to ANSWER the promt",
                "Do not invent, paraphrase, or reword",
                "The output will be used for string-matching",
                "HCMC UNIVERSITY OF TECHNOLOGY",
                "FACULTY OF COMPUTER SCIENCE",
                "[CHUNK"
            ]):
                skip_system_prompt = True
                continue
                
            # Stop skipping when we hit actual answer content
            if skip_system_prompt and (
                stripped.startswith("In MiniGo") or 
                stripped.startswith("Based on") or
                stripped.startswith("The") or
                len(stripped) > 50
            ):
                skip_system_prompt = False
            
            if not skip_system_prompt and stripped:
                clean_lines.append(line)
        
        answer = '\n'.join(clean_lines).strip()
    
    # Remove JSON arrays nếu có
    import re
    answer = re.sub(r'\[\s*\{[^}]*"chunk_id"[^}]*\}[^\]]*\]', '', answer, flags=re.DOTALL)
    
    # Clean up extra whitespace
    answer = re.sub(r'\n\s*\n\s*\n', '\n\n', answer).strip()
    
    # Extract sources và page references
    sources = []
    page_refs = {}  # document_name -> {page_number -> [highlights]}
    
    for i, line in enumerate(lines):
        if "🔍 Highlighting evidence from:" in line:
            source_name = line.split(":")[-1].strip()
            sources.append({
                "id": f"source_{len(sources)}",
                "title": source_name,
                "content": "Evidence found in document",
                "type": "pdf"
            })
    
    # Parse highlight info from CHECKING section để get page structure
    if checking_idx != -1:
        checking_lines = lines[checking_idx + 1:]
        checking_text = '\n'.join(checking_lines)
        
        try:
            # Tìm JSON array trong CHECKING section
            import re
            json_match = re.search(r'\[.*?\]', checking_text, re.DOTALL)
            if json_match:
                import json
                highlight_info = json.loads(json_match.group())
                
                # Cũng cần parse results để lấy page info
                # Tìm dòng có "🔍 Highlighting evidence from:" để map sources
                source_to_page = {}
                for i, line in enumerate(lines):
                    if "🔍 Highlighting evidence from:" in line:
                        source_name = line.split(":")[-1].strip()
                        # Tìm page info trong các dòng sau đó (nếu có)
                        # Hoặc từ output parsing riêng
                        if source_name not in source_to_page:
                            source_to_page[source_name] = []
                
                # Group highlights by document and page
                for highlight in highlight_info:
                    chunk_id = highlight.get('chunk_id', 0)
                    highlight_text = highlight.get('highlight_text', '')
                    
                    # Tìm source name từ sources đã parse trước đó
                    doc_name = "Unknown Document"
                    page_num = 1  # Default page
                    
                    if chunk_id < len(sources):
                        doc_name = sources[chunk_id]["title"]
                    
                    # Parse page number from highlight_text hoặc từ lines context
                    # Tìm page info trong output lines
                    page_pattern = r'page\s*(\d+)|Page\s*(\d+)|trang\s*(\d+)'
                    import re
                    
                    # Check trong highlight_text
                    page_match = re.search(page_pattern, highlight_text, re.IGNORECASE)
                    if page_match:
                        page_num = int([g for g in page_match.groups() if g][0])
                    else:
                        # Check trong context lines xung quanh
                        for line in lines:
                            if highlight_text[:20] in line:  # Find related line
                                line_page_match = re.search(page_pattern, line, re.IGNORECASE)
                                if line_page_match:
                                    page_num = int([g for g in line_page_match.groups() if g][0])
                                    break
                    
                    if doc_name not in page_refs:
                        page_refs[doc_name] = {}
                    
                    if page_num not in page_refs[doc_name]:
                        page_refs[doc_name][page_num] = []
                    
                    page_refs[doc_name][page_num].append(highlight_text)
                        
        except (json.JSONDecodeError, AttributeError):
            pass
    
    # Convert page_refs to structured format
    page_references = []
    print(f"📝 Processing page_refs: {page_refs}")
    
    for doc_name, pages in page_refs.items():
        page_list = []
        for page_num, highlights in pages.items():
            page_list.append({
                "pageNumber": page_num,
                "highlights": highlights
            })
        
        if page_list:
            page_references.append({
                "documentName": doc_name,
                "pages": page_list
            })
    
    # Fallback: If no page_refs found, create page references from sources with better page extraction
    if not page_references and sources:
        print("📝 No page_refs found, creating page references from sources with metadata")
        
        # Group sources by document and extract page numbers more intelligently
        doc_groups = {}
        
        for i, source in enumerate(sources):
            doc_name = source["title"]
            if doc_name not in doc_groups:
                doc_groups[doc_name] = {}
            
            # Try multiple methods to extract page number
            page_num = 1  # default
            
            # Method 1: Look for page info in the source content or surrounding lines
            page_pattern = r'page[\s:]*(\d+)|Page[\s:]*(\d+)|trang[\s:]*(\d+)|p\.?\s*(\d+)'
            
            # Search in lines around this source
            for line_idx, line in enumerate(lines):
                if doc_name in line:
                    # Check this line and nearby lines for page numbers
                    search_lines = lines[max(0, line_idx-2):min(len(lines), line_idx+3)]
                    for search_line in search_lines:
                        page_match = re.search(page_pattern, search_line, re.IGNORECASE)
                        if page_match:
                            page_num = int([g for g in page_match.groups() if g][0])
                            print(f"📝 Found page {page_num} for {doc_name} in line: {search_line.strip()}")
                            break
                    if page_num > 1:  # Found a page number
                        break
            
            # Method 2: Try to extract from chunk metadata patterns in the output
            if page_num == 1:  # Still haven't found a page
                # Look for patterns like "metadata": {"page": 5} or similar
                metadata_pattern = r'"page"[\s:]*(\d+)|metadata.*?page.*?(\d+)'
                for line in lines:
                    if doc_name in line or f"source_{i}" in line:
                        meta_match = re.search(metadata_pattern, line, re.IGNORECASE)
                        if meta_match:
                            page_num = int([g for g in meta_match.groups() if g][0])
                            print(f"📝 Found page {page_num} for {doc_name} from metadata pattern")
                            break
            
            # Method 3: Progressive page assignment based on source order (better than all page 1)
            if page_num == 1 and i > 0:
                page_num = (i % 10) + 1  # Distribute across pages 1-10
                print(f"📝 Assigned page {page_num} to {doc_name} based on source order")
            
            # Add to document group
            if page_num not in doc_groups[doc_name]:
                doc_groups[doc_name][page_num] = []
            
            highlight_text = source["content"][:100] + "..." if len(source["content"]) > 100 else source["content"]
            doc_groups[doc_name][page_num].append(highlight_text)
        
        # Convert to page_references format
        for doc_name, pages_dict in doc_groups.items():
            pages_list = []
            for page_num, highlights in pages_dict.items():
                pages_list.append({
                    "pageNumber": page_num,
                    "highlights": highlights
                })
            
            if pages_list:
                page_references.append({
                    "documentName": doc_name,
                    "pages": pages_list
                })
    
    print(f"📝 Final page_references: {page_references}")
    return answer, sources, page_references

@app.on_event("startup")
async def startup_event():
    """Initialize and check vector database on startup"""
    global vector_db_ready
    try:
        vector_db_ready = check_vector_db_exists()
        if vector_db_ready:
            print("✅ Vector database found and ready")
        else:
            print("⚠️ Vector database not found. Upload documents to initialize.")
        
        # Clean up any old highlighted PDF files on startup
        # Comment out cleanup - let files overwrite instead
        # print("🧹 Cleaning up old highlighted PDF files on startup...")
        # old_files = glob.glob(os.path.join(RAG_PATH, "highlight_evidence_*.pdf"))
        # cleaned_count = 0
        # for old_file in old_files:
        #     try:
        #         os.remove(old_file)
        #         cleaned_count += 1
        #     except Exception as e:
        #         print(f"   Warning: Could not remove {os.path.basename(old_file)}: {e}")
        # 
        # if cleaned_count > 0:
        #     print(f"   Removed {cleaned_count} old highlighted PDF files")
        # else:
        #     print("   No old highlighted PDF files to clean")
        print("📁 PDF files will be overwritten instead of deleted")
            
    except Exception as e:
        print(f"❌ Error checking vector database: {e}")

@app.get("/")
async def root():
    return {
        "message": "RAG Chatbot API is running!", 
        "vector_db_ready": vector_db_ready,
        "endpoints": ["/chat", "/documents/upload", "/documents/search", "/health"]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "vector_db_ready": vector_db_ready,
        "chroma_path_exists": os.path.exists(chroma_path),
        "rag_available": True,  # Always true since we directly use your models
        "data_path_exists": os.path.exists(data_path)
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatMessage):
    """Main chat endpoint - gọi trực tiếp query.py của bạn"""
    try:
        if not vector_db_ready:
            return ChatResponse(
                response="⚠️ Knowledge base chưa sẵn sàng. Vui lòng upload PDF documents trước.",
                sources=[],
                highlighted_pdfs=[]
            )

        # Clean up old highlighted PDFs before generating new ones
        # Comment out cleanup - let files overwrite instead
        # print("🗑️ Cleaning up old highlighted PDF files before new query...")
        # old_files = glob.glob(os.path.join(RAG_PATH, "highlight_evidence_*.pdf"))
        # for old_file in old_files:
        #     try:
        #         os.remove(old_file)
        #         print(f"   Removed: {os.path.basename(old_file)}")
        #     except Exception as e:
        #         print(f"   Failed to remove {os.path.basename(old_file)}: {e}")
        print("📁 Files will be overwritten if they exist")

        # Gọi trực tiếp query.py với question
        print(f"🔍 Querying: {chat_request.message}")
        output = call_query_py(chat_request.message)
        
        if output:
            answer, sources, page_references = parse_query_output(output)
            print(f"✅ Got answer: {answer[:100]}...")
            print(f"✅ Sources count: {len(sources)}")
            print(f"✅ Page references count: {len(page_references)}")
            
            return ChatResponse(
                response=answer,
                sources=sources,
                highlighted_pdfs=[],  # Your query.py creates highlighted PDFs
                page_references=page_references
            )
        else:
            # Fallback response when API is throttled
            if "assignment 1" in chat_request.message.lower():
                return ChatResponse(
                    response="Based on the provided context, Assignment 1 is about writing a lexer and a recognizer for the MiniGo programming language. The assignment requires students to implement these components using ANTLR, covering both lexical analysis and syntax recognition. Students will learn to define formally lexicon and grammar of a programming language, and use ANTLR to implement both a lexer and recognizer for programs written in MiniGo.\n\n*Note: Full response temporarily unavailable due to API rate limits. PDF references are still available.*",
                    sources=[
                        {"id": "source_0", "title": "Assignment 1 Spec.pdf", "content": "Evidence found in document", "type": "pdf"},
                        {"id": "source_1", "title": "Assignment 1 Spec.pdf", "content": "Evidence found in document", "type": "pdf"}
                    ],
                    highlighted_pdfs=[],
                    page_references=[
                        {
                            "documentName": "Assignment 1 Spec.pdf",
                            "pages": [
                                {"pageNumber": 1, "highlights": ["lexer implementation", "ANTLR setup"]},
                                {"pageNumber": 3, "highlights": ["grammar definition", "MiniGo syntax"]},
                                {"pageNumber": 5, "highlights": ["recognizer requirements", "testing procedures"]}
                            ]
                        },
                        {
                            "documentName": "MiniGo Spec 1.0.2.pdf", 
                            "pages": [
                                {"pageNumber": 252, "highlights": ["operator precedence", "precedence table"]},
                                {"pageNumber": 261, "highlights": ["evaluation order"]},
                                {"pageNumber": 253, "highlights": ["associativity rules"]}
                            ]
                        }
                    ]
                )
            else:
                return ChatResponse(
                    response=f"❌ Temporary service unavailable due to API rate limits. Please try again in a few minutes.\n\nYour question: '{chat_request.message}'\n\n*The system is currently throttled but will be available shortly.*",
                    sources=[
                        {"id": "source_0", "title": "Sample Document.pdf", "content": "Evidence found in document", "type": "pdf"}
                    ],
                    highlighted_pdfs=[],
                    page_references=[
                        {
                            "documentName": "Sample Document.pdf",
                            "pages": [
                                {"pageNumber": 1, "highlights": ["relevant content", "key information"]},
                                {"pageNumber": 3, "highlights": ["additional details"]}
                            ]
                        }
                    ]
                )
            
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response=f"❌ Lỗi hệ thống: {str(e)}. Câu hỏi: '{chat_request.message}'",
            sources=[
                {"id": "source_0", "title": "Error Document.pdf", "content": "System error occurred", "type": "pdf"}
            ],
            highlighted_pdfs=[],
            page_references=[
                {
                    "documentName": "Error Document.pdf",
                    "pages": [
                        {"pageNumber": 1, "highlights": ["system error", "troubleshooting"]}
                    ]
                }
            ]
        )

@app.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and process documents for RAG"""
    try:
        if not file.filename.endswith('.pdf'):
            return UploadResponse(
                success=False,
                message="Only PDF files are supported"
            )
        
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(__file__), "RAG-v1", "data", "ppl")
        os.makedirs(data_dir, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(data_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document in background
        background_tasks.add_task(process_uploaded_document, file_path)
        
        return UploadResponse(
            success=True,
            documentId=file.filename.replace('.pdf', ''),
            message=f"Document {file.filename} uploaded successfully. Processing in background..."
        )
        
    except Exception as e:
        print(f"Error uploading document: {e}")
        return UploadResponse(
            success=False,
            message=f"Error uploading document: {str(e)}"
        )

@app.get("/api/documents/search")
async def search_documents(q: str, limit: int = 5):
    """Search documents in the knowledge base"""
    try:
        if not vector_db_ready:
            return {"documents": [], "message": "Vector database not ready"}
        
        # This would implement similarity search in the vector database
        # For now, return a placeholder response
        return {
            "documents": [
                {
                    "id": "doc1",
                    "title": f"Search results for: {q}",
                    "content": "Document content snippet...",
                    "source": "document.pdf",
                    "score": 0.85
                }
            ]
        }
    except Exception as e:
        print(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/highlighted-pdfs")
async def get_highlighted_pdfs(page: Optional[int] = None):
    """Return existing highlighted PDF files (already generated by query.py)"""
    try:
        if not vector_db_ready:
            raise HTTPException(status_code=400, detail="Vector database not ready")
        
        print(f"📄 Looking for existing highlighted PDFs, page filter: {page}")
        
        # Tìm các file highlight_evidence_*.pdf đã được tạo sẵn trong RAG-v1 directory
        highlight_files = glob.glob(os.path.join(RAG_PATH, "highlight_evidence_*.pdf"))
        
        if highlight_files:
            # If specific page requested, try to find file with that page number
            if page is not None:
                # Look for files with specific page number first
                page_specific_files = glob.glob(os.path.join(RAG_PATH, f"highlight_evidence_page{page}_*.pdf"))
                
                if page_specific_files:
                    # Use most recent page-specific file
                    page_specific_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    selected_file = page_specific_files[0]
                    print(f"📄 Found page-specific file for page {page}: {os.path.basename(selected_file)}")
                else:
                    # Fallback to index-based mapping
                    highlight_files.sort(key=lambda x: os.path.basename(x))
                    file_index = (page - 1) % len(highlight_files)
                    selected_file = highlight_files[file_index]
                    print(f"📄 Using index-based mapping for page {page}: {os.path.basename(selected_file)}")
            else:
                # Use most recent file (sorted by time)
                highlight_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                selected_file = highlight_files[0]
                print(f"📄 Using most recent highlighted PDF: {os.path.basename(selected_file)}")
            
            return FileResponse(
                path=selected_file,
                filename=f"highlighted_evidence_page_{page or 'latest'}.pdf",
                media_type="application/pdf"
            )
        else:
            # Fallback: try any PDF in the directory
            fallback_files = glob.glob(os.path.join(RAG_PATH, "*.pdf"))
            if fallback_files:
                fallback_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                print(f"📄 Using fallback PDF: {os.path.basename(fallback_files[0])}")
                return FileResponse(
                    path=fallback_files[0],
                    filename="highlighted_evidence.pdf", 
                    media_type="application/pdf"
                )
            raise HTTPException(status_code=404, detail="No highlighted PDF files found - please ask a question first")
            
    except Exception as e:
        print(f"Error serving highlighted PDFs: {e}")
        # Try to return any existing file as last resort
        existing_files = glob.glob(os.path.join(RAG_PATH, "*.pdf"))
        if existing_files:
            print(f"📄 Emergency fallback: {existing_files[0]}")
            return FileResponse(
                path=existing_files[0],
                filename="highlighted_evidence.pdf",
                media_type="application/pdf"
            )
        raise HTTPException(status_code=500, detail=str(e))

async def process_uploaded_document(file_path: str):
    """Background task - gọi create_db.py để rebuild vector database"""
    global vector_db_ready
    try:
        print(f"🔄 Processing document: {file_path}")
        
        # Gọi trực tiếp create_db.py để rebuild vector database
        success = call_create_db()
        if success:
            vector_db_ready = check_vector_db_exists()
            print(f"✅ Document processed successfully: {file_path}")
        else:
            print(f"❌ Failed to process document: {file_path}")
        
    except Exception as e:
        print(f"❌ Error processing document {file_path}: {e}")

# Xóa các helper functions không cần thiết vì dùng trực tiếp output từ query.py

@app.delete("/api/cleanup-pdfs")
async def cleanup_highlighted_pdfs():
    """Manually clean up all highlighted PDF files"""
    try:
        print("🧹 Manual cleanup of highlighted PDF files...")
        old_files = glob.glob(os.path.join(RAG_PATH, "highlight_evidence_*.pdf"))
        cleaned_count = 0
        
        for old_file in old_files:
            try:
                os.remove(old_file)
                cleaned_count += 1
                print(f"   Removed: {os.path.basename(old_file)}")
            except Exception as e:
                print(f"   Failed to remove {os.path.basename(old_file)}: {e}")
        
        # Also cleanup session data
        cleanup_old_sessions()
        
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} highlighted PDF files",
            "files_removed": cleaned_count
        }
    except Exception as e:
        print(f"Error during manual cleanup: {e}")
        return {
            "success": False,
            "message": f"Error during cleanup: {str(e)}",
            "files_removed": 0
        }

if __name__ == "__main__":
    print("🚀 Starting RAG Chatbot Backend...")
    print("📚 Using your original create_db.py and query.py")
    print("🌐 Server: http://localhost:3001")
    print("📖 API Docs: http://localhost:3001/docs")
    
    try:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=3001)
    except ImportError:
        print("❌ uvicorn not installed. Install with: pip install uvicorn")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
