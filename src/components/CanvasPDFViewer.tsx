import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Button, SpaceBetween, Box, StatusIndicator } from '@cloudscape-design/components'

// Import PDF.js
declare global {
  interface Window {
    pdfjsLib: any;
  }
}

interface CanvasPDFViewerProps {
  pdfUrl: string | null
  initialPageNumber?: number
  onPageChange?: (pageNumber: number) => void
}

const CanvasPDFViewer: React.FC<CanvasPDFViewerProps> = ({
  pdfUrl,
  initialPageNumber = 1,
  onPageChange
}) => {
  const [pdfDoc, setPdfDoc] = useState<any>(null)
  const [currentPage, setCurrentPage] = useState<number>(initialPageNumber)
  const [totalPages, setTotalPages] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [zoomLevel, setZoomLevel] = useState<number>(0.65)
  const [pdfjsReady, setPdfjsReady] = useState<boolean>(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const renderTaskRef = useRef<any>(null)

  // Check if PDF.js is ready
  useEffect(() => {
    const checkPDFJS = () => {
      if (window.pdfjsLib && window.pdfjsLib.getDocument) {
        console.log('✅ PDF.js is ready')
        setPdfjsReady(true)
        return
      }
      
      setTimeout(checkPDFJS, 100)
    }
    
    checkPDFJS()
  }, [])

  // Load PDF document
  useEffect(() => {
    console.log('🔧 CanvasPDFViewer useEffect triggered')
    console.log('📄 pdfUrl:', pdfUrl)
    console.log('📚 pdfjsReady:', pdfjsReady)
    
    if (!pdfUrl || !pdfjsReady) {
      console.log('❌ Cannot load PDF - missing URL or PDF.js not ready')
      setPdfDoc(null)
      setLoading(false)
      return
    }

    const loadPDF = async () => {
      try {
        setLoading(true)
        setError(null)
        
        console.log('🔄 Loading PDF with PDF.js...')
        const loadingTask = window.pdfjsLib.getDocument(pdfUrl)
        const pdf = await loadingTask.promise
        
        console.log(`✅ PDF loaded successfully with ${pdf.numPages} pages`)
        
        setPdfDoc(pdf)
        setTotalPages(pdf.numPages)
        setLoading(false)
        
      } catch (err) {
        console.error('❌ PDF load error:', err)
        setError('Failed to load PDF document')
        setLoading(false)
      }
    }

    loadPDF()
  }, [pdfUrl, pdfjsReady])

  // Render current page to canvas
  const renderPage = useCallback(async () => {
    if (!pdfDoc || !canvasRef.current || currentPage < 1 || currentPage > totalPages) {
      return
    }

    try {
      // Cancel previous render task if exists
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel()
        renderTaskRef.current = null
      }

      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      console.log(`🎨 Rendering page ${currentPage}...`)
      
      // Clear canvas first to prevent conflicts
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Get page
      const page = await pdfDoc.getPage(currentPage)
      
      // Calculate scale for high-quality, large rendering
      const container = containerRef.current
      if (!container) return
      
      // Use maximum available space
      const containerWidth = container.clientWidth - 16
      const containerHeight = container.clientHeight - 60
      
      // Get natural viewport
      const viewport = page.getViewport({ scale: 1 })
      
      // Calculate scale for maximum readability
      const scaleToFitWidth = containerWidth / viewport.width
      const scaleToFitHeight = containerHeight / viewport.height
      
      // Prefer larger scale for better readability, min 1.5x
      const fitScale = Math.min(scaleToFitWidth, scaleToFitHeight)
      const scale = Math.max(fitScale, zoomLevel) // Use zoom level

      const scaledViewport = page.getViewport({ scale })
      
      // High-DPI canvas rendering for crisp display
      const devicePixelRatio = window.devicePixelRatio || 1
      const outputScale = devicePixelRatio
      
      // Set physical canvas size (high resolution)
      canvas.width = Math.floor(scaledViewport.width * outputScale)
      canvas.height = Math.floor(scaledViewport.height * outputScale)
      
      // Set display size (what user sees)
      canvas.style.width = `${scaledViewport.width}px`
      canvas.style.height = `${scaledViewport.height}px`
      
      // Scale the drawing context to match device pixel ratio
      ctx.scale(outputScale, outputScale)
      
      // Render page with task management
      const renderContext = {
        canvasContext: ctx,
        viewport: scaledViewport
      }
      
      // Store render task reference
      renderTaskRef.current = page.render(renderContext)
      await renderTaskRef.current.promise
      renderTaskRef.current = null
      console.log(`✅ Page ${currentPage} rendered successfully`)
      
    } catch (err: any) {
      if (err.name === 'RenderingCancelledException') {
        console.log(`🔄 Render cancelled for page ${currentPage}`)
      } else {
        console.error('Error rendering page:', err)
        setError(`Failed to render page ${currentPage}`)
      }
    }
  }, [pdfDoc, currentPage, totalPages, zoomLevel])

  // Render page when page changes
  useEffect(() => {
    if (pdfDoc && !loading) {
      renderPage()
    }
  }, [pdfDoc, loading, renderPage])

  // Update page from parent
  useEffect(() => {
    if (initialPageNumber !== currentPage && initialPageNumber >= 1 && initialPageNumber <= totalPages) {
      console.log(`📄 CanvasPDFViewer navigating to page ${initialPageNumber}`)
      setCurrentPage(initialPageNumber)
    }
  }, [initialPageNumber, currentPage, totalPages])

  const goToPage = (pageNumber: number) => {
    if (pageNumber >= 1 && pageNumber <= totalPages) {
      console.log(`🚀 Canvas PDF navigating to page ${pageNumber}`)
      setCurrentPage(pageNumber)
      onPageChange?.(pageNumber)
    }
  }

  const handleZoomIn = () => {
    const newZoom = Math.min(zoomLevel + 0.25, 3.0) // Max 3x zoom
    console.log(`🔍 Zoom In: ${zoomLevel} → ${newZoom}`)
    setZoomLevel(newZoom)
  }

  const handleZoomOut = () => {
    const newZoom = Math.max(zoomLevel - 0.25, 0.25) // Min 0.25x zoom
    console.log(`🔍 Zoom Out: ${zoomLevel} → ${newZoom}`)
    setZoomLevel(newZoom)
  }

  const handleZoomReset = () => {
    console.log(`🔍 Zoom Reset: ${zoomLevel} → 0.65`)
    setZoomLevel(0.65)
  }

  console.log('🎨 CanvasPDFViewer render - pdfUrl:', pdfUrl)
  console.log('🎨 CanvasPDFViewer render - loading:', loading)
  console.log('🎨 CanvasPDFViewer render - error:', error)
  console.log('🎨 CanvasPDFViewer render - pdfDoc:', !!pdfDoc)

  if (!pdfUrl) {
    console.log('📄 No pdfUrl - showing loading...')
    return (
      <Box textAlign="center" padding="xl">
        <StatusIndicator type="loading">Loading PDF...</StatusIndicator>
      </Box>
    )
  }

  if (error) {
    console.log('❌ Error state - showing error...')
    return (
      <Box textAlign="center" padding="xl">
        <StatusIndicator type="error">{error}</StatusIndicator>
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
          {/* Page Navigation */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Button
              variant="normal"
              iconName="angle-left"
              disabled={currentPage <= 1 || loading}
              onClick={() => goToPage(currentPage - 1)}
            >
              Previous
            </Button>
            
            <Box textAlign="center">
              <span style={{ fontSize: '14px' }}>
                Page {currentPage} of {totalPages || '...'}
              </span>
            </Box>
            
            <Button
              variant="normal"
              iconName="angle-right"
              disabled={currentPage >= totalPages || loading}
              onClick={() => goToPage(currentPage + 1)}
            >
              Next
            </Button>
          </div>

          {/* Zoom Controls */}
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <Button
              variant="normal"
              iconName="zoom-out"
              disabled={loading || zoomLevel <= 0.25}
              onClick={handleZoomOut}
            />
            
            <div style={{ minWidth: '60px' }}>
              <Button
                variant="normal"
                disabled={loading}
                onClick={handleZoomReset}
              >
                {Math.round(zoomLevel * 100)}%
              </Button>
            </div>
            
            <Button
              variant="normal"
              iconName="zoom-in"
              disabled={loading || zoomLevel >= 3.0}
              onClick={handleZoomIn}
            />
          </div>
        </SpaceBetween>
      </div>

      {/* PDF Content */}
      <div 
        ref={containerRef}
        style={{ 
          flex: 1, 
          overflow: 'auto',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          backgroundColor: '#f8f9fa',
          padding: '8px'
        }}
      >
        {loading && (
          <StatusIndicator type="loading">Loading PDF page...</StatusIndicator>
        )}
        
        <canvas
          ref={canvasRef}
          style={{
            maxWidth: 'none', // Allow canvas to be larger than container
            maxHeight: 'none',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            backgroundColor: 'white',
            borderRadius: '6px',
            display: loading ? 'none' : 'block',
            imageRendering: 'pixelated' // Prevent blur on scaling
          }}
        />
      </div>
    </div>
  )
}

export default CanvasPDFViewer
