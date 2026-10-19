"""支持 `python -m retrospective_agent ...`。"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
