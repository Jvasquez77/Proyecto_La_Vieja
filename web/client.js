/**
 * Cliente Tic-Tac-Toe Multijugador
 * Gestiona la interfaz de usuario y la comunicación con el servidor.
 */

// Configuración del servidor WebSocket
const WS_SERVER = 'ws://localhost:8765';

// Variables globales
let socket = null;
let playerName = '';
let currentRoom = null;
let mySymbol = '';
let isMyTurn = false;
let gameBoard = Array(9).fill(' ');
let reconnectAttempts = 0;
let maxReconnectAttempts = 5;

// Estado actual del juego
const GameState = {
    DISCONNECTED: 'disconnected',
    MENU: 'menu',
    WAITING: 'waiting',
    PLAYING: 'playing',
    ENDED: 'ended'
};

let currentState = GameState.DISCONNECTED;

// Elementos DOM
const screens = {
    connection: document.getElementById('connection-screen'),
    menu: document.getElementById('menu-screen'),
    game: document.getElementById('game-screen'),
    end: document.getElementById('end-screen')
};

const elements = {
    playerNameInput: document.getElementById('playerName'),
    connectBtn: document.getElementById('connectBtn'),
    roomNameInput: document.getElementById('roomName'),
    createRoomBtn: document.getElementById('createRoomBtn'),
    refreshRoomsBtn: document.getElementById('refreshRoomsBtn'),
    roomList: document.getElementById('roomList'),
    currentRoomName: document.getElementById('currentRoomName'),
    gameStatus: document.getElementById('gameStatus'),
    player1: document.getElementById('player1'),
    player2: document.getElementById('player2'),
    turnIndicator: document.getElementById('turnIndicator'),
    board: document.getElementById('board'),
    boardCells: document.querySelectorAll('.board-cell'),
    leaveGameBtn: document.getElementById('leaveGameBtn'),
    endMessage: document.getElementById('endMessage'),
    backToMenuBtn: document.getElementById('backToMenuBtn'),
    notifications: document.getElementById('notifications')
};

// Inicialización
document.addEventListener('DOMContentLoaded', init);

function init() {
    // Configurar manejadores de eventos
    elements.connectBtn.addEventListener('click', connectToServer);
    elements.createRoomBtn.addEventListener('click', createRoom);
    elements.refreshRoomsBtn.addEventListener('click', requestRoomList);
    elements.leaveGameBtn.addEventListener('click', leaveGame);
    elements.backToMenuBtn.addEventListener('click', backToMenu);
    
    // Configurar eventos de las celdas del tablero
    elements.boardCells.forEach(cell => {
        cell.addEventListener('click', () => makeMove(cell));
    });

    // Permitir usar Enter para conectar
    elements.playerNameInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            connectToServer();
        }
    });

    // Permitir usar Enter para crear sala
    elements.roomNameInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            createRoom();
        }
    });

    // Auto-focus en el campo de nombre de jugador
    elements.playerNameInput.focus();
}

// Cambiar entre pantallas
function showScreen(screenName) {
    // Ocultar todas las pantallas
    Object.values(screens).forEach(screen => {
        screen.classList.add('hidden');
    });
    
    // Mostrar la pantalla solicitada
    screens[screenName].classList.remove('hidden');
}

// ========== CONEXIÓN ==========

// Conectar al servidor WebSocket
function connectToServer() {
    playerName = elements.playerNameInput.value.trim();
    
    if (!playerName) {
        showNotification('Por favor, ingresa tu nombre', 'error');
        return;
    }
    
    try {
        console.log('Intentando conectar a WebSocket en:', WS_SERVER);
        showNotification('Conectando al servidor...', 'info');
        
        // Crear conexión WebSocket
        socket = new WebSocket(WS_SERVER);
        
        // Configurar manejadores de eventos WebSocket
        socket.onopen = () => {
            console.log('Conexión WebSocket establecida');
            reconnectAttempts = 0;
            
            // Enviar nombre de jugador como primer mensaje
            socket.send(playerName);
            
            // Cambiar a la pantalla de menú
            currentState = GameState.MENU;
            showScreen('menu');
            
            // Solicitar lista de salas
            requestRoomList();
            
            showNotification('Conexión establecida', 'success');
        };
        
        socket.onmessage = (event) => {
            console.log('Mensaje recibido del servidor:', event.data);
            handleMessage(event);
        };
        
        socket.onclose = (event) => {
            console.log('Conexión WebSocket cerrada. Código:', event.code, 'Razón:', event.reason);
            
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                const delay = Math.min(1000 * reconnectAttempts, 5000);
                showNotification(`Conexión perdida. Reintentando en ${delay/1000} segundos...`, 'error');
                
                setTimeout(() => {
                    console.log(`Reintentando conexión (intento ${reconnectAttempts})...`);
                    connectToServer();
                }, delay);
            } else {
                showNotification('No se pudo reconectar. Recarga la página para intentar de nuevo.', 'error');
                currentState = GameState.DISCONNECTED;
            }
        };
        
        socket.onerror = (error) => {
            console.error('Error en la conexión WebSocket:', error);
            showNotification('Error de conexión. Verifica que el servidor esté funcionando.', 'error');
        };
        
    } catch (error) {
        console.error('Error al conectar:', error);
        showNotification('No se pudo conectar al servidor', 'error');
    }
}

// ========== MANEJO DE MENSAJES ==========

// Procesar mensajes recibidos del servidor
function handleMessage(event) {
    const message = event.data;
    console.log('Mensaje recibido:', message);
    
    try {
        // Separar comando y argumentos
        const [command, ...args] = message.split('|');
        
        // Procesar según el comando
        switch (command) {
            case 'CREATE':
                handleCreateResponse(args);
                break;
                
            case 'JOIN':
                handleJoinResponse(args);
                break;
                
            case 'UPDATE':
                handleGameUpdate(args);
                break;
                
            case 'END':
                handleGameEnd(args);
                break;
                
            case 'ERROR':
                handleError(args);
                break;
                
            case 'LIST':
                handleRoomList(args);
                break;
                
            case 'LEAVE':
                handleLeaveResponse();
                break;
                
            default:
                console.warn('Comando desconocido:', command);
        }
    } catch (error) {
        console.error('Error al procesar mensaje:', error);
    }
}

// ========== MANEJADORES DE RESPUESTAS ==========

// Manejar respuesta a la creación de sala
function handleCreateResponse(args) {
    if (args.length < 2) return;
    
    const roomId = args[0];
    const roomName = args[1];
    
    currentRoom = {
        id: roomId,
        name: roomName
    };
    
    // Cambiar a modo de espera
    currentState = GameState.WAITING;
    elements.currentRoomName.textContent = roomName;
    elements.gameStatus.innerHTML = '<p>Esperando a otro jugador...</p>';
    
    showScreen('game');
    showNotification(`Sala "${roomName}" creada correctamente`, 'success');
}

// Manejar respuesta al unirse a una sala
function handleJoinResponse(args) {
    if (args.length < 2) return;
    
    const roomId = args[0];
    const roomName = args[1];
    
    currentRoom = {
        id: roomId,
        name: roomName
    };
    
    // Preparar pantalla de juego
    elements.currentRoomName.textContent = roomName;
    showScreen('game');
    showNotification(`Te has unido a la sala "${roomName}"`, 'success');
}

// Manejar actualizaciones del estado del juego
function handleGameUpdate(args) {
    if (args.length < 4) return;
    
    const status = args[0];
    const boardState = args[1];
    const isTurn = args[2] === 'True';
    const opponentName = args[3];
    
    // Actualizar estado del juego
    currentState = status === 'WAITING' ? GameState.WAITING : GameState.PLAYING;
    isMyTurn = isTurn;
    
    // Actualizar tablero
    updateBoard(boardState);
    
    // Actualizar información de jugadores
    if (status !== 'WAITING') {
        elements.player1.querySelector('.player-name').textContent = playerName;
        elements.player2.querySelector('.player-name').textContent = opponentName;
        
        // Determinar mi símbolo
        if (!mySymbol) {
            // Si no tengo símbolo asignado, asumo X para el primer jugador
            // esto es una simplificación, idealmente el servidor debería informarlo
            mySymbol = isMyTurn ? 'X' : 'O';
        }
    }
    
    // Actualizar indicador de turno
    updateTurnIndicator();
    
    // Actualizar mensaje de estado
    updateGameStatus(status);
}

// Manejar fin del juego
function handleGameEnd(args) {
    if (args.length < 1) return;
    
    const endMessage = args[0];
    elements.endMessage.textContent = endMessage;
    
    currentState = GameState.ENDED;
    showScreen('end');
}

// Manejar errores
function handleError(args) {
    if (args.length < 1) return;
    
    const errorMessage = args[0];
    showNotification(errorMessage, 'error');
}

// Manejar lista de salas
function handleRoomList(args) {
    if (args.length < 1) return;
    
    try {
        const roomsJson = args.join('|'); // Reunir los argumentos (por si el JSON contiene separadores)
        const rooms = JSON.parse(roomsJson);
        
        displayRoomList(rooms);
    } catch (error) {
        console.error('Error al procesar lista de salas:', error);
    }
}

// Manejar respuesta al abandonar sala
function handleLeaveResponse() {
    backToMenu();
    showNotification('Has abandonado la sala', 'info');
}

// ========== FUNCIONES DE JUEGO ==========

// Mostrar lista de salas disponibles
function displayRoomList(rooms) {
    const roomList = elements.roomList;
    
    // Limpiar lista actual
    roomList.innerHTML = '';
    
    if (rooms.length === 0) {
        roomList.innerHTML = '<p class="no-rooms">No hay salas disponibles. ¡Crea una nueva o actualiza la lista!</p>';
        return;
    }
    
    // Agregar cada sala a la lista
    rooms.forEach(room => {
        const roomItem = document.createElement('div');
        roomItem.className = 'room-item';
        
        roomItem.innerHTML = `
            <div class="room-info">
                <span class="room-name">${room.name}</span>
                <span class="room-creator">Creada por: ${room.creator}</span>
            </div>
            <button class="btn accent-btn join-btn">Unirse</button>
        `;
        
        // Agregar evento para unirse a la sala
        roomItem.querySelector('.join-btn').addEventListener('click', () => {
            joinRoom(room.id);
        });
        
        roomList.appendChild(roomItem);
    });
}

// Actualizar el tablero visual
function updateBoard(boardState) {
    // Convertir string del tablero a array
    gameBoard = boardState.split(',');
    
    // Actualizar cada celda
    elements.boardCells.forEach((cell, index) => {
        const value = gameBoard[index];
        cell.textContent = value !== ' ' ? value : '';
        
        // Limpiar clases
        cell.classList.remove('x', 'o');
        
        // Agregar clase según el valor
        if (value === 'X') {
            cell.classList.add('x');
        } else if (value === 'O') {
            cell.classList.add('o');
        }
    });
}

// Actualizar el indicador de turno
function updateTurnIndicator() {
    const turnIndicator = elements.turnIndicator;
    
    if (currentState === GameState.PLAYING) {
        // Posicionar el indicador
        if (isMyTurn) {
            turnIndicator.style.transform = 'translateX(-30px)';
        } else {
            turnIndicator.style.transform = 'translateX(30px)';
        }
        
        turnIndicator.style.opacity = '1';
    } else {
        turnIndicator.style.opacity = '0';
    }
}

// Actualizar mensaje de estado del juego
function updateGameStatus(status) {
    let statusMessage = '';
    
    switch (status) {
        case 'WAITING':
            statusMessage = 'Esperando a otro jugador...';
            break;
            
        case 'PLAYING':
            statusMessage = isMyTurn 
                ? '¡Es tu turno!' 
                : 'Esperando el movimiento del oponente...';
            break;
            
        case 'WIN':
            statusMessage = '¡Has ganado la partida!';
            break;
            
        case 'LOSS':
            statusMessage = 'Has perdido la partida';
            break;
            
        case 'DRAW':
            statusMessage = '¡Empate!';
            break;
    }
    
    elements.gameStatus.innerHTML = `<p>${statusMessage}</p>`;
}

// ========== ACCIONES DEL USUARIO ==========

// Crear una nueva sala
function createRoom() {
    const roomName = elements.roomNameInput.value.trim();
    
    if (!roomName) {
        showNotification('Ingresa un nombre para la sala', 'error');
        return;
    }
    
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(`CREATE|${roomName}`);
    }
}

// Unirse a una sala existente
function joinRoom(roomId) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(`JOIN|${roomId}`);
    }
}

// Solicitar lista de salas disponibles
function requestRoomList() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send('LIST');
    }
}

// Realizar un movimiento en el tablero
function makeMove(cell) {
    // Verificar si es un movimiento válido
    if (currentState !== GameState.PLAYING || !isMyTurn) {
        return;
    }
    
    const position = cell.dataset.index;
    
    // Verificar si la celda está vacía
    if (gameBoard[position] !== ' ') {
        return;
    }
    
    // Enviar movimiento al servidor
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(`MOVE|${position}`);
    }
}

// Abandonar la partida actual
function leaveGame() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send('LEAVE');
    }
}

// Volver al menú principal
function backToMenu() {
    currentRoom = null;
    currentState = GameState.MENU;
    
    // Limpiar tablero
    gameBoard = Array(9).fill(' ');
    updateBoard(gameBoard.join(','));
    
    showScreen('menu');
    
    // Actualizar lista de salas
    requestRoomList();
}

// ========== UTILIDADES ==========

// Mostrar una notificación
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    elements.notifications.appendChild(notification);
    
    // Eliminar después de 3 segundos
    setTimeout(() => {
        notification.remove();
    }, 3000);
} 