# Contributing

## Project setup

```bash
cp .env.example .env
docker compose -p school up -d
docker exec school-app-1 python seed_data.py
```

## Code style

- Python: follow PEP 8
- Templates: match existing patterns
- No comments in code unless necessary for clarity

## Before committing

```bash
# Run the app and verify it works
docker compose -p school up -d
# Check that pages load without errors
```

## Commit messages

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` code change without feature/fix
- `chore:` maintenance
