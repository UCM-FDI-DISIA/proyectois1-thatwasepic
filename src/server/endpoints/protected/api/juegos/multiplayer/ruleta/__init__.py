"""Paquete de handlers de ruleta multijugador.

Este archivo se deja intencionadamente casi vacío: la definición
del blueprint y las rutas viven en `routes.py`. Tener un `bp` aquí
creaba una definición duplicada y conflictos al importar el
paquete desde el registrador automático de blueprints.

# Nada más aquí: `routes.py` declara el `bp` y se registrará por
# el mecanismo de discovery en `endpoints.register_blueprints()`.
"""