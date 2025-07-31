# Chatbot RAG Application

A modern RAG (Retrieval-Augmented Generation) chatbot application built with React, TypeScript, and FastAPI, designed for AWS cloud deployment.

## 🏗️ Architecture

### Frontend
- **React 18** with TypeScript for type safety
- **AWS CloudScape** components for consistent UI
- **Vite** for fast development and optimized builds
- **PDF.js** for document viewing and highlighting
- **Environment-based configuration** for multi-stage deployment

### Backend
- **FastAPI** with Python for high-performance APIs
- **ChromaDB** for vector storage and retrieval
- **AWS Bedrock** integration for LLM and embeddings
- **PyMuPDF** for PDF processing and page extraction

### Cloud Infrastructure
- **AWS S3** for static hosting and document storage
- **AWS CloudFront** for global CDN
- **AWS ECS/Fargate** for containerized backend
- **AWS Bedrock** for AI/ML services
- **CloudFormation** for Infrastructure as Code

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- AWS CLI configured
- Docker (for backend deployment)

### Local Development

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd chatbot-rag
npm install
```

2. **Set up Python backend:**
```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment variables:**
```bash
# Copy and modify environment files
cp .env.development.example .env.development
cp .env.staging.example .env.staging
cp .env.production.example .env.production
```

4. **Start development servers:**
```bash
# Frontend (runs on http://localhost:5173)
npm run dev

# Backend (in separate terminal)
cd backend
python main.py
```

## 🌍 Environment Configuration

The application supports multiple deployment environments with automatic configuration:

### Environment Files
- `.env.development` - Local development settings
- `.env.staging` - Staging environment settings
- `.env.production` - Production environment settings

### Available Variables
```bash
VITE_API_URL=           # Backend API URL
VITE_ENVIRONMENT=       # Current environment (dev/staging/prod)
VITE_AWS_REGION=        # AWS region for services
VITE_S3_BUCKET=         # S3 bucket for documents
VITE_DEBUG_MODE=        # Enable debug logging
```

## 🏗️ Build & Deploy

### Build Commands
```bash
# Development build
npm run build:dev

# Staging build
npm run build:staging

# Production build
npm run build:prod
```

### AWS Deployment
```bash
# Deploy to staging (default)
npm run deploy

# Deploy to specific environment
npm run deploy:dev
npm run deploy:staging
npm run deploy:prod

# Or use the script directly
./scripts/deploy.sh [dev|staging|prod]
```

### Manual AWS Setup
1. **Configure AWS credentials:**
```bash
aws configure
```

2. **Deploy infrastructure:**
```bash
aws cloudformation deploy \
  --template-file aws/cloudformation.yaml \
  --stack-name chatbot-rag-prod \
  --capabilities CAPABILITY_IAM
```

3. **Build and upload frontend:**
```bash
npm run build:prod
aws s3 sync dist/ s3://your-bucket-name/
```

## 📁 Project Structure

```
├── src/
│   ├── components/          # React components
│   ├── services/           # API services
│   ├── types/              # TypeScript definitions
│   ├── utils/              # Utility functions
│   └── config/             # Environment configuration
├── backend/
│   ├── RAG-v1/            # RAG pipeline implementation
│   ├── main.py            # FastAPI application
│   └── requirements.txt   # Python dependencies
├── aws/                   # AWS CloudFormation templates
├── scripts/               # Deployment scripts
└── public/               # Static assets
```

## 🔧 Development

### Frontend Development
- Uses Vite proxy for API calls during development
- Hot module replacement for fast development
- TypeScript for type safety
- ESLint for code quality

### Backend Development
- FastAPI with automatic OpenAPI documentation
- Vector database integration with ChromaDB
- AWS services integration
- PDF processing and highlighting

### Environment Management
- Environment-specific builds and configurations
- API endpoint abstraction for deployment flexibility
- Feature flags for environment-specific functionality

## 📚 Key Features

- **Document Upload & Processing**: Support for PDF documents with text extraction
- **Vector Search**: Semantic search using embeddings and ChromaDB
- **PDF Highlighting**: Visual highlighting of relevant document sections
- **Multi-Environment Support**: Seamless deployment across dev/staging/production
- **AWS Integration**: Native AWS services integration for scalability
- **Responsive UI**: Modern interface using AWS CloudScape components

## 🐛 Troubleshooting

### Common Issues

1. **API Connection Errors**: Check environment variables and backend status
2. **PDF Rendering Issues**: Ensure PDF.js CDN is accessible
3. **Build Failures**: Verify Node.js version and dependencies
4. **AWS Deployment Issues**: Check AWS credentials and permissions

### Debug Mode
Enable debug logging by setting `VITE_DEBUG_MODE=true` in your environment file.

### Logs
- Frontend: Browser developer console
- Backend: FastAPI server logs
- AWS: CloudWatch logs for deployed services

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review AWS CloudFormation stack events for deployment issues
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
