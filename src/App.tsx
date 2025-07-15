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
  StatusIndicator,
  Select
} from '@cloudscape-design/components'
import type { SelectProps } from '@cloudscape-design/components'
import type { Message } from './types'
import { generateMessageId, isValidMessage } from './utils/helpers'
import { chatService } from './services/chatService'
import { CloudscapeChatMessage } from './components/CloudscapeChatMessage'
import aws from './assets/aws.png'

const APP_CONFIG = {
  models: [
    { value: 'amazon.FalconLite', label: 'amazon.FalconLite' },
    { value: 'anthropic.claude-v2', label: 'anthropic.claude-v2' },
    { value: 'anthropic.claude-v3-sonnet', label: 'anthropic.claude-v3-sonnet' },
    { value: 'anthropic.claude-v3-haiku', label: 'anthropic.claude-v3-haiku' },
    { value: 'amazon.titan-text-express-v1', label: 'amazon.titan-text-express-v1' }
  ],
  dataSources: [
    { value: 'no-workspace', label: 'No workspace (RAG data source)' },
    { value: 'aws-docs', label: 'AWS Documentation' },
    { value: 'custom-kb', label: 'Custom Knowledge Base' }
  ],
  defaultModel: 'amazon.FalconLite',
  defaultDataSource: 'no-workspace'
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState<SelectProps.Option | null>({ 
    value: APP_CONFIG.defaultModel, 
    label: APP_CONFIG.defaultModel 
  })
  const [selectedSource, setSelectedSource] = useState<SelectProps.Option | null>({ 
    value: APP_CONFIG.defaultDataSource, 
    label: APP_CONFIG.dataSources.find(ds => ds.value === APP_CONFIG.defaultDataSource)?.label || APP_CONFIG.defaultDataSource
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

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
          model: selectedModel?.value || APP_CONFIG.defaultModel,
          dataSource: selectedSource?.value || APP_CONFIG.defaultDataSource
        }
      )
      
      const botMessage: Message = {
        id: generateMessageId(),
        content: response.response,
        role: 'assistant',
        timestamp: new Date(),
        sources: response.sources
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
          <Container>
            <SpaceBetween direction="vertical" size="l">
              <Header
                variant="h1"
                description="Retrieval-Augmented Generation Assistant powered by AWS"
              >
                AWS GenAI Chatbot
              </Header>

              <Box>
                <div style={{ 
                  height: '500px', 
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
                          <div style={{ fontSize: '48px' }}>🤖</div>
                          <TextContent>
                            <h3>Welcome to AWS GenAI Chatbot</h3>
                            <p>Start a conversation by typing your question below.</p>
                          </TextContent>
                        </SpaceBetween>
                      </Box>
                    ) : (
                      <>
                        {messages.map((message) => (
                          <CloudscapeChatMessage key={message.id} message={message} />
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
                      
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <div style={{ flex: 1 }}>
                          <Select
                            selectedOption={selectedModel}
                            onChange={(event) => setSelectedModel(event.detail.selectedOption)}
                            options={APP_CONFIG.models}
                            placeholder="Select model"
                          />
                        </div>
                        <div style={{ flex: 1 }}>
                          <Select
                            selectedOption={selectedSource}
                            onChange={(event) => setSelectedSource(event.detail.selectedOption)}
                            options={APP_CONFIG.dataSources}
                            placeholder="Select data source"
                          />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <StatusIndicator type="success">Connected</StatusIndicator>
                        </div>
                      </div>
                    </SpaceBetween>
                  </div>
                </div>
              </Box>
            </SpaceBetween>
          </Container>
        }
        toolsHide
        navigationHide
      />
    </div>
  )
}

export default App
