# Mouse Clicker Trainer

A Python-based mouse clicker trainer application designed to help users improve their mouse accuracy and reaction speed, particularly designed for training of Mouseless and similar keyboard-mouse implementations.

## Features

*   **Circle Clicking:** Click on spawned circles as quickly and accurately as possible.
*   **Multiple Circles:** Supports spawning multiple circles on screen (configurable).
*   **Full-Screen Mode:** Runs in full-screen for an immersive experience.
*   **Quadrant Control:** Configure in which screen quadrants circles can spawn.
*   **Round-Based Gameplay:**
    *   Play in rounds of a configurable number of clicks (e.g., 10 clicks per round).
    *   View a summary of performance (average score, average time) after each round.
    *   Welcome screen to start the game.
*   **Scoring System:**
    *   Points are awarded based on reaction time and click precision.
    *   Displays last click's score and reaction time.
    *   Displays running average score and reaction time for the last N clicks.
*   **Sound Effects:** Basic hit and miss sounds (requires `pygame` and sound files).
*   **Controls:**
    *   `q`: Quit the application.
    *   `r`: Reset the game (restarts from the welcome/round 0 summary).
*   **Data Logging:**
    *   Each click's data (timestamp, reaction time, precision, misses since last hit, round info, target size, version) is logged.
    *   Round data is saved to a CSV file in a `results` folder, named with a timestamp.
    *   Historical results are loaded and aggregated when viewing round summaries (preparation for future plotting/analysis).

## Requirements

*   Python 3.x
*   Tkinter (usually included with Python)
*   Pygame (`pip install pygame`)
*   Pandas (`pip install pandas`)

## How to Run

1.  Ensure all requirements are installed.
2.  Place `hit.wav` and `miss.wav` sound files in the same directory as `mst.py` (or update paths in the script).
3.  Run the script: `python mst.py`

## Configuration

Several parameters can be configured directly in the `mst.py` script:
*   `CIRCLE_RADIUS`
*   `MAX_CIRCLES` (currently set to 1 for round-based play)
*   `TARGET_COLOR`, `BACKGROUND_COLOR`
*   `CIRCLES_PER_ROUND`
*   `spawn_qX_...` flags for quadrant control.
*   Sound file paths.
*   `VERSION` (for data logging) 