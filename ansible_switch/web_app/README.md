# Ansible Switch Manager - Web Interface

Interfaz web para el proyecto Ansible Switch Manager. Replica todas las funcionalidades del CLI original (`menu.py`) en un navegador web.

## Requisitos

- Python 3.10+
- FastAPI, uvicorn, pydantic

## Instalacion

```bash
pip install -r requirements.txt
```

## Uso

### Opcion 1: Script directo
```bash
start.bat
```

### Opcion 2: Manual
```bash
python -m uvicorn web_app.app:app --host 0.0.0.0 --port 8000
```

### Opcion 3: Desde Python
```bash
python app.py
```

Luego abre tu navegador en: **http://localhost:8000**

## Funcionalidades

La interfaz web replica exactamente las mismas pantallas e interacciones del CLI original:

| Pantalla | Descripcion |
|----------|-------------|
| **Home** | Topologia de switches con arbol jerarquico + menu de opciones |
| **Reset IPs** | Restaura todas las IPs a sus valores por defecto |
| **Assign IP** | Lista numerada de switches, seleccion por nombre, validacion de IP |
| **Ping** | Ping a switch individual o a cualquier host/IP, configurable cantidad de paquetes |
| **Ping All** | Ping a todos los switches con barra de progreso y tabla resumen |
| **Discovery** | Monitor de red en vivo con auto-refresh, escaneo profundo, asignacion de IPs descubiertas |

## Esquema de Colores

Los colores coinciden con el CLI original:
- **Cyan**: Bordes, headers, titulos
- **Verde**: IPs, exitos, dispositivos online
- **Amarillo**: Teclas de menu, nombres de switches
- **Rojo**: Errores, timeouts, dispositivos offline
- **Magenta**: Titulos de secciones
- **Gris (dim)**: Texto secundario, estadisticas

## API Endpoints

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/api/topology` | Topologia completa con IPs actuales |
| GET | `/api/switches` | Lista simplificada de switches |
| POST | `/api/reset-ips` | Restaura IPs por defecto |
| POST | `/api/assign-ip` | Asigna IP a un switch |
| POST | `/api/ping` | Ping a un target |
| POST | `/api/ping-all` | Ping a todos los switches |
| GET | `/api/discovery` | Dispositivos descubiertos (ARP) |
| POST | `/api/discovery/assign` | Asigna IP descubierta a switch |
| POST | `/api/discovery/sweep` | Inicia ping sweep de red |
