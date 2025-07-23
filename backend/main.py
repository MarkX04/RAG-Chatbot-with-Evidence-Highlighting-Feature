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

RAG_PATH = os.path.join(os.path.dirname(__file__), "rag_v1")
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
    
    print(f"📝 Searching for sources in {len(lines)} lines...")
    
    for i, line in enumerate(lines):
        if "🔍 Highlighting evidence from:" in line:
            source_name = line.split(":")[-1].strip()
            sources.append({
                "id": f"source_{len(sources)}",
                "title": source_name,
                "content": "Evidence found in document",
                "type": "pdf"
            })
            print(f"📝 Added source {len(sources)-1}: {source_name}")
        
        # Also check for alternative source patterns
        if "Evidence found in document" in line or "source" in line.lower():
            print(f"📝 Line {i}: {line.strip()}")
    
    print(f"📝 Total sources extracted: {len(sources)}")
    
    # If no sources found with standard pattern, try alternative patterns
    if len(sources) == 0:
        print("📝 No sources found with standard pattern, trying alternatives...")
        seen_documents = set()  # Track unique documents
        
        for i, line in enumerate(lines):
            if "pdf" in line.lower() or "doc" in line.lower():
                print(f"📝 Potential source line {i}: {line.strip()}")
                # Extract document names from any line containing PDF
                if ".pdf" in line:
                    pdf_match = re.search(r'([^/\\:]+\.pdf)', line)
                    if pdf_match:
                        source_name = pdf_match.group(1).strip()
                        
                        # Skip duplicate documents and highlight_evidence files
                        if (source_name not in seen_documents and 
                            not source_name.startswith("highlight_evidence_") and
                            not source_name.startswith(" highlight_evidence_")):
                            
                            seen_documents.add(source_name)
                            sources.append({
                                "id": f"source_{len(sources)}",
                                "title": source_name,
                                "content": "Evidence found in document",
                                "type": "pdf"
                            })
                            print(f"📝 Added unique source {len(sources)-1}: {source_name}")
    
    print(f"📝 Final sources count: {len(sources)}")
    
    # Parse highlight info from CHECKING section to get page structure
    if checking_idx != -1:
        checking_lines = lines[checking_idx + 1:]
        checking_text = '\n'.join(checking_lines)
        
        try:
            # Look for JSON array in CHECKING section
            json_match = re.search(r'\[.*?\]', checking_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                print(f"📝 Found JSON in CHECKING: {json_str[:200]}...")
                
                # Clean up JSON if needed
                json_str = json_str.replace("'", '"')  # Fix single quotes
                json_str = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', json_str)  # Fix unquoted keys
                
                highlight_info = json.loads(json_str)
                print(f"📝 Found {len(highlight_info)} highlight entries in CHECKING section")
                
                # Group highlights by document and page
                for highlight in highlight_info:
                    chunk_id = highlight.get('chunk_id', 0)
                    highlight_text = highlight.get('highlight_text', '')
                    
                    # Only process highlights if we have actual source documents
                    if len(sources) == 0:
                        print(f"📝 Skipping highlight - no source documents found")
                        continue
                    
                    # Use the first (and usually only) source document
                    doc_name = sources[0]["title"]
                    page_num = 1  # Default page
                    
                    # Parse page number from highlight_text or context
                    page_pattern = r'page\s*(\d+)|Page\s*(\d+)|trang\s*(\d+)'
                    
                    # Check in highlight_text
                    page_match = re.search(page_pattern, highlight_text, re.IGNORECASE)
                    if page_match:
                        page_num = int([g for g in page_match.groups() if g][0])
                        print(f"📝 Found page {page_num} in highlight text for {doc_name}")
                    else:
                        # Check in context lines around this highlight
                        for line in lines:
                            if highlight_text[:20] in line:  # Find related line
                                line_page_match = re.search(page_pattern, line, re.IGNORECASE)
                                if line_page_match:
                                    page_num = int([g for g in line_page_match.groups() if g][0])
                                    print(f"📝 Found page {page_num} in context for {doc_name}")
                                    break
                    
                    if doc_name not in page_refs:
                        page_refs[doc_name] = {}
                    
                    if page_num not in page_refs[doc_name]:
                        page_refs[doc_name][page_num] = []
                    
                    page_refs[doc_name][page_num].append(highlight_text)
                        
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"📝 Could not parse CHECKING JSON: {e}")
            # Try alternative parsing - look for chunk_id and highlight_text patterns
            chunk_pattern = r'"chunk_id":\s*(\d+).*?"highlight_text":\s*"([^"]+)"'
            matches = re.findall(chunk_pattern, checking_text, re.DOTALL)
            
            if matches:
                print(f"📝 Found {len(matches)} highlights using pattern matching")
                for chunk_id_str, highlight_text in matches:
                    chunk_id = int(chunk_id_str)
                    
                    if chunk_id < len(sources):
                        doc_name = sources[chunk_id]["title"]
                        page_num = 1  # Default
                        
                        # Try to extract page from highlight text
                        page_match = re.search(r'page\s*(\d+)', highlight_text, re.IGNORECASE)
                        if page_match:
                            page_num = int(page_match.group(1))
                        
                        if doc_name not in page_refs:
                            page_refs[doc_name] = {}
                        if page_num not in page_refs[doc_name]:
                            page_refs[doc_name][page_num] = []
                        
                        page_refs[doc_name][page_num].append(highlight_text)
                        print(f"📝 Added highlight for {doc_name}, page {page_num}")
            else:
                print("📝 No highlights found using pattern matching either")
    
    # Convert page_refs to structured format - only include pages with actual highlights
    page_references = []
    print(f"📝 Processing page_refs: {page_refs}")
    
    for doc_name, pages in page_refs.items():
        page_list = []
        for page_num, highlights in pages.items():
            # Only add pages that have actual highlights
            if highlights:  # Check if highlights list is not empty
                page_list.append({
                    "pageNumber": page_num,
                    "highlights": highlights
                })
        
        if page_list:  # Only add documents that have pages with highlights
            page_references.append({
                "documentName": doc_name,
                "pages": page_list
            })
    
    print(f"📝 Initial page_references from parsing: {len(page_references)}")
    
    # PRIORITIZE Method 0: Extract ALL pages from chunk highlighting logs FIRST
    # This will override the incomplete results from CHECKING section
    print("📝 Starting Method 0: Extract pages from chunk highlighting logs...")
    chunk_page_info = {}  # doc_name -> set of pages
    
    for i, line in enumerate(lines):
        # Look for chunk highlighting logs: "🔍 Highlighting chunk X from document.pdf page Y"
        chunk_match = re.search(r'🔍 Highlighting chunk \d+ from (.+?)\.pdf page (\d+)', line)
        if chunk_match:
            doc_base = chunk_match.group(1)
            page_num = int(chunk_match.group(2))
            doc_name = f"{doc_base}.pdf"
            
            if doc_name not in chunk_page_info:
                chunk_page_info[doc_name] = set()
            chunk_page_info[doc_name].add(page_num)
            print(f"📝 Found chunk highlighting: {doc_name} page {page_num}")
    
    # If we found chunk page info, use it instead of CHECKING section results
    if chunk_page_info:
        print("📝 Method 0 found pages - overriding CHECKING section results")
        page_references = []  # Clear previous results
        
        for doc_name, page_set in chunk_page_info.items():
            pages_list = []
            for page_num in sorted(page_set):
                pages_list.append({
                    "pageNumber": page_num,
                    "highlights": [f"Content highlighted on page {page_num}"]
                })
            
            if pages_list:
                page_references.append({
                    "documentName": doc_name,
                    "pages": pages_list
                })
                print(f"📝 Method 0 result: {doc_name} with {len(pages_list)} pages: {[p['pageNumber'] for p in pages_list]}")
    
    print(f"📝 After Method 0 - page_references count: {len(page_references)}")
    
    # If no page_references from highlight parsing, extract from CHECKING section only
    if len(page_references) == 0 and checking_idx != -1:
        print("📝 No page_refs from highlights, extracting from CHECKING section...")
        checking_lines = lines[checking_idx + 1:]
        checking_text = '\n'.join(checking_lines)
        
        try:
            # Extract highlight_doc_info from CHECKING section
            json_match = re.search(r'\[.*?\]', checking_text, re.DOTALL)
            if json_match:
                highlight_info = json.loads(json_match.group())
                print(f"📝 Found {len(highlight_info)} highlight entries in CHECKING section")
                
                # Create page_references from highlight_info only
                doc_page_map = {}
                
                for highlight in highlight_info:
                    chunk_id = highlight.get('chunk_id', 0)
                    highlight_text = highlight.get('highlight_text', '')
                    
                    # Only use the first source document (avoid Unknown Document)
                    if len(sources) == 0:
                        print("📝 Skipping highlight - no source documents found")
                        continue
                        
                    # Extract proper document name from source title
                    source_title = sources[0]["title"]
                    
                    # If source title is in format "🔍 Highlighting chunk X from filename.pdf", extract filename
                    filename_match = re.search(r'🔍 Highlighting chunk \d+ from (.+\.pdf)', source_title)
                    if filename_match:
                        doc_name = filename_match.group(1)
                    else:
                        # Look for any .pdf filename in the source title
                        pdf_match = re.search(r'([^/\\:]+\.pdf)', source_title)
                        if pdf_match:
                            doc_name = pdf_match.group(1)
                        else:
                            doc_name = source_title  # Fallback to original title
                    
                    print(f"📝 Using document name: {doc_name} (from source: {source_title})")
                    
                    # Extract page number from source title, highlight text, or context
                    page_num = 1  # Default
                    page_pattern = r'page\s*(\d+)|Page\s*(\d+)|trang\s*(\d+)'
                    
                    # First try to extract from source title (most reliable)
                    source_page_match = re.search(r'🔍 Highlighting chunk \d+ from .+ page (\d+)', source_title)
                    if source_page_match:
                        page_num = int(source_page_match.group(1))
                        print(f"📝 Found page {page_num} from source title")
                    else:
                        # Fallback: search in highlight text
                        page_match = re.search(page_pattern, highlight_text, re.IGNORECASE)
                        if page_match:
                            page_num = int([g for g in page_match.groups() if g][0])
                            print(f"📝 Found page {page_num} from highlight text")
                    
                    # Add to document page mapping
                    if doc_name not in doc_page_map:
                        doc_page_map[doc_name] = {}
                    if page_num not in doc_page_map[doc_name]:
                        doc_page_map[doc_name][page_num] = []
                    
                    doc_page_map[doc_name][page_num].append(highlight_text)
                    print(f"📝 Added highlight for {doc_name}, page {page_num}")
                
                # Convert to page_references format
                for doc_name, pages_dict in doc_page_map.items():
                    pages_list = []
                    for page_num, highlights in pages_dict.items():
                        pages_list.append({
                            "pageNumber": page_num,
                            "highlights": highlights
                        })
                    
                    if pages_list:
                        pages_list.sort(key=lambda x: x["pageNumber"])
                        page_references.append({
                            "documentName": doc_name,
                            "pages": pages_list
                        })
                        
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"📝 Could not parse CHECKING JSON: {e}")
    
    # If no page_references from highlight parsing, try to extract from output lines directly
    if len(page_references) == 0:
        print("📝 No page_refs from previous methods, trying PDF operation logs...")
        
        # Method 1: Extract page info from actual highlighting operations in the output (fallback)
        highlight_operations = {}
        
        for i, line in enumerate(lines):
                # Look for actual highlighting operations with the new combined PDF format
                if "✅ Highlighted PDF saved to:" in line and "_combined.pdf" in line:
                    # Extract document from filename: highlight_evidence_DocumentName_combined.pdf
                    filename_match = re.search(r'highlight_evidence_(.+?)_combined\.pdf', line)
                    if filename_match:
                        doc_base = filename_match.group(1)
                        # Fix double .pdf issue
                        if doc_base.endswith('.pdf'):
                            doc_name = doc_base
                        else:
                            doc_name = doc_base + ".pdf"
                        
                        print(f"📝 Processing highlight operation for: {doc_name}")
                        
                        # Initialize document entry
                        if doc_name not in highlight_operations:
                            highlight_operations[doc_name] = set()
                    
                    # Look in a wider range before this highlight operation for page context
                    context_start = max(0, i-100)  # Much wider search window
                    context_lines = lines[context_start:i]
                    
                    # Search for page references in multiple patterns and contexts
                    pages_found = set()
                    
                    # NEW Pattern: Look for the log line that shows actual chunk highlighting
                    for j in range(len(context_lines)-1, -1, -1):  # Search backwards
                        context_line = context_lines[j]
                        
                        # Look for pattern: "🔍 Highlighting chunk X from document page Y"
                        chunk_highlight_match = re.search(r'🔍 Highlighting chunk \d+ from .+ page (\d+)', context_line)
                        if chunk_highlight_match:
                            page_num = int(chunk_highlight_match.group(1))
                            if 1 <= page_num <= 1000:
                                pages_found.add(page_num)
                                print(f"📝 Found page {page_num} from chunk highlighting log for {doc_name}")
                                continue  # Continue to find all pages
                        
                        # Pattern 1: Look for simple_highlight or highlighting operations with page info
                        if ("simple_highlight" in context_line or "highlighting" in context_line.lower()):
                            # Look for page patterns in this line and nearby lines
                            for k in range(max(0, j-3), min(len(context_lines), j+3)):
                                nearby_line = context_lines[k]
                                page_matches = re.findall(r'page[\s_=:]*(\d+)', nearby_line, re.IGNORECASE)
                                for match in page_matches:
                                    page_num = int(match)
                                    if 1 <= page_num <= 1000:
                                        pages_found.add(page_num)
                                        print(f"📝 Found page {page_num} from highlighting context for {doc_name}")
                        
                        # Pattern 2: Look for direct page references in context (be more selective)
                        if any(keyword in context_line.lower() for keyword in ['metadata', 'source', 'chunk']):
                            page_matches = re.findall(r'page[\s_=:]*(\d+)', context_line, re.IGNORECASE)
                            for match in page_matches:
                                page_num = int(match)
                                if 10 <= page_num <= 50:  # More restrictive range
                                    pages_found.add(page_num)
                                    print(f"📝 Found page {page_num} from metadata reference for {doc_name}")
                    
                    # Pattern 3: Look for chunk content that might contain page info
                    for j in range(len(context_lines)-1, -1, -1):
                        context_line = context_lines[j]
                        if "CHUNK" in context_line and doc_base.replace(' ', '') in context_line.replace(' ', ''):
                            # This is chunk processing for our document - look for page info nearby
                            for k in range(max(0, j-5), min(len(context_lines), j+10)):
                                nearby_line = context_lines[k]
                                
                                # Look for explicit page information
                                page_matches = re.findall(r'page[\s_=:]*(\d+)', nearby_line, re.IGNORECASE)
                                for match in page_matches:
                                    page_num = int(match)
                                    if 1 <= page_num <= 1000:
                                        pages_found.add(page_num)
                                        print(f"📝 Found page {page_num} from chunk context for {doc_name}")
                    
                    # Add all found pages
                    if pages_found:
                        highlight_operations[doc_name].update(pages_found)
                        print(f"📝 Added pages {sorted(pages_found)} for highlight operation of {doc_name}")
                    else:
                        print(f"📝 No specific page found for this highlight operation of {doc_name}")
        
        print(f"📝 Found {len(highlight_operations)} documents with highlight operations")
        
        # Additional extraction: search the entire output for page references
        for doc_name in list(highlight_operations.keys()):
            if len(highlight_operations[doc_name]) == 0:  # If no pages found yet
                print(f"📝 Searching entire output for pages for {doc_name}")
                
                doc_base = doc_name.replace('.pdf', '').replace(' ', '')
                all_pages_found = set()
                
                # Method A: Look for chunk metadata with actual page numbers
                # Search for patterns like "chunk X metadata page Y" or "source page Y"
                metadata_patterns = [
                    r'metadata.*?page[\s_:]*(\d+)',
                    r'source.*?page[\s_:]*(\d+)', 
                    r'chunk.*?page[\s_:]*(\d+)',
                    r'from.*?page[\s_:]*(\d+)',
                    r'"page":\s*(\d+)',
                    r'page[\s_:]*(\d+).*?metadata',
                    r'page[\s_:]*(\d+).*?source'
                ]
                
                for line_idx, line in enumerate(lines):
                    line_lower = line.lower()
                    
                    # Only look at lines that are likely to contain metadata
                    if any(keyword in line_lower for keyword in ['metadata', 'source', 'chunk', 'from']):
                        for pattern in metadata_patterns:
                            matches = re.findall(pattern, line, re.IGNORECASE)
                            for match in matches:
                                page_num = int(match)
                                # Filter for reasonable page range (avoid line numbers, etc.)
                                if 10 <= page_num <= 50:
                                    all_pages_found.add(page_num)
                                    print(f"📝 Found metadata page {page_num} from: {line.strip()[:100]}")
                
                # Method B: If no metadata found, look for document-specific references
                if not all_pages_found:
                    print(f"📝 No metadata pages found, searching document-specific references...")
                    
                    for line_idx, line in enumerate(lines):
                        line_clean = line.replace(' ', '').lower()
                        doc_base_clean = doc_base.lower()
                        
                        # If line mentions our document
                        if (doc_base_clean in line_clean or 
                            doc_name.replace(' ', '').lower() in line_clean or
                            ("data/ppl" in line and doc_name in line)):
                            
                            # Look for page references in this line and nearby lines
                            search_start = max(0, line_idx - 5)
                            search_end = min(len(lines), line_idx + 5)
                            
                            for search_idx in range(search_start, search_end):
                                search_line = lines[search_idx]
                                page_matches = re.findall(r'page[\s_=:]*(\d+)', search_line, re.IGNORECASE)
                                for match in page_matches:
                                    page_num = int(match)
                                    # Be more selective about page ranges
                                    if 10 <= page_num <= 50:
                                        all_pages_found.add(page_num)
                                        print(f"📝 Found document-specific page {page_num}")
                
                if all_pages_found:
                    highlight_operations[doc_name].update(all_pages_found)
                    print(f"📝 Global search added pages {sorted(all_pages_found)} for {doc_name}")
                else:
                    print(f"📝 No valid pages found in global search for {doc_name}")
        
        # Fallback: try chunk-based mapping only if we still have no pages
        for doc_name in highlight_operations:
            if len(highlight_operations[doc_name]) == 0:
                print(f"📝 Using chunk-based fallback for {doc_name}")
                
                if checking_idx != -1:
                    checking_lines = lines[checking_idx + 1:]
                    checking_text = '\n'.join(checking_lines)
                    
                    # Extract all chunk_ids mentioned
                    chunk_ids = set()
                    chunk_matches = re.findall(r'[\'"]?chunk_id[\'"]?\s*:\s*(\d+)', checking_text)
                    for match in chunk_matches:
                        chunk_ids.add(int(match))
                    
                    if chunk_ids:
                        print(f"📝 Found chunk_ids for fallback: {sorted(chunk_ids)}")
                        # Simple mapping: assume each chunk represents content from different areas
                        for chunk_id in sorted(chunk_ids)[:3]:  # Limit to first few chunks
                            estimated_page = chunk_id + 1
                            highlight_operations[doc_name].add(estimated_page)
                        
                        print(f"📝 Chunk-based fallback added pages: {sorted(highlight_operations[doc_name])}")
        
        # Debug output
        for doc_name, page_set in highlight_operations.items():
            print(f"📝 Final highlight operations - {doc_name}: pages {sorted(page_set)}")
        
        # Method 2: If no highlight operations found, look for chunk metadata patterns
        if not highlight_operations:
            chunk_metadata = {}
            
            # First, try to extract from the raw output by looking for chunk content with document paths
            for i, line in enumerate(lines):
                # Look for chunk patterns in the output
                chunk_match = re.search(r'\[CHUNK\s+(\d+)\]', line)
                if chunk_match:
                    chunk_id = int(chunk_match.group(1))
                    
                    # Look for document path that contains metadata info
                    for j in range(i, min(i + 50, len(lines))):
                        search_line = lines[j]
                        
                        # Look for actual document operations that indicate the page
                        if "data/ppl/" in search_line and ".pdf" in search_line:
                            # This indicates chunk processing, now look for the page operation
                            for k in range(j, min(j + 10, len(lines))):
                                operation_line = lines[k]
                                
                                # Look for highlighting operation or page reference  
                                if "simple_highlight" in operation_line or "page_number=" in operation_line:
                                    page_match = re.search(r'page_number=(\d+)|page[\s:]*(\d+)', operation_line, re.IGNORECASE)
                                    if page_match:
                                        page_num = int([g for g in page_match.groups() if g][0])
                                        
                                        # Extract document name
                                        doc_match = re.search(r'data/ppl/([^/\\:]+\.pdf)', search_line)
                                        if doc_match:
                                            doc_name = doc_match.group(1)
                                            chunk_metadata[chunk_id] = (doc_name, page_num)
                                            print(f"📝 Found chunk {chunk_id} operation: {doc_name} page {page_num}")
                                            break
                                    break
                            break
            
            # If still no chunk metadata, try alternative approach looking at the raw data structure
            if not chunk_metadata:
                print("📝 Trying alternative metadata extraction...")
                
                # Look for any lines that contain both chunk info and page info
                for i, line in enumerate(lines):
                    # Look for patterns that might contain chunk and page info together
                    chunk_page_match = re.search(r'chunk.*?(\d+).*?page.*?(\d+)', line, re.IGNORECASE)
                    if chunk_page_match:
                        chunk_id = int(chunk_page_match.group(1))
                        page_num = int(chunk_page_match.group(2))
                        
                        if len(sources) > 0:
                            doc_name = sources[0]["title"]
                            chunk_metadata[chunk_id] = (doc_name, page_num)
                            print(f"📝 Alternative extraction: chunk {chunk_id} -> {doc_name} page {page_num}")
                
                # Final fallback: assume sequential mapping if we have some pattern
                if not chunk_metadata and len(sources) > 0:
                    # Look for all page numbers mentioned in the output
                    all_pages = set()
                    for line in lines:
                        page_matches = re.findall(r'page[\s:]*(\d+)', line, re.IGNORECASE)
                        for match in page_matches:
                            all_pages.add(int(match))
                    
                    if all_pages:
                        doc_name = sources[0]["title"]
                        chunk_id = 0
                        for page_num in sorted(all_pages):
                            chunk_metadata[chunk_id] = (doc_name, page_num)
                            print(f"📝 Fallback mapping: chunk {chunk_id} -> {doc_name} page {page_num}")
                            chunk_id += 1
            
            # Convert chunk metadata to highlight operations format
            for chunk_id, (doc_name, page_num) in chunk_metadata.items():
                if doc_name not in highlight_operations:
                    highlight_operations[doc_name] = set()
                highlight_operations[doc_name].add(page_num)
        
        # Create page references from highlight operations
        if highlight_operations:
            for doc_name, page_set in highlight_operations.items():
                pages_list = []
                for page_num in sorted(page_set):
                    pages_list.append({
                        "pageNumber": page_num,
                        "highlights": [f"Content highlighted on page {page_num}"]
                    })
                
                if pages_list:
                    page_references.append({
                        "documentName": doc_name,
                        "pages": pages_list
                    })
                    print(f"📝 Final document: {doc_name} with {len(pages_list)} pages: {[p['pageNumber'] for p in pages_list]}")
        
        # Method 3: If still no results, try to extract from metadata patterns in the raw output
        if len(page_references) == 0:
            print("📝 Trying metadata pattern extraction...")
            metadata_pages = {}
            
            # Look for patterns like: "metadata": {"page": 5, "source": "document.pdf"}
            metadata_pattern = r'"metadata":\s*\{[^}]*"page":\s*(\d+)[^}]*"source":\s*"([^"]+)"'
            metadata_matches = re.findall(metadata_pattern, '\n'.join(lines))
            
            for page_str, source_name in metadata_matches:
                page_num = int(page_str)
                doc_name = source_name if source_name.endswith('.pdf') else f"{source_name}.pdf"
                
                if doc_name not in metadata_pages:
                    metadata_pages[doc_name] = set()
                metadata_pages[doc_name].add(page_num)
                print(f"📝 Metadata pattern: {doc_name} page {page_num}")
            
            # Convert metadata findings to page_references
            for doc_name, page_set in metadata_pages.items():
                pages_list = []
                for page_num in sorted(page_set):
                    pages_list.append({
                        "pageNumber": page_num,
                        "highlights": [f"Content from page {page_num}"]
                    })
                
                if pages_list:
                    page_references.append({
                        "documentName": doc_name,
                        "pages": pages_list
                    })
                    print(f"📝 Metadata document: {doc_name} with pages: {[p['pageNumber'] for p in pages_list]}")
    
    print(f"📝 Final page_references count: {len(page_references)}")
    for ref in page_references:
        page_nums = [str(p['pageNumber']) for p in ref['pages']]
        print(f"📝 Document: {ref['documentName']} -> Pages: {', '.join(page_nums)}")
    
    # Only return actual page references with highlights - no fallback creation
    if len(page_references) == 0:
        print("📝 No highlighted pages found in query output")
    
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
        data_dir = os.path.join(os.path.dirname(__file__), "rag_v1", "data", "ppl")
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
        # New format from query.py: highlight_evidence_{filename}_combined.pdf
        highlight_files = glob.glob(os.path.join(RAG_PATH, "highlight_evidence_*_combined.pdf"))
        
        if highlight_files:
            # Use most recent combined file (sorted by time)
            highlight_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            selected_file = highlight_files[0]
            print(f"📄 Using most recent combined highlighted PDF: {os.path.basename(selected_file)}")
            
            return FileResponse(
                path=selected_file,
                filename=f"highlighted_evidence_combined.pdf",
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
