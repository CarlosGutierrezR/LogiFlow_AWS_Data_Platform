"""Entry point de Glue para el job landing->raw.

Glue ejecuta este archivo como script; el código real llega en src.zip
vía --extra-py-files. Los argumentos del job (--date, --landing-path,
--raw-path) los define Terraform / start-job-run y los parsea el módulo.
"""

# Nota: NO usar sys.exit() en Glue — el runner interpreta SystemExit como
# fallo del job aunque el código de salida sea 0. Si run() lanza excepción,
# Glue marcará FAILED por sí solo.

from src.etl import landing_to_raw

if __name__ == "__main__":
    landing_to_raw.run()
