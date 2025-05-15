"""
Módulo que implementa la lógica de una sala de juego para Tic-Tac-Toe.
Cada sala es un hilo independiente que gestiona dos jugadores y su partida.
"""

import threading
import time
import random

# Estados del juego
STATUS_WAITING = "WAITING"
STATUS_PLAYING = "PLAYING" 
STATUS_WIN = "WIN"
STATUS_LOSS = "LOSS"
STATUS_DRAW = "DRAW"

# Comandos
CMD_UPDATE = "UPDATE"
CMD_END = "END"
CMD_ERROR = "ERROR"

def create_message(command, *args):
    return command + '|' + '|'.join(str(arg) for arg in args)

class GameRoom(threading.Thread):
    """
    Representa una sala de juego que gestiona una partida entre dos jugadores.
    Implementa la lógica del juego y la comunicación con los clientes.
    """
    
    def __init__(self, room_id, room_name, creator_socket, creator_name):
        """Inicializa una nueva sala de juego."""
        super().__init__()
        self.room_id = room_id
        self.room_name = room_name
        
        # Información de los jugadores
        self.player1 = {
            "socket": creator_socket,
            "name": creator_name,
            "symbol": "X"
        }
        self.player2 = None
        
        # Estado del juego
        self.board = [" " for _ in range(9)]
        self.current_turn = None
        self.status = STATUS_WAITING
        self.winner = None
        
        # Control de hilo
        self.daemon = True
        self.lock = threading.Lock()
        self.running = True
    
    def add_player(self, player_socket, player_name):
        """Añade un segundo jugador a la sala."""
        with self.lock:
            if self.player2 is not None:
                return False
                
            self.player2 = {
                "socket": player_socket,
                "name": player_name,
                "symbol": "O"
            }
            
            # Sala llena, comenzar juego
            self.status = STATUS_PLAYING
            self.current_turn = random.choice([1, 2])
            
            self._notify_game_start()
            return True
    
    def run(self):
        """Método principal del hilo. Gestiona el ciclo de vida del juego."""
        try:
            while self.player2 is None and self.running:
                time.sleep(0.5)
                
            if self.running:
                self._update_game_state()
                
                while self.status == STATUS_PLAYING and self.running:
                    time.sleep(0.1)
            
        except Exception as e:
            print(f"Error en sala {self.room_id}: {e}")
        finally:
            self._cleanup()
    
    def process_move(self, player_num, position):
        """Procesa un movimiento de un jugador."""
        with self.lock:
            if player_num != self.current_turn:
                return False
                
            if not (0 <= position <= 8) or self.board[position] != " ":
                return False
                
            symbol = "X" if player_num == 1 else "O"
            self.board[position] = symbol
            
            self.current_turn = 2 if player_num == 1 else 1
            
            self._check_game_state()
            self._update_game_state()
            
            return True
    
    def _check_game_state(self):
        """Comprueba si hay un ganador o un empate."""
        win_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Filas
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columnas
            [0, 4, 8], [2, 4, 6]              # Diagonales
        ]
        
        for combo in win_combinations:
            a, b, c = combo
            if self.board[a] != " " and self.board[a] == self.board[b] == self.board[c]:
                self.winner = 1 if self.board[a] == "X" else 2
                self.status = STATUS_WIN
                return
        
        if " " not in self.board:
            self.status = STATUS_DRAW
            return
    
    def _update_game_state(self):
        """Envía actualizaciones del estado del juego a ambos jugadores."""
        if not self.running:
            return
            
        if self.player2 is None:
            self._send_to_player(self.player1["socket"], CMD_UPDATE, 
                               STATUS_WAITING, self._board_to_string(), 0, "-")
            return
        
        p1_status = self.status
        p2_status = self.status
        
        if self.status == STATUS_WIN:
            p1_status = STATUS_WIN if self.winner == 1 else STATUS_LOSS
            p2_status = STATUS_WIN if self.winner == 2 else STATUS_LOSS
        
        self._send_to_player(self.player1["socket"], CMD_UPDATE, 
                           p1_status, self._board_to_string(), 
                           self.current_turn == 1, self.player2["name"])
                           
        self._send_to_player(self.player2["socket"], CMD_UPDATE, 
                           p2_status, self._board_to_string(), 
                           self.current_turn == 2, self.player1["name"])
        
        if self.status in [STATUS_WIN, STATUS_DRAW]:
            winner_name = None
            if self.winner:
                winner_name = self.player1["name"] if self.winner == 1 else self.player2["name"]
                
            end_message = "Empate" if self.status == STATUS_DRAW else f"Ganador: {winner_name}"
            
            self._send_to_player(self.player1["socket"], CMD_END, end_message)
            self._send_to_player(self.player2["socket"], CMD_END, end_message)
    
    def _notify_game_start(self):
        """Notifica a ambos jugadores que el juego ha comenzado."""
        self._send_to_player(self.player1["socket"], CMD_UPDATE, 
                           STATUS_PLAYING, self._board_to_string(), 
                           self.current_turn == 1, self.player2["name"])
                           
        self._send_to_player(self.player2["socket"], CMD_UPDATE, 
                           STATUS_PLAYING, self._board_to_string(), 
                           self.current_turn == 2, self.player1["name"])
    
    def _board_to_string(self):
        """Convierte el tablero a una representación de cadena."""
        return ",".join(self.board)
    
    def _send_to_player(self, socket, command, *args):
        """Envía un mensaje a un jugador."""
        try:
            message = create_message(command, *args)
            socket.sendall((message + "\n").encode('utf-8'))
        except Exception as e:
            print(f"Error al enviar mensaje: {e}")
            self.running = False
    
    def player_left(self, player_socket):
        """Gestiona la salida de un jugador."""
        with self.lock:
            if not self.running:
                return
                
            if self.player1 and self.player1["socket"] == player_socket:
                player_num = 1
                other_socket = self.player2["socket"] if self.player2 else None
                left_name = self.player1["name"]
            elif self.player2 and self.player2["socket"] == player_socket:
                player_num = 2
                other_socket = self.player1["socket"]
                left_name = self.player2["name"]
            else:
                return
            
            if other_socket:
                self._send_to_player(other_socket, CMD_ERROR, f"El jugador {left_name} ha abandonado la partida")
                self._send_to_player(other_socket, CMD_END, f"Victoria por abandono")
            
            self.running = False
    
    def _cleanup(self):
        """Limpia los recursos utilizados por la sala."""
        self.running = False
        
        try:
            if self.player1:
                self.player1["socket"].close()
        except:
            pass
            
        try:
            if self.player2:
                self.player2["socket"].close()
        except:
            pass
        
        print(f"Sala {self.room_id} cerrada y recursos liberados.") 