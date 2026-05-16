# CLAUDE.md — Working in this repository

This file tells Claude how to contribute to PersistentMemoryforAgents.

## Core principles

- **Readable over clever.** Prefer clear variable names and short functions over terse one-liners.
- **Modular by design.** Each file in `app/` has a single responsibility. Do not let concerns bleed across modules.
- **No paid APIs.** Do not introduce OpenAI, Anthropic, Cohere, or any other cloud AI API. All ML must run locally or be approximated with standard libraries.
- **FastAPI + stdlib first.** Prefer FastAPI and Python standard libraries. If adding a new package, justify it and add it to `requirements.txt`.
- **No overengineering.** Do not add abstract base classes, factory patterns, or plugin systems unless the complexity clearly demands them. Three readable functions beat a premature abstraction.

## Making changes

1. Find the relevant module in `app/`. Each file owns one concern (see `docs/ARCHITECTURE.md` for the component map).
2. Add or update a test in `tests/test_memory.py` for every new behavior.
3. If you change a public API endpoint, a model field, or the scoring formula, update `docs/ARCHITECTURE.md`.
4. Write short, factual commit messages ("add BM25 retrieval", not "implement sophisticated search algorithm").

## Running the server

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

## Running tests

```bash
pytest tests/ -v
```

## Scoring changes

`retrieval.py:composite_score` drives every retrieval result and every GC decision. Changing its weights is a significant change. Test against the full suite and explain the tradeoff in the PR.

## What to avoid

- Circular imports between `app/` modules
- Business logic in `app/main.py` route functions — delegate to `MemoryManager`
- Catching broad `Exception` silently
- Leaving `# TODO` stubs without a follow-up task
- Adding `print()` debug statements to committed code
