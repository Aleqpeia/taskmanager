#!/bin/bash
# Run the complete test suite

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Please install it first:"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Ensure dependencies are installed
echo "Installing dependencies..."
poetry install --no-root
poetry install

# Run tests with coverage
echo "Running tests with coverage..."
poetry run pytest tests/ \
    --cov=src/taskmanager \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=85 \
    tests/test_*.py

echo "Running integration tests..."
poetry run pytest tests/test_integration.py -v

echo "Test results available in htmlcov/index.html" 