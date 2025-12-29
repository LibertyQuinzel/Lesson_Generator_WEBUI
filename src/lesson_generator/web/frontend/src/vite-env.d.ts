// CSS module definitions
declare module '*.css' {
  const content: Record<string, string>
  export default content
}

// Vite client types
/// <reference types="vite/client" />