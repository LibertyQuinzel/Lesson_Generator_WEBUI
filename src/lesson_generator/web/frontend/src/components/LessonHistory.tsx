import { useState, useEffect } from 'react'

interface LessonStatus {
  lesson_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  topics: string[]
  progress: Record<string, any>
  error_message?: string
  result_files?: string[]
  download_url?: string
}

interface LessonHistoryProps {
  onViewLesson: (lessonId: string) => void
}

export const LessonHistory = ({ onViewLesson }: LessonHistoryProps) => {
  const [lessons, setLessons] = useState<LessonStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'completed' | 'failed' | 'processing'>('all')

  const fetchLessons = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/v1/lessons/')
      
      if (response.ok) {
        const data = await response.json()
        setLessons(data)
        setError(null)
      } else {
        throw new Error('Failed to load lesson history')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLessons()
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-swiss-black bg-swiss-gray-100'
      case 'failed': return 'text-swiss-red bg-swiss-white border border-swiss-red'
      case 'processing': return 'text-swiss-gray-700 bg-swiss-gray-100'
      case 'pending': return 'text-swiss-gray-600 bg-swiss-gray-100'
      default: return 'text-swiss-gray-600 bg-swiss-gray-100'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '●'
      case 'failed': return '●'
      case 'processing': return '●'
      case 'pending': return '●'
      default: return '●'
    }
  }

  const filteredLessons = lessons.filter(lesson => {
    if (filter === 'all') return true
    return lesson.status === filter
  }).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  const handleDelete = async (lessonId: string) => {
    if (!confirm('Are you sure you want to delete this lesson? This action cannot be undone.')) {
      return
    }

    try {
      const response = await fetch(`/api/v1/lessons/${lessonId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Refresh the lessons list
        await fetchLessons()
      } else {
        throw new Error('Failed to delete lesson')
      }
    } catch (err) {
      alert(`Error deleting lesson: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  if (loading) {
    return (
      <div className="bg-swiss-white border border-swiss-gray-200 p-8">
        <h2 className="text-xl font-light text-swiss-black mb-8 tracking-tight">
          Lesson History
        </h2>
        <div className="text-center py-12">
          <div className="inline-block h-8 w-8 border-2 border-swiss-gray-300 border-t-swiss-black animate-spin mb-6"></div>
          <p className="text-sm text-swiss-gray-600 tracking-wide">Loading lesson history</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-swiss-white border border-swiss-gray-200 p-8">
        <h2 className="text-xl font-light text-swiss-black mb-8 tracking-tight">
          Lesson History
        </h2>
        <div className="text-center py-12">
          <div className="w-12 h-12 mx-auto mb-6 border-2 border-swiss-red flex items-center justify-center">
            <span className="text-swiss-red text-lg">!</span>
          </div>
          <p className="text-sm text-swiss-red mb-8 font-medium">{error}</p>
          <button
            onClick={fetchLessons}
            className="px-6 py-3 bg-swiss-black text-swiss-white hover:bg-swiss-gray-800 transition-colors duration-200 text-sm font-medium tracking-wide"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-swiss-white border border-swiss-gray-200 p-8">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-xl font-light text-swiss-black tracking-tight">
          Lesson History
        </h2>
        <button
          onClick={fetchLessons}
          className="text-swiss-gray-600 hover:text-swiss-black transition-colors text-sm font-medium tracking-wide"
          title="Refresh"
        >
          Refresh
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="mb-8 border-b border-swiss-gray-200">
        <nav className="flex space-x-12">
          {[
            { id: 'all', label: 'All', count: lessons.length },
            { id: 'completed', label: 'Completed', count: lessons.filter(l => l.status === 'completed').length },
            { id: 'processing', label: 'Processing', count: lessons.filter(l => l.status === 'processing').length },
            { id: 'failed', label: 'Failed', count: lessons.filter(l => l.status === 'failed').length }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id as any)}
              className={`pb-4 border-b-2 font-medium text-sm transition-colors duration-200 ${
                filter === tab.id
                  ? 'border-swiss-black text-swiss-black'
                  : 'border-transparent text-swiss-gray-600 hover:text-swiss-black hover:border-swiss-gray-300'
              }`}
            >
              {tab.label}
              <span className="ml-3 bg-swiss-gray-100 text-swiss-gray-600 py-1 px-2 text-xs font-medium tracking-wide">
                {tab.count}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Lessons List */}
      {filteredLessons.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 mx-auto mb-6 border border-swiss-gray-300 flex items-center justify-center">
            <span className="text-swiss-gray-400 text-xl">—</span>
          </div>
          <p className="text-sm text-swiss-gray-600 tracking-wide">
            {filter === 'all' ? 'No lessons generated yet' : `No ${filter} lessons found`}
          </p>
        </div>
      ) : (
        <div className="max-h-[60vh] overflow-y-auto pr-2 scrollable">
          <div className="space-y-6">
            {filteredLessons.map((lesson) => (
            <div
              key={lesson.lesson_id}
              className="border border-swiss-gray-200 bg-swiss-white p-6 hover:border-swiss-gray-300 transition-colors duration-200"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-4 mb-4">
                    <span className={`text-sm ${getStatusColor(lesson.status).split(' ')[0]}`}>{getStatusIcon(lesson.status)}</span>
                    <span className={`px-3 py-1 text-xs font-medium tracking-wide ${getStatusColor(lesson.status)}`}>
                      {lesson.status.toUpperCase()}
                    </span>
                    <span className="text-xs text-swiss-gray-500 font-medium tracking-wide uppercase">
                      {lesson.lesson_id}
                    </span>
                  </div>
                  
                  <div className="mb-4">
                    <p className="font-medium text-swiss-black mb-2">
                      {lesson.topics.join(', ')}
                    </p>
                    <div className="text-xs text-swiss-gray-600 space-y-1">
                      <p>
                        <span className="font-medium tracking-wide uppercase">Created:</span> {new Date(lesson.created_at).toLocaleString()}
                      </p>
                      {lesson.updated_at !== lesson.created_at && (
                        <p>
                          <span className="font-medium tracking-wide uppercase">Updated:</span> {new Date(lesson.updated_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>

                  {lesson.error_message && (
                    <div className="mt-4 p-4 border border-swiss-red bg-swiss-white">
                      <p className="text-xs text-swiss-red font-medium tracking-wide uppercase mb-1">Error</p>
                      <p className="text-sm text-swiss-red">{lesson.error_message}</p>
                    </div>
                  )}

                  {lesson.progress?.percentage && (
                    <div className="mt-4">
                      <div className="flex justify-between text-xs text-swiss-gray-600 font-medium tracking-wide uppercase mb-2">
                        <span>Progress</span>
                        <span>{Math.round(lesson.progress.percentage)}%</span>
                      </div>
                      <div className="w-full bg-swiss-gray-200 h-1">
                        <div
                          className="bg-swiss-black h-1 transition-all duration-300"
                          style={{ width: `${lesson.progress.percentage}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex space-x-3 ml-4">
                  {lesson.status === 'completed' && (
                    <>
                      <button
                        onClick={() => onViewLesson(lesson.lesson_id)}
                        className="px-3 py-2 border border-swiss-gray-300 text-swiss-black hover:border-swiss-black text-xs font-medium tracking-wide transition-colors duration-200"
                        title="Preview Lesson"
                      >
                        VIEW
                      </button>
                      {lesson.download_url && (
                        <a
                          href={lesson.download_url}
                          className="px-3 py-2 bg-swiss-black text-swiss-white hover:bg-swiss-gray-800 text-xs font-medium tracking-wide transition-colors duration-200"
                          title="Download Lesson"
                        >
                          DOWNLOAD
                        </a>
                      )}
                    </>
                  )}
                  <button
                    onClick={() => handleDelete(lesson.lesson_id)}
                    className="px-3 py-2 border border-swiss-red text-swiss-red hover:bg-swiss-red hover:text-swiss-white text-xs font-medium tracking-wide transition-colors duration-200"
                    title="Delete Lesson"
                  >
                    DELETE
                  </button>
                </div>
              </div>
            </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}