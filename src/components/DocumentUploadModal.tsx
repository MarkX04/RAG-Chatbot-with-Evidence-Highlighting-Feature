import { useState } from 'react'
import {
  Modal,
  Box,
  SpaceBetween,
  Button,
  FileUpload,
  StatusIndicator,
  Alert
} from '@cloudscape-design/components'
import type { FileUploadProps } from '@cloudscape-design/components'
import { chatService } from '../services/chatService'

interface DocumentUploadModalProps {
  visible: boolean
  onDismiss: () => void
  onUploadSuccess: () => void
}

export function DocumentUploadModal({ visible, onDismiss, onUploadSuccess }: DocumentUploadModalProps) {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<{
    type: 'success' | 'error' | 'info' | null
    message: string
  }>({ type: null, message: '' })

  const handleUpload = async () => {
    if (files.length === 0) {
      setUploadStatus({
        type: 'error',
        message: 'Please select at least one PDF file to upload.'
      })
      return
    }

    setUploading(true)
    setUploadStatus({ type: null, message: '' })

    try {
      const results = await Promise.all(
        files.map(file => chatService.uploadDocument(file))
      )

      const successCount = results.filter(r => r.success).length
      const failureCount = results.length - successCount

      if (successCount > 0) {
        setUploadStatus({
          type: 'success',
          message: `Successfully uploaded ${successCount} document(s). ${failureCount > 0 ? `${failureCount} failed.` : 'Knowledge base is being updated...'}`
        })
        
        // Call success callback after a delay to allow processing
        setTimeout(() => {
          onUploadSuccess()
          onDismiss()
        }, 2000)
      } else {
        setUploadStatus({
          type: 'error',
          message: 'Failed to upload documents. Please check the backend server.'
        })
      }
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: `Upload error: ${error instanceof Error ? error.message : 'Unknown error'}`
      })
    } finally {
      setUploading(false)
    }
  }

  const handleFileChange: FileUploadProps['onChange'] = ({ detail }) => {
    setFiles(detail.value)
    setUploadStatus({ type: null, message: '' })
  }

  const resetModal = () => {
    setFiles([])
    setUploadStatus({ type: null, message: '' })
    setUploading(false)
  }

  return (
    <Modal
      onDismiss={() => {
        onDismiss()
        resetModal()
      }}
      visible={visible}
      size="medium"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={onDismiss}>
              Cancel
            </Button>
            <Button 
              variant="primary" 
              onClick={handleUpload}
              loading={uploading}
              disabled={files.length === 0}
            >
              {uploading ? 'Uploading...' : 'Upload Documents'}
            </Button>
          </SpaceBetween>
        </Box>
      }
      header="Upload Documents to Knowledge Base"
    >
      <SpaceBetween direction="vertical" size="l">
        <Box>
          Upload PDF documents to enhance the chatbot's knowledge base. 
          The documents will be processed and indexed for RAG (Retrieval-Augmented Generation).
        </Box>

        <FileUpload
          onChange={handleFileChange}
          value={files}
          multiple
          accept=".pdf"
          showFileLastModified
          showFileSize
          showFileThumbnail
          i18nStrings={{
            uploadButtonText: e => e ? "Choose files" : "Choose file",
            dropzoneText: e => e ? "Drop files to upload" : "Drop file to upload",
            removeFileAriaLabel: e => `Remove file ${e + 1}`,
            limitShowFewer: "Show fewer files",
            limitShowMore: "Show more files",
            errorIconAriaLabel: "Error"
          }}
          constraintText="Only PDF files are supported. Multiple files can be selected."
        />

        {uploadStatus.type && (
          <Alert
            statusIconAriaLabel={uploadStatus.type}
            type={uploadStatus.type}
          >
            {uploadStatus.message}
          </Alert>
        )}

        {uploading && (
          <Box>
            <StatusIndicator type="loading">
              Processing documents and updating knowledge base...
            </StatusIndicator>
          </Box>
        )}
      </SpaceBetween>
    </Modal>
  )
}
