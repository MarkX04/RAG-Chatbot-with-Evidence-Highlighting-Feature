interface LoadingProps {
  message?: string
}

export const Loading = ({ message = 'Thinking...' }: LoadingProps) => {
  return (
    <div className="flex justify-start">
      <div className="bg-gray-100 text-gray-900 max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
        <div className="flex items-center space-x-2">
          <div className="animate-pulse">🤔</div>
          <span className="text-sm">{message}</span>
          <div className="flex space-x-1">
            <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"></div>
            <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
        </div>
      </div>
    </div>
  )
}
