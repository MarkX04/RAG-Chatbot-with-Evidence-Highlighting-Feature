import React, { useState } from 'react';
import { Modal, Button, Box, SpaceBetween, Header } from '@cloudscape-design/components';

interface PDFViewerProps {
  isOpen: boolean;
  onClose: () => void;
  pdfUrl?: string;
  message?: string;
}

const PDFViewer: React.FC<PDFViewerProps> = ({
  isOpen,
  onClose,
  pdfUrl,
  message
}) => {
  const [error, setError] = useState<string | null>(null);

  const handleDownload = () => {
    if (pdfUrl) {
      const link = document.createElement('a');
      link.href = pdfUrl;
      link.download = 'highlighted_evidence.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <Modal
      visible={isOpen}
      onDismiss={onClose}
      size="max"
      header={
        <Header
          variant="h1"
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="normal" onClick={handleDownload}>
                📥 Download PDF
              </Button>
              <Button variant="primary" onClick={onClose}>
                Close
              </Button>
            </SpaceBetween>
          }
        >
          📄 Evidence PDF - Highlighted References
        </Header>
      }
    >
      <Box padding="m">
        {error ? (
          <Box textAlign="center" padding="xl">
            <div style={{ color: '#d13212', fontSize: '16px', marginBottom: '16px' }}>
              ⚠️ Unable to load PDF
            </div>
            <div style={{ color: '#687078', marginBottom: '20px' }}>
              {error}
            </div>
            <SpaceBetween direction="horizontal" size="s">
              <Button variant="normal" onClick={handleDownload}>
                📥 Download Instead
              </Button>
              <Button onClick={onClose}>Close</Button>
            </SpaceBetween>
          </Box>
        ) : pdfUrl ? (
          <div style={{ height: '80vh', width: '100%' }}>
            <iframe
              src={`${pdfUrl}#view=FitH`}
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
                borderRadius: '8px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
              }}
              title="Highlighted Evidence PDF"
              onError={() => {
                setError('Failed to load PDF. The file might be processing or there was an error generating the highlights.');
              }}
            />
          </div>
        ) : (
          <Box textAlign="center" padding="xl">
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📄</div>
            <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '8px' }}>
              Generating Highlighted PDF...
            </div>
            <div style={{ color: '#687078', marginBottom: '20px' }}>
              Creating evidence highlights for: "{message}"
            </div>
            <div style={{ 
              display: 'inline-block',
              width: '20px',
              height: '20px',
              border: '3px solid #e4e7ea',
              borderTop: '3px solid #0972d3',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }} />
            <style>
              {`
                @keyframes spin {
                  0% { transform: rotate(0deg); }
                  100% { transform: rotate(360deg); }
                }
              `}
            </style>
          </Box>
        )}
      </Box>
    </Modal>
  );
};

export default PDFViewer;
