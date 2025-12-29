import { useState } from 'react'
import { Header } from './components/layout/Header'
import { LessonGenerator } from './components/LessonGenerator'
import { LessonHistory } from './components/LessonHistory'
import { LessonPreview } from './components/LessonPreview'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState<'generate' | 'history'>('generate')
  const [previewLessonId, setPreviewLessonId] = useState<string | null>(null)

  const handleViewLesson = (lessonId: string) => {
    setPreviewLessonId(lessonId)
  }

  return (
    <div className="min-h-screen">
      <Header />
  <main className="max-w-screen-2xl mx-auto px-8 py-12">
        {/* Tab Navigation (spans full width so sidebar lines up with generator) */}
        <div className="mb-6">
          <nav>
            <div className="flex space-x-4">
              <button
                onClick={() => setActiveTab('generate')}
                className={`px-6 py-3 text-sm font-medium tracking-wide transition-colors duration-200 border ${
                  activeTab === 'generate'
                    ? 'bg-swiss-black text-swiss-white border-swiss-black'
                    : 'bg-swiss-white text-swiss-black border-swiss-gray-300 hover:border-swiss-black'
                }`}
              >
                Generate Lessons
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`px-6 py-3 text-sm font-medium tracking-wide transition-colors duration-200 border ${
                  activeTab === 'history'
                    ? 'bg-swiss-black text-swiss-white border-swiss-black'
                    : 'bg-swiss-white text-swiss-black border-swiss-gray-300 hover:border-swiss-black'
                }`}
              >
                Lesson History
              </button>
            </div>
          </nav>
        </div>

  <div className="md:grid md:grid-cols-5 gap-8 items-start">
          {/* Main content (generator/history) */}
          <div className="md:col-span-3">
            <div>
              {activeTab === 'generate' && <LessonGenerator />}
              {activeTab === 'history' && <LessonHistory onViewLesson={handleViewLesson} />}
            </div>
          </div>

          {/* Sidebar is the detailed block below */}
            <aside className="md:col-span-2">
              <div className="bg-swiss-white border border-swiss-gray-200 p-6 rounded-md">
                <h3 className="text-lg font-medium text-swiss-black mb-3">📚 How to Use Lessons</h3>


                <h4 className="text-sm font-medium text-swiss-black mb-2">🎯 Step-by-Step Workflow</h4>
                <div className="space-y-2 mb-4">
                  <div className="flex items-start space-x-2">
                    <span className="flex-shrink-0 w-5 h-5 bg-swiss-black text-swiss-white text-xs flex items-center justify-center rounded-full font-medium">1</span>
                    <div>
                      <p className="text-sm font-medium text-swiss-black">Generate or Browse</p>
                      <p className="text-xs text-swiss-gray-600">Generate lessons on the topics you wish to learn, or check out the modules from the lesson history tab.</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="flex-shrink-0 w-5 h-5 bg-swiss-black text-swiss-white text-xs flex items-center justify-center rounded-full font-medium">2</span>
                    <div>
                      <p className="text-sm font-medium text-swiss-black">Download & Run</p>
                      <p className="text-xs text-swiss-gray-600">Download lesson modules to your computer. Run the example code to see how it works in practice.</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="flex-shrink-0 w-5 h-5 bg-swiss-black text-swiss-white text-xs flex items-center justify-center rounded-full font-medium">3</span>
                    <div>
                      <p className="text-sm font-medium text-swiss-black">Write, Experiment & Modify</p>
                      <p className="text-xs text-swiss-gray-600">Finish the exercises, add features, break things and fix them. This hands-on experimentation is where real learning happens.</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-2">
                    <span className="flex-shrink-0 w-5 h-5 bg-swiss-black text-swiss-white text-xs flex items-center justify-center rounded-full font-medium">4</span>
                    <div>
                      <p className="text-sm font-medium text-swiss-black">Use Git and GitHub to learn version control</p>
                      <p className="text-xs text-swiss-gray-600">Create a learning portfolio to track your progress and showcase your skills. Use tools like GitHub actions to automate testing.</p>
                    </div>
                  </div>
                </div>

                <h4 className="text-sm font-medium text-swiss-black mb-2">🚀 Version Control Setup</h4>
                <p className="text-xs text-swiss-gray-600 mb-2">Track your learning progress with Git and share your work on GitHub:</p>
                <div className="bg-swiss-gray-100 p-3 rounded mb-3">
                  <pre className="text-xs text-swiss-gray-800 overflow-auto">{`git init
git add .
git commit -m "Initial lesson modules"
git remote add origin <your-repo-url>
git push -u origin main`}</pre>
                </div>

                <div className="text-xs text-swiss-gray-600 space-y-1">
                  <p><strong>Best Practices:</strong></p>
                  <ul className="list-disc list-inside space-y-1 ml-2">
                    <li>Commit after completing each lesson or major change</li>
                    <li>Write clear commit messages describing what you learned</li>
                    <li>Add README files to document your learning notes and how to run each module</li>
                  </ul>
                </div>

              </div>
            </aside>
        </div>

        {/* Preview Modal */}
        {previewLessonId && (
          <LessonPreview
            lessonId={previewLessonId}
            onClose={() => setPreviewLessonId(null)}
            onDownload={() => {
              setPreviewLessonId(null)
              // Download will be handled by the LessonPreview component
            }}
          />
        )}
      </main>
    </div>
  )
}

export default App