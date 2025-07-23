import React from 'react'
import { Box, Button, SpaceBetween, Badge } from '@cloudscape-design/components'

interface PDFReference {
  documentName: string
  pages: {
    pageNumber: number
    highlights: string[]
  }[]
}

interface PDFPageSelectorProps {
  references: PDFReference[]
  onPageSelect: (documentName: string, pageNumber: number, highlights: string[]) => void
}

const PDFPageSelector: React.FC<PDFPageSelectorProps> = ({ references, onPageSelect }) => {
  if (!references || references.length === 0) {
    return null
  }

  return (
    <Box margin={{ top: 's' }}>
      <SpaceBetween direction="vertical" size="s">
        <Box variant="h4" color="text-label">
          Refer to the following pages in the mentioned docs:
        </Box>
        
        {references.map((doc, docIndex) => (
          <Box key={docIndex}>
            <Box margin={{ bottom: 'xs' }}>
              <strong>{doc.documentName}</strong>
            </Box>
            
            <SpaceBetween direction="horizontal" size="xs">
              {doc.pages.map((page, pageIndex) => (
                <Button
                  key={pageIndex}
                  variant="primary"
                  onClick={() => {
                    // Log the button click for debugging
                    console.log(`🔥 PDFPageSelector button clicked: ${doc.documentName}, page ${page.pageNumber}`)
                    console.log('onPageSelect function exists:', !!onPageSelect)
                    onPageSelect(doc.documentName, page.pageNumber, page.highlights)
                  }}
                >
                  Page {page.pageNumber}
                  {page.highlights.length > 1 && (
                    <span style={{ marginLeft: '4px' }}>
                      <Badge color="blue">
                        {page.highlights.length}
                      </Badge>
                    </span>
                  )}
                </Button>
              ))}
            </SpaceBetween>
          </Box>
        ))}
      </SpaceBetween>
    </Box>
  )
}

export default PDFPageSelector
