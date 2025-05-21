import tkinter as tk
import random
import time
import math
import pygame # Added pygame
import pandas as pd # Added pandas
import os # Added os
from datetime import datetime # Added datetime

# --- Pygame Mixer Initialization ---
try:
    pygame.mixer.init()
    HIT_SOUND = pygame.mixer.Sound("hit.wav") # Replace with your sound file
    MISS_SOUND = pygame.mixer.Sound("miss.wav") # Replace with your sound file
    SOUND_ENABLED = True
except Exception as e:
    print(f"Could not initialize sound: {e}. Sound will be disabled.")
    HIT_SOUND = None
    MISS_SOUND = None
    SOUND_ENABLED = False

# --- Constants ---
VERSION = "0.1"
RESULTS_DIR = "results"
DATAFRAME_COLUMNS = [
    "click_datetime", "reaction_time", "precision_factor", "round_start_time_iso",
    "game_version", "target_radius", "misses_since_last_hit",
    "round_number", "click_in_round_number", "clicked_quadrant"
]

WINDOW_WIDTH = 800 # Will be updated to screen width
WINDOW_HEIGHT = 600 # Will be updated to screen height
CIRCLE_RADIUS = 30
MAX_CIRCLES = 1 
TARGET_COLOR = "orange" 
BACKGROUND_COLOR = "lightgrey" 
SCORE_FONT = ("Arial", 14)
MAX_HISTORY_LENGTH = 10
CIRCLES_PER_ROUND = 10 

START_NEXT_ROUND_CIRCLE_COLOR = "orange"
START_NEXT_ROUND_CIRCLE_RADIUS = 50
SUMMARY_FONT = ("Arial", 20, "bold")

# Quadrant UI
QUAD_INDICATOR_ENABLED_COLOR = "orange"
QUAD_INDICATOR_DISABLED_COLOR = "darkkhaki" 
QUAD_INDICATOR_WIDTH = 16 * 5
QUAD_INDICATOR_HEIGHT = 10 * 5
QUAD_INDICATOR_KEY_FONT = ("Arial", 7) 

# Quadrant spawning flags
spawn_q1_top_right = True
spawn_q2_top_left = True
spawn_q3_bottom_left = False
spawn_q4_bottom_right = False

# --- Game State ---
circles = [] # List to store active circle objects (dictionaries)
score_history = [] # Store (points, reaction_time) tuples for last N clicks
last_click_points = 0
avg_points = 0
last_reaction_time = 0.0
avg_reaction_time = 0.0
start_time = None # To measure reaction time for the current target - review if still needed with per-circle spawn_time


# Round specific state
current_round_clicks = 0
current_round_number = 0
game_paused_for_summary = False
current_round_score_history = [] # list of (points, reaction_time)
summary_elements_ids = [] # To store IDs of summary text and button on canvas
summary_circle_data = {} # Holds info for the "start next round" circle {id, x, y, radius}

# New pandas-related game state
current_round_start_time = None # Stores datetime object for the start of the round
miss_counter_since_last_hit = 0
current_round_data_rows = [] # List of dicts for current round's data
all_time_results_df = pd.DataFrame(columns=DATAFRAME_COLUMNS) # Holds all loaded CSV data

# New UI state for quadrant indicators
quad_indicator_canvas_ids = {"q2_tl": None, "q1_tr": None, "q3_bl": None, "q4_br": None} # For the rectangle shapes
quad_indicator_text_ids = {"q2_tl": None, "q1_tr": None, "q3_bl": None, "q4_br": None}   # For the text (U, I, J, K) on the shapes
quad_error_message_id = None # To store the canvas ID of the "Please enable a quadrant" message

# Mapping for easy access to keys, flags, and display text for indicators
QUAD_CONFIG_MAP = {
    "q2_tl": {"key_char": "U", "spawn_flag_name": "spawn_q2_top_left", "x_mult": 0, "y_mult": 0},
    "q1_tr": {"key_char": "I", "spawn_flag_name": "spawn_q1_top_right", "x_mult": 1, "y_mult": 0},
    "q3_bl": {"key_char": "J", "spawn_flag_name": "spawn_q3_bottom_left", "x_mult": 0, "y_mult": 1},
    "q4_br": {"key_char": "K", "spawn_flag_name": "spawn_q4_bottom_right", "x_mult": 1, "y_mult": 1}
}

# --- Main Application Class ---
class ClickTrainerApp:
    def __init__(self, master):
        self.master = master
        master.title("Mouse Clicker Trainer")

        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        master.attributes('-fullscreen', True)

        global WINDOW_WIDTH, WINDOW_HEIGHT
        WINDOW_WIDTH = screen_width
        WINDOW_HEIGHT = screen_height

        master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Canvas for drawing - now uses full window height
        self.canvas = tk.Canvas(master, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg=BACKGROUND_COLOR)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.handle_click)

        # Score display frame removed
        # self.score_frame = tk.Frame(master, height=100)
        # self.score_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Labels for scores and times - now placed directly on master window
        label_y_position = WINDOW_HEIGHT - 30 # Position labels near the bottom
        label_start_x = 10
        label_width = 200 # Approximate width for each label based on font and text

        self.last_score_label = tk.Label(master, text="Last Score: 0", font=SCORE_FONT, fg="black", bg=BACKGROUND_COLOR, width=20, anchor="w")
        self.last_score_label.place(x=label_start_x, y=label_y_position)

        self.avg_score_label = tk.Label(master, text=f"Avg Score ({MAX_HISTORY_LENGTH}): 0", font=SCORE_FONT, fg="black", bg=BACKGROUND_COLOR, width=20, anchor="w")
        self.avg_score_label.place(x=label_start_x + label_width, y=label_y_position)

        self.last_time_label = tk.Label(master, text="Last Time: 0.00s", font=SCORE_FONT, fg="black", bg=BACKGROUND_COLOR, width=20, anchor="w")
        self.last_time_label.place(x=label_start_x + label_width * 2, y=label_y_position)

        self.avg_time_label = tk.Label(master, text=f"Avg Time ({MAX_HISTORY_LENGTH}): 0.00s", font=SCORE_FONT, fg="black", bg=BACKGROUND_COLOR, width=20, anchor="w")
        self.avg_time_label.place(x=label_start_x + label_width * 3, y=label_y_position)

        # Round progress label (top center)
        self.round_progress_label = tk.Label(master, text="", font=SCORE_FONT, fg="black", bg=BACKGROUND_COLOR)
        self.round_progress_label.place(relx=0.5, y=10, anchor=tk.N)

        # Key bindings
        master.bind('<q>', self.quit_game)
        master.bind('<r>', self.reset_game_event)

        # Quadrant toggle key bindings
        master.bind('<u>', self.toggle_q2_tl_event) # Top-Left
        master.bind('<i>', self.toggle_q1_tr_event) # Top-Right
        master.bind('<j>', self.toggle_q3_bl_event) # Bottom-Left
        master.bind('<k>', self.toggle_q4_br_event) # Bottom-Right

        # Ensure results directory exists
        os.makedirs(RESULTS_DIR, exist_ok=True)

        # Initialize round state for the very first round (starts with summary)
        self.end_round_and_show_summary()

    def quit_game(self, event=None):
        self.master.destroy()

    def reset_game_event(self, event=None):
        self.reset_game()

    def clear_summary_elements(self):
        global summary_elements_ids, quad_indicator_canvas_ids, quad_indicator_text_ids, quad_error_message_id
        for element_id in summary_elements_ids:
            self.canvas.delete(element_id)
        summary_elements_ids.clear()

        for key_map in [quad_indicator_canvas_ids, quad_indicator_text_ids]:
            for key in key_map:
                if key_map[key]:
                    self.canvas.delete(key_map[key])
                key_map[key] = None
        
        if quad_error_message_id:
            self.canvas.delete(quad_error_message_id)
            quad_error_message_id = None

    def reset_game(self):
        global circles, score_history, last_click_points, avg_points, last_reaction_time, avg_reaction_time, start_time
        global current_round_clicks, current_round_number, game_paused_for_summary, current_round_score_history, summary_elements_ids
        global miss_counter_since_last_hit, current_round_data_rows, all_time_results_df, DATAFRAME_COLUMNS

        # Clear existing game circles from canvas and list
        for circle_data in circles[:]:
            self.canvas.delete(circle_data["id"])
        circles.clear()

        # Clear summary display if any
        self.clear_summary_elements()

        # Reset overall scores and history
        score_history.clear()
        last_click_points = 0
        avg_points = 0
        last_reaction_time = 0.0
        avg_reaction_time = 0.0
        start_time = None

        # Reset round-specific state
        current_round_clicks = 0
        current_round_score_history.clear()
        current_round_number = 1
        game_paused_for_summary = False

        # Reset pandas-related data for the session
        miss_counter_since_last_hit = 0
        current_round_data_rows.clear()
        all_time_results_df = pd.DataFrame(columns=DATAFRAME_COLUMNS)

        # Clear round progress label on full reset before showing summary
        if hasattr(self, 'round_progress_label'):
            self.round_progress_label.config(text="")

        self.update_score_display()
        self.end_round_and_show_summary() # As per user's startup preference
        print("Game Reset!")

    def start_new_round_setup(self):
        """Called at the beginning of a new round or game reset."""
        global current_round_clicks, current_round_score_history, game_paused_for_summary, circles
        global current_round_start_time, current_round_data_rows, miss_counter_since_last_hit, CIRCLES_PER_ROUND

        current_round_clicks = 0
        current_round_score_history.clear()
        game_paused_for_summary = False
        self.clear_summary_elements()
        for circle_data in circles[:]:
            self.canvas.delete(circle_data["id"])
        circles.clear()

        current_round_start_time = datetime.now()
        current_round_data_rows.clear()

        # Update round progress label for the new round
        if hasattr(self, 'round_progress_label') and current_round_number > 0:
            self.round_progress_label.config(text=f"Clicks: 0/{CIRCLES_PER_ROUND}")
        elif hasattr(self, 'round_progress_label'): # For round 0 / initial welcome screen
             self.round_progress_label.config(text="")

        self.spawn_initial_circles()

    def end_round_and_show_summary_event(self, event=None):
        """Event wrapper for ending round and showing summary."""
        print("Key 'r' pressed, manually ending round and showing summary.")
        self.end_round_and_show_summary()

    def end_round_and_show_summary(self):
        global game_paused_for_summary, current_round_number, current_round_score_history, summary_elements_ids, circles
        global current_round_data_rows, RESULTS_DIR, DATAFRAME_COLUMNS, VERSION # Pandas related

        # Clear round progress label when summary is shown
        if hasattr(self, 'round_progress_label'): # Check if label exists, for safety during init
            self.round_progress_label.config(text="")

        self.clear_summary_elements()

        # --- Save current round data ---
        if current_round_data_rows:
            round_df = pd.DataFrame(current_round_data_rows)
            # Ensure columns are in the defined order and all are present
            for col in DATAFRAME_COLUMNS:
                if col not in round_df.columns:
                    round_df[col] = None # Or a suitable default if a column was somehow missed for a row
            round_df = round_df[DATAFRAME_COLUMNS]

            timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"results_{timestamp_str}.csv"
            filepath = os.path.join(RESULTS_DIR, filename)
            try:
                round_df.to_csv(filepath, index=False)
                print(f"Round {current_round_number} data saved to {filepath}")
            except Exception as e:
                print(f"Error saving round data to {filepath}: {e}")
        # else: print("No click data to save for this round.") # If round ended with 0 clicks

        # --- Load all historical results ---
        self.load_all_results()
        # Now all_time_results_df is populated and can be used for plotting, etc.
        # For now, we just print. Example: print(all_time_results_df.head())

        game_paused_for_summary = True
        self.draw_or_update_quad_indicators() # Draw/update indicators when summary is shown

        # Calculate round summary
        round_avg_score = 0
        round_avg_time = 0.0
        if current_round_score_history:
            total_round_points = sum(item[0] for item in current_round_score_history)
            total_round_time = sum(item[1] for item in current_round_score_history)
            round_avg_score = total_round_points // len(current_round_score_history)
            round_avg_time = total_round_time / len(current_round_score_history)

        # Display summary text (ensure this happens after indicators so text isn't covered if overlap)
        summary_y_start = WINDOW_HEIGHT // 2 - 100
        if current_round_number == 0:
            text_id1 = self.canvas.create_text(WINDOW_WIDTH // 2, summary_y_start,
                                           text="Welcome to the Mouse Clicker Trainer!",
                                           font=SUMMARY_FONT, fill="black")
            text_id2 = self.canvas.create_text(WINDOW_WIDTH // 2, summary_y_start + 40,
                                            text="Click below to start",
                                            font=SCORE_FONT, fill="black")
            text_id3 = self.canvas.create_text(WINDOW_WIDTH // 2, summary_y_start + 70,
                                            text=f"Each round will last {CIRCLES_PER_ROUND} circles",
                                            font=SCORE_FONT, fill="black")
            summary_elements_ids.extend([text_id1, text_id2, text_id3])
        else:
            text_id1 = self.canvas.create_text(WINDOW_WIDTH // 2, summary_y_start,
                                           text=f"Round {current_round_number} Complete!",
                                           font=SUMMARY_FONT, fill="black")
            text_id2 = self.canvas.create_text(WINDOW_WIDTH // 2, summary_y_start + 40,
                                            text=f"Avg Score this Round: {round_avg_score}",
                                            font=SCORE_FONT, fill="black")
            text_id3 = self.canvas.create_text(WINDOW_WIDTH // 2, summary_y_start + 70,
                                            text=f"Avg Time this Round: {round_avg_time:.2f}s",
                                            font=SCORE_FONT, fill="black")
            summary_elements_ids.extend([text_id1, text_id2, text_id3])

        # Spawn "Start Next Round" circle
        cx, cy = WINDOW_WIDTH // 2, summary_y_start + 150
        start_button_id = self.canvas.create_oval(cx - START_NEXT_ROUND_CIRCLE_RADIUS,
                                                 cy - START_NEXT_ROUND_CIRCLE_RADIUS,
                                                 cx + START_NEXT_ROUND_CIRCLE_RADIUS,
                                                 cy + START_NEXT_ROUND_CIRCLE_RADIUS,
                                                 fill=START_NEXT_ROUND_CIRCLE_COLOR, outline="black")
        if current_round_number == 0:
            start_button_text_id_text = f"Start\nRound"
        else:
            start_button_text_id_text = f"Start Next\nRound"
        start_button_text_id = self.canvas.create_text(cx, cy, text=start_button_text_id_text, font=("Arial", 10, "bold"), fill="black", justify=tk.CENTER)
        
        # Store the button and its properties for click detection
        # We only need to store one "summary circle" data because only one can exist
        global summary_circle_data # Add this to globals if not already
        summary_circle_data = {"id": start_button_id, "x": cx, "y": cy, "radius": START_NEXT_ROUND_CIRCLE_RADIUS}
        summary_elements_ids.extend([start_button_id, start_button_text_id])

        print(f"Round {current_round_number} ended. Summary displayed.")

    def spawn_circle(self):
        global start_time, circles # Ensure circles is global here if modified
        global spawn_q1_top_right, spawn_q2_top_left, spawn_q3_bottom_left, spawn_q4_bottom_right

        if not (spawn_q1_top_right or spawn_q2_top_left or spawn_q3_bottom_left or spawn_q4_bottom_right):
            print("No quadrants enabled for spawning!")
            return

        if len(circles) < MAX_CIRCLES:
            available_quadrants = []
            if spawn_q1_top_right: available_quadrants.append(1)
            if spawn_q2_top_left: available_quadrants.append(2)
            if spawn_q3_bottom_left: available_quadrants.append(3)
            if spawn_q4_bottom_right: available_quadrants.append(4)

            if not available_quadrants:
                print("Error: No available quadrants selected for spawning despite initial check.") # Should not happen
                return

            chosen_quadrant = random.choice(available_quadrants)

            mid_x = WINDOW_WIDTH // 2
            mid_y = WINDOW_HEIGHT // 2

            # Define spawn boundaries for each quadrant, ensuring circle fits
            # Min/max for x and y within the quadrant
            x_min, x_max, y_min, y_max = 0, 0, 0, 0

            quad_name = "unknown" # For logging
            if chosen_quadrant == 1: # Top-Right
                quad_name = "tr"
                x_min = mid_x + CIRCLE_RADIUS
                x_max = WINDOW_WIDTH - CIRCLE_RADIUS
                y_min = CIRCLE_RADIUS
                y_max = mid_y - CIRCLE_RADIUS
            elif chosen_quadrant == 2: # Top-Left
                quad_name = "tl"
                x_min = CIRCLE_RADIUS
                x_max = mid_x - CIRCLE_RADIUS
                y_min = CIRCLE_RADIUS
                y_max = mid_y - CIRCLE_RADIUS
            elif chosen_quadrant == 3: # Bottom-Left
                quad_name = "bl"
                x_min = CIRCLE_RADIUS
                x_max = mid_x - CIRCLE_RADIUS
                y_min = mid_y + CIRCLE_RADIUS
                y_max = WINDOW_HEIGHT - CIRCLE_RADIUS
            elif chosen_quadrant == 4: # Bottom-Right
                quad_name = "br"
                x_min = mid_x + CIRCLE_RADIUS
                x_max = WINDOW_WIDTH - CIRCLE_RADIUS
                y_min = mid_y + CIRCLE_RADIUS
                y_max = WINDOW_HEIGHT - CIRCLE_RADIUS

            # Ensure valid spawn range (e.g., screen not too small for quadrant definitions)
            if x_min >= x_max or y_min >= y_max:
                print(f"Warning: Quadrant {chosen_quadrant} is too small to spawn a circle. Spawning anywhere.")
                # Fallback to spawning anywhere if a quadrant is ill-defined (e.g. screen too small)
                x = random.randint(CIRCLE_RADIUS, WINDOW_WIDTH - CIRCLE_RADIUS)
                y = random.randint(CIRCLE_RADIUS, WINDOW_HEIGHT - CIRCLE_RADIUS)
            else:
                x = random.randint(x_min, x_max)
                y = random.randint(y_min, y_max)

            circle_id = self.canvas.create_oval(x - CIRCLE_RADIUS, y - CIRCLE_RADIUS,
                                                x + CIRCLE_RADIUS, y + CIRCLE_RADIUS,
                                                fill=TARGET_COLOR, outline=TARGET_COLOR)
            circles.append({"id": circle_id, "x": x, "y": y, "radius": CIRCLE_RADIUS, "spawn_time": time.time(), "quadrant_name": quad_name})
            # The original start_time logic for a single global timer seems less relevant now 
            # as each circle has its own spawn_time. If MAX_CIRCLES=1, it's equivalent.
            # if len(circles) == 1:
            #    start_time = circles[-1]["spawn_time"]

    def spawn_initial_circles(self):
        for _ in range(MAX_CIRCLES):
            self.spawn_circle()

    def update_score_display(self):
        global last_click_points, avg_points, last_reaction_time, avg_reaction_time
        self.last_score_label.config(text=f"Last Score: {last_click_points}")
        self.avg_score_label.config(text=f"Avg Score ({MAX_HISTORY_LENGTH}): {avg_points}")
        self.last_time_label.config(text=f"Last Time: {last_reaction_time:.2f}s")
        self.avg_time_label.config(text=f"Avg Time ({MAX_HISTORY_LENGTH}): {avg_reaction_time:.2f}s")

    def handle_click(self, event):
        global start_time, last_click_points, avg_points, last_reaction_time, avg_reaction_time, score_history
        global circles, game_paused_for_summary, summary_circle_data, current_round_clicks, CIRCLES_PER_ROUND
        global current_round_number, current_round_score_history
        global miss_counter_since_last_hit, current_round_data_rows, current_round_start_time
        global VERSION, CIRCLE_RADIUS

        if game_paused_for_summary:
            if summary_circle_data:
                dist_sq_summary = (event.x - summary_circle_data["x"])**2 + (event.y - summary_circle_data["y"])**2
                if dist_sq_summary <= summary_circle_data["radius"]**2:
                    # Check if at least one quadrant is enabled before starting
                    if not self.check_and_display_quad_error():
                        print("Attempted to start round with no quadrants enabled.")
                        return # Don't start the round

                    print("Starting next round...")
                    if current_round_number == 0: # If it was the welcome screen
                        current_round_number = 1 # Start with Round 1
                    else:
                        current_round_number += 1
                    self.start_new_round_setup()
                    return
            return

        # --- Game is active (not paused for summary) ---
        clicked_on_circle = False
        for circle_data in circles[:]: # Iterate over a copy for safe removal
            dist_sq = (event.x - circle_data["x"])**2 + (event.y - circle_data["y"])**2
            if dist_sq <= circle_data["radius"]**2:
                clicked_on_circle = True
                current_time = time.time()
                reaction = current_time - circle_data["spawn_time"]
                distance_from_center = math.sqrt(dist_sq)
                precision_factor = max(0, (CIRCLE_RADIUS - distance_from_center) / CIRCLE_RADIUS)

                reaction_score_component = max(0, int(100 / (reaction + 0.01)))
                precision_score_component = int(precision_factor * 100)
                points = reaction_score_component + precision_score_component

                last_click_points = points
                last_reaction_time = reaction

                # Update overall display history (for UI labels)
                score_history.append((points, reaction))
                if len(score_history) > MAX_HISTORY_LENGTH:
                    score_history.pop(0)
                
                # Update current round display history (for UI summary)
                current_round_score_history.append((points, reaction))

                # --- Data Logging for Pandas ---
                click_data_row = {
                    "click_datetime": datetime.now().isoformat(),
                    "reaction_time": reaction,
                    "precision_factor": precision_factor,
                    "round_start_time_iso": current_round_start_time.isoformat() if current_round_start_time else None,
                    "game_version": VERSION,
                    "target_radius": CIRCLE_RADIUS,
                    "misses_since_last_hit": miss_counter_since_last_hit,
                    "round_number": current_round_number,
                    "click_in_round_number": current_round_clicks + 1, # current_round_clicks not yet incremented
                    "clicked_quadrant": circle_data.get("quadrant_name", "unknown") # Log the quadrant
                }
                current_round_data_rows.append(click_data_row)
                miss_counter_since_last_hit = 0
                # --- End Data Logging ---

                # Calculate overall averages for UI
                if score_history:
                    total_hist_points = sum(item[0] for item in score_history)
                    total_hist_time = sum(item[1] for item in score_history)
                    avg_points = total_hist_points // len(score_history)
                    avg_reaction_time = total_hist_time / len(score_history)

                self.canvas.delete(circle_data["id"])
                circles.remove(circle_data)
                if SOUND_ENABLED and HIT_SOUND:
                    HIT_SOUND.play()
                
                current_round_clicks += 1 # Increment before using in print or label
                print(f"Hit! Round: {current_round_number}, Click: {current_round_clicks}/{CIRCLES_PER_ROUND}, Time: {reaction:.2f}s, Points: {points}")

                # Update round progress label
                if hasattr(self, 'round_progress_label'):
                    self.round_progress_label.config(text=f"Clicks: {current_round_clicks}/{CIRCLES_PER_ROUND}")

                if current_round_clicks >= CIRCLES_PER_ROUND:
                    self.end_round_and_show_summary()
                else:
                    self.spawn_circle() # Spawn a new game circle
                break # Processed click for one circle

        if not clicked_on_circle and not game_paused_for_summary: # Only process miss if game not paused
            if SOUND_ENABLED and MISS_SOUND:
                MISS_SOUND.play()
            print("Miss!")
            miss_counter_since_last_hit += 1 # Increment miss counter

        if not game_paused_for_summary: # Don't update score display if summary is shown (it has its own text)
             self.update_score_display()

    def load_all_results(self):
        """Loads all .csv files from the RESULTS_DIR into the all_time_results_df."""
        global all_time_results_df, RESULTS_DIR, DATAFRAME_COLUMNS
        
        all_loaded_dfs = []
        if not os.path.exists(RESULTS_DIR):
            print(f"Results directory '{RESULTS_DIR}' not found. No data loaded.")
            all_time_results_df = pd.DataFrame(columns=DATAFRAME_COLUMNS)
            return

        for filename in os.listdir(RESULTS_DIR):
            if filename.endswith(".csv"):
                filepath = os.path.join(RESULTS_DIR, filename)
                try:
                    df = pd.read_csv(filepath)
                    all_loaded_dfs.append(df)
                    print(f"Loaded: {filename}")
                except Exception as e:
                    print(f"Error loading {filepath}: {e}")
        
        if all_loaded_dfs:
            all_time_results_df = pd.concat(all_loaded_dfs, ignore_index=True)
            # Ensure DataFrame has all columns, even if some CSVs were from older versions/missing columns
            for col in DATAFRAME_COLUMNS:
                if col not in all_time_results_df.columns:
                    all_time_results_df[col] = None # Or a more appropriate default
            all_time_results_df = all_time_results_df[DATAFRAME_COLUMNS] # Reorder/select columns
            print(f"Total historical records loaded: {len(all_time_results_df)}")
        else:
            print("No previous results found to load.")
            all_time_results_df = pd.DataFrame(columns=DATAFRAME_COLUMNS)

    def draw_or_update_quad_indicators(self):
        global quad_indicator_canvas_ids, quad_indicator_text_ids, QUAD_CONFIG_MAP
        global QUAD_INDICATOR_WIDTH, QUAD_INDICATOR_HEIGHT, QUAD_INDICATOR_ENABLED_COLOR, QUAD_INDICATOR_DISABLED_COLOR, QUAD_INDICATOR_KEY_FONT
        global summary_elements_ids, spawn_q1_top_right, spawn_q2_top_left, spawn_q3_bottom_left, spawn_q4_bottom_right # Direct flag access

        start_button_y_center = WINDOW_HEIGHT // 2 - 100 + 150
        grid_base_y = start_button_y_center + START_NEXT_ROUND_CIRCLE_RADIUS + 30 # Increased padding a bit

        grid_total_width = (QUAD_INDICATOR_WIDTH * 2) # No padding between indicators
        grid_start_x = (WINDOW_WIDTH - grid_total_width) // 2

        # Clear previous error message if any (it will be redrawn if still needed by handle_click)
        global quad_error_message_id
        if quad_error_message_id:
            self.canvas.delete(quad_error_message_id)
            quad_error_message_id = None

        for q_map_key, config in QUAD_CONFIG_MAP.items():
            q_flag = globals()[config["spawn_flag_name"]] # Get current state of the spawn flag
            x_offset_mult = config["x_mult"]
            y_offset_mult = config["y_mult"]
            key_char = config["key_char"]

            x0 = grid_start_x + (x_offset_mult * QUAD_INDICATOR_WIDTH)
            y0 = grid_base_y + (y_offset_mult * QUAD_INDICATOR_HEIGHT)
            x1 = x0 + QUAD_INDICATOR_WIDTH
            y1 = y0 + QUAD_INDICATOR_HEIGHT

            color = QUAD_INDICATOR_ENABLED_COLOR if q_flag else QUAD_INDICATOR_DISABLED_COLOR

            if quad_indicator_canvas_ids[q_map_key]:
                self.canvas.delete(quad_indicator_canvas_ids[q_map_key])
            rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black")
            quad_indicator_canvas_ids[q_map_key] = rect_id
            if rect_id not in summary_elements_ids: summary_elements_ids.append(rect_id)

            # Add key text
            if quad_indicator_text_ids[q_map_key]:
                self.canvas.delete(quad_indicator_text_ids[q_map_key])
            text_color = "black" if q_flag else "gray40" # Dim text if disabled
            text_id = self.canvas.create_text(x0 + QUAD_INDICATOR_WIDTH / 2, 
                                               y0 + QUAD_INDICATOR_HEIGHT / 2, 
                                               text=key_char, 
                                               font=QUAD_INDICATOR_KEY_FONT, 
                                               fill=text_color)
            quad_indicator_text_ids[q_map_key] = text_id
            if text_id not in summary_elements_ids: summary_elements_ids.append(text_id)

    def toggle_quadrant_flag(self, flag_name_key_in_map):
        """Toggles a quadrant flag using QUAD_CONFIG_MAP and redraws UI if summary is active."""
        global game_paused_for_summary, QUAD_CONFIG_MAP
        spawn_flag_to_toggle = QUAD_CONFIG_MAP[flag_name_key_in_map]["spawn_flag_name"]

        current_value = globals()[spawn_flag_to_toggle]
        globals()[spawn_flag_to_toggle] = not current_value
        print(f"Toggled {spawn_flag_to_toggle} to {globals()[spawn_flag_to_toggle]}")
        
        if game_paused_for_summary:
            self.draw_or_update_quad_indicators()
            # Also check if the error message for "no quadrants enabled" needs to be shown/hidden
            self.check_and_display_quad_error()

    # Specific event handlers for each key - now pass the map key
    def toggle_q1_tr_event(self, event=None): # Top-Right (I)
        self.toggle_quadrant_flag("q1_tr")

    def toggle_q2_tl_event(self, event=None): # Top-Left (U)
        self.toggle_quadrant_flag("q2_tl")

    def toggle_q3_bl_event(self, event=None): # Bottom-Left (J)
        self.toggle_quadrant_flag("q3_bl")

    def toggle_q4_br_event(self, event=None): # Bottom-Right (K)
        self.toggle_quadrant_flag("q4_br")

    def check_and_display_quad_error(self):
        """Checks if any quadrant is enabled and displays/hides an error message."""
        global spawn_q1_top_right, spawn_q2_top_left, spawn_q3_bottom_left, spawn_q4_bottom_right, quad_error_message_id
        any_quad_enabled = spawn_q1_top_right or spawn_q2_top_left or spawn_q3_bottom_left or spawn_q4_bottom_right
        
        # Position for error message: below the quadrant indicators
        grid_base_y = (WINDOW_HEIGHT // 2 - 100 + 150) + START_NEXT_ROUND_CIRCLE_RADIUS + 30
        error_y_pos = grid_base_y + (QUAD_INDICATOR_HEIGHT * 2) + 10 # 10px below the grid

        if not any_quad_enabled:
            if not quad_error_message_id:
                quad_error_message_id = self.canvas.create_text(WINDOW_WIDTH // 2, error_y_pos,
                                                                text="At least one quadrant must be enabled to start!",
                                                                font=SCORE_FONT, fill="black", anchor=tk.N)
                if quad_error_message_id not in summary_elements_ids: summary_elements_ids.append(quad_error_message_id)
        else:
            if quad_error_message_id:
                self.canvas.delete(quad_error_message_id)
                if quad_error_message_id in summary_elements_ids: summary_elements_ids.remove(quad_error_message_id)
                quad_error_message_id = None
        return any_quad_enabled


# --- Main ---
if __name__ == "__main__":
    root = tk.Tk()
    app = ClickTrainerApp(root)
    root.mainloop()
