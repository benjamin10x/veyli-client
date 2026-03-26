# VEYLI Client

Portal del cliente para consultar y gestionar sus envios. Este proyecto consume la API central y presenta una interfaz enfocada al usuario final.

## Objetivo

Desde aqui el cliente puede:

- iniciar sesion o registrarse
- ver resumen de actividad
- crear envios
- consultar mis envios
- revisar historial
- rastrear paquetes
- editar su perfil
- revisar notificaciones y estado de sus entregas

## Stack

- Python 3.12
- Flask 3
- Jinja2
- Requests

## Puerto y contenedor

- Cliente web: `http://localhost:5001`

Servicio Docker:

- `veyli-client`

## Conexion con la API

El cliente depende directamente de la API de [`/home/ben/pi/api`](/home/ben/pi/api).

Valor comun en Docker local:

```txt
http://host.docker.internal:8001/api/v1
```

## Variables principales

Archivo base: [`.env.example`](/home/ben/pi/veyli-client/.env.example)

Variables importantes:

- `FLASK_ENV`
- `SECRET_KEY`
- `API_BASE_URL`
- `API_TIMEOUT`
- `JWT_STORAGE_MODE`

## Levantar con Docker

Desde [`/home/ben/pi/veyli-client`](/home/ben/pi/veyli-client):

```bash
docker compose up -d --build
```

Ver logs:

```bash
docker logs -f veyli-client
```

Detener:

```bash
docker compose down
```

## Ejecutar sin Docker

```bash
cd /home/ben/pi/veyli-client
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## Estructura

```text
veyli-client/
├── app/
│   ├── templates/      # vistas Jinja
│   ├── static/         # estilos e imagenes
│   ├── routes.py       # rutas Flask
│   ├── api_client.py   # cliente HTTP hacia FastAPI
│   └── __init__.py
├── tests/
├── Dockerfile
├── docker-compose.yml
└── run.py
```

## Pantallas principales

- `Inicio`
- `Mis envios`
- `Rastrear envio`
- `Historial`
- `Perfil`
- `Soporte`
- `Login`
- `Registro`
- `Recuperar contrasena`

## Sesion y autenticacion

- la autenticacion se hace contra la API
- la sesion se guarda en Flask
- si el token expira, el cliente limpia la sesion y redirige automaticamente al login
- el registro publico crea usuarios cliente por defecto

## Notificaciones

El header del cliente consume el feed de notificaciones desde la API.

Comportamiento actual:

- solo ve notificaciones relacionadas con sus propios envios
- el contador muestra pendientes no vistas
- al abrir el panel, se consideran vistas y el contador baja a cero
- cuando entran nuevas notificaciones, el contador vuelve a subir

## Flujo recomendado de trabajo

1. Levantar primero la API
2. Confirmar `API_BASE_URL`
3. Levantar el cliente
4. Iniciar sesion o registrar cuenta

## Problemas comunes

`401 Unauthorized`

- la API no esta disponible, el token expiro o `API_BASE_URL` es incorrecta

`No cargan envios o historial`

- revisa logs del cliente y la respuesta de la API

`No abre localhost:5001`

- verifica que el contenedor `veyli-client` este arriba

`Las vistas no reflejan cambios`

- si estas usando Docker con volumen, recarga el navegador y revisa logs del contenedor
