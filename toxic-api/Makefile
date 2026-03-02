.PHONY: help install dev test docker docker-up docker-down lint format clean

help:
	@echo "ToxicShield API - Available Commands"
	@echo "===================================="
	@echo "  make install       - Install dependencies"
	@echo "  make dev           - Run development server"
	@echo "  make test          - Run tests"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start Docker Compose"
	@echo "  make docker-down   - Stop Docker Compose"
	@echo "  make lint          - Lint code (requires pylint)"
	@echo "  make format        - Format code (requires black)"
	@echo "  make clean         - Clean cache and temp files"

install:
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

dev:
	python app.py

prod:
	uvicorn app:app --host 0.0.0.0 --port 8000

test:
	python test_api.py

docker-build:
	docker build -t toxic-api:latest .
	@echo "✅ Docker image built successfully"

docker-up:
	docker-compose up --build
	@echo "✅ Docker Compose started"

docker-down:
	docker-compose down
	@echo "✅ Docker Compose stopped"

lint:
	pylint app.py
	@echo "✅ Linting completed"

format:
	black app.py test_api.py
	@echo "✅ Code formatted"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
	@echo "✅ Cleaned cache and temporary files"

# Additional useful commands
check-health:
	curl http://localhost:8000/health | python -m json.tool

check-api:
	curl -X POST http://localhost:8000/api/check \
		-H "Content-Type: application/json" \
		-d '{"text": "You are stupid!", "threshold": 0.5}' | python -m json.tool

docs:
	@echo "📚 Opening API documentation..."
	@echo "Swagger UI: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"

venv:
	python3 -m venv venv
	@echo "✅ Virtual environment created"
	@echo "📝 Activate with: source venv/bin/activate (or venv\\Scripts\\activate on Windows)"
