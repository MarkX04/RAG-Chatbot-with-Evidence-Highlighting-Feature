# RAG Chatbot with Evidence Highlighting Feature

## Overview
In this workshop, we will build a chatbox web application with RAG functionality along with an evidence highlighting feature directly on a PDF file. We will also explore the basics of large language models, the mechanism and principles of a RAG chatbox, and the algorithm for the evidence highlighting feature.

## Key Features

- **Web UI and API Access**: Modern React interface and API endpoints for integration
- **AWS Bedrock Integration**: Uses Claude 3.5 Sonnet for intelligent responses
- **Document Processing**: Upload and index PDF documents for knowledge base
- **Vector Database**: ChromaDB for efficient document retrieval
- **PDF Highlighting**: Automatic highlighting of relevant document sections
- **Real-time Chat**: Interactive chat interface with source references
- **Page-specific Navigation**: Jump directly to relevant pages in source documents

## Getting Started
### Prerequisites

- **Node.js** (v18 or higher)
- **Python** (v3.8 or higher)
- **AWS Account** with Bedrock access
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/MarkX04/RAG-Chatbot-with-Evidence-Highlighting-Feature
cd chatbot-rag
```

### 2. Environment Setup

#### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Configure AWS credentials (one of the following methods):
   - AWS CLI: `aws configure`
   - Environment variables:
     ```bash
     export AWS_ACCESS_KEY_ID=your_access_key
     export AWS_SECRET_ACCESS_KEY=your_secret_key
     export AWS_DEFAULT_REGION=us-east-1
     ```
   - IAM roles (if running on EC2)

#### Frontend Setup

1. Navigate to the project root:
```bash
cd ..  # Back to project root
```

2. Install Node.js dependencies:
```bash
npm install
```

### 3. Running the Application

You can run the application using VS Code tasks or manually:

#### Option 1: Using VS Code Tasks (Recommended)

1. **Start Backend Server**: Press `Cmd+Shift+P` (macOS) and select "Tasks: Run Task" → "Start Backend Server"
2. **Start Development Server**: Press `Cmd+Shift+P` and select "Tasks: Run Task" → "Start Development Server"

#### Option 2: Manual Setup

**Start the Backend:**
```bash
cd backend
source venv/bin/activate
python main.py
```

The backend will start on `http://localhost:3001`

**Start the Frontend:**
In a new terminal:
```bash
npm run dev
```

The frontend will start on `http://localhost:5173`

### 4. Initial Setup

1. Open your browser and go to `http://localhost:5173`
2. Click "📁 Upload Documents" to add PDF files to your knowledge base
3. Wait for documents to be processed (check the status indicator)
4. Start asking questions about your documents!

## Usage

### Uploading Documents

1. Click the "📁 Upload Documents" button
2. Select one or more PDF files
3. Wait for processing to complete
4. The status indicator will show "RAG Ready" when done

### Asking Questions

1. Type your question in the chat input
2. Press Enter or click "Send"
3. The AI will respond with relevant information from your documents
4. Click on page reference buttons to view specific document pages

### Viewing Document References

- **Page Buttons**: Click to jump to specific pages in source documents
- **PDF Viewer**: Opens on the right side when you click a page reference
- **Highlighting**: Relevant text sections are automatically highlighted

## Development

### Project Structure

```
chatbot-rag/
├── src/                           # React frontend source
│   ├── components/                # UI components
│   │   ├── CanvasPDFViewer.tsx   # Canvas-based PDF viewer
│   │   ├── CloudscapeChatMessage.tsx # Chat message components
│   │   ├── DocumentUploadModal.tsx   # Document upload interface
│   │   ├── PDFPageSelector.tsx       # Page selection component
│   ├── services/                  # API services
│   │   └── chatService.ts         # Chat API integration
│   ├── types/                     # TypeScript types
│   │   └── index.ts              # Type definitions
│   ├── utils/                     # Utility functions
│   │   └── helpers.ts            # Helper functions
│   └── assets/                    # Static assets
├── backend/                       # Python backend
│   ├── main.py                   # FastAPI application
│   ├── requirements.txt          # Python dependencies
│   ├── rag_v1/                   # RAG implementation
│   │   ├── create_db.py         # Vector database creation
│   │   ├── query.py             # Query processing
│   │   ├── chroma/              # ChromaDB storage
│   │   └── data/                # Document storage
```

### Key Technologies

- **Frontend**: React 19, TypeScript, Vite, AWS Cloudscape Design
- **Backend**: FastAPI, LangChain, ChromaDB, PyMuPDF
- **AI/ML**: AWS Bedrock (Claude 3.5 Sonnet), Cohere Embeddings

### API Endpoints

- `GET /health` - Backend health check
- `POST /api/chat` - Send chat messages
- `POST /api/documents/upload` - Upload documents
- `GET /api/highlighted-pdfs` - Get highlighted PDF files
- `DELETE /api/cleanup-pdfs` - Clean up temporary files

## Configuration

### Available Tasks

The project includes VS Code tasks for easy development:

- **Start Development Server**: Runs `npm run dev` for the frontend
- **Start Backend Server**: Activates virtual environment and runs the Python backend

### Environment Variables

Create environment files as needed:

**Backend (.env in rag_v1 folder):**
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Google API (for fallback)
GOOGLE_API_KEY=your_google_api_key

# Vector Database
CHROMA_PATH=chroma
DATA_PATH=data
```

**Frontend (.env in root folder):**
```bash
# API Configuration
VITE_API_URL=http://localhost:3001/api

# App Configuration
VITE_APP_NAME=RAG Chatbot
VITE_MAX_MESSAGE_LENGTH=4000
```

## Deployment

For production deployment, please switch to the `deploy` branch which contains optimized configuration and deployment instructions:

```bash
git checkout deploy
```

Then follow the README instructions in the deploy branch for production setup, Docker configuration, and cloud deployment options.

## Documentation

For complete documentation, visit our workshop: [Working with Retrieval-Augmented Generation with Evidence Highlighting Feature](https://markx04.github.io/rag-chatbot-workshop/)

## Troubleshooting

### Common Issues

1. **Backend not starting**:
   - Check Python dependencies: `pip install -r requirements.txt`
   - Verify AWS credentials are configured
   - Ensure port 3001 is available

2. **Frontend build errors**:
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Check Node.js version: `node --version` (should be 18+)

3. **PDF upload fails**:
   - Check backend logs for errors
   - Ensure `backend/data` and `backend/rag_v1/data` directories exist
   - Verify file permissions

4. **AWS Bedrock errors**:
   - Verify AWS credentials and region
   - Check Bedrock service availability in your region
   - Ensure your account has Bedrock access

### Debug Mode

Enable debug logging by setting environment variables:

```bash
# Backend debug
export PYTHONPATH=$PYTHONPATH:./backend
export DEBUG=1

# Frontend debug
export VITE_DEBUG=true
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---