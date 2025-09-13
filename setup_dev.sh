#!/bin/bash

# Django Development Setup Script
echo "🚀 Setting up Django development environment..."

# Activate virtual environment
source /home/smendez-/Documents/VerbPractice/.venv/bin/activate

# Run migrations
echo "📦 Running migrations..."
python manage.py migrate

# Create test users
echo "👥 Creating test users..."
python manage.py setup_test_users

echo "✅ Setup complete!"
echo ""
echo "🔑 Test credentials:"
echo "  admin: Pasw1234 (superuser)"
echo "  testuser1: Pasw1234"
echo "  testuser2: Pasw1234"
echo ""
echo "🌐 Start the server with: python manage.py runserver"
