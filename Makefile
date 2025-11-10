.PHONY: install lint test format clean run docker-build docker-run

install:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio faker pytest-mock black isort flake8 mypy

lint:
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	isort src/ tests/

test:
	pytest --cov=src/nlp_service --cov-report=html --cov-report=term-missing --cov-fail-under=80

test-fast:
	pytest -x -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
	rm -rf build dist *.egg-info

run:
	uvicorn nlp_service.api.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker-compose build

docker-run:
	docker-compose up

docker-down:
	docker-compose down

docker-clean:
	docker-compose down -v
