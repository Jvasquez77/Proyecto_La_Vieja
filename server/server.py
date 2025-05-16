import socket
import threading
import uuid
import sys
import json
import os

# Importaciones de módulos del servidor
from game_room import GameRoom
from protocol import (
    CMD_CREATE, CMD_JOIN, CMD_MOVE, CMD_LIST, CMD_LEAVE,
    parse_message, create_message
)

class TicTacToeServer:
    
    def __init__(self, host='0.0.0.0', port=9000):
        """Inicializa el servidor."""
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
        # Diccionario de salas {room_id: GameRoom}
        self.rooms = {}
        self.rooms_lock = threading.Lock()
        
        # Diccionario para mapear sockets a salas {socket: room_id}
        self.client_rooms = {}
        self.client_lock = threading.Lock()
    
    def start(self):
        """Inicia el servidor y comienza a escuchar conexiones."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"Servidor iniciado en {self.host}:{self.port}")
            
            while self.running:
                client_socket, client_address = self.server_socket.accept()
                print(f"Nueva conexión desde {client_address}")
                
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("Servidor detenido por el usuario")
        except Exception as e:
            print(f"Error en el servidor: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el servidor y libera los recursos."""
        self.running = False
        
        with self.rooms_lock:
            for room in self.rooms.values():
                room.running = False
            self.rooms.clear()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
                
        print("Servidor detenido y recursos liberados")
    
    def handle_client(self, client_socket):
        """Maneja la comunicación con un cliente."""
        try:
            player_name = client_socket.recv(1024).decode('utf-8').strip()
            if not player_name:
                player_name = f"Jugador_{uuid.uuid4().hex[:6]}"
                
            print(f"Jugador conectado: {player_name}")
            
            while self.running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                for message in data.strip().split('\n'):
                    if not message:
                        continue
                        
                    self.process_message(client_socket, message, player_name)
                    
        except Exception as e:
            print(f"Error al manejar cliente: {e}")
        finally:
            self.remove_client(client_socket)
            try:
                client_socket.close()
            except:
                pass
    
    def process_message(self, client_socket, message, player_name):
        """Procesa un mensaje recibido de un cliente."""
        try:
            command, args = parse_message(message)
            
            if command == CMD_CREATE:
                self.create_room(client_socket, args, player_name)
            elif command == CMD_JOIN:
                self.join_room(client_socket, args, player_name)
            elif command == CMD_MOVE:
                self.process_move(client_socket, args)
            elif command == CMD_LIST:
                self.list_rooms(client_socket)
            elif command == CMD_LEAVE:
                self.leave_room(client_socket)
            else:
                print(f"Comando desconocido: {command}")
                
        except Exception as e:
            print(f"Error al procesar mensaje: {e}")
    
    def create_room(self, client_socket, args, player_name):
        """Crea una nueva sala de juego."""
        if len(args) < 1:
            return
            
        room_name = args[0]
        room_id = str(uuid.uuid4())
        
        with self.rooms_lock:
            self.leave_current_room(client_socket)
            
            room = GameRoom(room_id, room_name, client_socket, player_name, self.on_room_closed)
            self.rooms[room_id] = room
            
            with self.client_lock:
                self.client_rooms[client_socket] = room_id
            
            room.start()
            
            print(f"Sala creada: {room_name} (ID: {room_id}) por {player_name}")
            
            self.send_message(client_socket, "CREATE", room_id, room_name)
    
    def join_room(self, client_socket, args, player_name):
        """Une a un jugador a una sala existente."""
        if len(args) < 1:
            return
            
        room_id = args[0]
        
        with self.rooms_lock:
            if room_id not in self.rooms:
                self.send_message(client_socket, "ERROR", "Sala no encontrada")
                return
                
            room = self.rooms[room_id]
            
            self.leave_current_room(client_socket)
            
            if room.add_player(client_socket, player_name):
                with self.client_lock:
                    self.client_rooms[client_socket] = room_id
                    
                print(f"Jugador {player_name} unido a sala {room.room_name} (ID: {room_id})")
                
                self.send_message(client_socket, "JOIN", room_id, room.room_name)
            else:
                self.send_message(client_socket, "ERROR", "Sala llena")
    
    def process_move(self, client_socket, args):
        """Procesa un movimiento de un jugador."""
        if len(args) < 1:
            return
            
        try:
            position = int(args[0])
            
            room_id = self.get_client_room(client_socket)
            if not room_id:
                return
                
            with self.rooms_lock:
                if room_id not in self.rooms:
                    return
                    
                room = self.rooms[room_id]
                
                player_num = None
                if room.player1 and room.player1["socket"] == client_socket:
                    player_num = 1
                elif room.player2 and room.player2["socket"] == client_socket:
                    player_num = 2
                
                if player_num:
                    room.process_move(player_num, position)
                
        except ValueError:
            pass
    
    def list_rooms(self, client_socket):
        """Envía la lista de salas disponibles al cliente."""
        available_rooms = []
        
        with self.rooms_lock:
            for room_id, room in self.rooms.items():
                if room.status == "WAITING":
                    available_rooms.append({
                        "id": room_id,
                        "name": room.room_name,
                        "creator": room.player1["name"]
                    })
        
        self.send_message(client_socket, "LIST", json.dumps(available_rooms))
    
    def leave_room(self, client_socket):
        """Saca a un jugador de su sala actual."""
        self.leave_current_room(client_socket)
        
        self.send_message(client_socket, "LEAVE")
    
    def leave_current_room(self, client_socket):
        """Saca a un jugador de su sala actual (uso interno)."""
        room_id = self.get_client_room(client_socket)
        if not room_id:
            return
            
        with self.rooms_lock:
            if room_id in self.rooms:
                room = self.rooms[room_id]
                
                room.player_left(client_socket)
                
                if (not room.player1 or room.player1["socket"] == client_socket) and \
                   (not room.player2 or room.player2["socket"] == client_socket):
                    del self.rooms[room_id]
        
        with self.client_lock:
            if client_socket in self.client_rooms:
                del self.client_rooms[client_socket]
    
    def get_client_room(self, client_socket):
        """Obtiene el ID de la sala en la que está un cliente."""
        with self.client_lock:
            return self.client_rooms.get(client_socket)
    
    def remove_client(self, client_socket):
        """Elimina a un cliente del servidor."""
        self.leave_current_room(client_socket)
    
    def send_message(self, client_socket, command, *args):
        """Envía un mensaje a un cliente."""
        try:
            message = create_message(command, *args)
            client_socket.sendall((message + "\n").encode('utf-8'))
        except Exception as e:
            print(f"Error al enviar mensaje: {e}")

    def on_room_closed(self, room_id, players):
        """Maneja la notificación de que una sala ha sido cerrada."""
        print(f"Sala {room_id} cerrada, liberando jugadores...")
        
        with self.rooms_lock:
            if room_id in self.rooms:
                del self.rooms[room_id]
        
        # Liberar a los jugadores de la asignación a sala
        with self.client_lock:
            for socket, _ in players:
                if socket in self.client_rooms and self.client_rooms[socket] == room_id:
                    del self.client_rooms[socket]
        
        print(f"Jugadores liberados de la sala {room_id}, ahora pueden unirse a otras salas.")

if __name__ == "__main__":
    # Obtener puerto del primer argumento, o usar 9000 por defecto
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    
    # Crear e iniciar el servidor
    server = TicTacToeServer(port=port)
    server.start() 