"""Entry point de Glue para el job raw->processed (+ quarantine)."""

# Nota: NO usar sys.exit() en Glue — el runner interpreta SystemExit como
# fallo del job aunque el código de salida sea 0.

from src.etl import raw_to_processed

if __name__ == "__main__":
    raw_to_processed.run()
