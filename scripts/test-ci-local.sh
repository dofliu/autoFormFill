#!/bin/bash
# Local CI test script for AutoFormFill
# Run this script to test CI/CD pipeline locally

set -e

echo "🚀 Starting local CI test for AutoFormFill..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

# Check Python version
echo "1. Checking Python version..."
python --version
print_status $? "Python check"

# Check Node.js version
echo "2. Checking Node.js version..."
node --version
print_status $? "Node.js check"

# Install Python dependencies
echo "3. Installing Python dependencies..."
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio black flake8 mypy isort ruff bandit safety
print_status $? "Python dependencies"

# Install frontend dependencies
echo "4. Installing frontend dependencies..."
cd frontend
npm ci
print_status $? "Frontend dependencies"
cd ..

# Run Python linters
echo "5. Running Python linters..."

echo "  - Running black..."
black --check --diff .
print_status $? "Black formatting"

echo "  - Running isort..."
isort --check-only --diff .
print_status $? "Import sorting"

echo "  - Running flake8..."
flake8 . --count --show-source --statistics
print_status $? "Flake8 linting"

echo "  - Running ruff..."
ruff check .
print_status $? "Ruff linting"

echo "  - Running mypy..."
mypy --ignore-missing-imports --show-error-codes .
print_status $? "Type checking"

# Run security checks
echo "6. Running security checks..."

echo "  - Running bandit..."
bandit -r app -f json -o bandit-report.json || true
echo "Bandit scan completed (warnings allowed)"

echo "  - Running safety..."
safety check --full-report || echo "Safety check completed (warnings allowed)"

# Create test directories
echo "7. Creating test directories..."
mkdir -p test_uploads test_outputs test_chroma data
print_status $? "Test directories"

# Run Python tests
echo "8. Running Python tests..."
python -m pytest tests/ -v --cov=app --cov-report=term --cov-report=html --maxfail=5 --disable-warnings
print_status $? "Python tests"

# Run frontend checks
echo "9. Running frontend checks..."
cd frontend

echo "  - TypeScript type checking..."
npx tsc --noEmit --project tsconfig.json
print_status $? "TypeScript type checking"

echo "  - ESLint..."
npm run lint
print_status $? "ESLint"

echo "  - Building frontend..."
npm run build
print_status $? "Frontend build"

# Check build output
if [ -d "dist" ]; then
    echo "  - Build output check..."
    ls -la dist/
    print_status 0 "Build output"
else
    echo -e "${RED}✗ Build failed: dist directory not found${NC}"
    exit 1
fi

cd ..

# Clean up test directories
echo "10. Cleaning up test directories..."
rm -rf test_uploads test_outputs test_chroma
print_status $? "Cleanup"

# Docker build test
echo "11. Testing Docker builds..."

echo "  - Building backend Docker image..."
docker build -t autoformfill-backend:local-test -f Dockerfile .
print_status $? "Backend Docker build"

echo "  - Building frontend Docker image..."
docker build -t autoformfill-frontend:local-test -f Dockerfile.frontend .
print_status $? "Frontend Docker build"

echo "  - Testing docker-compose configuration..."
docker-compose config
print_status $? "Docker Compose config"

# Clean up Docker images
echo "12. Cleaning up Docker images..."
docker rmi autoformfill-backend:local-test autoformfill-frontend:local-test || true
print_status $? "Docker cleanup"

echo ""
echo "=============================================="
echo -e "${GREEN}✅ All local CI tests passed!${NC}"
echo "=============================================="
echo ""
echo "Next steps:"
echo "1. Commit your changes: git add . && git commit -m 'Your message'"
echo "2. Push to GitHub: git push origin main"
echo "3. Check GitHub Actions for automated CI/CD pipeline"
echo ""
echo "For production deployment:"
echo "- Set up GitHub Secrets for API keys"
echo "- Configure deployment environment"
echo "- Review security settings"