import asyncio
import curses
import random
from itertools import cycle

TIC_TIMEOUT = 0.01
STARS_AMOUNT = 100
BORDER_WIDTH = 2

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258


def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -1

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = 1

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = 1

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -1

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True
    return rows_direction, columns_direction, space_pressed


def load_spaceship_frames():
    """Load frames from files"""
    with open('animation_frames/rocket_frame_1.txt', 'r') as file:
        frame1 = file.read()
    with open('animation_frames/rocket_frame_2.txt', 'r') as file:
        frame2 = file.read()
    return (frame1, frame2)


def get_frame_size(text):
    """Calculate size of multiline text fragment.
    Returns pair (rows number, colums number)"""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


async def draw_spaceship(canvas, spaceship_row, spaceship_column,
        canvas_height, canvas_width, spaceship_frames):
    """Render frames of spaceship"""
    spaceship_frames = load_spaceship_frames()
    spaceship_frame_row, spaceship_frame_column = get_frame_size(
        spaceship_frames[0]
    )
    times = int(2//TIC_TIMEOUT)

    for frame in cycle(spaceship_frames):
        for __ in range(0, times):
            draw_frame(
                canvas, spaceship_row, spaceship_column,
                frame, negative=False
            )
            await asyncio.sleep(0)
            draw_frame(
                canvas, spaceship_row, spaceship_column,
                frame, negative=True
            )
            rows_direction, columns_direction, space_pressed = \
                read_controls(canvas)
            spaceship_row = min(
                canvas_height-spaceship_frame_row-BORDER_WIDTH,
                spaceship_row + rows_direction
            )
            spaceship_row = max(
                BORDER_WIDTH//2,
                spaceship_row + rows_direction
            )
            spaceship_column = min(
                canvas_width-spaceship_frame_column-BORDER_WIDTH,
                spaceship_column + columns_direction
            )
            spaceship_column = max(
                BORDER_WIDTH//2,
                spaceship_column + columns_direction
            )


async def fire(canvas, start_row, start_column,
        rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        # times = int(1//TIC_TIMEOUT)
        # for __ in range(0, times):
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol='*'):
    """Render star"""
    canvas.addstr(row, column, symbol, curses.A_DIM)
    delay = random.randint(0, int(2//TIC_TIMEOUT))
    for __ in range(0, delay):
        await asyncio.sleep(0)

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        times = int(2//TIC_TIMEOUT)
        for __ in range(0, times):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        times = int(0.3//TIC_TIMEOUT)
        for __ in range(0, times):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        times = int(0.5//TIC_TIMEOUT)
        for __ in range(0, times):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        times = int(0.3//TIC_TIMEOUT)
        for __ in range(0, times):
            await asyncio.sleep(0)


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas.
    Erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right
            # corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def draw(canvas):
    """Main function of game"""
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    canvas_height, canvas_width = canvas.getmaxyx()
    coroutines = []

    spaceship_frames = load_spaceship_frames()

    for _ in range(0, STARS_AMOUNT):
        row = random.randint(BORDER_WIDTH, canvas_height-BORDER_WIDTH)
        column = random.randint(BORDER_WIDTH, canvas_width-BORDER_WIDTH)
        symbol = random.choice('+*.:')
        coroutines.append(blink(canvas, row, column, symbol))

    spaceship_row = int(canvas_height//2-1)
    spaceship_column = int(canvas_width//2-1)
    coroutines.append(draw_spaceship(
        canvas, spaceship_row, spaceship_column,
        canvas_height, canvas_width, spaceship_frames,
    ))
    coroutines.append(
        fire(canvas, spaceship_row, spaceship_column, rows_speed=-0.01)
    )

    while True:
        canvas.refresh()
        for coroutine in coroutines:
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
