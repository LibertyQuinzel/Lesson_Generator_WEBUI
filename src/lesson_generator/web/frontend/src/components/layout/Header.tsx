export const Header = () => {
  return (
    <header className="bg-swiss-white border-b border-swiss-gray-200">
      <div className="max-w-7xl mx-auto px-8 py-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-light tracking-tight text-swiss-black leading-none mb-1">
              Lesson Generator
            </h1>
            <p className="text-xs font-normal text-swiss-gray-600 tracking-wide uppercase">
              Programming Course Creator
            </p>
          </div>
          <nav className="hidden md:flex items-center space-x-8 mt-1">
            <a
              href="/api/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-swiss-black hover:text-swiss-blue transition-colors duration-200 tracking-wide border-b border-transparent hover:border-swiss-blue pb-1"
            >
              API Documentation
            </a>
            <a
              href="/api/v1/system/health"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-swiss-black hover:text-swiss-blue transition-colors duration-200 tracking-wide border-b border-transparent hover:border-swiss-blue pb-1"
            >
              System Status
            </a>
          </nav>
        </div>
      </div>
    </header>
  )
}