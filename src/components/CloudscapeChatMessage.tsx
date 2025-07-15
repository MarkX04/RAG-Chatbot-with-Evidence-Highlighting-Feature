import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Box } from '@cloudscape-design/components'
import type { Message } from '../types'

interface ChatMessageProps {
  message: Message
}

const formatTimestamp = (date: Date): string => {
  return date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const parseMessageContent = (content: string) => {
  const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex, match.index)
      })
    }

    parts.push({
      type: 'code',
      language: match[1] || 'text',
      content: match[2].trim()
    })

    lastIndex = match.index + match[0].length
  }

  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.slice(lastIndex)
    })
  }

  return parts.length > 0 ? parts : [{ type: 'text', content }]
}

export const CloudscapeChatMessage = ({ message }: ChatMessageProps) => {
  const parsedContent = parseMessageContent(message.content)
  const isUser = message.role === 'user'

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '16px',
        width: '100%'
      }}
    >
      <div
        style={{
          maxWidth: '85%',
          minWidth: '200px'
        }}
      >
        <div
          style={{
            padding: '16px',
            borderRadius: '8px',
            backgroundColor: isUser ? '#0972d3' : '#ffffff',
            color: isUser ? '#ffffff' : '#16191f',
            border: !isUser ? '1px solid #e9ebed' : 'none',
            boxShadow: !isUser ? '0 1px 4px rgba(0,0,0,0.05)' : 'none',
            lineHeight: '1.5'
          }}
        >
          {parsedContent.map((part, index) => {
            if (part.type === 'code') {
              return (
                <Box key={index} margin={{ vertical: 's' }}>
                  <div
                    style={{
                      backgroundColor: isUser ? 'rgba(255,255,255,0.1)' : '#fafbfc',
                      border: isUser ? '1px solid rgba(255,255,255,0.2)' : '1px solid #e9ebed',
                      borderRadius: '6px',
                      overflow: 'hidden'
                    }}
                  >
                    <SyntaxHighlighter
                      language={part.language}
                      style={oneLight}
                      customStyle={{
                        margin: 0,
                        padding: '16px',
                        fontSize: '13px',
                        backgroundColor: isUser ? 'rgba(255,255,255,0.05)' : '#fafbfc',
                        border: 'none',
                        color: isUser ? '#ffffff' : '#16191f'
                      }}
                      showLineNumbers={part.content.split('\n').length > 3}
                    >
                      {part.content}
                    </SyntaxHighlighter>
                  </div>
                </Box>
              )
            } else {
              return (
                <div key={index} style={{ 
                  fontSize: '14px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {part.content}
                </div>
              )
            }
          })}
          
          <div 
            style={{ 
              fontSize: '12px', 
              marginTop: '8px',
              opacity: 0.7,
              textAlign: 'right'
            }}
          >
            {formatTimestamp(message.timestamp)}
          </div>
        </div>
      </div>
    </div>
  )
}
