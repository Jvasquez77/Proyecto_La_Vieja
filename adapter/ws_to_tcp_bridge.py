"""
Adaptador para conectar WebSockets (cliente web) con el servidor TCP.
Actúa como un puente entre la interfaz web y el servidor del juego.
"""

import asyncio
import websockets
import socket
import threading
import json
import sys
import os

# Modificar ruta para encontrar el módulo protocol
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))
try:
    from protocol import parse_message, create_message
except ImportError:
    # Definir funciones básicas en caso de que no se pueda importar
    def parse_message(message):
        parts = message.split('|')
        return parts[0], parts[1:] if len(parts) > 1 else []
        
    def create_message(command, *args):
        return command + '|' + '|'.join(str(arg) for arg in args)

class WebSocketToTCPBridge:
    """
    Puente que conecta clientes WebSocket con el servidor TCP.
    Mantiene una conexión TCP por cada conexión WebSocket.
    """
    
    def __init__(self, ws_port=8765, tcp_host='localhost', tcp_port=9000):
        """Inicializa el puente WebSocket a TCP."""
        self.ws_port = ws_port
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        
        # Mapeo de conexiones WebSocket a sockets TCP
        self.connections = {}
        
        # Lock para acceso seguro al diccionario de conexiones
        self.lock = threading.Lock()
        
        # Loop de eventos para cada hilo
        self.main_loop = None
    
    async def start(self):
        """Inicia el servidor WebSocket."""
        try:
            # Guardar el loop principal
            self.main_loop = asyncio.get_running_loop()
            
            print(f"DEBUG: Intentando iniciar servidor WebSocket en 0.0.0.0:{self.ws_port}")
            server = await websockets.serve(self.handle_websocket, "0.0.0.0", self.ws_port)
            print(f"Servidor WebSocket iniciado en el puerto {self.ws_port}")
            print(f"Conectando con servidor TCP en {self.tcp_host}:{self.tcp_port}")
            
            # Mantener el servidor en ejecución
            await server.wait_closed()
            
        except Exception as e:
            print(f"Error al iniciar el servidor WebSocket: {e}")
            print(f"DEBUG: Detalles del error: {type(e).__name__}")
            # Mostrar la pila de llamadas para depurar
            import traceback
            traceback.print_exc()
    
    async def handle_websocket(self, websocket):
        """Maneja una conexión WebSocket."""
        tcp_socket = None
        print(f"DEBUG: Nueva conexión WebSocket recibida")
        
        try:
            # Conectar al servidor TCP
            print(f"DEBUG: Intentando conectar a servidor TCP {self.tcp_host}:{self.tcp_port}")
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect((self.tcp_host, self.tcp_port))
            print(f"DEBUG: Conexión TCP establecida correctamente")
            
            # Registrar la conexión
            with self.lock:
                self.connections[websocket] = tcp_socket
            
            # Crear un evento para indicar cuándo finalizar el hilo
            close_event = threading.Event()
            
            # Iniciar hilo para recibir mensajes del servidor TCP
            tcp_thread = threading.Thread(
                target=self.receive_from_tcp,
                args=(tcp_socket, websocket, close_event, self.main_loop)
            )
            tcp_thread.daemon = True
            tcp_thread.start()
            
            # Recibir mensajes del cliente WebSocket
            try:
                print(f"DEBUG: Iniciando recepción de mensajes WebSocket")
                async for message in websocket:
                    print(f"DEBUG: Mensaje WebSocket recibido: {message[:50]}...")
                    try:
                        # Enviar al servidor TCP
                        tcp_socket.sendall((message + "\n").encode('utf-8'))
                        print(f"DEBUG: Mensaje enviado al servidor TCP")
                    except Exception as e:
                        print(f"Error al enviar mensaje al TCP: {e}")
                        break
            finally:
                print(f"DEBUG: Finalizando conexión WebSocket")
                close_event.set()  # Señalar al hilo que debe terminar
        
        except Exception as e:
            print(f"Error en la conexión WebSocket: {e}")
            print(f"DEBUG: Detalles del error en la conexión: {type(e).__name__}")
            # Mostrar la pila de llamadas para depurar
            import traceback
            traceback.print_exc()
        finally:
            # Limpiar recursos
            with self.lock:
                if websocket in self.connections:
                    del self.connections[websocket]
            
            if tcp_socket:
                try:
                    tcp_socket.close()
                    print(f"DEBUG: Socket TCP cerrado")
                except:
                    pass
    
    def receive_from_tcp(self, tcp_socket, websocket, close_event, loop):
        """Recibe mensajes del servidor TCP y los reenvía al cliente WebSocket."""
        buffer = ""
        
        try:
            while not close_event.is_set():
                # Configurar el socket para que sea no bloqueante con timeout
                tcp_socket.settimeout(0.1)
                
                try:
                    data = tcp_socket.recv(1024)
                    if not data:
                        break
                    
                    # Decodificar y procesar los datos recibidos
                    text = buffer + data.decode('utf-8')
                    buffer = ""
                    
                    # Procesar cada mensaje completo (terminado en \n)
                    lines = text.split('\n')
                    for i in range(len(lines) - 1):
                        if lines[i]:
                            # Enviar el mensaje de vuelta al websocket usando el loop principal
                            async def send_message(ws, msg):
                                try:
                                    await ws.send(msg)
                                except Exception as e:
                                    print(f"Error al enviar mensaje WebSocket: {e}")
                            
                            future = asyncio.run_coroutine_threadsafe(
                                send_message(websocket, lines[i]),
                                loop
                            )
                            # Esperar a que la tarea se complete
                            try:
                                future.result(timeout=1)
                            except Exception as e:
                                print(f"Error esperando el resultado: {e}")
                    
                    # Guardar el último fragmento si no está completo
                    if lines[-1]:
                        buffer = lines[-1]
                except socket.timeout:
                    # Timeout normal, verificar si debemos terminar
                    continue
                except Exception as e:
                    print(f"Error al recibir datos del TCP: {e}")
                    break
        
        except Exception as e:
            print(f"Error en hilo TCP: {e}")
        finally:
            # Cerrar la conexión TCP
            try:
                tcp_socket.close()
            except:
                pass
            
            # Cerrar la conexión WebSocket
            with self.lock:
                if websocket in self.connections:
                    del self.connections[websocket]
            
            # Cerrar la conexión WebSocket usando el loop principal
            async def close_ws(ws):
                try:
                    await ws.close()
                except:
                    pass
            
            try:
                asyncio.run_coroutine_threadsafe(close_ws(websocket), loop)
            except:
                pass

if __name__ == "__main__":
    # Obtener puertos de los argumentos o usar valores por defecto
    ws_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    tcp_host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
    tcp_port = int(sys.argv[3]) if len(sys.argv) > 3 else 9000
    
    # Crear e iniciar el puente
    bridge = WebSocketToTCPBridge(ws_port, tcp_host, tcp_port)
    
    try:
        asyncio.run(bridge.start())
    except KeyboardInterrupt:
        print("Puente detenido por el usuario")
    except Exception as e:
        print(f"Error al ejecutar el puente: {e}") 