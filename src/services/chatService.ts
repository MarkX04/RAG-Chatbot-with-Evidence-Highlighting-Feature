import type { Message, DocumentSource, PageReference } from '../types'
import { API_ENDPOINTS } from '../config/environment'

interface ChatConfig {
  model: string
  dataSource: string
}

export class ChatService {
  private apiKey: string | undefined

  constructor(apiKey?: string) {
    this.apiKey = apiKey
  }

  /**
   * Check if backend server is running and RAG is available
   */
  async healthCheck(): Promise<{
    status: string
    vectorDbReady: boolean
    ragAvailable: boolean
  }> {
    try {
      const response = await fetch(API_ENDPOINTS.HEALTH)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      return {
        status: data.status,
        vectorDbReady: data.vector_db_ready,
        ragAvailable: data.rag_available
      }
    } catch (error) {
      console.error('Backend health check failed:', error)
      return {
        status: 'error',
        vectorDbReady: false,
        ragAvailable: false
      }
    }
  }

  async sendMessage(
    message: string, 
    conversationHistory: Message[], 
    config?: ChatConfig
  ): Promise<{
    response: string
    sources?: DocumentSource[]
    highlighted_pdfs?: string[]
    page_references?: PageReference[]
  }> {

    try {
      // First check if backend is available
      const health = await this.healthCheck()
      
      if (health.status === 'error') {
        return {
          response: `❌ Backend server is not available. Please make sure the Python backend is running on port 3001.\n\nTo start the backend:\n1. cd backend\n2. ./setup.sh (first time only)\n3. ./run.sh`,
          sources: []
        }
      }

      if (!health.ragAvailable) {
        return {
          response: `⚠️ RAG functionality is not available. Please check backend configuration and ensure all dependencies are installed.\n\nMessage: "${message}"`,
          sources: []
        }
      }

      if (!health.vectorDbReady) {
        return {
          response: `⚠️ Knowledge base is not ready. Please upload PDF documents first to enable RAG functionality.\n\nYour question: "${message}"\n\nTo upload documents: Use the document upload feature or place PDF files in RAG-v1/data/ppl/ directory.`,
          sources: []
        }
      }

      const response = await fetch(API_ENDPOINTS.CHAT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({
          message,
          history: conversationHistory.slice(-10),
          model: config?.model || 'anthropic.claude-v3-sonnet',
          dataSource: config?.dataSource || 'no-workspace'
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return {
        response: data.response,
        sources: data.sources || [],
        highlighted_pdfs: data.highlighted_pdfs || [],
        page_references: data.page_references || []
      }
    } catch (error) {
      console.error('Error sending message:', error)
      
      return {
        response: `❌ Error connecting to RAG backend: ${error instanceof Error ? error.message : 'Unknown error'}\n\nYour message: "${message}"\n\nPlease ensure:\n1. Backend server is running (cd backend && ./run.sh)\n2. AWS credentials are configured\n3. Vector database is initialized`,
        sources: []
      }
    }
  }

  async uploadDocument(file: File): Promise<{ success: boolean; documentId?: string }> {
    try {
      const formData = new FormData()
      formData.append('file', file)  // Changed from 'document' to 'file'

      const response = await fetch(API_ENDPOINTS.UPLOAD, {
        method: 'POST',
        headers: {
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: formData
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return { success: true, documentId: data.documentId }
    } catch (error) {
      console.error('Error uploading document:', error)
      return { success: false }
    }
  }

  async searchDocuments(query: string, limit = 5): Promise<DocumentSource[]> {
    try {
      const response = await fetch(`${API_ENDPOINTS.SEARCH}?q=${encodeURIComponent(query)}&limit=${limit}`, {
        headers: {
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data.documents || []
    } catch (error) {
      console.error('Error searching documents:', error)
      return []
    }
  }
}

export const chatService = new ChatService()
