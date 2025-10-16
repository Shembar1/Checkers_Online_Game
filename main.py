import pygame
import sys
import socket
import threading
import json
import time
import server


pygame.init()

# Constants
WIDTH, HEIGHT = 800, 800
ROWS, COLS = 8, 8
SQUARE_SIZE = WIDTH // COLS

# Colors
RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
GREY = (128, 128, 128)
CROWN = (255, 215, 0)  # Gold color for king pieces

# Network settings
PORT = 5555
HEADER_SIZE = 10

class Piece:
    PADDING = 15
    OUTLINE = 2

    def __init__(self, row, col, color):
        self.row = row
        self.col = col
        self.color = color
        self.king = False
        self.x = 0
        self.y = 0
        self.calc_pos()

    def calc_pos(self):
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        self.king = True

    def draw(self, win):
        radius = SQUARE_SIZE // 2 - self.PADDING
        pygame.draw.circle(win, GREY, (self.x, self.y), radius + self.OUTLINE)
        pygame.draw.circle(win, self.color, (self.x, self.y), radius)
        if self.king:
            # Draw a crown symbol
            pygame.draw.circle(win, CROWN, (self.x, self.y), radius // 2)

    def move(self, row, col):
        self.row = row
        self.col = col
        self.calc_pos()

    def __repr__(self):
        return str(self.color)

class Board:
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.create_board()

    def draw_squares(self, win):
        win.fill(BLACK)
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(win, RED, (row * SQUARE_SIZE, col * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def create_board(self):
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2):
                    if row < 3:
                        self.board[row].append(Piece(row, col, WHITE))
                    elif row > 4:
                        self.board[row].append(Piece(row, col, RED))
                    else:
                        self.board[row].append(0)
                else:
                    self.board[row].append(0)

    def draw(self, win):
        self.draw_squares(win)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(win)

    def move(self, piece, row, col):
        self.board[piece.row][piece.col], self.board[row][col] = self.board[row][col], self.board[piece.row][piece.col]
        piece.move(row, col)

        if row == ROWS - 1 or row == 0:
            piece.make_king()
            if piece.color == RED:
                self.red_kings += 1
            else:
                self.white_kings += 1

    def get_piece(self, row, col):
        return self.board[row][col]

    def get_valid_moves(self, piece):
        moves = {}
        left = piece.col - 1
        right = piece.col + 1
        row = piece.row

        if piece.color == RED or piece.king:
            moves.update(self._traverse_left(row - 1, max(row - 3, -1), -1, piece.color, left))
            moves.update(self._traverse_right(row - 1, max(row - 3, -1), -1, piece.color, right))

        if piece.color == WHITE or piece.king:
            moves.update(self._traverse_left(row + 1, min(row + 3, ROWS), 1, piece.color, left))
            moves.update(self._traverse_right(row + 1, min(row + 3, ROWS), 1, piece.color, right))

        return moves

    def _traverse_left(self, start, stop, step, color, left, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if left < 0:
                break

            current = self.board[r][left]
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, left)] = last + skipped
                else:
                    moves[(r, left)] = last

                if last:
                    if step == -1:
                        row = max(r - 3, 0)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left(r + step, row, step, color, left - 1, skipped=last))
                    moves.update(self._traverse_right(r + step, row, step, color, left + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]

            left -= 1

        return moves

    def _traverse_right(self, start, stop, step, color, right, skipped=[]):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if right >= COLS:
                break

            current = self.board[r][right]
            if current == 0:
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, right)] = last + skipped
                else:
                    moves[(r, right)] = last

                if last:
                    if step == -1:
                        row = max(r - 3, 0)
                    else:
                        row = min(r + 3, ROWS)
                    moves.update(self._traverse_left(r + step, row, step, color, right - 1, skipped=last))
                    moves.update(self._traverse_right(r + step, row, step, color, right + 1, skipped=last))
                break
            elif current.color == color:
                break
            else:
                last = [current]

            right += 1

        return moves

    def remove(self, pieces):
        for piece in pieces:
            self.board[piece.row][piece.col] = 0
            if piece.color == RED:
                self.red_left -= 1
            else:
                self.white_left -= 1

    def winner(self):
        if self.red_left <= 0:
            return WHITE
        elif self.white_left <= 0:
            return RED
        return None

    def serialize(self):
        # Convert board to serializable format
        serialized = []
        for row in range(ROWS):
            serialized_row = []
            for col in range(COLS):
                piece = self.board[row][col]
                if piece == 0:
                    serialized_row.append(None)
                else:
                    serialized_row.append({
                        'color': piece.color,
                        'king': piece.king,
                        'row': piece.row,
                        'col': piece.col
                    })
            serialized.append(serialized_row)
        return serialized

    def deserialize(self, data):
        # Recreate board from serialized data
        self.board = []
        self.red_left = self.white_left = 0
        self.red_kings = self.white_kings = 0
        
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                piece_data = data[row][col]
                if piece_data is None:
                    self.board[row].append(0)
                else:
                    color = tuple(piece_data['color']) if isinstance(piece_data['color'], list) else piece_data['color']
                    piece = Piece(row, col, color)
                    if piece_data['king']:
                        piece.make_king()
                        if color == RED:
                            self.red_kings += 1
                        else:
                            self.white_kings += 1
                    self.board[row].append(piece)
                    
                    if color == RED:
                        self.red_left += 1
                    else:
                        self.white_left += 1

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = "localhost"
        self.port = PORT
        self.addr = (self.server, self.port)
        self.id = self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)
            return self.client.recv(2048).decode()
        except:
            pass

    def send(self, data):
        try:
            # Serialize data to JSON string
            json_data = json.dumps(data)
            # Add header with message length
            message = f"{len(json_data):<{HEADER_SIZE}}" + json_data
            self.client.send(message.encode())
            
            # Receive response
            response_header = self.client.recv(HEADER_SIZE).decode()
            if response_header:
                response_length = int(response_header.strip())
                response_data = self.client.recv(response_length).decode()
                return json.loads(response_data)
        except socket.error as e:
            print(e)
            return None

class Game:
    def __init__(self, win, network):
        self._init()
        self.win = win
        self.network = network
        self.player_color = None
        self.connected = False

    def _init(self):
        self.selected = None
        self.board = Board()
        self.turn = RED
        self.valid_moves = {}

    def update(self):
        self.board.draw(self.win)
        self.draw_valid_moves(self.valid_moves)
        self.draw_game_info()
        pygame.display.update()

    def reset(self):
        self._init()

    def select(self, row, col):
        if self.selected:
            result = self._move(row, col)
            if not result:
                self.selected = None
                self.select(row, col)

        piece = self.board.get_piece(row, col)
        if piece != 0 and piece.color == self.turn and piece.color == self.player_color:
            self.selected = piece
            self.valid_moves = self.board.get_valid_moves(piece)
            return True

        return False

    def _move(self, row, col):
        piece = self.board.get_piece(row, col)
        if self.selected and piece == 0 and (row, col) in self.valid_moves:
            # Send move to server
            move_data = {
                'type': 'move',
                'from': (self.selected.row, self.selected.col),
                'to': (row, col),
                'skipped': [(p.row, p.col) for p in self.valid_moves[(row, col)]]
            }
            
            response = self.network.send(move_data)
            if response and response.get('status') == 'success':
                self.board.move(self.selected, row, col)
                skipped = self.valid_moves[(row, col)]
                if skipped:
                    self.board.remove(skipped)
                self.change_turn()
                return True
        return False

    def draw_valid_moves(self, moves):
        for move in moves:
            row, col = move
            pygame.draw.circle(self.win, BLUE, (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), 15)

    def draw_game_info(self):
        font = pygame.font.SysFont('Arial', 24)
        
        # Display player color
        if self.player_color:
            color_text = "Your color: " + ("RED" if self.player_color == RED else "WHITE")
            color_surface = font.render(color_text, True, self.player_color)
            self.win.blit(color_surface, (10, 10))
        
        # Display turn information
        turn_text = "Current turn: " + ("RED" if self.turn == RED else "WHITE")
        turn_surface = font.render(turn_text, True, self.turn)
        self.win.blit(turn_surface, (10, 40))
        
        # Display connection status
        status_text = "Connected: " + ("Yes" if self.connected else "No")
        status_color = GREEN if self.connected else RED
        status_surface = font.render(status_text, True, status_color)
        self.win.blit(status_surface, (10, 70))

    def change_turn(self):
        self.valid_moves = {}
        self.selected = None
        if self.turn == RED:
            self.turn = WHITE
        else:
            self.turn = RED

    def get_board(self):
        return self.board

    def receive_updates(self):
        while True:
            try:
                # Request game state from server
                request = {'type': 'get_state'}
                response = self.network.send(request)
                
                if response:
                    if response.get('type') == 'game_state':
                        # Update board
                        self.board.deserialize(response['board'])
                        self.turn = tuple(response['turn']) if isinstance(response['turn'], list) else response['turn']
                        self.connected = True
                        
                        # Check if game ended
                        winner = self.board.winner()
                        if winner:
                            return winner
                    
                    elif response.get('type') == 'player_assignment':
                        self.player_color = tuple(response['color']) if isinstance(response['color'], list) else response['color']
                        self.connected = True
                
                time.sleep(0.5)  # Poll every 0.5 seconds
                
            except Exception as e:
                print(f"Error receiving updates: {e}")
                self.connected = False
                time.sleep(1)

def draw_menu(win):
    win.fill(BLACK)
    font_large = pygame.font.SysFont('Arial', 50)
    font_small = pygame.font.SysFont('Arial', 36)
    
    title = font_large.render('CHECKERS - LAN MULTIPLAYER', True, WHITE)
    host_text = font_small.render('1 - HOST GAME', True, GREEN)
    join_text = font_small.render('2 - JOIN GAME', True, BLUE)
    quit_text = font_small.render('3 - QUIT', True, RED)
    
    win.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 4))
    win.blit(host_text, (WIDTH // 2 - host_text.get_width() // 2, HEIGHT // 2))
    win.blit(join_text, (WIDTH // 2 - join_text.get_width() // 2, HEIGHT // 2 + 50))
    win.blit(quit_text, (WIDTH // 2 - quit_text.get_width() // 2, HEIGHT // 2 + 100))
    
    pygame.display.update()

def get_local_ip():
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def draw_waiting_screen(win, is_host=False, ip=""):
    win.fill(BLACK)
    font_large = pygame.font.SysFont('Arial', 40)
    font_small = pygame.font.SysFont('Arial', 30)
    
    if is_host:
        title = font_large.render('WAITING FOR PLAYER TO CONNECT', True, WHITE)
        ip_text = font_small.render(f'Your IP: {ip}', True, GREEN)
        port_text = font_small.render(f'Port: {PORT}', True, GREEN)
        instruction = font_small.render('Give this information to your friend', True, BLUE)
        
        win.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 4))
        win.blit(ip_text, (WIDTH // 2 - ip_text.get_width() // 2, HEIGHT // 2))
        win.blit(port_text, (WIDTH // 2 - port_text.get_width() // 2, HEIGHT // 2 + 40))
        win.blit(instruction, (WIDTH // 2 - instruction.get_width() // 2, HEIGHT // 2 + 100))
    else:
        title = font_large.render('CONNECTING TO SERVER...', True, WHITE)
        win.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2))
    
    pygame.display.update()

def draw_connection_screen(win):
    win.fill(BLACK)
    font_large = pygame.font.SysFont('Arial', 40)
    font_small = pygame.font.SysFont('Arial', 30)
    
    title = font_large.render('ENTER SERVER IP ADDRESS', True, WHITE)
    instruction = font_small.render('Type IP and press ENTER', True, BLUE)
    default_ip = font_small.render('Default: localhost', True, GREY)
    
    win.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 4))
    win.blit(instruction, (WIDTH // 2 - instruction.get_width() // 2, HEIGHT // 2))
    win.blit(default_ip, (WIDTH // 2 - default_ip.get_width() // 2, HEIGHT // 2 + 40))
    
    pygame.display.update()

def get_ip_input(win):
    input_ip = "localhost"
    font = pygame.font.SysFont('Arial', 36)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return input_ip
                elif event.key == pygame.K_BACKSPACE:
                    input_ip = input_ip[:-1]
                else:
                    # Only allow numbers, dots, and localhost
                    if event.unicode.isdigit() or event.unicode == '.' or (event.unicode.isalpha() and input_ip == "localhos"):
                        input_ip += event.unicode
        
        win.fill(BLACK)
        draw_connection_screen(win)
        
        # Draw current input
        ip_surface = font.render(input_ip, True, GREEN)
        win.blit(ip_surface, (WIDTH // 2 - ip_surface.get_width() // 2, HEIGHT // 2 + 80))
        
        pygame.display.update()

def main():
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('Checkers - LAN Multiplayer')
    
    clock = pygame.time.Clock()
    
    # Show menu
    menu = True
    while menu:
        draw_menu(win)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    # Host game

                    local_ip = get_local_ip()
                    
                    # Start server in a separate thread
                    server_thread = threading.Thread(target=server.start_server)
                    server_thread.daemon = True
                    server_thread.start()
                    
                    draw_waiting_screen(win, is_host=True, ip=local_ip)
                    
                    # Connect to local server as player 1
                    network = Network()
                    game = Game(win, network)
                    
                    # Wait for another player to connect
                    while True:
                        response = network.send({'type': 'get_state'})
                        if response and response.get('players_connected') == 2:
                            break
                        time.sleep(1)
                    
                    menu = False
                    
                elif event.key == pygame.K_2:
                    # Join game
                    server_ip = get_ip_input(win)
                    
                    draw_waiting_screen(win, is_host=False)
                    
                    network = Network()
                    network.server = server_ip
                    network.addr = (server_ip, PORT)
                    
                    try:
                        network.id = network.connect()
                        game = Game(win, network)
                        menu = False
                    except:
                        print("Failed to connect to server")
                        # Return to menu on connection failure
                
                elif event.key == pygame.K_3:
                    pygame.quit()
                    sys.exit()
        
        clock.tick(60)
    
    # Start game
    winner = None
    
    # Start thread to receive game updates
    update_thread = threading.Thread(target=game.receive_updates)
    update_thread.daemon = True
    update_thread.start()
    
    while True:
        clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN and game.connected:
                pos = pygame.mouse.get_pos()
                col, row = pos[0] // SQUARE_SIZE, pos[1] // SQUARE_SIZE
                game.select(row, col)
        
        game.update()
        
        # Check for winner from the update thread
        current_winner = game.board.winner()
        if current_winner:
            winner = current_winner
            break
    
    # Display winner
    font = pygame.font.SysFont('Arial', 50)
    if winner == RED:
        text = font.render('Red Wins!', True, RED)
    else:
        text = font.render('White Wins!', True, WHITE)
    
    win.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - text.get_height() // 2))
    pygame.display.update()
    pygame.time.delay(5000)

if __name__ == "__main__":
    main()