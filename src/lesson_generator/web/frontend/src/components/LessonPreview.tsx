import { useState, useEffect } from 'react'

interface LessonPreviewData {
  lesson_id: string
  topics: string[]
  created_at: string
  file_structure: Array<{
    path: string
    type: 'file' | 'directory'
    size?: number
  }>
  readme_content?: string
  total_files: number
  modules: Array<{
    name: string
    files: Array<{
      name: string
      type: string
      size: number
    }>
  }>
}

interface LessonPreviewProps {
  lessonId: string
  onClose: () => void
  onDownload: () => void
}

export const LessonPreview = ({ lessonId, onClose, onDownload }: LessonPreviewProps) => {
  const [previewData, setPreviewData] = useState<LessonPreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'structure' | 'readme' | 'modules'>('structure')

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const fetchPreview = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/lessons/${lessonId}/preview`)
      
      if (response.ok) {
        const data = await response.json()
        setPreviewData(data)
        setError(null)
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load preview')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  // Load preview on mount
  useEffect(() => {
    fetchPreview()
  }, [lessonId])

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A'
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-swiss-black bg-opacity-60 flex items-center justify-center z-50 p-8">
        <div className="bg-swiss-white p-16 max-w-md w-full">
          <div className="text-center">
            <div className="inline-block h-8 w-8 border-2 border-swiss-gray-300 border-t-swiss-black animate-spin mb-8"></div>
            <p className="text-sm text-swiss-gray-600 tracking-wide">Loading lesson preview</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-swiss-black bg-opacity-60 flex items-center justify-center z-50 p-8">
        <div className="bg-swiss-white p-16 max-w-lg w-full">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-8 border-2 border-swiss-red flex items-center justify-center">
              <span className="text-swiss-red text-lg">!</span>
            </div>
            <h3 className="text-lg font-medium text-swiss-black mb-4 tracking-tight">Preview Failed</h3>
            <p className="text-sm text-swiss-gray-600 mb-12 break-words leading-relaxed">{error}</p>
            <div className="flex justify-center space-x-6">
              <button
                onClick={onClose}
                className="px-8 py-3 border border-swiss-gray-300 text-swiss-black hover:border-swiss-black transition-colors duration-200 text-sm font-medium tracking-wide"
              >
                Close
              </button>
              <button
                onClick={fetchPreview}
                className="px-8 py-3 bg-swiss-black text-swiss-white hover:bg-swiss-gray-800 transition-colors duration-200 text-sm font-medium tracking-wide"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!previewData) return null

  return (
    <div 
      className="fixed inset-0 bg-swiss-black bg-opacity-60 flex items-center justify-center z-50 p-8"
      onClick={onClose}
    >
      <div 
        className="bg-swiss-white max-w-7xl w-full h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-8 border-b border-swiss-gray-200 flex-shrink-0">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <h2 className="text-2xl font-light text-swiss-black mb-6 tracking-tight">Lesson Preview</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                <div>
                  <p className="text-swiss-gray-600 font-medium tracking-wide uppercase mb-1">Topics</p>
                  <p className="text-swiss-black">{previewData.topics.join(', ')}</p>
                </div>
                <div>
                  <p className="text-swiss-gray-600 font-medium tracking-wide uppercase mb-1">Created</p>
                  <p className="text-swiss-black">{new Date(previewData.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-swiss-gray-600 font-medium tracking-wide uppercase mb-1">Files Generated</p>
                  <p className="text-swiss-black">{previewData.total_files} files</p>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-swiss-gray-400 hover:text-swiss-black text-2xl font-light flex-shrink-0 ml-8 transition-colors duration-200"
            >
              ×
            </button>
          </div>

          {/* Tabs */}
          <div className="mt-8 border-b border-swiss-gray-200">
            <nav className="flex space-x-12 overflow-x-auto">
              {[
                { id: 'structure', label: 'File Structure', count: previewData.total_files },
                { id: 'readme', label: 'README', available: !!previewData.readme_content },
                { id: 'modules', label: 'Modules', count: previewData.modules.length }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`pb-4 font-medium text-sm whitespace-nowrap border-b-2 transition-colors duration-200 ${
                    activeTab === tab.id
                      ? 'border-swiss-black text-swiss-black'
                      : 'border-transparent text-swiss-gray-600 hover:text-swiss-black hover:border-swiss-gray-300'
                  } ${!tab.available && tab.id === 'readme' ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={!tab.available && tab.id === 'readme'}
                >
                  {tab.label}
                  {tab.count !== undefined && (
                    <span className="ml-3 bg-swiss-gray-100 text-swiss-gray-600 py-1 px-2 text-xs font-medium tracking-wide">
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8 scrollable">
          {activeTab === 'structure' && (
            <div>
              <h3 className="text-lg font-medium mb-8 text-swiss-black tracking-tight">File Structure</h3>
              <div className="bg-swiss-gray-100 p-6 font-mono text-sm border border-swiss-gray-200">
                <div className="space-y-1">
                  {previewData.file_structure.map((item, index) => (
                    <div
                      key={index}
                      className={`flex justify-between py-1 ${
                        item.type === 'directory' ? 'font-medium text-swiss-black' : 'text-swiss-gray-700'
                      }`}
                    >
                      <span className="break-all">
                        {item.type === 'directory' ? '/' : ''}{item.path}
                      </span>
                      {item.size && (
                        <span className="text-swiss-gray-500 ml-4 flex-shrink-0 text-xs">{formatFileSize(item.size)}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'readme' && previewData.readme_content && (
            <div>
              <h3 className="text-lg font-medium mb-8 text-swiss-black tracking-tight">README Content</h3>
              <div className="bg-swiss-gray-100 p-6 border border-swiss-gray-200">
                <pre className="whitespace-pre-wrap text-sm text-swiss-gray-800 overflow-wrap break-words font-mono leading-relaxed">
                  {previewData.readme_content}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'modules' && (
            <div>
              <h3 className="text-lg font-medium mb-8 text-swiss-black tracking-tight">Module Structure</h3>
              <div className="space-y-8">
                {previewData.modules.map((module, index) => (
                  <div key={index} className="border border-swiss-gray-200">
                    <div className="bg-swiss-gray-100 p-4 border-b border-swiss-gray-200">
                      <h4 className="font-medium text-swiss-black">{module.name}</h4>
                    </div>
                    <div className="p-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {module.files.map((file, fileIndex) => (
                          <div
                            key={fileIndex}
                            className="border border-swiss-gray-200 p-3 bg-swiss-white text-sm"
                          >
                            <div className="flex justify-between items-start">
                              <span className="font-medium break-all text-swiss-black">{file.name}</span>
                              <span className="text-xs text-swiss-gray-500 uppercase ml-3 flex-shrink-0 font-mono">
                                {file.type}
                              </span>
                            </div>
                            <div className="text-xs text-swiss-gray-500 mt-2 font-mono">
                              {formatFileSize(file.size)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-8 border-t border-swiss-gray-200 bg-swiss-gray-100 flex-shrink-0">
          <div className="flex justify-end space-x-6">
            <button
              onClick={onClose}
              className="px-8 py-3 border border-swiss-gray-300 text-swiss-black hover:border-swiss-black transition-colors duration-200 text-sm font-medium tracking-wide"
            >
              Close Preview
            </button>
            <button
              onClick={onDownload}
              className="px-8 py-3 bg-swiss-black text-swiss-white hover:bg-swiss-gray-800 transition-colors duration-200 text-sm font-medium tracking-wide"
            >
              Download Lessons
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}