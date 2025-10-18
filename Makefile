.PHONY: test coverage build

test:
	pytest

coverage:
	pytest --cov=anbapi/app --cov-report=xml:coverage.xml

build:
	docker build -f anbapi/Dockerfile -t anbapi:dev .
