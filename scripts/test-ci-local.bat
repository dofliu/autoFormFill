@echo off
REM Local CI test script for AutoFormFill (Windows)
REM Run this script to test CI/CD pipeline locally

echo 🚀 Starting local CI test for AutoFormFill...
echo ==============================================

REM Check Python version
echo 1. Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo ✗ Python check failed
    exit /b 1
)
echo ✓ Python check

REM Check Node.js version
echo 2. Checking Node.js version...
node --version
if %errorlevel% neq 0 (
    echo ✗ Node.js check failed
    exit /b 1
)
echo ✓ Node.js check

REM Install Python dependencies
echo 3. Installing Python dependencies...
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio black flake8 mypy isort ruff bandit safety
if %errorlevel% neq 0 (
    echo ✗ Python dependencies failed
    exit /b 1
)
echo ✓ Python dependencies

REM Install frontend dependencies
echo 4. Installing frontend dependencies...
cd frontend
npm ci
if %errorlevel% neq 0 (
    echo ✗ Frontend dependencies failed
    exit /b 1
)
echo ✓ Frontend dependencies
cd ..

REM Run Python linters
echo 5. Running Python linters...

echo   - Running black...
black --check --diff .
if %errorlevel% neq 0 (
    echo ✗ Black formatting failed
    exit /b 1
)
echo ✓ Black formatting

echo   - Running isort...
isort --check-only --diff .
if %errorlevel% neq 0 (
    echo ✗ Import sorting failed
    exit /b 1
)
echo ✓ Import sorting

echo   - Running flake8...
flake8 . --count --show-source --statistics
if %errorlevel% neq 0 (
    echo ✗ Flake8 linting failed
    exit /b 1
)
echo ✓ Flake8 linting

echo   - Running ruff...
ruff check .
if %errorlevel% neq 0 (
    echo ✗ Ruff linting failed
    exit /b 1
)
echo ✓ Ruff linting

echo   - Running mypy...
mypy --ignore-missing-imports --show-error-codes .
if %errorlevel% neq 0 (
    echo ✗ Type checking failed
    exit /b 1
)
echo ✓ Type checking

REM Run security checks
echo 6. Running security checks...

echo   - Running bandit...
bandit -r app -f json -o bandit-report.json
if %errorlevel% neq 0 (
    echo ⚠ Bandit scan completed (warnings allowed)
) else (
    echo ✓ Bandit scan
)

echo   - Running safety...
safety check --full-report
if %errorlevel% neq 0 (
    echo ⚠ Safety check completed (warnings allowed)
) else (
    echo ✓ Safety check
)

REM Create test directories
echo 7. Creating test directories...
if not exist test_uploads mkdir test_uploads
if not exist test_outputs mkdir test_outputs
if not exist test_chroma mkdir test_chroma
if not exist data mkdir data
echo ✓ Test directories

REM Run Python tests
echo 8. Running Python tests...
python -m pytest tests/ -v --cov=app --cov-report=term --cov-report=html --maxfail=5 --disable-warnings
if %errorlevel% neq 0 (
    echo ✗ Python tests failed
    exit /b 1
)
echo ✓ Python tests

REM Run frontend checks
echo 9. Running frontend checks...
cd frontend

echo   - TypeScript type checking...
npx tsc --noEmit --project tsconfig.json
if %errorlevel% neq 0 (
    echo ✗ TypeScript type checking failed
    exit /b 1
)
echo ✓ TypeScript type checking

echo   - ESLint...
npm run lint
if %errorlevel% neq 0 (
    echo ✗ ESLint failed
    exit /b 1
)
echo ✓ ESLint

echo   - Building frontend...
npm run build
if %errorlevel% neq 0 (
    echo ✗ Frontend build failed
    exit /b 1
)
echo ✓ Frontend build

REM Check build output
if exist dist (
    echo   - Build output check...
    dir dist
    echo ✓ Build output
) else (
    echo ✗ Build failed: dist directory not found
    exit /b 1
)

cd ..

REM Clean up test directories
echo 10. Cleaning up test directories...
rmdir /s /q test_uploads 2>nul
rmdir /s /q test_outputs 2>nul
rmdir /s /q test_chroma 2>nul
echo ✓ Cleanup

REM Docker build test (optional - skip if Docker not installed)
echo 11. Testing Docker builds (optional)...

where docker >nul 2>nul
if %errorlevel% equ 0 (
    echo   - Building backend Docker image...
    docker build -t autoformfill-backend:local-test -f Dockerfile .
    if %errorlevel% neq 0 (
        echo ⚠ Backend Docker build failed (optional)
    ) else (
        echo ✓ Backend Docker build
    )
    
    echo   - Building frontend Docker image...
    docker build -t autoformfill-frontend:local-test -f Dockerfile.frontend .
    if %errorlevel% neq 0 (
        echo ⚠ Frontend Docker build failed (optional)
    ) else (
        echo ✓ Frontend Docker build
    )
    
    echo   - Testing docker-compose configuration...
    docker-compose config
    if %errorlevel% neq 0 (
        echo ⚠ Docker Compose config failed (optional)
    ) else (
        echo ✓ Docker Compose config
    )
    
    echo   - Cleaning up Docker images...
    docker rmi autoformfill-backend:local-test 2>nul
    docker rmi autoformfill-frontend:local-test 2>nul
    echo ✓ Docker cleanup
) else (
    echo ⚠ Docker not installed, skipping Docker tests
)

echo.
echo ==============================================
echo ✅ All local CI tests passed!
echo ==============================================
echo.
echo Next steps:
echo 1. Commit your changes: git add . && git commit -m "Your message"
echo 2. Push to GitHub: git push origin main
echo 3. Check GitHub Actions for automated CI/CD pipeline
echo.
echo For production deployment:
echo - Set up GitHub Secrets for API keys
echo - Configure deployment environment
echo - Review security settings