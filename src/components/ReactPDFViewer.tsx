import React, { useState, useCallback } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { Box, Button, SpaceBetween, StatusIndicator } from '@cloudscape-design/components'

// Set up PDF.js worker with compatible version
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js`

interface ReactPDFViewerProps {
  pdfUrl: string | null
  initialPageNumber?: number
  onPageChange?: (pageNumber: number) => void
}

const ReactPDFViewer: React.FC<ReactPDFViewerProps> = ({ 
  pdfUrl, 
  initialPageNumber = 1,
  onPageChange 
}) => {
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(initialPageNumber)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    console.log('PDF loaded successfully with', numPages, 'pages')
    setNumPages(numPages)
    setLoading(false)
    setError(null)
  }, [])

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('PDF load error:', error)
    setError('Failed to load PDF with react-pdf. Click to view with browser viewer.')
    setLoading(false)
  }, [])

  const goToPage = useCallback((newPageNumber: number) => {
    if (newPageNumber >= 1 && newPageNumber <= numPages) {
      console.log(`🚀 React-PDF navigating to page ${newPageNumber} (instant!)`)
      setPageNumber(newPageNumber)
      onPageChange?.(newPageNumber)
    }
  }, [numPages, onPageChange])

  // Update page when initialPageNumber changes (from parent)
  React.useEffect(() => {
    if (initialPageNumber !== pageNumber && initialPageNumber >= 1) {
      console.log(`Updating page from parent: ${pageNumber} → ${initialPageNumber}`)
      goToPage(initialPageNumber)
    }
  }, [initialPageNumber, pageNumber, goToPage])

  if (!pdfUrl) {
    return (
      <Box textAlign="center" padding="xl">
        <StatusIndicator type="loading">Loading PDF...</StatusIndicator>
      </Box>
    )
  }

  if (error) {
    return (
      <Box textAlign="center" padding="xl">
        <StatusIndicator type="error">{error}</StatusIndicator>
        <div style={{ marginTop: '16px' }}>
          <Button
            variant="primary"
            onClick={() => {
              // Fallback to browser PDF viewer
              if (pdfUrl) {
                window.open(pdfUrl, '_blank')
              }
            }}
          >
            Open in Browser PDF Viewer
          </Button>
        </div>
      </Box>
    )
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden'
    }}>
      {/* Navigation Controls */}
      <div style={{ 
        padding: '8px', 
        borderBottom: '1px solid #e9ebed',
        backgroundColor: '#fafbfc'
      }}>
        <SpaceBetween direction="horizontal" size="s">
          <Button
            variant="normal"
            iconName="angle-left"
            disabled={pageNumber <= 1 || loading}
            onClick={() => goToPage(pageNumber - 1)}
          >
            Previous
          </Button>
          
          <Box textAlign="center">
            <span style={{ fontSize: '14px' }}>
              Page {pageNumber} of {numPages || '...'}
            </span>
          </Box>
          
          <Button
            variant="normal"
            iconName="angle-right"
            disabled={pageNumber >= numPages || loading}
            onClick={() => goToPage(pageNumber + 1)}
          >
            Next
          </Button>
        </SpaceBetween>
      </div>

      {/* PDF Content */}
      <div style={{ 
        flex: 1, 
        overflow: 'auto',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        padding: '16px',
        backgroundColor: '#f5f5f5'
      }}>
        {loading && (
          <StatusIndicator type="loading">Loading PDF...</StatusIndicator>
        )}
        
        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading=""
        >
          <Page
            pageNumber={pageNumber}
            scale={1.2}
            renderTextLayer={false}
            renderAnnotationLayer={false}
            className="pdf-page"
          />
        </Document>
      </div>
    </div>
  )
}

export default ReactPDFViewer
