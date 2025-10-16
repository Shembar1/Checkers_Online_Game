import socket
import threading
import json
import time

# Network settings
PORT = 5555
HEADER_SIZE = 10

class CheckersServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host = "0.0.0.0"  # Listen on all interfaces
        self.port = PORT
        self.addr = (self.host, self.port)
        
        self.players = []
        self.game_state = {
            'board': None,
            'turn': (255, 0, 0),  # RED starts
            'players_connected': 0
        }
        self.initialize_game()
        
    def initialize_game(self):
        # Create initial board state using the same Board class logic
        board = self.create_initial_board()
        self.game_state['board'] = board
        self.game_state['players_connected'] = 0
        
    def create_initial_board(self):
        # Create the initial board configuration
        board = []
        RED = (255, 0, 0)
        WHITE = (255, 255, 255)
        
        for row in range(8):
            board_row = []
            for col in range(8):
                if col % 2 == ((row + 1) % 2):
                    if row < 3:
                        board_row.append({
                            'color': WHITE,
                            'king': False,
                            'row': row,
                            'col': col
                        })
                    elif row > 4:
                        board_row.append({
                            'color': RED,
                            'king': False,
                            'row': row,
                            'col': col
                        })
                    else:
                        board_row.append(None)
                else:
                    board_row.append(None)
            board.append(board_row)
        return board
        
    def handle_client(self, conn, addr, player_id):
        print(f"New connection from {addr}, player {player_id}")
        
        # Send player their color assignment
        color = (255, 0, 0) if player_id == 0 else (255, 255, 255)  # RED or WHITE
        assignment = {
            'type': 'player_assignment',
            'color': color,
            'player_id': player_id
        }
        self.send(conn, assignment)
        
        while True:
            try:
                # Receive message
                message_header = conn.recv(HEADER_SIZE)
                if not message_header:
                    break
                    
                message_length = int(message_header.strip())
                message_data = conn.recv(message_length).decode()
                data = json.loads(message_data)
                
                # Process message
                response = self.process_message(data, player_id)
                if response:
                    self.send(conn, response)
                    
            except Exception as e:
                print(f"Error with client {addr}: {e}")
                break
        
        # Remove player on disconnect
        if player_id < len(self.players):
            self.players[player_id] = None
        self.game_state['players_connected'] = len([p for p in self.players if p is not None])
        print(f"Player {player_id} disconnected")
        conn.close()
    
    def process_message(self, data, player_id):
        message_type = data.get('type')
        
        if message_type == 'get_state':
            return {
                'type': 'game_state',
                'board': self.game_state['board'],
                'turn': self.game_state['turn'],
                'players_connected': self.game_state['players_connected']
            }
            
        elif message_type == 'move':
            # Verify it's this player's turn
            current_player_color = (255, 0, 0) if player_id == 0 else (255, 255, 255)
            if self.game_state['turn'] != current_player_color:
                return {'status': 'error', 'message': 'Not your turn'}
            
            # Process the move
            from_row, from_col = data['from']
            to_row, to_col = data['to']
            
            # Update the board state
            board = self.game_state['board']
            
            # Get the piece being moved
            piece_data = board[from_row][from_col]
            if not piece_data or piece_data['color'] != current_player_color:
                return {'status': 'error', 'message': 'Invalid piece'}
            
            # Move the piece
            board[to_row][to_col] = {
                'color': piece_data['color'],
                'king': piece_data['king'],
                'row': to_row,
                'col': to_col
            }
            board[from_row][from_col] = None
            
            # Check for king promotion
            if (current_player_color == (255, 0, 0) and to_row == 0) or \
               (current_player_color == (255, 255, 255) and to_row == 7):
                board[to_row][to_col]['king'] = True
            
            # Update turn
            self.game_state['turn'] = (255, 255, 255) if self.game_state['turn'] == (255, 0, 0) else (255, 0, 0)
            
            return {'status': 'success'}
        
        return {'status': 'unknown_command'}
    
    def send(self, conn, data):
        try:
            json_data = json.dumps(data)
            message = f"{len(json_data):<{HEADER_SIZE}}" + json_data
            conn.send(message.encode())
        except Exception as e:
            print(f"Error sending data: {e}")
    
    def start(self):
        try:
            self.server.bind(self.addr)
            self.server.listen(2)  # Allow 2 players
            print(f"Checkers server started on {self.host}:{self.port}")
            print("Waiting for connections...")
            
            while True:
                conn, addr = self.server.accept()
                
                # Assign player ID
                player_id = None
                for i in range(2):
                    if i >= len(self.players):
                        self.players.append(None)
                    if self.players[i] is None:
                        player_id = i
                        self.players[i] = conn
                        break
                
                if player_id is not None:
                    self.game_state['players_connected'] = len([p for p in self.players if p is not None])
                    thread = threading.Thread(target=self.handle_client, args=(conn, addr, player_id))
                    thread.daemon = True
                    thread.start()
                    print(f"Player {player_id} connected. Total players: {self.game_state['players_connected']}")
                    
                    # Start game when both players are connected
                    if self.game_state['players_connected'] == 2:
                        print("Both players connected! Starting game...")
                else:
                    print("Game is full, rejecting connection")
                    conn.close()
                    
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.server.close()

def start_server():
    server = CheckersServer()
    server.start()

if __name__ == "__main__":
    start_server()