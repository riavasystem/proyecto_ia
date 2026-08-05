"""Genera docs/openapi.json a partir del schema real de la app FastAPI.

Uso:
    python scripts/generate_openapi.py            # sobreescribe docs/openapi.json
    python scripts/generate_openapi.py --check     # falla si el archivo commiteado
                                                     # quedó desactualizado (CI)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.json"


def main() -> int:
    schema = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"

    if "--check" in sys.argv:
        current = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
        if current != schema:
            print(
                f"{OUTPUT_PATH} está desactualizado respecto al contrato real de la API.\n"
                "Corré 'python scripts/generate_openapi.py' y commiteá el resultado.",
                file=sys.stderr,
            )
            return 1
        print("docs/openapi.json está al día.")
        return 0

    OUTPUT_PATH.write_text(schema)
    print(f"Escrito {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
