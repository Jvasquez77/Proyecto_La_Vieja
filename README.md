# Juego La Vieja

juego Clasico de Tres en Línea multijugador que se ejecuta sobre una arquitectura cliente-servidor utilizando sockets TCP/IP y una interfaz web.
## Características

- Servidor TCP multihilo en Python
- Interfaz de usuario web con HTML, CSS y JavaScript
- Comunicación en tiempo real a través de WebSockets
- Salas de juego independientes
- Sistema de turnos y validación de jugadas
- Notificaciones de estado del juego

## Arquitectura

El sistema sigue una arquitectura cliente-servidor:

- **Servidor**: Implementado en Python, maneja la lógica del juego, las salas y la comunicación TCP.
- **Cliente**: Interfaz web que se ejecuta en el navegador.
- **Adaptador**: Puente que conecta los WebSockets (navegador) con el servidor TCP.

### Diagrama de Componentes

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Cliente   │       │  Adaptador  │       │  Servidor   │
│    (Web)    │◄────► │  WebSocket  │◄────► │    TCP/IP   │
└─────────────┘       └─────────────┘       └─────────────┘
```

### Organización de Archivos

```
/
├── server/
│   ├── server.py           # Servidor TCP y lógica de salas
│   ├── game_room.py        # Clase GameRoom (hilo por sala)
│   └── protocol.py         # Protocolo de mensajes
├── web/
│   ├── index.html          # Interfaz de usuario
│   ├── styles.css          # Estilos visuales
│   └── client.js           # Lógica del cliente
├── adapter/
│   └── ws_to_tcp_bridge.py # Adaptador WebSocket ↔ TCP
├── run.py                  # Script de inicio y gestión
├── requirements.txt        # Dependencias
└── README.md               # Este archivo
```

## Requisitos

- Python 3.6 o superior
- Librerías de Python:
  - `websockets` (para el adaptador WebSocket)
  - `psutil` (para gestión de procesos y limpieza)

## Instalación

El script de inicio configurará automáticamente todo lo necesario, incluyendo la creación de un entorno virtual e instalación de dependencias si es necesario.

La instalacion Manual requeriria de:
```bash
python3 -m venv venv
source venv/bin/activate  
pip install -r requirements.txt
```

## Ejecución

1. Para Ejecutar todos los componentes a la vez:
```bash
python3 run.py --open-browser
```
Este script iniciará el servidor TCP, el adaptador WebSocket y un servidor HTTP simple,
y abrirá automáticamente el navegador si se usa la opción --open-browser.

2. Para iniciar componentes individualmente:

   a. Inicia el servidor TCP:
   ```bash
   python3 server/server.py [puerto]
   ```
   El puerto predeterminado es 9000.

   b. Inicia el adaptador WebSocket:
   ```bash
   python3 adapter/ws_to_tcp_bridge.py [puerto_ws] [host_tcp] [puerto_tcp]
   ```
   Los valores predeterminados son: puerto_ws=8765, host_tcp=localhost, puerto_tcp=9000.

   c. Servir los archivos web (si quieres jugar en red local):
   ```bash
   cd web
   python3 -m http.server 8000
   ```
   Y luego accede desde el navegador a: `http://localhost:8000/`

## Limpieza de Recursos

El proyecto incluye una funcionalidad para liberar recursos (procesos, puertos y archivos temporales):

```bash
python3 run.py --cleanup
```

Esta utilidad:
- Crea automáticamente un entorno virtual e instala las dependencias si es necesario
- Termina procesos que estén usando los puertos del servidor
- Elimina archivos temporales y cachés de Python
- Libera recursos del sistema utilizados por el juego

## Protocolo de Comunicación

La comunicación entre cliente y servidor utiliza un protocolo de mensajes simple basado en texto:

```
COMANDO|arg1|arg2|...
```

### Comandos Principales:

| Comando | Descripción              |
|---------|--------------------------|
| CREATE  | Crear una sala           |
| JOIN    | Unirse a una sala        |
| MOVE    | Realizar un movimiento   |
| UPDATE  | Actualización del estado |
| END     | Fin del juego            |
| LIST    | Listar salas disponibles |
| LEAVE   | Abandonar la sala        |
| ERROR   | Mensaje de error         |

## Conceptos Aplicados

- **Multiprogramación**: Se utiliza un hilo por sala de juego para gestionar las partidas en paralelo.
- **Gestión de Memoria**: Los recursos (sockets, hilos) se liberan cuando las salas se cierran.
- **Sincronización**: Se emplean mecanismos como `threading.Lock` para el acceso seguro a recursos compartidos.
- **Comunicación en Red**: Se implementa un sistema de comunicación basado en sockets TCP/IP.

## Autor

Julio Cesar Vasquez Garcia V-27.777.893