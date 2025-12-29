
import { useState } from 'react'
import { LessonPreview } from './LessonPreview'

interface GenerationResultProps {
  status: 'completed' | 'failed'
  lessonId?: string
  downloadUrl?: string
  error?: string
  onReset: () => void
}

export const GenerationResult = ({
  status,
  lessonId,
  downloadUrl,
  error,
  onReset
}: GenerationResultProps) => {
  const [showPreview, setShowPreview] = useState(false)

  let content = null

  if (status === 'completed') {
    content = (
      <div className="space-y-6">
        <div className="text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h3 className="text-2xl font-light text-swiss-black mb-2 tracking-tight">
            Lessons Generated Successfully!
          </h3>
          <p className="text-swiss-gray-600 tracking-wide">
            Your programming lessons are ready for download
          </p>
        </div>

        <div className="bg-swiss-white border border-swiss-gray-200 p-6">
          <div className="flex items-center justify-center space-x-4">
            <div className="text-swiss-black">
              <svg className="h-8 w-8" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="text-swiss-black text-lg font-light tracking-wide">
              Generation Complete
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          {lessonId && (
            <button
              onClick={() => setShowPreview(true)}
              className="flex-1 bg-swiss-black text-swiss-white py-4 px-8 hover:bg-swiss-gray-800 focus:outline-none transition-colors duration-200 text-sm font-medium tracking-wide"
            >
              👁️ Preview Lessons
            </button>
          )}
          {downloadUrl && (
            <a
              href={downloadUrl}
              className="flex-1 bg-swiss-black text-swiss-white py-4 px-8 hover:bg-swiss-gray-800 focus:outline-none transition-colors duration-200 text-sm font-medium tracking-wide"
            >
              📥 Download Lessons
            </a>
          )}
          <button
            onClick={onReset}
            className="flex-1 bg-swiss-white text-swiss-black border border-swiss-gray-300 py-4 px-8 hover:border-swiss-black focus:outline-none transition-colors duration-200 text-sm font-medium tracking-wide"
          >
            ➕ Generate More
          </button>
        </div>
      </div>
    )
  } else if (status === 'failed') {
    content = (
      <div className="space-y-6">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <h3 className="text-2xl font-light text-swiss-black mb-2 tracking-tight">
            Generation Failed
          </h3>
          <p className="text-swiss-gray-600 tracking-wide">
            Something went wrong during lesson generation
          </p>
        </div>

        <div className="bg-swiss-white border border-swiss-gray-300 p-6">
          <div className="flex items-start">
            <div className="text-swiss-black mr-3 mt-0.5">
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="text-swiss-black">
              <p className="font-medium mb-1 tracking-wide">Error Details:</p>
              <p className="text-sm text-swiss-gray-600 tracking-wide">{error || 'Unknown error occurred'}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          <button
            onClick={onReset}
            className="flex-1 bg-swiss-black text-swiss-white py-4 px-8 hover:bg-swiss-gray-800 focus:outline-none transition-colors duration-200 text-sm font-medium tracking-wide"
          >
            🔄 Try Again
          </button>
          <button
            onClick={() => window.open('/api/docs', '_blank')}
            className="flex-1 bg-swiss-white text-swiss-black border border-swiss-gray-300 py-4 px-8 hover:border-swiss-black focus:outline-none transition-colors duration-200 text-sm font-medium tracking-wide"
          >
            📋 API Docs
          </button>
        </div>
      </div>
    )
  }

  return (
    <>
      {content}
      {showPreview && lessonId && (
        <LessonPreview
          lessonId={lessonId}
          onClose={() => setShowPreview(false)}
          onDownload={() => {
            setShowPreview(false)
            if (downloadUrl) {
              window.open(downloadUrl, '_blank')
            }
          }}
        />
      )}
    </>
  )
}