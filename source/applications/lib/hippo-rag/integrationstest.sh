set -e 
pytest ./tests/test_openie_integration.py
pytest ./tests/tests_indexer_integration.py
pytest ./tests/tests_retrival_integration.py
