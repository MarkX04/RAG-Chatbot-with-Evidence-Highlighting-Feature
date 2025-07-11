// Types for the chatbot application

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  sources?: DocumentSource[]
}

export interface DocumentSource {
  id: string
  title: string
  content: string
  url?: string
  score?: number
}

export interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
}

export interface RAGConfig {
  apiKey?: string
  model: string
  maxTokens: number
  temperature: number
  topK: number
  topP: number
}

export interface VectorDatabase {
  index: (documents: Document[]) => Promise<void>
  search: (query: string, limit?: number) => Promise<DocumentSource[]>
  delete: (id: string) => Promise<void>
}

export interface Document {
  id: string
  content: string
  metadata: Record<string, any>
}
