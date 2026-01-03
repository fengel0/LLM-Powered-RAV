set -e
pytest -s tests/simple_request_test.py
pytest tests/sub_request_test.py

