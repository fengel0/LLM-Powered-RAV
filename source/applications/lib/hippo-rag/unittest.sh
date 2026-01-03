set -e 
pytest tests/test_helper.py
pytest tests/test_indexer.py
pytest tests/test_hippo_rag.py
