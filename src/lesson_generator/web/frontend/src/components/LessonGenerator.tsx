import { useState, useEffect } from 'react'
import { GenerationForm, GenerationFormData } from './forms/GenerationForm'
import { ProgressTracker } from './ProgressTracker'
import { GenerationResult } from './GenerationResult'

interface LessonGenerationState {
  lessonId: string | null
  status: 'idle' | 'generating' | 'completed' | 'failed'
  progress: number
  message: string
  error?: string
  downloadUrl?: string
}

export const LessonGenerator = () => {
  const [generationState, setGenerationState] = useState<LessonGenerationState>({
    lessonId: null,
    status: 'idle',
    progress: 0,
    message: ''
  })

  const handleStartGeneration = async (formData: GenerationFormData) => {
    try {
      setGenerationState({
        lessonId: null,
        status: 'generating',
        progress: 0,
        message: 'Starting lesson generation...'
      })

      const response = await fetch('/api/v1/lessons/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Network error' }))
        throw new Error(errorData.detail?.[0]?.msg || errorData.message || `HTTP ${response.status}`)
      }

      const result = await response.json()
      
      setGenerationState(prev => ({
        ...prev,
        lessonId: result.lesson_id,
        message: result.message || 'Generation started successfully'
      }))
      
    } catch (error) {
      console.error('Generation start error:', error)
      setGenerationState({
        lessonId: null,
        status: 'failed',
        progress: 0,
        message: '',
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      })
    }
  }

  const handleReset = () => {
    setGenerationState({
      lessonId: null,
      status: 'idle',
      progress: 0,
      message: '',
      error: undefined,
      downloadUrl: undefined
    })
  }

  // Poll for status updates when generating
  useEffect(() => {
    if (!generationState.lessonId || generationState.status !== 'generating') {
      return
    }

    let pollCount = 0
    const maxPolls = 300 // Stop after 10 minutes (300 * 2 seconds)

    const interval = setInterval(async () => {
      try {
        pollCount++
        
        if (pollCount > maxPolls) {
          setGenerationState(prev => ({
            ...prev,
            status: 'failed',
            error: 'Generation timed out after 10 minutes'
          }))
          return
        }

        const response = await fetch(`/api/v1/lessons/${generationState.lessonId}/status`)
        
        if (!response.ok) {
          if (response.status === 404) {
            // Task not found, might need recovery
            setGenerationState(prev => ({
              ...prev,
              status: 'failed',
              error: 'Generation task was lost. Please try again.'
            }))
            return
          }
          throw new Error(`HTTP ${response.status}`)
        }

        const status = await response.json()
        const progress = Math.min(100, Math.max(0, status.progress?.percentage || 0))
        const message = status.progress?.current_step || status.message || 'Processing...'

        // Add some logging to debug progress updates
        console.log(`Progress update: ${progress}% - ${message}`)

        setGenerationState(prev => ({
          ...prev,
          progress,
          message,
          status: status.status === 'completed' ? 'completed' : 
                 status.status === 'failed' ? 'failed' : 'generating',
          downloadUrl: status.status === 'completed' 
            ? `/api/v1/lessons/${generationState.lessonId}/download` 
            : undefined,
          error: status.status === 'failed' ? status.error_message : undefined
        }))

      } catch (error) {
        console.error('Status check error:', error)
        
        // Only fail after multiple consecutive errors
        if (pollCount % 5 === 0) { // Every 5th poll failure
          setGenerationState(prev => ({
            ...prev,
            status: 'failed',
            error: `Connection error: ${error instanceof Error ? error.message : 'Unknown error'}`
          }))
        }
      }
    }, 1000) // Reduced from 2000ms to 1000ms for more responsive updates

    return () => clearInterval(interval)
  }, [generationState.lessonId, generationState.status])

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">
        Generate Programming Lessons
      </h2>

      {generationState.status === 'idle' && (
        <GenerationForm onSubmit={handleStartGeneration} />
      )}

      {generationState.status === 'generating' && (
        <ProgressTracker 
          onCancel={handleReset}
        />
      )}

      {(generationState.status === 'completed' || generationState.status === 'failed') && (
        <GenerationResult 
          status={generationState.status}
          lessonId={generationState.lessonId || undefined}
          downloadUrl={generationState.downloadUrl}
          error={generationState.error}
          onReset={handleReset}
        />
      )}
    </div>
  )
}