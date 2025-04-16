import pygame
import sys
import json
import random
import os
import time
from pygame import key

import asyncio
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription
import threading
import uuid
import ssl

# Initialize pygame
pygame.init()

# Game settings
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Drawing Game")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (193, 9, 48, 230)  # RGBA color with 90% opacity
GREEN = (64, 255, 47)
YELLOW = (255, 208, 64)
BLUE = (0, 0, 255)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
PINK = (255, 192, 203)
BROWN = (139, 69, 19)
CYAN = (0, 255, 255)
DARK_GRAY = (50, 50, 50)
LIGHT_GRAY = (220, 220, 220)

# Color palette for drawing
color_palette = [
    {"color": BLACK, "name": "Black"},
    {"color": WHITE, "name": "White"},
    {"color": BROWN, "name": "Brown"},
    {"color": RED, "name": "Red"},
    {"color": BLUE, "name": "Blue"},
    {"color": CYAN, "name": "Cyan"},
    {"color": GREEN, "name": "Green"},
    {"color": YELLOW, "name": "Yellow"},
    {"color": ORANGE, "name": "Orange"},
    {"color": PINK, "name": "Pink"},
    {"color": PURPLE, "name": "Purple"},
]

# Add to your color definitions (at the top with other colors)
PLAYER_COLORS = [
    CYAN,          # Player 1
    GREEN,         # Player 2
    YELLOW,        # Player 3
    ORANGE,        # Player 4
    PINK,          # Player 5
    PURPLE,        # Player 6
    (0, 255, 0),   # Lime (Player 7)
    (255, 0, 255)  # Magenta (Player 8)
]

# Initialize current drawing color
current_color = BLACK
current_color_index = 0

# Drawing mode
DRAW_MODE = "draw"
PEN_MODE = "pen"
ERASE_MODE = "erase"
FILL_MODE = "fill"
current_mode = PEN_MODE

# Font
font = pygame.font.Font(None, 24)
large_font = pygame.font.Font(None, 36)

# Load background image
try:
    background_image = pygame.image.load("./picture/623096b01138c7b09a970d4197150cfc.png")
    background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))
except:
    background_image = pygame.Surface((WIDTH, HEIGHT))
    background_image.fill(WHITE)

# Load logo image
try:
    logo = pygame.image.load("./picture/3b955b32cdb396eb0f8235e5c4299b7f.png")
    logo_width, logo_height = logo.get_size()
    new_width = 400
    new_height = int((new_width / logo_width) * logo_height)
    logo = pygame.transform.scale(logo, (new_width, new_height))
except:
    logo = pygame.Surface((400, 200))
    logo.fill(BLUE)

# Load tool icons
try:
    eraser_icon = pygame.image.load("./picture/eraser.png")
    eraser_icon = pygame.transform.scale(eraser_icon, (25, 25))
except pygame.error:
    eraser_icon = None

try:
    pen_icon = pygame.image.load("./picture/pen.png")
    pen_icon = pygame.transform.scale(pen_icon, (25, 25))
except pygame.error:
    pen_icon = None

try:
    bucket_icon = pygame.image.load("./picture/color.png")
    bucket_icon = pygame.transform.scale(bucket_icon, (25, 25))
except pygame.error:
    bucket_icon = None


# Game states
MENU = "menu"
DRAWING = "drawing"
WORD_CHOOSING = "word_choosing"
GUESSING = "guessing"
game_state = MENU

# User data storage
user_data = {"name": "", "logged_in": False, "session_id": None, "role": "guesser"}

# Game session data
game_session = {
    "players": [],
    "current_drawer": None,
    "round": 0,
    "max_rounds": 3,
    "correct_guessers": [],
    "round_start_time": 0,
    "round_duration": 90,  # 1 minute 30 seconds
    "round_end_time": 0
}

# Scoreboard
scores = {}

# Word guessing system
selected_word = ""
word_hint = ""
word_reveal_timer = 0
word_reveal_interval = 10000  # milliseconds between letter reveals (slower now)
last_reveal_time = 0
revealed_letters = 0

# Chat system
chat_messages = []
chat_input = ""
chat_active = False
chat_box = pygame.Rect(WIDTH - 250, 50, 230, 600)
chat_input_box = pygame.Rect(WIDTH - 250, 660, 230, 30)

# Game timing
game_start_time = 0
current_time = 0
max_score = 1000
score_decay_rate = 2  # Points lost per second

# Updated button positions for new menu layout
button_width, button_height = 250, 30
create_room_button = pygame.Rect((WIDTH - button_width) // 2, 260, button_width, button_height)
join_room_button = pygame.Rect((WIDTH - button_width) // 2, 300, button_width, button_height)
drawer_demo_button = pygame.Rect((WIDTH - button_width) // 2, 340, button_width, button_height)
guesser_demo_button = pygame.Rect((WIDTH - button_width) // 2, 380, button_width, button_height)
quit_button = pygame.Rect((WIDTH - button_width) // 2, 420, button_width, button_height)

# Name input box position updated to be above the first button
room_input = ""
input_box_width, input_box_height = 250, 30
input_box = pygame.Rect((WIDTH - input_box_width) // 2, create_room_button.y - 70, input_box_width, input_box_height)
user_text = user_data["name"] if user_data["name"] else ""
placeholder_text = "Enter your name (or leave blank for Anonymous)"
active = False
room_placeholder = "Enter room ID (or leave blank for 'default_room')"
room_active = False
room_box = pygame.Rect((WIDTH - input_box_width) // 2, input_box.y + input_box_height + 10, input_box_width, input_box_height)


# Calculate logo position
logo_x = (WIDTH - new_width) // 2
logo_y = input_box.y - new_height - 30

# Update menu background to accommodate more buttons
menu_background = pygame.Surface((button_width + 20, button_height * 5 + 150), pygame.SRCALPHA)
menu_background.fill(RED)

# Drawing state variables
drawing = False
last_pos = None

# Define toolbar height
toolbar_height = 50

# Add a back button for drawing mode (at the bottom)
back_button = pygame.Rect(10, HEIGHT - toolbar_height + 10, 100, 30)

# Add pen tool button (left of bucket)
pen_button = pygame.Rect(WIDTH - 360, HEIGHT - toolbar_height + 10, 30, 30)

# Add paint bucket button (left of eraser, right of pen)
bucket_button = pygame.Rect(WIDTH - 320, HEIGHT - toolbar_height + 10, 30, 30)

# Add an eraser button
eraser_button = pygame.Rect(WIDTH - 280, HEIGHT - toolbar_height + 10, 30, 30)

# Color picker buttons - positioned at the bottom
color_button_size = 30
color_buttons = []
color_palette_x = 120
color_palette_y = HEIGHT - toolbar_height + 10
color_palette_spacing = 5

# Initialize color picker buttons
for i, color_data in enumerate(color_palette):
    x_pos = color_palette_x + i * (color_button_size + color_palette_spacing)
    color_buttons.append({
        "rect": pygame.Rect(x_pos, color_palette_y, color_button_size, color_button_size),
        "color": color_data["color"],
        "name": color_data["name"],
    })

# Status message
status_message = ""
status_timer = 0

# Fixed brush size options
brush_sizes = [6, 15, 50]
brush_size_index = 0
brush_size = brush_sizes[brush_size_index]

# Brush size option buttons
brush_size_buttons = []
brush_button_spacing = 10
brush_button_size = 40
brush_size_x = WIDTH - 190

for i, size in enumerate(brush_sizes):
    x_pos = brush_size_x + i * (brush_button_size + brush_button_spacing)
    brush_size_buttons.append({
        "rect": pygame.Rect(x_pos, HEIGHT - toolbar_height + 5, brush_button_size, brush_button_size),
        "size": size,
    })
def generate_room_id():
    return ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5))
# Initialize word hint
def init_word_hint(word):
    global word_hint, revealed_letters, last_reveal_time, selected_word
    word_hint = ["_"] * len(word)
    revealed_letters = 0
    last_reveal_time = pygame.time.get_ticks()

# Update word hint
def update_word_hint():
    global word_hint, revealed_letters, last_reveal_time, selected_word
    
    current_time = pygame.time.get_ticks()
    if (current_time - last_reveal_time > word_reveal_interval and 
        revealed_letters < len(selected_word)):
        
        # Find all hidden positions
        hidden_positions = [i for i, c in enumerate(word_hint) if c == "_"]
        if hidden_positions:
            # Reveal a random hidden character
            pos = random.choice(hidden_positions)
            word_hint[pos] = selected_word[pos]
            revealed_letters += 1
            last_reveal_time = current_time

# Calculate current score
def calculate_score():
    elapsed_time = (pygame.time.get_ticks() - game_start_time) / 1000  # Convert to seconds
    score = max(0, max_score - int(elapsed_time * score_decay_rate))
    return score

# Check guess
def check_guess(guess):
    global selected_word, chat_messages, scores, game_session
    
    guess = guess.lower().strip()
    correct_word = selected_word.lower()
    
    # Always show the guessed word in chat
    chat_messages.append(f"{user_data['name']}: {guess}")
    
    if guess == correct_word:
        # Check if player already guessed correctly
        if user_data["name"] in game_session["correct_guessers"]:
            return False
            
        score = calculate_score()
        if user_data["name"] not in scores or score > scores.get(user_data["name"], 0):
            scores[user_data["name"]] = score
        chat_messages.append(f"System: {user_data['name']} guessed correctly! +{score} points!")
        game_session["correct_guessers"].append(user_data["name"])
        return True
    return False

# Draw scoreboard
def draw_scoreboard():
    # Background
    pygame.draw.rect(screen, DARK_GRAY, (10, 10, 200, 150))
    
    # Title
    title = font.render("Scoreboard", True, WHITE)
    screen.blit(title, (20, 20))
    
    # Round info
    round_text = font.render(f"Round: {game_session['round']}/{game_session['max_rounds']}", True, WHITE)
    screen.blit(round_text, (20, 45))
    
    # Time remaining
    if game_state in [DRAWING, GUESSING]:
        remaining = max(0, game_session["round_end_time"] - pygame.time.get_ticks()) // 1000
        time_text = font.render(f"Time: {remaining}s", True, WHITE)
        screen.blit(time_text, (20, 70))
    
    # Drawer info
    if game_session["current_drawer"]:
        drawer_text = font.render(f"Drawer: {game_session['current_drawer']}", True, WHITE)
        screen.blit(drawer_text, (20, 95))
    
    # Players
    y_offset = 120
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    for i, (name, score) in enumerate(sorted_scores):
        if i >= 3:  # Limit to top 3 players
            break
        player_text = font.render(f"{i+1}. {name}: {score}", True, WHITE)
        screen.blit(player_text, (20, 20 + y_offset))
        y_offset += 25

# Draw chat
def draw_chat():
    # Background
    pygame.draw.rect(screen, DARK_GRAY, chat_box)
    
    # Title
    chat_title = font.render("Chat", True, WHITE)
    screen.blit(chat_title, (chat_box.x + 10, chat_box.y + 10))
    
    # Chat messages (last 15 messages)
    y_offset = 40
    max_width = chat_box.width - 20
    
    # Define special colors
    system_color = WHITE
    current_player_color = (64, 255, 64)  # Bright green
    
    # Process messages
    wrapped_messages = []
    for msg in chat_messages[-15:]:  # Show last 15 messages
        # Determine message type and color
        if msg.startswith("System:"):
            color = system_color
            sender = "System"
        else:
            # Extract sender name
            sender = msg.split(":")[0] if ":" in msg else "Unknown"
            
            # Color assignment
            if sender == user_data["name"]:
                color = current_player_color  # Highlight current player
            else:
                color = get_player_color(sender)
        
        # Word wrapping
        words = msg.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width = font.size(test_line)[0]
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append((' '.join(current_line), color))
                current_line = [word]
        
        if current_line:
            lines.append((' '.join(current_line), color))
        
        wrapped_messages.extend(lines)
    
    # Display messages that fit
    visible_messages = []
    current_y = y_offset
    
    for msg, color in wrapped_messages[-15:]:
        if current_y + 20 > chat_box.height - 40:
            break
            
        visible_messages.append((msg, color, current_y))
        current_y += 20
    
    # Draw messages (newest at bottom)
    for msg, color, y_pos in visible_messages:
        if font.size(msg)[0] > max_width:
            msg = msg[:int(len(msg)*0.9)] + "..."
        msg_text = font.render(msg, True, color)
        screen.blit(msg_text, (chat_box.x + 10, chat_box.y + y_pos))
    
    # Input box
    if user_data["role"] == "guesser" and user_data["name"] not in game_session["correct_guessers"]:
        pygame.draw.rect(screen, LIGHT_GRAY, chat_input_box)
        pygame.draw.rect(screen, BLACK, chat_input_box, 2)
        
        input_text = chat_input
        text_width = font.size(input_text)[0]
        max_input_width = chat_input_box.width - 10
        
        while text_width > max_input_width and len(input_text) > 3:
            input_text = input_text[:-1]
            text_width = font.size(input_text)[0]
        
        if chat_active and int(time.time() * 2) % 2 == 0:
            input_text += "|"
            
        input_surface = font.render(input_text, True, BLACK)
        screen.blit(input_surface, (chat_input_box.x + 5, chat_input_box.y + 5))
    else:
        pygame.draw.rect(screen, DARK_GRAY, chat_input_box)
        message = "You are the drawer" if user_data["role"] == "drawer" else "You already guessed!"
        input_text = font.render(message, True, WHITE)
        screen.blit(input_text, (chat_input_box.x + 5, chat_input_box.y + 5))

# Draw word hint
def draw_word_hint():
    # Background
    pygame.draw.rect(screen, DARK_GRAY, (WIDTH//2 - 150, 10, 300, 40))
    
    # Display the hint with revealed letters
    hint_text = large_font.render(" ".join(word_hint), True, WHITE)
    screen.blit(hint_text, (WIDTH//2 - hint_text.get_width()//2, 20))

# Smooth line drawing
def draw_smooth_line(surface, color, start_pos, end_pos, radius):
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]
    distance = max(1, int((dx**2 + dy**2) ** 0.5))
    steps = max(1, distance // (radius // 2))

    for i in range(steps + 1):
        t = i / steps
        x = int(start_pos[0] + dx * t)
        y = int(start_pos[1] + dy * t)
        pygame.draw.circle(surface, color, (x, y), radius)

# Flood fill
def flood_fill(surface, position, fill_color, threshold=0):
    x, y = int(position[0]), int(position[1])
    target_color = surface.get_at((x, y))
    
    if target_color == fill_color:
        return

    queue = [(x, y)]
    processed = set()
    width, height = surface.get_size()

    while queue:
        current_x, current_y = queue.pop(0)

        if current_x < 0 or current_x >= width or current_y < 0 or current_y >= height:
            continue

        if (current_x, current_y) in processed:
            continue

        current_color = surface.get_at((current_x, current_y))
        if current_color != target_color:
            continue

        surface.set_at((current_x, current_y), fill_color)
        processed.add((current_x, current_y))

        queue.append((current_x + 1, current_y))
        queue.append((current_x - 1, current_y))
        queue.append((current_x, current_y + 1))
        queue.append((current_x, current_y - 1))

# Handle system keys
def handle_system_keys():
    keys = key.get_pressed()
    mods = pygame.key.get_mods()
    if keys[pygame.K_CAPSLOCK]:
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_CAPSLOCK))

# Function to save user data to a file
def save_user_data():
    with open("user_data.json", "w") as f:
        json.dump(user_data, f)

# Function to load user data from file if it exists
def load_user_data():
    try:
        if os.path.exists("user_data.json"):
            with open("user_data.json", "r") as f:
                return json.load(f)
        return {"name": "", "logged_in": False, "session_id": None, "role": "guesser"}
    except Exception as e:
        print(f"Error loading user data: {e}")
        return {"name": "", "logged_in": False, "session_id": None, "role": "guesser"}

# Load words pool
def load_words_from_json(json_file_path):
    try:
        if not os.path.exists(json_file_path):
            sample_words = ["dog", "cat", "house", "tree", "car", "sun", "moon", "star", "book", "phone", "computer", "apple", "banana", "chair", "table"]
            with open(json_file_path, "w") as f:
                json.dump(sample_words, f, indent=4)
            return sample_words

        with open(json_file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading words: {e}")
        return ["dog", "cat", "house"]

# Random words function
def get_random_words(words_pool, num_words=3):
    if len(words_pool) < num_words:
        return words_pool
    return random.sample(words_pool, min(num_words, len(words_pool)))

# Word selection scene
def word_selection_screen(screen, json_file_path, num_options=3):
    words_pool = load_words_from_json(json_file_path)
    word_options = get_random_words(words_pool, num_options)

    # Button dimensions
    button_width = 280
    button_height = 60
    button_margin = 20
    total_height = (button_height + button_margin) * len(word_options)
    start_y = (screen.get_height() - total_height) // 2

    # Title
    title_font = pygame.font.SysFont("Arial", 40)
    title_text = title_font.render("Choose a word to draw:", True, BLACK)
    title_rect = title_text.get_rect(center=(screen.get_width() // 2, start_y - 60))

    # Buttons
    button_font = pygame.font.SysFont("Arial", 30)
    buttons = []
    for i, word in enumerate(word_options):
        button_y = start_y + i * (button_height + button_margin)
        button_rect = pygame.Rect((screen.get_width() - button_width) // 2, button_y, button_width, button_height)
        buttons.append((button_rect, word))

    selected_word = None
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None, None

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for button, word in buttons:
                    if button.collidepoint(mouse_pos):
                        selected_word = word
                        running = False

        # Draw
        screen.fill(WHITE)
        screen.blit(title_text, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        for button, word in buttons:
            button_color = GREEN if button.collidepoint(mouse_pos) else BLUE
            pygame.draw.rect(screen, button_color, button, border_radius=10)
            pygame.draw.rect(screen, BLACK, button, width=2, border_radius=10)

            text = button_font.render(word, True, WHITE)
            text_rect = text.get_rect(center=button.center)
            screen.blit(text, text_rect)

        pygame.display.flip()

    return selected_word, DRAWING

# Add this to clear player colors when starting a new game
def reset_player_colors():
    if hasattr(get_player_color, "player_colors"):
        get_player_color.player_colors = {}

# Start new round
def start_new_round():
    reset_player_colors()
    global game_session, selected_word, chat_messages, canvas, game_start_time
    
    # Clear canvas for new round
    canvas.fill(WHITE)
    
    # Reset correct guessers for new round
    game_session["correct_guessers"] = []
    
    # Select new drawer (simple rotation for now)
    if not game_session["players"]:
        game_session["players"] = list(scores.keys())
    
    if not game_session["players"]:
        # If no players, use current user as drawer
        game_session["current_drawer"] = user_data["name"]
    else:
        if game_session["current_drawer"] is None:
            game_session["current_drawer"] = game_session["players"][0]
        else:
            try:
                current_index = game_session["players"].index(game_session["current_drawer"])
                next_index = (current_index + 1) % len(game_session["players"])
                game_session["current_drawer"] = game_session["players"][next_index]
            except ValueError:
                game_session["current_drawer"] = game_session["players"][0]
    
    # Set user role
    user_data["role"] = "drawer" if user_data["name"] == game_session["current_drawer"] else "guesser"
    
    # Increment round counter
    game_session["round"] += 1
    
    # Set round timer (90 seconds)
    game_session["round_start_time"] = pygame.time.get_ticks()
    game_session["round_end_time"] = game_session["round_start_time"] + (game_session["round_duration"] * 1000)
    
    # Reset chat messages
    chat_messages = []
    chat_messages.append(f"System: Round {game_session['round']} started!")
    chat_messages.append(f"System: {game_session['current_drawer']} is drawing!")
    
    # Only drawer can select word
    if user_data["role"] == "drawer":
        return WORD_CHOOSING
    else:
        # For guessers, we need to wait for drawer to select word
        return GUESSING

# End round and calculate scores
def end_round():
    global game_session, scores
    
    # Calculate drawer's score (10 points per correct guess)
    drawer_score = len(game_session["correct_guessers"]) * 10
    if game_session["current_drawer"] in scores:
        scores[game_session["current_drawer"]] += drawer_score
    else:
        scores[game_session["current_drawer"]] = drawer_score
    
    chat_messages.append(f"System: {game_session['current_drawer']} earned {drawer_score} points as drawer!")
    
    # Check if game should continue
    if game_session["round"] < game_session["max_rounds"]:
        return start_new_round()
    else:
        end_game_session()
        return MENU

# End game session
def end_game_session():
    reset_player_colors()
    global game_session, scores, chat_messages
    
    # Show winner
    if scores:
        winner = max(scores.items(), key=lambda x: x[1])
        chat_messages.append(f"System: Game over! Winner is {winner[0]} with {winner[1]} points!")
    
    # Reset game session
    game_session = {
        "players": [],
        "current_drawer": None,
        "round": 0,
        "max_rounds": 3,
        "correct_guessers": [],
        "round_start_time": 0,
        "round_duration": 90,
        "round_end_time": 0
    }
    
    # Reset scores and chat for new game
    scores = {}
    chat_messages = []

# Add this helper function to track player colors
def get_player_color(player_name):
    if not hasattr(get_player_color, "player_colors"):
        get_player_color.player_colors = {}
    
    if player_name not in get_player_color.player_colors:
        # Assign next available color
        color_index = len(get_player_color.player_colors) % len(PLAYER_COLORS)
        get_player_color.player_colors[player_name] = PLAYER_COLORS[color_index]
    
    return get_player_color.player_colors[player_name]

# Check if all players have guessed correctly
def all_players_guessed():
    # Get all players except the drawer
    all_players = set(scores.keys())
    remaining_guessers = all_players - {game_session["current_drawer"]} - set(game_session["correct_guessers"])
    
    # If no remaining guessers (and we have at least 2 players)
    return not remaining_guessers and len(all_players) > 1


# oak code
class DrawingGameNetwork:
    def __init__(self, player_id, room_id="default_room"):
        self.player_id = player_id
        self.room_id = room_id
        self.websocket = None
        self.peer_connections = {}
        self.data_channels = {}
        self.room_id = None
        self.room_members = []
    def set_canvas(self, canvas):
        self.canvas = canvas   
    async def connect_to_server(self):
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE # สำหรับการทดสอบ
            headers = {
            "Origin": "https://localhost",
            "User-Agent": "DrawingGame/1.0",
            "Sec-WebSocket-Protocol": "chat"
        }
            
            
            ws_url = f"wss://localhost:8000/ws/{self.player_id}"
            
            #ws_url = f"ws://localhost:8000/ws/{self.player_id}"
            print("Connecting with Origin: https://localhost")
            print("WebSocket URL:", ws_url)
            print("Headers:", {
                "Origin": "https://localhost",
                "User-Agent": "DrawingGame/1.0"
            })
            print(f"Player ID: {self.player_id}")
        
            self.websocket = await websockets.connect(
                ws_url,
                ssl=ssl_context,             
                extra_headers=headers
            
            )
            print(f"Successfully connected to ")
            asyncio.create_task(self.listen_to_server())
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.local_mode = True
        
    async def listen_to_server(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                if data["type"] == "room_joined":
                    self.room_id = data["room_id"]
                    self.room_members = data["members"]
                    print(f"Joined room {self.room_id} with members: {self.room_members}")
                    for member in self.room_members:
                        if member != self.player_id:
                            await self.initialize_p2p(member)
  
                elif data["type"] == "member_left":
                    self.room_members = data["members"]
                    print(f"Member left: {data['member_id']}")
                    
                elif data["type"] == "offer":
                    await self.handle_offer(data)
                    
                elif data["type"] == "answer":
                    await self.handle_answer(data)
                    
                elif data["type"] == "ice-candidate":
                    await self.handle_ice_candidate(data)
                    
                elif data["type"] == "draw-data":
                    self.handle_remote_draw(data["data"])
                    
        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
            
    async def join_room(self, room_id):
        if self.websocket:
            await self.websocket.send(json.dumps({
                "type": "join_room",
                "room_id": room_id,
                "player_id": self.player_id
            }))
            
    async def initialize_p2p(self, target_id):
        pc = RTCPeerConnection()
        self.peer_connections[target_id] = pc
        
        channel = pc.createDataChannel("drawing")
        
        @channel.on("open")
        def on_open():
            print(f"Data channel opened with {target_id}")
            self.data_channels[target_id] = channel
            
        @channel.on("message")
        def on_message(msg):
            data = json.loads(msg)
            self.handle_remote_draw(data)
        
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        await self.websocket.send(json.dumps({
            "type": "offer",
            "sender_id": self.player_id,
            "target_id": target_id,
            "offer": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type},
            "room_id": self.room_id
        }))
        
    async def handle_offer(self, data):
        pc = RTCPeerConnection()
        self.peer_connections[data["sender_id"]] = pc
        
        @pc.on("datachannel")
        def on_datachannel(channel):
            print(f"Data channel received from {data['sender_id']}")
            self.data_channels[data["sender_id"]] = channel
            
            @channel.on("message")
            def on_message(msg):
                self.handle_remote_draw(json.loads(msg))
        
        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=data["offer"]["sdp"], type=data["offer"]["type"])
        )
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        await self.websocket.send(json.dumps({
            "type": "answer",
            "sender_id": self.player_id,
            "target_id": data["sender_id"],
            "answer": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type},
            "room_id": self.room_id
        }))
        
    async def handle_answer(self, data):
        pc = self.peer_connections[data["sender_id"]]
        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=data["answer"]["sdp"], type=data["answer"]["type"])
        )
        
    async def handle_ice_candidate(self, data):
        pc = self.peer_connections[data["sender_id"]]
        await pc.addIceCandidate(data["candidate"])
        
    def send_drawing_data(self, draw_data):
        if hasattr(self, 'local_mode') and self.local_mode:
            # ในโหมด local ไม่ต้องส่งข้อมูลทางเครือข่าย
            return
        
        for target_id, channel in self.data_channels.items():
            if channel.readyState == "open":
                channel.send(json.dumps({
                    "type": "draw",
                    "data": draw_data,
                    "sender_id": self.player_id
                }))
    
    def handle_remote_draw(self, data):
        """Handle drawing data received from other players"""
        try:
            if data["type"] == "draw_start":
                pygame.draw.circle(self.canvas, data["color"], 
                             data["pos"], data["brush_size"]//2)
            elif data["type"] == "draw":
                pygame.draw.line(self.canvas, data["color"], 
                           data["start_pos"], data["end_pos"], 
                           data["brush_size"])
            
        except Exception as e:
            print(f"Error handling remote draw: {e}")



'''#####################################################################################'''
class DrawingGame:
    def __init__(self):
        
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.canvas.fill(WHITE)
        self.drawing = False
        self.last_pos = None
        self.current_color = BLACK  # Should match your current color variable
        self.brush_size = brush_sizes[brush_size_index]  # Use your existing brush size
        
    # Network setup
        self.network = DrawingGameNetwork(
    player_id=user_data.get("name") or str(uuid.uuid4()),
    room_id=(room_input or "default_room")
)
        self.network.set_canvas(self.canvas)
        self.network_thread = threading.Thread(target=self.start_network)
        self.network_thread.daemon = True
        self.network_thread.start()
        self.running = True

    def run(self):
        import pygame
        clock = pygame.time.Clock()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                 self.running = False

            # Update game logic here
            self.update()

            # Redraw screen
            self.draw()

            pygame.display.flip()
            clock.tick(60)  # Run at 60 FPS

        # Clean up when exiting
        if hasattr(self, 'network_thread'):
            self.network_thread.join()

    def update(self):
        pass  # ถ้ายังไม่มี logic อัปเดต สามารถเว้นไว้ก่อน

    def draw(self):
        self.canvas.fill((255, 255, 255))  # ตัวอย่างการเคลียร์หน้าจอ
        # สามารถวาด object ต่างๆ ลงบน self.canvas ได้ที่นี่

    def start_network(self):
        """Start network connection in a separate thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # ตั้งค่า room_id จากชื่อผู้เล่นหรือห้อง
            room_id = self.network.room_id or f"room_{self.network.player_id}"
            
            # เชื่อมต่อเซิร์ฟเวอร์และเข้าร่วมห้อง
            loop.run_until_complete(self.network.connect_to_server())
            loop.run_until_complete(self.network.join_room(room_id))
            
            # รัน event loop ต่อเนื่อง
            loop.run_forever()
        except Exception as e:
            print(f"Network error: {e}")
        finally:
            loop.close()
        
    def handle_drawing_event(self, event):
        # Get the current mouse position
        current_pos = pygame.mouse.get_pos()
    
        # If we're just starting to draw
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.drawing = True
            self.last_pos = current_pos
        
            # Create a draw start point
            draw_data = {
                "type": "draw_start",
                "pos": current_pos,
                "color": self.current_color,
                "brush_size": self.brush_size
            }
            self.network.send_drawing_data(draw_data)
    
        # If we're dragging to draw
        elif event.type == pygame.MOUSEMOTION and self.drawing:
            if self.last_pos:
                # Draw locally
                pygame.draw.line(self.canvas, self.current_color,
                           self.last_pos, current_pos,
                           self.brush_size)
            
                #  Send drawing data to network
                draw_data = {
                    "type": "draw",
                    "start_pos": self.last_pos,
                    "end_pos": current_pos,
                    "color": self.current_color,
                    "brush_size": self.brush_size
                }
                self.network.send_drawing_data(draw_data)
        
            self.last_pos = current_pos
    
        # If we stop drawing
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drawing = False
            self.last_pos = None


game_instance = DrawingGame()
canvas = game_instance.canvas

# Main game loop
running = True
game_instance = None
while running:
    handle_system_keys()

    # Get current time
    current_time = pygame.time.get_ticks()
    
    # Update word hint if in drawing mode
    if game_state in [DRAWING, GUESSING] and selected_word:
        update_word_hint()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            user_data["logged_in"] = False
            save_user_data()
            if game_instance:  # ปิด network ก่อนออก
                game_instance.running = False
                if hasattr(game_instance, 'network_thread'):
                    game_instance.network_thread.join()
            running = False

        elif game_state == MENU:
            if event.type == pygame.MOUSEBUTTONDOWN:

                if input_box.collidepoint(event.pos):
                    active = True
                    room_active = False
                elif room_box.collidepoint(event.pos):
                    room_active = True
                    active = False  # ปิดการใช้งานช่องชื่อ
                else:
                    active = False
                    room_active = False
                if event.button == 1:
                    if create_room_button.collidepoint(event.pos):
                        if not user_text:
                            user_text = "Anonymous"
                        user_data["name"] = user_text
                        user_data["logged_in"] = True
                        user_data["role"] = "drawer"
                        save_user_data()

                        room_input = generate_room_id()

                        game_instance = DrawingGame()  # สร้าง instance ใหม่
                        canvas = game_instance.canvas  # ใช้ canvas จาก game_instance
                        game_instance.network.room_id = room_input or "default_room"  # ตั้งค่าห้อง

                        status_message = f"Creating room as {user_data['name']}..."
                        status_timer = 60
                        game_state = start_new_round()
                        
                    elif join_room_button.collidepoint(event.pos):
                        if not user_text:
                            user_text = "Anonymous"
                        user_data["name"] = user_text
                        user_data["logged_in"] = True
                        user_data["role"] = "guesser"
                        save_user_data()
                        if not room_input:  # ถ้าไม่กรอกรหัสห้อง
                            status_message = "Please enter room ID to join!"
                            status_timer = 60
                            continue

                        game_instance = DrawingGame()  # สร้าง instance ใหม่
                        canvas = game_instance.canvas  # ใช้ canvas จาก game_instance
                        game_instance.network.room_id = room_input or "default_room"  # ตั้งค่าห้อง

                        status_message = f"Joining room as {user_data['name']}..."
                        status_timer = 60
                        game_state = GUESSING
                        
                    elif drawer_demo_button.collidepoint(event.pos):
                        if not user_text:
                            user_text = "Demo Drawer"
                        user_data["name"] = user_text
                        user_data["logged_in"] = True
                        user_data["role"] = "drawer"
                        save_user_data()
                        status_message = "Starting drawer demo..."
                        status_timer = 60
                        game_session["current_drawer"] = user_data["name"]
                        game_state = WORD_CHOOSING
                        
                    elif guesser_demo_button.collidepoint(event.pos):
                        if not user_text:
                            user_text = "Demo Guesser"
                        user_data["name"] = user_text
                        user_data["logged_in"] = True
                        user_data["role"] = "guesser"
                        save_user_data()
                        status_message = "Starting guesser demo..."
                        status_timer = 60
                        game_session["current_drawer"] = "Computer"
                        selected_word = random.choice(load_words_from_json("words.json"))
                        init_word_hint(selected_word)
                        game_state = GUESSING
                        
                    elif quit_button.collidepoint(event.pos):
                        running = False

            elif event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        active = False
                    elif event.key == pygame.K_BACKSPACE:
                        user_text = user_text[:-1]
                    else:
                        user_text += event.unicode

                elif room_active:
                    if event.key == pygame.K_RETURN:
                        room_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        room_input = room_input[:-1]
                    else:
                        room_input += event.unicode

        elif game_state == WORD_CHOOSING:
            selected_word, game_state = word_selection_screen(screen, "words.json")
            if selected_word:
                init_word_hint(selected_word)
                game_start_time = pygame.time.get_ticks()
                chat_messages.append(f"System: New round started! Guess the word!")
                if user_data["name"] not in scores:
                    scores[user_data["name"]] = 0

        elif game_state == DRAWING:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Check UI elements first
                    if back_button.collidepoint(event.pos):
                        game_state = MENU
                    elif pen_button.collidepoint(event.pos):
                        current_mode = PEN_MODE
                        status_message = f"Pen tool activated: {color_palette[current_color_index]['name']}"
                        status_timer = 30
                    elif bucket_button.collidepoint(event.pos):
                        current_mode = FILL_MODE
                        status_message = "Paint bucket tool activated"
                        status_timer = 30
                    elif eraser_button.collidepoint(event.pos):
                        current_mode = ERASE_MODE
                        status_message = "Eraser tool activated"
                        status_timer = 30
                    elif chat_input_box.collidepoint(event.pos) and user_data["role"] == "guesser" and user_data["name"] not in game_session["correct_guessers"]:
                        chat_active = True
                    else:
                        # Check brush size buttons
                        for i, btn in enumerate(brush_size_buttons):
                            if btn["rect"].collidepoint(event.pos):
                                brush_size_index = i
                                brush_size = brush_sizes[brush_size_index]
                                status_message = f"Brush size: {brush_size}px"
                                status_timer = 30
                                break

                        # Check color buttons
                        for i, btn in enumerate(color_buttons):
                            if btn["rect"].collidepoint(event.pos):
                                current_color = btn["color"]
                                current_color_index = i
                                if current_mode == ERASE_MODE or current_mode == FILL_MODE:
                                    current_mode = PEN_MODE
                                status_message = f"Selected color: {btn['name']}"
                                status_timer = 30
                                break

                        # Start drawing if not clicking UI
                        if event.pos[1] < HEIGHT - toolbar_height and not chat_input_box.collidepoint(event.pos):
                            if current_mode == FILL_MODE:
                                flood_fill(canvas, event.pos, current_color)
                                status_message = f"Area filled with {color_palette[current_color_index]['name']}"
                                status_timer = 30
                            else:
                                drawing = True
                                last_pos = event.pos
                                active_color = WHITE if current_mode == ERASE_MODE else current_color
                                active_brushsize = brush_size + 20 if current_mode == ERASE_MODE else brush_size
                                pygame.draw.circle(canvas, active_color, last_pos, active_brushsize // 2)
                                if user_data["role"] == "drawer" and game_instance:
                                    game_instance.handle_drawing_event(event)


            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    drawing = False
                    last_pos = None
                    if user_data["role"] == "drawer":
                        game_instance.handle_drawing_event(event)

            elif event.type == pygame.MOUSEMOTION:
                if drawing and event.pos[1] < HEIGHT - toolbar_height:
                    current_pos = event.pos
                    if last_pos:
                        active_color = WHITE if current_mode == ERASE_MODE else current_color
                        active_brushsize = brush_size + 20 if current_mode == ERASE_MODE else brush_size
                        draw_smooth_line(canvas, active_color, last_pos, current_pos, active_brushsize // 2)
                        
                        if user_data["role"] == "drawer":
                            game_instance.handle_drawing_event(event)
                    last_pos = current_pos
            
            elif event.type == pygame.KEYDOWN and chat_active and user_data["role"] == "guesser" and user_data["name"] not in game_session["correct_guessers"]:
                if event.key == pygame.K_RETURN:
                    if chat_input:
                        if check_guess(chat_input):
                            # Check if all players have guessed or round should end
                            # For now, just clear input
                            pass
                        chat_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                else:
                    chat_input += event.unicode

        elif game_state == GUESSING:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if back_button.collidepoint(event.pos):
                        game_state = MENU
                    elif chat_input_box.collidepoint(event.pos) and user_data["role"] == "guesser" and user_data["name"] not in game_session["correct_guessers"]:
                        chat_active = True
            
            elif event.type == pygame.KEYDOWN and chat_active and user_data["role"] == "guesser" and user_data["name"] not in game_session["correct_guessers"]:
                if event.key == pygame.K_RETURN:
                    if chat_input:
                        if check_guess(chat_input):
                            # Check if all players have guessed or round should end
                            # For now, just clear input
                            pass
                        chat_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                else:
                    chat_input += event.unicode

    # Check if round should end (time is up or all players guessed correctly)
    if game_state in [DRAWING, GUESSING]:
        time_up = pygame.time.get_ticks() > game_session["round_end_time"]
        all_guessed = all_players_guessed()
        
        if time_up or all_guessed:
            if time_up:
                chat_messages.append("System: Time's up!")
            elif all_guessed:
                chat_messages.append("System: All players guessed correctly!")
            game_state = end_round()

    # Clear the screen
    screen.fill(WHITE)

    if game_state == MENU:
        # Draw menu
        
        screen.blit(background_image, (0, 0))
        screen.blit(logo, (logo_x, logo_y))
        screen.blit(menu_background, (create_room_button.x - 10, input_box.y - 10))

        
        
        # Draw input box
        pygame.draw.rect(screen, WHITE, input_box, border_radius=10)
        pygame.draw.rect(screen, BLACK, input_box, 2, border_radius=10)
        
        if active:
            text_surface = font.render(user_text, True, BLACK)
        else:
            text_surface = font.render(placeholder_text if user_text == "" else user_text, 
                                     True, GRAY if user_text == "" else BLACK)

        screen.blit(text_surface, (input_box.x + 10, input_box.y + 10))
        # Draw new buttons with different colors

        if user_data.get("role") == "drawer" and room_input:
            room_id_text = font.render(f"Room ID: {room_input}", True, WHITE)
            room_id_rect = room_id_text.get_rect(center=(WIDTH // 2, quit_button.bottom + 60))
            pygame.draw.rect(screen, BLACK, room_id_rect.inflate(20, 10), border_radius=5)
            screen.blit(room_id_text, room_id_rect)

        pygame.draw.rect(screen, BLUE, create_room_button, border_radius=10)
        pygame.draw.rect(screen, GREEN, join_room_button, border_radius=10)
        pygame.draw.rect(screen, PURPLE, drawer_demo_button, border_radius=10)
        pygame.draw.rect(screen, ORANGE, guesser_demo_button, border_radius=10)
        pygame.draw.rect(screen, RED, quit_button, border_radius=10)
        
        # Button labels
        create_text = font.render("Create Room", True, WHITE)
        join_text = font.render("Join Room", True, WHITE)
        drawer_text = font.render("Drawer Demo", True, WHITE)
        guesser_text = font.render("Guesser Demo", True, WHITE)
        quit_text = font.render("Quit", True, WHITE)
        
        pygame.draw.rect(screen, WHITE, room_box, border_radius=10)
        pygame.draw.rect(screen, BLACK, room_box, 2, border_radius=10)

        room_text_to_display = room_placeholder if room_input == "" and not room_active else room_input
        room_color = GRAY if room_input == "" and not room_active else BLACK
        room_text_surface = font.render(room_text_to_display, True, room_color)
        screen.blit(room_text_surface, (room_box.x + 10, room_box.y + 10))
        screen.blit(create_text, (create_room_button.x + 70, create_room_button.y + 10))
        screen.blit(join_text, (join_room_button.x + 80, join_room_button.y + 10))
        screen.blit(drawer_text, (drawer_demo_button.x + 70, drawer_demo_button.y + 10))
        screen.blit(guesser_text, (guesser_demo_button.x + 65, guesser_demo_button.y + 10))
        screen.blit(quit_text, (quit_button.x + 100, quit_button.y + 10))


        if status_timer > 0:
            status_timer -= 1
            status_text = font.render(status_message, True, WHITE)
            status_rect = status_text.get_rect(center=(WIDTH // 2, quit_button.bottom + 30))
            pygame.draw.rect(screen, BLACK, status_rect.inflate(20, 10), border_radius=5)
            screen.blit(status_text, status_rect)

    elif game_state == DRAWING:
        # Draw canvas area
        screen.blit(canvas, (0, 0))

        # Draw new features
        if selected_word:
            draw_word_hint()
        draw_scoreboard()
        draw_chat()

        # Draw toolbar (only for drawer)
        if user_data["role"] == "drawer":
            toolbar_bg = pygame.Surface((WIDTH, toolbar_height), pygame.SRCALPHA)
            toolbar_bg.fill((0, 0, 0, 128))
            screen.blit(toolbar_bg, (0, HEIGHT - toolbar_height))

            # Draw back button
            pygame.draw.rect(screen, RED, back_button)
            back_text = font.render("Back", True, WHITE)
            screen.blit(back_text, (back_button.x + 30, back_button.y + 10))

            # Draw tool buttons
            pygame.draw.rect(screen, GREEN if current_mode == PEN_MODE else GRAY, pen_button)
            pygame.draw.rect(screen, BLACK, pen_button, 2)
            if pen_icon:
                screen.blit(pen_icon, (pen_button.x + 2, pen_button.y + 2))
            
            pygame.draw.rect(screen, GREEN if current_mode == FILL_MODE else GRAY, bucket_button)
            pygame.draw.rect(screen, BLACK, bucket_button, 2)
            if bucket_icon:
                screen.blit(bucket_icon, (bucket_button.x + 2, bucket_button.y + 2))
            
            pygame.draw.rect(screen, GREEN if current_mode == ERASE_MODE else GRAY, eraser_button)
            pygame.draw.rect(screen, BLACK, eraser_button, 2)
            if eraser_icon:
                screen.blit(eraser_icon, (eraser_button.x + 2, eraser_button.y + 2))

            # Draw color buttons
            for i, btn in enumerate(color_buttons):
                pygame.draw.rect(screen, btn["color"], btn["rect"])
                border_color = BLACK if btn["color"] != BLACK else WHITE
                pygame.draw.rect(screen, border_color, btn["rect"], 2)
                if i == current_color_index and current_mode != ERASE_MODE:
                    pygame.draw.rect(screen, WHITE, btn["rect"].inflate(4, 4), 2)

            # Draw brush size buttons
            for i, btn in enumerate(brush_size_buttons):
                pygame.draw.rect(screen, GRAY, btn["rect"], border_radius=5)
                pygame.draw.rect(screen, BLACK, btn["rect"], 1, border_radius=5)
                if i == brush_size_index:
                    pygame.draw.rect(screen, WHITE, btn["rect"].inflate(4, 4), 2, border_radius=7)

                dot_color = current_color if current_mode != ERASE_MODE else WHITE
                dot_size = btn["size"] if btn["size"] < brush_button_size - 10 else brush_button_size - 10
                pygame.draw.circle(screen, dot_color, btn["rect"].center, dot_size // 2)
                pygame.draw.circle(screen, BLACK, btn["rect"].center, dot_size // 2, 1)

            # Draw current mode
            if current_mode == ERASE_MODE:
                mode_text = font.render("Mode: Eraser", True, WHITE)
            elif current_mode == FILL_MODE:
                mode_text = font.render(f"Mode: Paint Bucket | Color: {color_palette[current_color_index]['name']}", True, WHITE)
            else:
                mode_text = font.render(f"Mode: Pen | Color: {color_palette[current_color_index]['name']}", True, WHITE)
            screen.blit(mode_text, (WIDTH // 2 - 150, HEIGHT - toolbar_height + 15))

        # Draw status message
        if status_timer > 0:
            status_timer -= 1
            status_text = font.render(status_message, True, WHITE)
            status_rect = status_text.get_rect(center=(WIDTH // 2, HEIGHT - toolbar_height - 20))
            pygame.draw.rect(screen, BLACK, status_rect.inflate(20, 10), border_radius=5)
            screen.blit(status_text, status_rect)

    elif game_state == GUESSING:
        # Draw canvas area
        screen.blit(canvas, (0, 0))

        # Draw UI elements
        if selected_word:
            draw_word_hint()
        draw_scoreboard()
        draw_chat()

        # Draw back button (smaller and at top left)
        pygame.draw.rect(screen, RED, back_button)
        back_text = font.render("Back", True, WHITE)
        screen.blit(back_text, (back_button.x + 30, back_button.y + 10))

        # Draw status message
        if status_timer > 0:
            status_timer -= 1
            status_text = font.render(status_message, True, WHITE)
            status_rect = status_text.get_rect(center=(WIDTH // 2, HEIGHT - toolbar_height - 20))
            pygame.draw.rect(screen, BLACK, status_rect.inflate(20, 10), border_radius=5)
            screen.blit(status_text, status_rect)

    pygame.display.flip()

if game_instance:
    game_instance.running = False  # ส่งสัญญาณให้ network thread หยุดทำงาน
    if hasattr(game_instance, 'network_thread') and game_instance.network_thread.is_alive():
        game_instance.network_thread.join()  # รอให้ thread ทำงานเสร็จ
pygame.quit()



if __name__ == "__main__":
    game_instance = DrawingGame()
    game_instance.run()
    pygame.quit()
    sys.exit()
