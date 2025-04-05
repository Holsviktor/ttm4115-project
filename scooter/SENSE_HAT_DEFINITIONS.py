
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


def _handle_joystick_input(self):
    while not self.stop_joystick_thread:
        for event in self.sense.stick.get_events():
            if event.action == 'pressed':
                if event.direction == 'up':
                    self._display_arrow('up')
                elif event.direction == 'down':
                    self._display_arrow('down')
                elif event.direction == 'left':
                    self._display_arrow('left')
                elif event.direction == 'right':
                    self._display_arrow('right')
                elif event.direction == 'middle':
                    self._display_arrow('stop')

        time.sleep(0.1)

def _display_arrow(self, direction):
    arrows = {
        'up': [
            [0,0,0,0,1,0,0,0],
            [0,0,0,1,1,1,0,0],
            [0,0,1,1,1,1,1,0],
            [0,1,0,0,1,0,0,1],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
        ],
        'down': [
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0,0],
            [0,1,0,0,1,0,0,1],
            [0,0,1,1,1,1,1,0],
            [0,0,0,1,1,1,0,0],
            [0,0,0,0,1,0,0,0],
        ],
        'right': [
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,1,0,0],
            [0,0,0,0,1,1,0,0],
            [0,0,1,1,1,1,1,0],
            [0,0,0,0,1,1,0,0],
            [0,0,0,0,0,1,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0],
        ],
        'left': [
            [0,0,0,0,0,0,0,0],
            [0,0,1,0,0,0,0,0],
            [0,0,1,1,0,0,0,0],
            [0,1,1,1,1,1,1,0],
            [0,0,1,1,0,0,0,0],
            [0,0,1,0,0,0,0,0],
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
        flat_pixels = [self._get_color(pixel) for row in arrow for pixel in row]
        self.sense.set_pixels(flat_pixels)


def _get_color(self, pixel_value):
    return G if pixel_value == 1 else O


def stop(self):
    self.stop_joystick_thread = True
    if self.joystick_thread:
        self.joystick_thread.join()
    self.sense.clear()
