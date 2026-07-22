"""ETL PySpark de LogiFlow: landing → raw → processed (+ quarantine).

Los jobs son portables: corren en Spark local (pruebas) y en AWS Glue
(producción) sin dependencias de awsglue — los argumentos llegan por CLI.
"""
