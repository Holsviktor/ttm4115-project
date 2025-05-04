# Global Color Definitions
import time


G = (0, 255, 0)   # Green
B = (0, 0, 255)   # Blue
R = (255, 0, 0)   # Red
O = (0, 0, 0)     # Off
Y = (255, 255, 0) # Yellow


# Cross Pixel Map
cross_pixels = [
    O, O, O, O, R, O, O, O,
    O, O, O, O, R, O, O, O,
    O, O, O, O, R, O, O, O,
    R, R, R, R, R, R, R, R,
    O, O, O, O, R, O, O, O,
    O, O, O, O, R, O, O, O,
    O, O, O, O, R, O, O, O,
    O, O, O, O, R, O, O, O,
]


# Lightning Bolt Pixel Map
lightning_bolt_pixels = [
    O, O, O, O, Y, O, O, O,
    O, O, O, Y, Y, O, O, O,
    O, O, O, Y, O, O, O, O,
    O, O, Y, Y, O, O, O, O,
    O, Y, Y, O, O, O, O, O,
    O, Y, O, O, O, O, O, O,
    Y, Y, O, O, O, O, O, O,
    O, Y, O, O, O, O, O, O,
]


# Number 5 Pixel Map
five_digit_pixels = [
    O, O, G, G, G, G, O, O,
    O, O, G, O, O, O, O, O,
    O, O, G, O, O, O, O, O,
    O, O, G, G, G, O, O, O,
    O, O, O, O, O, G, O, O,
    O, O, O, O, O, G, O, O,
    O, O, O, O, O, G, O, O,
    O, O, G, G, G, O, O, O
]


# Number 2 Pixel Map
two_digit_pixels = [
    O, O, O, B, B, B, O, O,
    O, O, B, O, O, O, B, O,
    O, O, O, O, O, O, B, O,
    O, O, O, O, O, O, O, O,
    O, O, O, O, B, B, O, O,
    O, O, O, B, O, O, O, O,
    O, O, B, O, O, O, O, O,
    O, O, B, B, B, B, B, O
]


# Waiting for Press Pixel Map
question_mark_pixels = [
    O, O, O, R, R, O, O, O,
    O, O, R, O, O, R, O, O,
    O, O, O, O, O, R, O, O,
    O, O, O, O, R, O, O, O,
    O, O, O, R, O, O, O, O,
    O, O, O, R, O, O, O, O,
    O, O, O, O, O, O, O, O,
    O, O, O, R, O, O, O, O
]


def _display_arrow(direction, sense):
    arrows = {
        'up': [
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,1,1,1,0,0],
            [0,0,1,0,1,0,1,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,0,0,0,0],
        ],
        'down': [
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,1,0,1,0,1,0],
            [0,0,0,1,1,1,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,0,0,0,0],
        ],
        'right': [
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,0,1,0,0],
            [0,1,1,1,1,1,1,0],
            [0,0,0,0,0,1,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
        ],
        'left': [
            [0,0,0,0,0,0,0,0],
            [0,0,0,1,0,0,0,0],
            [0,0,1,0,0,0,0,0],
            [0,1,1,1,1,1,1,0],
            [0,0,1,0,0,0,0,0],
            [0,0,0,1,0,0,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
        ],
        'stop': [
            [1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,1],
            [1,1,1,1,1,1,1,1],
        ]
    }

    arrow = arrows.get(direction, None)
    if arrow:
        flat_pixels = [_get_color(pixel) for row in arrow for pixel in row]
        sense.set_pixels(flat_pixels)


def _get_color(pixel_value):
    return G if pixel_value == 1 else O


def stop(self):
    self.stop_joystick_thread = True
    if self.joystick_thread:
        self.joystick_thread.join()
    self.sense.clear()


padlock_pixels = [
    O, O, O, O, G, G, O, O,
    O, O, O, G, O, O, G, O,
    O, O, G, O, O, O, O, G,
    O, O, G, O, O, O, O, G,
    O, O, G, O, O, O, O, G,
    O, O, G, O, O, O, O, G,
    O, G, G, G, G, G, G, G,
    O, G, O, O, O, O, O, G,
]


def animate_unlocking(sense):
    frames = [
        # Frame 1: Locked Padlock (initial state)
        [
            O, O, O, O, G, G, O, O,
            O, O, O, G, O, O, G, O,
            O, O, G, O, O, O, O, G,
            O, O, G, O, O, O, O, G,
            O, O, G, O, O, O, O, G,
            O, O, G, O, O, O, O, G,
            O, G, G, G, G, G, G, G,
            O, G, O, O, O, O, O, G,
        ],
        # Frame 2: Shackle starts to open
        [
            O, O, O, O, G, G, O, O,
            O, O, O, G, O, O, G, O,
            O, O, G, O, O, O, O, O,
            O, O, G, O, O, O, O, G,
            O, O, G, O, O, O, O, G,
            O, O, G, O, O, O, O, G,
            O, G, G, G, G, G, G, G,
            O, G, O, O, O, O, O, G,
        ],
        # Frame 3: Shackle half open
        [
            O, O, O, O, G, G, O, O,
            O, O, O, O, O, O, G, O,
            O, O, G, O, O, O, O, O,
            O, O, G, O, O, O, O, O,
            O, O, G, O, O, O, O, G,
            O, O, G, O, O, O, O, G,
            O, G, G, G, G, G, G, G,
            O, G, O, O, O, O, O, G,
        ],
        # Frame 4: Shackle fully open
        [
            O, O, O, O, O, O, O, O,
            O, O, O, O, O, O, G, O,
            O, O, G, O, O, O, O, O,
            O, O, G, O, O, O, O, O,
            O, O, G, O, O, O, O, G,
            O, O, G, O, O, O, O, G,
            O, G, G, G, G, G, G, G,
            O, G, O, O, O, O, O, G,
        ],
        # Frame 5: Padlock turns green to indicate unlocked
        [
            G, G, G, G, G, G, G, G,
            G, G, G, G, G, G, G, G,
            G, G, G, G, G, G, G, G,
            G, G, G, G, G, G, G, G,
            G, G, G, G, G, G, G, G,
            G, G, G, G, G, G, G, G,
            G, G, G, G, G, G, G, G,
            G, G, G, G, G, G, G, G,
        ],
    ]

    # Play animation
    for frame in frames:
        sense.set_pixels(frame)
        time.sleep(0.3)
        
        
        
def animate_locking(sense):
    frames = [
        # Frame 1: Shackle fully open
        [
            O, O, O, O, O, O, O, O,
            O, O, O, O, O, O, G, O,
            O, O, R, O, O, O, O, O,
            O, O, R, O, O, O, O, O,
            O, O, R, O, O, O, O, R,
            O, O, R, O, O, O, O, R,
            O, R, R, R, R, R, R, R,
            O, R, O, O, O, O, O, R,
        ],
        # Frame 2: Shackle half open
        [
            O, O, O, O, R, R, O, O,
            O, O, O, O, O, O, R, O,
            O, O, R, O, O, O, O, O,
            O, O, R, O, O, O, O, O,
            O, O, R, O, O, O, O, R,
            O, O, R, O, O, O, O, R,
            O, R, R, R, R, R, R, R,
            O, R, O, O, O, O, O, R,
        ],
        # Frame 3: Shackle starts to open
        [
            O, O, O, O, R, R, O, O,
            O, O, O, R, O, O, R, O,
            O, O, R, O, O, O, O, O,
            O, O, R, O, O, O, O, R,
            O, O, R, O, O, O, O, R,
            O, O, R, O, O, O, O, R,
            O, R, R, R, R, R, R, R,
            O, R, O, O, O, O, O, R,
        ],
        # Frame 4: Locked Padlock (initial state)
        [
            O, O, O, O, R, R, O, O,
            O, O, O, R, O, O, R, O,
            O, O, R, O, O, O, O, R,
            O, O, R, O, O, O, O, R,
            O, O, R, O, O, O, O, R,
            O, O, R, O, O, O, O, R,
            O, R, R, R, R, R, R, R,
            O, R, O, O, O, O, O, R,
        ],

        # Frame 5: Padlock turns red to indicate locked
        [
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
            R, R, R, R, R, R, R, R,
        ],
    ]

    # Play animation
    for frame in frames:
        sense.set_pixels(frame)
        time.sleep(0.3)
