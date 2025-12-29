#!/bin/bash

# Build script for Lesson Generator Web Interface
# This script builds the React frontend and integrates it with the FastAPI backend

set -e

echo "🏗️  Building Lesson Generator Web Interface..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Install frontend dependencies if node_modules doesn't exist
FRONTEND_DIR="src/lesson_generator/web/frontend"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    npm install
    cd -
fi

# Build the React frontend
echo "⚛️  Building React frontend..."
cd "$FRONTEND_DIR"
npm run build
cd -

# Copy built files to FastAPI static directory
STATIC_DIR="src/lesson_generator/web/static-new"
if [ -d "$STATIC_DIR" ]; then
    echo "✨ Frontend built successfully!"
    echo "📁 Static files available at: $STATIC_DIR"
    echo ""
    echo "🚀 To start the web interface:"
    echo "   python -m lesson_generator.web.main"
    echo ""
    echo "🌐 Then open: http://localhost:8000"
else
    echo "❌ Error: Build failed - static directory not found"
    exit 1
fi

echo "✅ Build complete!"