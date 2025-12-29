#!/bin/bash

# Lesson Generator - Docker Deployment Script
set -e

echo "🚀 Deploying Lesson Generator with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your OpenAI API key before running the application."
    echo "   OPENAI_API_KEY=your_actual_api_key_here"
    echo ""
    read -p "Press Enter after configuring .env file to continue..."
fi

# Build and start the application
echo "🏗️  Building Docker images..."
docker-compose -f docker-compose.prod.yml build --no-cache

echo "🚀 Starting Lesson Generator..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for the application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if the application is healthy
echo "🔍 Checking application health..."
if curl -f http://localhost:8000/api/v1/system/health > /dev/null 2>&1; then
    echo "✅ Lesson Generator is running successfully!"
    echo ""
    echo "🌐 Web Interface: http://localhost:8000"
    echo "📋 API Documentation: http://localhost:8000/api/docs"
    echo ""
    echo "🔧 Management Commands:"
    echo "  View logs:      docker-compose -f docker-compose.prod.yml logs -f"
    echo "  Stop service:   docker-compose -f docker-compose.prod.yml down"
    echo "  Restart:        docker-compose -f docker-compose.prod.yml restart"
    echo "  Update:         ./deploy.sh"
else
    echo "❌ Application failed to start properly."
    echo "📋 Check logs with: docker-compose -f docker-compose.prod.yml logs"
    exit 1
fi