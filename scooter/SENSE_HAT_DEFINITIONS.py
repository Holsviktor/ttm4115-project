
# Global Color Definitions
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
