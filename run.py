"""
Script para iniciar todos los componentes del juego.
"""

import os
import sys
import subprocess
import time
import argparse
import webbrowser
import signal
import glob
import shutil

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def ensure_dependencies():
    """
    Verifica y asegura que todas las dependencias estén instaladas.
    
    Returns:
        bool: True si las dependencias están disponibles, False si se necesita reiniciar
    """
    global PSUTIL_AVAILABLE
    
    # Verificar si estamos en un entorno virtual
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    # Verificar si el módulo websockets está disponible
    try:
        import websockets
        websockets_available = True
    except ImportError:
        websockets_available = False
    
    # Si ya estamos en un entorno virtual y todas las dependencias están disponibles, no hacemos nada
    if in_venv and PSUTIL_AVAILABLE and websockets_available:
        return True
    
    # Si no estamos en un entorno virtual o faltan dependencias, proceder con la creación/activación
    print("Faltan dependencias necesarias. Configurando entorno...")
    
    # Verificar si ya existe un entorno virtual
    venv_dir = os.path.join(os.path.dirname(__file__), 'venv')
    venv_python = os.path.join(venv_dir, 'bin', 'python') if sys.platform != 'win32' else os.path.join(venv_dir, 'Scripts', 'python.exe')
    
    if not os.path.exists(venv_dir):
        print("Creando un entorno virtual...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', venv_dir], check=True)
            print(f"Entorno virtual creado en: {venv_dir}")
        except subprocess.CalledProcessError as e:
            print(f"Error al crear el entorno virtual: {e}")
            print("Intente manualmente con:")
            print(f"python3 -m venv {venv_dir}")
            print("source venv/bin/activate")
            print("pip install -r requirements.txt")
            return False
    
    # Intentar activar el entorno virtual e instalar dependencias
    pip_cmd = os.path.join(os.path.dirname(venv_python), 'pip') if sys.platform != 'win32' else os.path.join(os.path.dirname(venv_python), 'pip.exe')
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    print("Instalando dependencias en el entorno virtual...")
    try:
        subprocess.run([pip_cmd, 'install', '-r', requirements_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al instalar dependencias: {e}")
        print("Intente manualmente.")
        return False
    
    # Solo reiniciar si no estamos ya en el entorno virtual correcto
    if not in_venv:
        print("\nDependencias instaladas. Reiniciando con el entorno virtual...")
        arguments = sys.argv[:]
        
        os.execv(venv_python, [venv_python] + arguments)
        # No llegará aquí debido al execv
        return False
    
    # Si ya estábamos en el entorno virtual pero faltaban dependencias,
    # importamos los módulos ahora que están instalados
    if not PSUTIL_AVAILABLE:
        try:
            import psutil
            PSUTIL_AVAILABLE = True
        except ImportError:
            pass
            
    if not websockets_available:
        try:
            import websockets
        except ImportError:
            pass
    
    return True

def run_server(tcp_port, wait=False):
    """Ejecuta el servidor TCP."""
    print(f"Iniciando servidor TCP en el puerto {tcp_port}...")
    
    # Obtener la ruta del script server.py
    server_script = os.path.join(os.path.dirname(__file__), 'server', 'server.py')
    
    # Ejecutar el servidor como un proceso separado
    server_process = subprocess.Popen([sys.executable, server_script, str(tcp_port)])
    
    if wait:
        # Esperar un momento para que el servidor se inicie
        time.sleep(1)
    
    return server_process

def run_bridge(ws_port, tcp_host, tcp_port, wait=False):
    """Ejecuta el adaptador WebSocket a TCP."""
    print(f"Iniciando adaptador WebSocket en el puerto {ws_port}...")
    print(f"Conectando con servidor TCP en {tcp_host}:{tcp_port}...")
    
    # Obtener la ruta del script de puente
    bridge_script = os.path.join(os.path.dirname(__file__), 'adapter', 'ws_to_tcp_bridge.py')
    
    # Ejecutar el puente como un proceso separado
    bridge_process = subprocess.Popen([
        sys.executable, bridge_script, str(ws_port), tcp_host, str(tcp_port)
    ])
    
    if wait:
        # Esperar un momento para que el puente se inicie
        time.sleep(1)
    
    return bridge_process

def run_http_server(http_port):
    """Ejecuta un servidor HTTP simple para servir los archivos web."""
    print(f"Iniciando servidor HTTP en el puerto {http_port}...")
    
    # Obtener la ruta del directorio web
    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    
    # Cambiar al directorio web
    os.chdir(web_dir)
    
    # Ejecutar el servidor HTTP como un proceso separado
    http_process = subprocess.Popen([
        sys.executable, '-m', 'http.server', str(http_port)
    ])
    
    return http_process

def cleanup_resources(tcp_port, ws_port, http_port, processes=None):
    """
    Limpia recursos, libera puertos y elimina archivos temporales.
    
    Args:
        tcp_port: Puerto del servidor TCP
        ws_port: Puerto del servidor WebSocket
        http_port: Puerto del servidor HTTP
        processes: Lista de procesos a terminar
    """
    print("\nLimpiando recursos...")
    
    # Matar todos los procesos Python
    try:
        print("Terminando todos los procesos Python...")
        subprocess.run(["pkill", "-f", "python"], check=False)
        # Damos un pequeño tiempo para que los procesos terminen
        time.sleep(1) 
    except Exception as e:
        print(f"Error al terminar procesos Python: {e}")
    
    if processes:
        for process in processes:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    try:
                        process.kill()
                    except:
                        pass
    
    if PSUTIL_AVAILABLE:
        kill_processes_by_port(tcp_port)
        kill_processes_by_port(ws_port)
        kill_processes_by_port(http_port)
    else:
        print("No se pueden liberar puertos (psutil no disponible)")
    
    print("Buscando y eliminando archivos temporales...")
    temp_files = []
    temp_files.extend(glob.glob('**/*.pyc', recursive=True))
    temp_files.extend(glob.glob('**/__pycache__', recursive=True))
    temp_files.extend(glob.glob('**/*.log', recursive=True))
    
    # Agregar entornos virtuales a la lista de elementos a eliminar
    venv_path = os.path.join(os.path.dirname(__file__), 'venv')
    old_venv_path = os.path.join(os.path.dirname(__file__), '.venv')
    
    if os.path.exists(venv_path):
        temp_files.append(venv_path)
        print("Se eliminará el entorno virtual (venv)")
        
    if os.path.exists(old_venv_path):
        temp_files.append(old_venv_path)
        print("Se eliminará el entorno virtual (.venv)")
    
    for file in temp_files:
        try:
            if os.path.isdir(file):
                shutil.rmtree(file)
            else:
                os.remove(file)
        except Exception as e:
            print(f"No se pudo eliminar {file}: {e}")
    
    print("Limpieza completada.")

def kill_processes_by_port(port):
    """
    Busca y termina cualquier proceso que esté usando un puerto específico.
    
    Args:
        port: Puerto a liberar
    """
    try:
        # Intentar encontrar procesos usando un puerto específico
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.connections()
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"Terminando proceso {proc.pid} ({proc.name()}) en puerto {port}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except:
                            proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        print(f"Error al intentar liberar el puerto {port}: {e}")

def signal_handler(sig, frame):
    """
    Maneja señales de interrupción (Ctrl+C) para realizar limpieza.
    """
    print("\nInterrupción recibida. Finalizando procesos...")
    cleanup_resources(args.tcp_port, args.ws_port, args.http_port, [server_process, bridge_process, http_process])
    sys.exit(0)

def main():
    """Función principal que inicia todos los componentes."""
    global args, server_process, bridge_process, http_process
    
    parser = argparse.ArgumentParser(description='Iniciar el juego Tic-Tac-Toe multijugador')
    parser.add_argument('--tcp-port', type=int, default=9000, help='Puerto del servidor TCP (predeterminado: 9000)')
    parser.add_argument('--ws-port', type=int, default=8765, help='Puerto del servidor WebSocket (predeterminado: 8765)')
    parser.add_argument('--http-port', type=int, default=8000, help='Puerto del servidor HTTP (predeterminado: 8000)')
    parser.add_argument('--tcp-host', type=str, default='localhost', help='Host del servidor TCP (predeterminado: localhost)')
    parser.add_argument('--open-browser', action='store_true', help='Abrir el navegador automáticamente')
    parser.add_argument('--cleanup', action='store_true', help='Realizar limpieza de recursos y salir')
    
    args = parser.parse_args()
    
    # Verificar dependencias siempre, excepto para cleanup
    if not args.cleanup and not ensure_dependencies():
        # Si ensure_dependencies devuelve False, el script se reiniciará o falló
        return
    
    # Verificar dependencias si se está ejecutando cleanup
    if args.cleanup and not PSUTIL_AVAILABLE and not ensure_dependencies():
        # Si ensure_dependencies devuelve False, el script se reiniciará o falló
        return
    
    # Establecer el manejador de señales para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Si solo se requiere limpieza, ejecutar y salir
    if args.cleanup:
        cleanup_resources(args.tcp_port, args.ws_port, args.http_port)
        return
    
    server_process = None
    bridge_process = None
    http_process = None
    
    try:
        # Iniciar el servidor TCP
        server_process = run_server(args.tcp_port, wait=True)
        
        # Iniciar el adaptador WebSocket
        bridge_process = run_bridge(args.ws_port, args.tcp_host, args.tcp_port, wait=True)
        
        # Iniciar el servidor HTTP
        http_process = run_http_server(args.http_port)
        
        # Abrir el navegador si se solicita
        if args.open_browser:
            url = f"http://localhost:{args.http_port}"
            print(f"Abriendo navegador en {url}...")
            webbrowser.open(url)
        
        # Información para el usuario
        print("\n=== Juego Tic-Tac-Toe Multijugador ===")
        print(f"Servidor TCP ejecutándose en: {args.tcp_host}:{args.tcp_port}")
        print(f"Adaptador WebSocket ejecutándose en: ws://localhost:{args.ws_port}")
        print(f"Interfaz web disponible en: http://localhost:{args.http_port}")
        print("\nPresiona Ctrl+C para detener todos los servidores\n")
        
        # Mantener el script en ejecución
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDeteniendo servidores...")
    finally:
        # Terminar todos los procesos
        cleanup_resources(args.tcp_port, args.ws_port, args.http_port, [server_process, bridge_process, http_process])

if __name__ == "__main__":
    main() 