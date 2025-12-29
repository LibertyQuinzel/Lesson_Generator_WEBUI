
interface ProgressTrackerProps {
  onCancel: () => void
}

export const ProgressTracker = ({
  onCancel
}: ProgressTrackerProps) => {
  return (
    <div className="bg-swiss-white border border-swiss-gray-200 p-8 space-y-8">
      <div className="text-center">
        <div className="relative inline-block mb-6">
          {/* Outer ring */}
          <div className="h-16 w-16 rounded-full border-4 border-swiss-gray-200"></div>
          {/* Rotating ring */}
          <div className="absolute inset-0 h-16 w-16 rounded-full border-4 border-transparent border-t-swiss-black animate-spin"></div>
          {/* Inner circle */}
          <div className="absolute inset-2 h-12 w-12 rounded-full bg-swiss-gray-100 flex items-center justify-center">
            <div className="h-8 w-8 rounded-full bg-swiss-black opacity-20"></div>
          </div>
        </div>
        <h3 className="text-lg font-light text-swiss-black mb-3 tracking-tight">
          Generating Your Lessons
        </h3>
        <p className="text-sm text-swiss-gray-600 tracking-wide">
          This process may take several minutes
        </p>
      </div>

      <button
        onClick={onCancel}
        className="w-full border border-swiss-gray-300 text-swiss-black py-3 px-8 hover:border-swiss-black focus:outline-none transition-colors duration-200 text-sm font-medium tracking-wide"
      >
        Cancel Generation
      </button>
    </div>
  )
}