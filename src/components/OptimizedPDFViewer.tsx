import React, { useState, useEffect, useRef } from 'react'
import { Box, Button, SpaceBetween, StatusIndicator } from '@cloudscape-design/components'

interface OptimizedPDFViewerProps {
  pdfUrl: string | null
  initialPageNumber?: number
  onPageChange?: (pageNumber: number) => void
}

const OptimizedPDFViewer: React.FC<OptimizedPDFViewerProps> = ({ 
  pdfUrl, 
  initialPageNumber = 1,
  onPageChange 
}) => {
  const [currentPage, setCurrentPage] = useState<number>(initialPageNumber)
  const [loading, setLoading] = useState<boolean>(true)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [iframeKey, setIframeKey] = useState<number>(0)

  // Force reload iframe when page changes
  const navigateToPage = (pageNumber: number) => {
    console.log(`Navigating to page ${pageNumber}`)
    setCurrentPage(pageNumber)
    setLoading(true)
    setIframeKey(prev => prev + 1) // Force iframe reload
    onPageChange?.(pageNumber)
  }

  // Update when parent changes page
  useEffect(() => {
    if (initialPageNumber !== currentPage && initialPageNumber >= 1) {
      console.log(`Parent requested page change: ${currentPage} → ${initialPageNumber}`)
      navigateToPage(initialPageNumber)
    }
  }, [initialPageNumber, currentPage])

  const handleIframeLoad = () => {
    setLoading(false)
    console.log(`PDF loaded - Page ${currentPage}`)
  }

  if (!pdfUrl) {
    return (
      <Box textAlign="center" padding="xl">
        <StatusIndicator type="loading">Loading PDF...</StatusIndicator>
      </Box>
    )
  }

  const pdfSrcWithPage = `${pdfUrl}#page=${currentPage}&toolbar=1&navpanes=1&scrollbar=1&zoom=page-width`

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden'
    }}>
      {/* Navigation Controls */}
      <div style={{ 
        padding: '12px', 
        borderBottom: '1px solid #e9ebed',
        backgroundColor: '#fafbfc'
      }}>
        <SpaceBetween direction="horizontal" size="s">
          <Button
            variant="normal"
            iconName="angle-left"
            disabled={currentPage <= 1}
            onClick={() => navigateToPage(Math.max(1, currentPage - 1))}
          >
            Previous Page
          </Button>
          
          <Box textAlign="center">
            <span style={{ fontSize: '14px', fontWeight: 'bold' }}>
              Page {currentPage}
            </span>
            <div style={{ fontSize: '12px', color: '#5f6b7a', marginTop: '2px' }}>
              PDF navigation with optimized loading
            </div>
          </Box>
          
          <Button
            variant="normal"
            iconName="angle-right"
            onClick={() => navigateToPage(currentPage + 1)}
          >
            Next Page
          </Button>
        </SpaceBetween>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div style={{ 
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 10,
          background: 'rgba(255,255,255,0.9)',
          padding: '20px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}>
          <StatusIndicator type="loading">Loading page {currentPage}...</StatusIndicator>
        </div>
      )}

      {/* PDF Content */}
      <div style={{ 
        flex: 1, 
        overflow: 'hidden',
        position: 'relative'
      }}>
        <iframe
          key={iframeKey}
          ref={iframeRef}
          src={pdfSrcWithPage}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            borderRadius: '0 0 4px 4px'
          }}
          title={`PDF - Page ${currentPage}`}
          onLoad={handleIframeLoad}
        />
      </div>
    </div>
  )
}

export default OptimizedPDFViewer
