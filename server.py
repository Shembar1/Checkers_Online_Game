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
        # Create initial board state
        from game import Board  # Import here to avoid circular imports
        board = Board()
        self.game_state['board'] = board.serialize()
        self.game_state['players_connected'] = 0
        
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
            
            # Process the move (in a real implementation, you'd validate the move)
            from_row, from_col = data['from']
            to_row, to_col = data['to']
            
            # Update game state
            from game import Board
            board = Board()
            board.deserialize(self.game_state['board'])
            
            # Find the piece and move it
            piece = board.get_piece(from_row, from_col)
            if piece and piece.color == current_player_color:
                board.move(piece, to_row, to_col)
                
                # Remove skipped pieces
                skipped_positions = data.get('skipped', [])
                skipped_pieces = []
                for row, col in skipped_positions:
                    skipped_piece = board.get_piece(row, col)
                    if skipped_piece:
                        skipped_pieces.append(skipped_piece)
                if skipped_pieces:
                    board.remove(skipped_pieces)
                
                # Update turn
                self.game_state['turn'] = (255, 255, 255) if self.game_state['turn'] == (255, 0, 0) else (255, 0, 0)
                self.game_state['board'] = board.serialize()
                
                return {'status': 'success'}
            else:
                return {'status': 'error', 'message': 'Invalid move'}
        
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