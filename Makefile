.PHONY: help install train test clean

help:
	@echo "Toxicity Detection - Available Commands"
	@echo "========================================"
	@echo "make install    - Install dependencies"
	@echo "make train      - Train the model"
	@echo "make test       - Test the model"
	@echo "make clean      - Clean results and logs"
	@echo "make format     - Format code with black"

install:
	pip install -r requirements.txt

train:
	python train.py

test:
	python test_model.py

clean:
	rm -rf results logs __pycache__ *.pyc
	find . -type d -name __pycache__ -delete

.PHONY: help install train test clean
