import asyncio
from os import listdir
from os.path import join, isfile
import curses
import random
from itertools import cycle
from physics import update_speed
from curses_tools import get_frame_size, draw_frame, read_controls
from obstacles import Obstacle
from explosion import explode
from game_scenario import get_garbage_delay_tics, PHRASES


TIC_TIMEOUT = 0.001
STARS_AMOUNT = 100
BORDER_WIDTH = 2

row_speed = column_speed = 0

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
coroutines = []
obstacles = []
obstacles_in_last_collisions = []
year = 1957
GUN_YEAR = 2020


def load_spaceship_frames():
    """Load frames from files"""
    with open('animation_frames/rocket_frame_1.txt', 'r') as file:
        frame1 = file.read()
    with open('animation_frames/rocket_frame_2.txt', 'r') as file:
        frame2 = file.read()
    return (frame1, frame2)


async def draw_spaceship(canvas, spaceship_row, spaceship_column,
        canvas_height, canvas_width, spaceship_frames):
    """Render frames of spaceship"""
    global row_speed, column_speed, coroutines, year
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
            row_speed, column_speed = update_speed(
                row_speed, column_speed,
                rows_direction, columns_direction,
                fading=0.9,
                )
            spaceship_row += row_speed
            spaceship_column += column_speed

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
            if space_pressed and year >= GUN_YEAR:
                coroutines.append(
                    fire(canvas, spaceship_row, spaceship_column, rows_speed=-0.01)
                    )
            for obstacle in obstacles:
                if obstacle.has_collision(spaceship_row, spaceship_column):
                    coroutines.append(show_gameover(canvas))
                    return


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
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed
        for obstacle in obstacles:
            if obstacle.has_collision(row, column, row, column):
                obstacles_in_last_collisions.append(obstacle)
                coroutines.append(explode(canvas, row, column))
                return


async def sleep(tics=1):
    for __ in range(0, tics):
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol='*'):
    """Render star"""
    canvas.addstr(row, column, symbol, curses.A_DIM)

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        times = int(2//TIC_TIMEOUT)
        await sleep(tics=times)

        canvas.addstr(row, column, symbol)
        times = int(0.3//TIC_TIMEOUT)
        await sleep(tics=times)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        times = int(0.5//TIC_TIMEOUT)
        await sleep(tics=times)

        canvas.addstr(row, column, symbol)
        times = int(0.3//TIC_TIMEOUT)
        await sleep(tics=times)


async def fly_garbage(canvas, column, garbage_frame, speed=0.01):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    global obstacles
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0
    rows_size, column_size = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, column, rows_size, column_size)
    obstacles.append(obstacle)

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
        obstacle.row += speed
        if obstacle in obstacles_in_last_collisions:
            obstacles_in_last_collisions.remove(obstacle)
            obstacles.remove(obstacle)
            return


async def fill_orbit_with_garbage(canvas):
    rows, columns = canvas.getmaxyx()
    frames = []
    global coroutines, obstacles, year

    path = 'animation_frames/trash'
    files = [f for f in listdir(path) if isfile(join(path, f))]
    for file in files:
        with open(join(path, file), "r", encoding="utf-8") as garbage_file:
            frames.append(garbage_file.read())

    while True:
        tics = get_garbage_delay_tics(year)
        if not tics:
            await asyncio.sleep(0)
        else:
            column = random.randint(0, columns)
            frame = random.choice(frames)
            coroutines.append(fly_garbage(canvas, column, frame))
            await sleep(tics=tics*100)


async def proceed_scenario(canvas, speed=1.5):
    times = int(speed//TIC_TIMEOUT)
    global year

    while True:
        year_phrase = f'{year} {PHRASES.get(year) or ""}'
        draw_frame(canvas, 0, 0, str(year_phrase))
        await sleep(tics=times)
        draw_frame(canvas, 0, 0, str(year_phrase), negative=True)
        year += 1


async def show_gameover(canvas):
    with open('animation_frames/game_over_frame.txt', 'r') as file:
        game_over_frame = file.read()
    rows_number, columns_number = canvas.getmaxyx()
    game_over_frame_row, game_over_frame_column = get_frame_size(game_over_frame)
    start_row = (rows_number - game_over_frame_row) / 2
    start_column = (columns_number - game_over_frame_column) / 2
    while True:
        draw_frame(canvas, start_row, start_column, game_over_frame)
        await asyncio.sleep(0)


def draw(canvas):
    """Main function of game"""
    canvas.border()
    canvas.nodelay(True)
    curses.curs_set(False)
    canvas_height, canvas_width = canvas.getmaxyx()

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
    coroutines.append(fill_orbit_with_garbage(canvas))
    coroutines.append(proceed_scenario(canvas))

    while True:
        canvas.refresh()
        for coroutine in list(coroutines):
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
