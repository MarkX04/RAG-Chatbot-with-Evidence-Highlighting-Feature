// API service for RAG chatbot (placeholder implementation)

import type { Message, DocumentSource } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api'

export class ChatService {
  private apiKey: string | undefined

  constructor(apiKey?: string) {
    this.apiKey = apiKey
  }

  async sendMessage(message: string, conversationHistory: Message[]): Promise<{
    response: string
    sources: DocumentSource[]
  }> {
    // This is a placeholder implementation
    // In a real app, this would call your RAG backend
    
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({
          message,
          history: conversationHistory.slice(-10) // Send last 10 messages for context
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return {
        response: data.response,
        sources: data.sources || []
      }
    } catch (error) {
      console.error('Error sending message:', error)
      
      // Fallback response for development
      return {
        response: `I received your message: "${message}". This is a placeholder response. In a real implementation, this would query a knowledge base and generate a contextual response using RAG.`,
        sources: []
      }
    }
  }

  async uploadDocument(file: File): Promise<{ success: boolean; documentId?: string }> {
    try {
      const formData = new FormData()
      formData.append('document', file)

      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
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
      const response = await fetch(`${API_BASE_URL}/documents/search?q=${encodeURIComponent(query)}&limit=${limit}`, {
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
