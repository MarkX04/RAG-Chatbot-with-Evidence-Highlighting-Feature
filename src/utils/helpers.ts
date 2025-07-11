// Utility functions for the chatbot

export const formatTimestamp = (date: Date): string => {
  return date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

export const generateMessageId = (): string => {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export const scrollToBottom = (elementId: string): void => {
  const element = document.getElementById(elementId)
  if (element) {
    element.scrollTop = element.scrollHeight
  }
}

export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export const sanitizeInput = (input: string): string => {
  return input.trim().replace(/\s+/g, ' ')
}

export const isValidMessage = (message: string): boolean => {
  return message.trim().length > 0 && message.length <= 4000
}
