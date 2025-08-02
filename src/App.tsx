import { useState, useEffect, useRef } from 'react'
import {
  AppLayout,
  TopNavigation,
  SpaceBetween,
  Input,
  Button,
  Box,
  TextContent,
  StatusIndicator
} from '@cloudscape-design/components'
import type { Message } from './types'
import { generateMessageId, isValidMessage } from './utils/helpers'
import { chatService } from './services/chatService'
import { CloudscapeChatMessage } from './components/CloudscapeChatMessage'
import { DocumentUploadModal } from './components/DocumentUploadModal'
import CanvasPDFViewer from './components/CanvasPDFViewer'
import { API_ENDPOINTS } from './config/environment'
import aws from './assets/aws.png'

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [backendStatus, setBackendStatus] = useState<{
    status: string
    vectorDbReady: boolean
    ragAvailable: boolean
  }>({ status: 'unknown', vectorDbReady: false, ragAvailable: false })
  
  const [selectedPDF, setSelectedPDF] = useState<{
    documentName: string
    pageNumber: number
    highlights: string[]
  } | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    checkBackendStatus()
  }, [])
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const checkBackendStatus = async () => {
    const status = await chatService.healthCheck()
    setBackendStatus(status)
    
    // Clean up PDF files on page load/reload
    try {
      const response = await fetch(API_ENDPOINTS.CLEANUP_PDFS, {
        method: 'DELETE'
      })
      if (response.ok) {
        const data = await response.json()
        console.log('PDF cleanup result:', data)
      }
    } catch (error) {
      console.log('PDF cleanup skipped (backend not available):', error)
    }
  }

  const handleUploadSuccess = () => {
    // Refresh backend status after successful upload
    checkBackendStatus()
  }

  const handleSendMessage = async () => {
    if (!isValidMessage(inputValue) || isLoading) return

    const userMessage: Message = {
      id: generateMessageId(),
      content: inputValue.trim(),
      role: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await chatService.sendMessage(
        userMessage.content, 
        messages,
        {
          model: 'anthropic.claude-v3-sonnet',
          dataSource: 'no-workspace'
        }
      )
      
      const botMessage: Message = {
        id: generateMessageId(),
        content: response.response,
        role: 'assistant',
        timestamp: new Date(),
        sources: response.sources,
        pageReferences: response.page_references
      }
      
      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      console.error('Error getting response:', error)
      const errorMessage: Message = {
        id: generateMessageId(),
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        role: 'assistant',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handlePDFPageSelect = async (documentName: string, pageNumber: number, highlights: string[]) => {
    console.log(`Opening PDF: ${documentName}, page ${pageNumber}`)
    console.log('Current selectedPDF:', selectedPDF)
    console.log('Current pdfUrl:', pdfUrl)
    
    // Check if same document BEFORE updating state
    const isSameDocument = pdfUrl && selectedPDF?.documentName === documentName
    
    console.log('🔧 Setting selectedPDF state...')
    setSelectedPDF({ documentName, pageNumber, highlights })
    
    if (isSameDocument) {
      console.log(`✨ Same document - ReactPDFViewer will navigate instantly to page ${pageNumber}`)
      return 
    }
    
    console.log(`Loading new document: ${documentName}`)
    console.log('🔧 Checking if need to revoke existing URL...')
    
    if (pdfUrl) {
      console.log('Revoking existing PDF URL:', pdfUrl)
      URL.revokeObjectURL(pdfUrl)
      setPdfUrl(null)
    }
    
    console.log('Starting PDF fetch process...')
    
    try {
      console.log('Fetching PDF from API...')
      const response = await fetch(`${API_ENDPOINTS.HIGHLIGHTED_PDFS}?page=${pageNumber}`)

      console.log('API Response status:', response.status)
      console.log('API Response ok:', response.ok)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      console.log('Converting response to blob...')
      const blob = await response.blob()
      console.log('Blob size:', blob.size, 'bytes')

      const url = URL.createObjectURL(blob)
      console.log('Created object URL:', url)
      
      setPdfUrl(url)
      console.log('PDF URL set successfully')

    } catch (error) {
      console.error('Error loading PDF:', error)
      setPdfUrl(null)
    }
  }

  return (
    <div id="app" style={{ height: '100vh' }}>
      <TopNavigation
        identity={{
          href: "#",
          logo: {
            src: aws,
            alt: "AWS"
          }
        }}
      />
      
      <AppLayout
        navigationHide
        toolsHide
        content={
          // Full screen two-column layout
          <div style={{ display: 'flex', gap: '12px', height: 'calc(100vh - 60px)' }}>
            {/* Left Column - Chat */}
            <div style={{ 
              flex: selectedPDF ? '0 0 45%' : '1', 
              minWidth: selectedPDF ? '500px' : '600px',
              maxWidth: selectedPDF ? '45%' : 'none'
            }}>
              <div style={{ 
                height: '100%',
                border: '1px solid #e9ebed',
                borderRadius: '8px',
                backgroundColor: 'white',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div style={{ 
                  flex: 1, 
                  padding: '16px', 
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column'
                }}>
                  {messages.length === 0 ? (
                    <Box textAlign="center" padding="xxl">
                      <SpaceBetween direction="vertical" size="m">
                        <div style={{ 
                          textAlign: "center",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "center",
                          alignItems: "center",
                          height: "100%",
                          minHeight: "300px"
                        }}>
                          <TextContent>
                            <h3 style={{ margin: "0 0 16px 0", fontSize: "24px" }}>Welcome to AWS GenAI Chatbot</h3>
                            <p style={{ margin: "0", fontSize: "16px", color: "#5f6b7a" }}>Start a conversation by typing your question below.</p>
                          </TextContent>
                        </div>
                      </SpaceBetween>
                    </Box>
                  ) : (
                    <>
                      {messages.map((message) => (
                        <CloudscapeChatMessage 
                          key={message.id} 
                          message={message} 
                          onPDFPageSelect={handlePDFPageSelect}
                        />
                      ))}
                      {isLoading && (
                        <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '16px' }}>
                          <div
                            style={{
                              padding: '16px',
                              borderRadius: '8px',
                              backgroundColor: '#ffffff',
                              border: '1px solid #e9ebed',
                              boxShadow: '0 1px 4px rgba(0,0,0,0.05)'
                            }}
                          >
                            <StatusIndicator type="loading">Thinking...</StatusIndicator>
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </>
                  )}
                </div>

                <div style={{ 
                  padding: '16px', 
                  borderTop: '1px solid #e9ebed',
                  backgroundColor: '#fafbfc'
                }}>
                  <SpaceBetween direction="vertical" size="s">
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
                      <div style={{ flex: 1 }}>
                        <Input
                          value={inputValue}
                          onChange={(event) => setInputValue(event.detail.value)}
                          placeholder="Send a message"
                          disabled={isLoading}
                          onKeyDown={(event) => {
                            if (event.detail.key === 'Enter') {
                              handleSendMessage()
                            }
                          }}
                        />
                      </div>
                      <Button
                        variant="primary"
                        disabled={!inputValue.trim() || isLoading}
                        onClick={handleSendMessage}
                      >
                        Send
                      </Button>
                    </div>
                    
                    <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '8px' }}>
                      <Button
                        variant="normal"
                        onClick={() => setIsUploadModalOpen(true)}
                      >
                        Upload Documents
                      </Button>
                      <StatusIndicator 
                        type={backendStatus.status === 'healthy' ? 'success' : 'error'}
                      >
                        {backendStatus.ragAvailable ? 
                          (backendStatus.vectorDbReady ? 'RAG Ready' : 'Upload Docs') : 
                          'Backend Offline'
                        }
                      </StatusIndicator>
                    </div>
                  </SpaceBetween>
                </div>
              </div>
            </div>
            
            {/* Right Column - PDF Viewer */}
            {selectedPDF && (
              <div style={{ flex: '1', minWidth: '400px' }}>
                <div style={{
                  height: '85vh',
                  border: '1px solid #e9ebed',
                  borderRadius: '8px',
                  backgroundColor: '#ffffff',
                  display: 'flex',
                  flexDirection: 'column'
                }}>
                  <div style={{
                    padding: '16px',
                    borderBottom: '1px solid #e9ebed',
                    backgroundColor: '#fafbfc'
                  }}>
                    <SpaceBetween direction="horizontal" size="s">
                      <div>
                        <strong>{selectedPDF.documentName}</strong> - Page {selectedPDF.pageNumber}
                      </div>
                      <Button
                        variant="icon"
                        iconName="close"
                        onClick={() => {
                          setSelectedPDF(null)
                          if (pdfUrl) {
                            URL.revokeObjectURL(pdfUrl)
                            setPdfUrl(null)
                          }
                        }}
                      />
                    </SpaceBetween>
                    {selectedPDF.highlights.length > 0 && (
                      <div style={{ marginTop: '8px', fontSize: '12px', color: '#5f6b7a' }}>
                        Highlights: {selectedPDF.highlights.join(', ')}
                      </div>
                    )}
                  </div>
                  
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    {pdfUrl ? (
                      <>
                        {console.log('Rendering CanvasPDFViewer with pdfUrl:', pdfUrl)}
                        <CanvasPDFViewer 
                          pdfUrl={pdfUrl}
                          initialPageNumber={selectedPDF.pageNumber + 1}
                          onPageChange={(newPage) => {
                            console.log(`Canvas PDF page changed: ${newPage}`)
                            setSelectedPDF(prev => prev ? { 
                              ...prev, 
                              pageNumber: newPage - 1 
                            } : null)
                          }}
                        />
                      </>
                    ) : (
                      <>
                        {console.log('No pdfUrl - showing loading...')}
                        <Box textAlign="center" padding="xl">
                          <StatusIndicator type="loading">Loading PDF...</StatusIndicator>
                        </Box>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        }
      />

      <DocumentUploadModal
        visible={isUploadModalOpen}
        onDismiss={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  )
}

export default App
