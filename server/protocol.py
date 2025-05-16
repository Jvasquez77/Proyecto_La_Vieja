"""
Protocolo de comunicación para el juego.
Define los comandos y formatos de mensajes entre cliente y servidor.
"""

# Prefijos de comandos
CMD_CREATE = "CREATE"        # Crear una sala
CMD_JOIN = "JOIN"            # Unirse a una sala
CMD_MOVE = "MOVE"            # Realizar un movimiento
CMD_UPDATE = "UPDATE"        # Actualización del estado del juego
CMD_END = "END"              # Fin del juego
CMD_ERROR = "ERROR"          # Mensaje de error
CMD_LIST = "LIST"            # Listar salas disponibles
CMD_LEAVE = "LEAVE"          # Abandonar una sala
CMD_ROOM_CLOSED = "ROOM_CLOSED"  # Notificación de sala cerrada

# Separador para los mensajes
SEP = "|"

# Códigos de estado del juego
STATUS_WAITING = "WAITING"   # Esperando otro jugador
STATUS_PLAYING = "PLAYING"   # Juego en curso
STATUS_WIN = "WIN"           # Victoria
STATUS_LOSS = "LOSS"         # Derrota
STATUS_DRAW = "DRAW"         # Empate

def create_message(command, *args):
    """Crea un mensaje con el formato del protocolo."""
    return f"{command}{SEP}{SEP.join(str(arg) for arg in args)}"

def parse_message(message):
    """Analiza un mensaje recibido según el protocolo."""
    parts = message.strip().split(SEP)
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    return command, args 