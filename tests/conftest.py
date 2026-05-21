import os

# Force in-memory backend for all tests so they never touch ~/.pma_store.db
os.environ.setdefault("PMA_STORAGE", "memory")
