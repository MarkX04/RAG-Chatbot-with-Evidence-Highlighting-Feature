import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Box } from '@cloudscape-design/components'
import PDFPageSelector from './PDFPageSelector'
import type { Message } from '../types'

interface ChatMessageProps {
  message: Message
  onPDFPageSelect?: (documentName: string, pageNumber: number, highlights: string[]) => void
}

const formatTimestamp = (date: Date): string => {
  return date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const parseMessageContent = (content: string) => {
  // Debug: Log content to see what we're parsing
  console.log('Parsing content:', content)
  
  // Check if content contains a table (pipe-separated format)
  const hasTable = content.includes('|') && content.includes('---')
  console.log('Has table:', hasTable)
  
  if (hasTable) {
    console.log('Using table parsing')
    return parseTableContent(content)
  }
  
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

const parseTableContent = (content: string) => {
  const lines = content.split('\n')
  const parts = []
  let currentTextPart = ''
  let tableLines = []
  let inTable = false

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    
    // Check if this line is part of a table
    if (line.includes('|') && (line.includes('---') || lines[i+1]?.includes('---') || inTable)) {
      // If we have accumulated text, add it as a text part
      if (currentTextPart.trim()) {
        parts.push({
          type: 'text',
          content: currentTextPart.trim()
        })
        currentTextPart = ''
      }
      
      inTable = true
      tableLines.push(line)
      
      // Check if table ends (next line doesn't contain |)
      if (i === lines.length - 1 || !lines[i + 1]?.includes('|')) {
        parts.push({
          type: 'table',
          content: tableLines.join('\n')
        })
        tableLines = []
        inTable = false
      }
    } else {
      if (inTable) {
        // Table ended, process accumulated table lines
        parts.push({
          type: 'table',
          content: tableLines.join('\n')
        })
        tableLines = []
        inTable = false
      }
      currentTextPart += line + '\n'
    }
  }

  // Add remaining text
  if (currentTextPart.trim()) {
    parts.push({
      type: 'text',
      content: currentTextPart.trim()
    })
  }

  return parts.length > 0 ? parts : [{ type: 'text', content }]
}

const renderTable = (tableContent: string, isUser: boolean) => {
  const lines = tableContent.split('\n').filter(line => line.trim())
  if (lines.length < 2) return <div>{tableContent}</div>
  
  // Find header and separator
  let headerIndex = -1
  let separatorIndex = -1
  
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('---')) {
      separatorIndex = i
      headerIndex = i - 1
      break
    }
  }
  
  if (headerIndex === -1 || separatorIndex === -1) {
    return <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{tableContent}</div>
  }
  
  const headers = lines[headerIndex].split('|').map(h => h.trim()).filter(h => h)
  const dataRows = lines.slice(separatorIndex + 1).map(line => 
    line.split('|').map(cell => cell.trim()).filter(cell => cell)
  )
  
  return (
    <table style={{
      borderCollapse: 'collapse',
      width: '100%',
      marginTop: '8px',
      marginBottom: '8px',
      backgroundColor: isUser ? 'rgba(255,255,255,0.1)' : '#ffffff',
      border: `1px solid ${isUser ? 'rgba(255,255,255,0.2)' : '#e9ebed'}`
    }}>
      <thead>
        <tr style={{ backgroundColor: isUser ? 'rgba(255,255,255,0.1)' : '#f2f3f3' }}>
          {headers.map((header, index) => (
            <th key={index} style={{
              padding: '8px 12px',
              textAlign: 'left',
              fontWeight: 'bold',
              borderBottom: `1px solid ${isUser ? 'rgba(255,255,255,0.2)' : '#e9ebed'}`,
              color: isUser ? '#ffffff' : '#16191f',
              fontSize: '13px'
            }}>
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {dataRows.map((row, rowIndex) => (
          <tr key={rowIndex} style={{
            borderBottom: `1px solid ${isUser ? 'rgba(255,255,255,0.1)' : '#f2f3f3'}`
          }}>
            {row.map((cell, cellIndex) => (
              <td key={cellIndex} style={{
                padding: '8px 12px',
                color: isUser ? '#ffffff' : '#16191f',
                fontSize: '13px',
                fontFamily: 'monospace'
              }}>
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export const CloudscapeChatMessage = ({ message, onPDFPageSelect }: ChatMessageProps) => {
  // Debug: Log message to see page references
  console.log('=== CloudscapeChatMessage Debug ===')
  console.log('Message object:', message)
  console.log('Page references:', message.pageReferences)
  console.log('Page references type:', typeof message.pageReferences)
  console.log('Page references length:', message.pageReferences?.length)
  console.log('Sources:', message.sources)
  console.log('Message role:', message.role)
  
  // Use actual page references from backend only
  const actualPageReferences = message.pageReferences || []
  
  console.log('Using page references:', actualPageReferences)
  console.log('Should show PDF selector:', message.role !== 'user' && actualPageReferences.length > 0)
  
  const parsedContent = parseMessageContent(message.content)
  const isUser = message.role === 'user'

  const handlePageSelect = async (documentName: string, pageNumber: number, highlights: string[]) => {
    // Call parent's PDF page select handler
    console.log(`Selected: ${documentName}, page ${pageNumber}`, highlights)
    if (onPDFPageSelect) {
      onPDFPageSelect(documentName, pageNumber, highlights)
    }
  }

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
                      language={(part as any).language}
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
            } else if (part.type === 'table') {
              return (
                <Box key={index} margin={{ vertical: 's' }}>
                  <div style={{ overflowX: 'auto' }}>
                    {renderTable(part.content, isUser)}
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
          
          {/* PDF Page Selector - hiển thị thay vì Check Ref button */}
          {(() => {
            const isUser = message.role === 'user'
            const hasPageRefs = actualPageReferences && actualPageReferences.length > 0
            console.log('PDF Selector Check:', { isUser, hasPageRefs, actualPageReferences })
            
            return !isUser && hasPageRefs && (
              <PDFPageSelector 
                references={actualPageReferences}
                onPageSelect={handlePageSelect}
              />
            )
          })()}
          
          <div 
            style={{ 
              fontSize: '12px', 
              marginTop: '8px',
              opacity: 0.7,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              {formatTimestamp(message.timestamp)}
            </div>
            {/* Removed Check Ref button - PDF will be shown in right panel */}
          </div>
        </div>
      </div>
    </div>
  )
}
