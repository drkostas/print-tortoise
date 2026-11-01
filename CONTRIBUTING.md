# Contributing

```bash
pip install -e '.[test]'
pytest -q
```

The tests use whichever engines the machine has. Ghostscript and Apple's engine are compared only where they are present.
