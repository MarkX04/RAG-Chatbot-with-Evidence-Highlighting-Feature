import { useState, useEffect, useRef } from 'react'
import {
  AppLayout,
  TopNavigation,
  Container,
  Header,
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
  
  // PDF viewer state
  const [selectedPDF, setSelectedPDF] = useState<{
    documentName: string
    pageNumber: number
    highlights: string[]
  } | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Check backend status on component mount
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
      const response = await fetch('http://localhost:3001/api/cleanup-pdfs', {
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

  // Function to navigate PDF to specific page (similar to goToPage in HTML code)
  const navigatePDFToPage = (iframeElement: HTMLIFrameElement, newUrl: string) => {
    // Set src to blank and then to desired src to prevent browser caching issues
    iframeElement.src = 'about:blank'
    setTimeout(() => {
      iframeElement.src = newUrl
    }, 100) // Set a slight delay to ensure the reload
  }

  const handlePDFPageSelect = async (documentName: string, pageNumber: number, highlights: string[]) => {
    console.log(`Opening PDF: ${documentName}, page ${pageNumber}`)
    
    // Set selected PDF info immediately for UI feedback
    setSelectedPDF({ documentName, pageNumber, highlights })
    
    // Clear current PDF URL while loading new one
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl)
      setPdfUrl(null)
    }
    
    try {
      // Show loading state by setting pdfUrl to null first
      const response = await fetch(`http://localhost:3001/api/highlighted-pdfs?page=${pageNumber}`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      
      // Add page parameter to URL for browser to jump to specific page
      const pdfUrlWithPage = `${url}#page=${pageNumber}`
      setPdfUrl(pdfUrlWithPage)
      
      // Use improved navigation function after a delay to ensure iframe is ready
      setTimeout(() => {
        const iframe = document.getElementById('pdf-viewer-iframe') as HTMLIFrameElement
        if (iframe && pdfUrlWithPage) {
          console.log(`Navigating PDF iframe to page ${pageNumber}`)
          navigatePDFToPage(iframe, pdfUrlWithPage)
        }
      }, 300)
      
    } catch (error) {
      console.error('Error loading PDF:', error)
      // Show error message or fallback
      const fallbackUrl = `http://localhost:3001/api/highlighted-pdfs?page=${pageNumber}#page=${pageNumber}`
      setPdfUrl(fallbackUrl)
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
        utilities={[{
          type: "menu-dropdown",
          iconName: "user-profile",
          items: [
            { id: "settings", text: "Settings" },
              { id: "support", text: "Support" },
              { id: "signout", text: "Sign out" }
            ]
          }
        ]}
      />
      
      <AppLayout
        navigation={<div />}
        content={
          // Two-column layout
          <div style={{ display: 'flex', gap: '16px', minHeight: '85vh' }}>
            {/* Left Column - Chat */}
            <div style={{ flex: selectedPDF ? '1' : '1', minWidth: '400px' }}>
              <div style={{ 
                height: '85vh',
                border: '1px solid #e9ebed',
                borderRadius: '8px',
                backgroundColor: '#ffffff',
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
                        📁 Upload Documents
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
                      <iframe
                        id="pdf-viewer-iframe"
                        src={pdfUrl}
                        style={{
                          width: '100%',
                          height: '100%',
                          border: 'none'
                        }}
                        title={`${selectedPDF.documentName} - Page ${selectedPDF.pageNumber} Highlights`}
                        onLoad={() => {
                          console.log('PDF iframe loaded successfully')
                        }}
                      />
                    ) : (
                      <Box textAlign="center" padding="xl">
                        <StatusIndicator type="loading">Loading PDF...</StatusIndicator>
                      </Box>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        }
        toolsHide
        navigationHide
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
