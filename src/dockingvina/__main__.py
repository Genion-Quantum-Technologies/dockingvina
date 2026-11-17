"""Stateless Argo stage entrypoint."""
from .steps import main

if __name__ == "__main__":
    raise SystemExit(main())
