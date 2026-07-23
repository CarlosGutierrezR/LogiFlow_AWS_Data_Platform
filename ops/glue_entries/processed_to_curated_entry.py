"""Entry point de Glue para el job processed->curated (modelo dimensional).

Sin sys.exit(): Glue interpreta SystemExit como fallo aunque el código sea 0.
"""

from src.etl import processed_to_curated

if __name__ == "__main__":
    processed_to_curated.run()
