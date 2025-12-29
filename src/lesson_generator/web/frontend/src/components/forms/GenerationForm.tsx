import { useState } from 'react'

export interface GenerationFormData {
  // name and description removed
  topics: string[]
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  modules?: number
  // config removed - backend will create proper config with AI always enabled
}

interface GenerationFormProps {
  onSubmit: (data: GenerationFormData) => void
}

export const GenerationForm = ({ onSubmit }: GenerationFormProps) => {
  // name and description removed
  const [topics, setTopics] = useState('')
  const [difficulty, setDifficulty] = useState<'beginner' | 'intermediate' | 'advanced'>('intermediate')
  const [numModules, setNumModules] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: any) => {
    e.preventDefault()
    
    const topicList = topics.split('\n').filter(t => t.trim()).map(t => t.trim())
    // topics input is optional, fallback to AI if empty
    // (actual AI fallback logic should be handled in backend)

    setIsSubmitting(true)
    
    const modulesValue = numModules && numModules.toString().trim() ? Number(numModules) : undefined

    const formData: GenerationFormData = {
      topics: topicList,
      difficulty,
      ...(modulesValue !== undefined ? { modules: modulesValue } : {}),
      // Remove config entirely - let backend create proper config with AI enabled
    }

    try {
      await onSubmit(formData)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-swiss-white border border-swiss-gray-200 p-8">
      <h2 className="text-xl font-light text-swiss-black mb-8 tracking-tight">Generate New Lessons</h2>
      
      <form onSubmit={handleSubmit} className="space-y-8">
        <div>
          <label htmlFor="topics" className="block text-sm font-medium text-swiss-gray-600 mb-3 tracking-wide uppercase">
            Topics (Each topic creates one lesson)
          </label>
          <textarea
            id="topics"
            value={topics}
            onChange={(e) => setTopics(e.target.value)}
            className="w-full px-4 py-3 border border-swiss-gray-300 bg-swiss-white focus:outline-none focus:border-swiss-black transition-colors duration-200 text-sm"
            rows={5}
            placeholder="python_fundamentals&#10;design_patterns&#10;web_development"
            required
          />
          <p className="mt-2 text-xs text-swiss-gray-500 tracking-wide">
            List the topics you wish to create lessons for. Enter each topic on a separate line.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <label htmlFor="difficulty" className="block text-sm font-medium text-swiss-gray-600 mb-3 tracking-wide uppercase">
              Difficulty Level
            </label>
            <select
              id="difficulty"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as 'beginner' | 'intermediate' | 'advanced')}
              className="w-full px-4 py-3 border border-swiss-gray-300 bg-swiss-white focus:outline-none focus:border-swiss-black transition-colors duration-200 text-sm"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div>
            <label htmlFor="modules" className="block text-sm font-medium text-swiss-gray-600 mb-3 tracking-wide uppercase">
              Number of Modules (per lesson)
            </label>
            <input
              type="number"
              id="modules"
              value={numModules}
              onChange={(e) => setNumModules(e.target.value)}
              min="1"
              max="10"
              placeholder=""
              className="w-full px-4 py-3 border border-swiss-gray-300 bg-swiss-white focus:outline-none focus:border-swiss-black transition-colors duration-200 text-sm"
            />
            <p className="mt-2 text-xs text-swiss-gray-500 tracking-wide">
              Number of modules in each lesson
            </p>
          </div>
        </div>

        {/* Exercises and examples options removed - backend will handle defaults */}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-swiss-black text-swiss-white py-4 px-8 hover:bg-swiss-gray-800 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 text-sm font-medium tracking-wide"
        >
          {isSubmitting ? 'Starting Generation...' : 'Generate Lessons'}
        </button>
      </form>
    </div>
  )
}