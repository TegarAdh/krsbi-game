import pygame
import math
import random
import sys

#  KONFIGURASI LAYAR & LAPANGAN

WIDTH, HEIGHT = 1100, 780
FPS = 60

FIELD_W, FIELD_H = 960, 720
OFFSET_X, OFFSET_Y = 70, 30

COLS, ROWS = 24, 18
CELL_W = FIELD_W // COLS
CELL_H = FIELD_H // ROWS

#  PARAMETER ROBOT & BOLA

ROBOT_SPEED = 3.2
BALL_SPEED  = 10

# --- Artificial Potential Field ---
ATTRACTIVE_GAIN  = 1.0
REPULSIVE_GAIN   = 25_000
REPULSIVE_RANGE  = CELL_W * 2.2   
SAFE_RADIUS      = CELL_W * 1.6   
ESCAPE_BLEND     = 0.72           

#  WARNA

WHITE  = (255, 255, 255)
BLUE   = (  0, 120, 255)
RED    = (220,  50,  50)
YELLOW = (255, 220,   0)
CYAN   = (  0, 255, 255)
ORANGE = (255, 165,   0)
GREEN_DARK  = ( 20, 110,  20)
GREEN_LINE  = ( 40, 140,  40)
TRACE_COLOR = (100, 100, 255)

#  POSISI GRID TETAP

ROBOT_START  = [6, 16]
BALL_START   = [0,  8]
GOAL_GRID    = [23,  8]
PENALTY_GRID = [19,  8]
START_GRID   = [ 5, 15]   # kotak oranye (3×3)

ENEMY_SPAWN  = [[8, 7], [10, 10], [16, 9]]
ENEMY_MOVE_DELAY = 18   # frame antar langkah musuh

#  INISIALISASI PYGAME

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Artificial Potential Field – Soccer Robot")
clock = pygame.time.Clock()
font  = pygame.font.SysFont("arial", 22)

#  STATE GLOBAL

robot_grid = [0, 0]
ball_grid  = [0, 0]
robot_pos  = [0.0, 0.0]
ball_pos   = [0.0, 0.0]

mode         = "CHASE_BALL"
ball_kicked  = False
ball_vel     = [0.0, 0.0]
goal_scored  = False
goal_timer   = 0
trace        = []
enemies      = []
enemy_timer  = 0

#  UTILITAS KOORDINAT

def grid_to_pixel(g: list) -> list:
    """Ubah koordinat grid → piksel (tengah sel)."""
    return [
        OFFSET_X + g[0] * CELL_W + CELL_W // 2,
        OFFSET_Y + g[1] * CELL_H + CELL_H // 2,
    ]


def pixel_to_grid(p: list) -> list:
    """Ubah koordinat piksel → grid (dijepit ke batas lapangan)."""
    x = int((p[0] - OFFSET_X) / CELL_W)
    y = int((p[1] - OFFSET_Y) / CELL_H)
    return [max(0, min(COLS - 1, x)), max(0, min(ROWS - 1, y))]


def dist(a: list, b: list) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def normalize(x: float, y: float) -> tuple:
    mag = math.hypot(x, y)
    if mag == 0:
        return 0.0, 0.0
    return x / mag, y / mag

#  RESET PERMAINAN

def reset_game():
    global robot_grid, ball_grid, robot_pos, ball_pos
    global mode, ball_kicked, ball_vel
    global goal_scored, goal_timer, trace, enemies, enemy_timer

    robot_grid[:] = ROBOT_START[:]
    ball_grid[:]  = BALL_START[:]

    robot_pos[:] = grid_to_pixel(robot_grid)
    ball_pos[:]  = grid_to_pixel(ball_grid)

    mode        = "CHASE_BALL"
    ball_kicked = False
    ball_vel    = [0.0, 0.0]

    goal_scored = False
    goal_timer  = 0
    enemy_timer = 0

    trace   = []
    enemies = [e[:] for e in ENEMY_SPAWN]

#  TARGET ROBOT

def get_target() -> list:
    """Kembalikan posisi piksel target berdasarkan mode saat ini."""
    if mode == "CHASE_BALL":
        return ball_pos
    if mode == "GO_PENALTY":
        return grid_to_pixel(PENALTY_GRID)
    return robot_pos  # SHOOT – robot diam

#  DETEKSI BAHAYA

def nearest_enemy(pos: list) -> tuple:
    """Kembalikan (posisi_piksel, jarak) musuh terdekat."""
    best_pos, best_dist = None, float("inf")
    for e in enemies:
        ep = grid_to_pixel(e)
        d  = dist(pos, ep)
        if d < best_dist:
            best_dist, best_pos = d, ep
    return best_pos, best_dist


def in_danger(pos: list) -> bool:
    _, d = nearest_enemy(pos)
    return d < SAFE_RADIUS

#  ARTIFICIAL POTENTIAL FIELD

def normal_vector() -> tuple:
    """Hitung vektor gerak normal (atraktif + repulsif)."""
    target = get_target()

    # Gaya atraktif ke target
    fx = (target[0] - robot_pos[0]) * ATTRACTIVE_GAIN
    fy = (target[1] - robot_pos[1]) * ATTRACTIVE_GAIN

    # Gaya repulsif dari setiap musuh
    for e in enemies:
        ep = grid_to_pixel(e)
        d  = dist(robot_pos, ep)
        if 1 < d < REPULSIVE_RANGE:
            rep = REPULSIVE_GAIN / (d * d)
            fx += rep * (robot_pos[0] - ep[0]) / d
            fy += rep * (robot_pos[1] - ep[1]) / d

    return normalize(fx, fy)


def smooth_escape_vector() -> tuple:
    """Vektor kabur halus: campuran arah menjauh musuh + arah ke target."""
    target = get_target()

    # Arah ke target
    tx, ty = normalize(target[0] - robot_pos[0], target[1] - robot_pos[1])

    # Arah menjauh musuh terdekat
    enemy, _ = nearest_enemy(robot_pos)
    ex, ey   = normalize(robot_pos[0] - enemy[0], robot_pos[1] - enemy[1])

    # Blend linier
    bx = ESCAPE_BLEND * ex + (1 - ESCAPE_BLEND) * tx
    by = ESCAPE_BLEND * ey + (1 - ESCAPE_BLEND) * ty

    return normalize(bx, by)

#  UPDATE ROBOT

def move_robot():
    global mode, ball_kicked, ball_vel

    # Pilih vektor gerak
    if in_danger(robot_pos):
        vx, vy = smooth_escape_vector()
    else:
        vx, vy = normal_vector()

    # Pindahkan & jepit ke dalam lapangan
    robot_pos[0] = max(OFFSET_X + 10, min(OFFSET_X + FIELD_W - 10,
                       robot_pos[0] + ROBOT_SPEED * vx))
    robot_pos[1] = max(OFFSET_Y + 10, min(OFFSET_Y + FIELD_H - 10,
                       robot_pos[1] + ROBOT_SPEED * vy))

    robot_grid[:] = pixel_to_grid(robot_pos)

    # Transisi state
    if mode == "CHASE_BALL" and dist(robot_pos, ball_pos) < 18:
        mode = "GO_PENALTY"

    elif mode == "GO_PENALTY":
        pen = grid_to_pixel(PENALTY_GRID)
        if dist(robot_pos, pen) < 18:
            mode = "SHOOT"
            gp   = grid_to_pixel(GOAL_GRID)
            dx, dy  = gp[0] - ball_pos[0], gp[1] - ball_pos[1]
            dd       = math.hypot(dx, dy)
            ball_vel = [BALL_SPEED * dx / dd, BALL_SPEED * dy / dd]
            ball_kicked = True

#  UPDATE BOLA

def update_ball():
    global goal_scored

    # Bola mengikuti robot sampai ditendang
    if mode == "GO_PENALTY":
        ball_pos[:] = robot_pos[:]

    if ball_kicked:
        ball_pos[0] += ball_vel[0]
        ball_pos[1] += ball_vel[1]

    if ball_pos[0] > OFFSET_X + FIELD_W:
        goal_scored = True

#  UPDATE MUSUH (gerak acak)

def move_enemies():
    global enemy_timer

    enemy_timer += 1
    if enemy_timer < ENEMY_MOVE_DELAY:
        return
    enemy_timer = 0

    MOVES = [(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]
    for e in enemies:
        dx, dy = random.choice(MOVES)
        nx, ny = e[0] + dx, e[1] + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS:
            e[0], e[1] = nx, ny

#  GAMBAR

def draw_field():
    # Batas lapangan
    pygame.draw.rect(screen, WHITE, (OFFSET_X, OFFSET_Y, FIELD_W, FIELD_H), 3)

    # Garis vertikal + nomor kolom
    for i in range(COLS):
        x = OFFSET_X + i * CELL_W
        pygame.draw.line(screen, GREEN_LINE, (x, OFFSET_Y), (x, OFFSET_Y + FIELD_H))
        lbl = font.render(str(i), True, WHITE)
        screen.blit(lbl, (x + CELL_W // 2 - 8, OFFSET_Y - 25))

    # Garis horizontal + nomor baris
    for j in range(ROWS):
        y = OFFSET_Y + j * CELL_H
        pygame.draw.line(screen, GREEN_LINE, (OFFSET_X, y), (OFFSET_X + FIELD_W, y))
        lbl = font.render(str(j), True, WHITE)
        screen.blit(lbl, (OFFSET_X - 28, y + CELL_H // 2 - 10))

    # Garis batas kanan & bawah
    pygame.draw.line(screen, GREEN_LINE,
        (OFFSET_X + FIELD_W, OFFSET_Y), (OFFSET_X + FIELD_W, OFFSET_Y + FIELD_H))
    pygame.draw.line(screen, GREEN_LINE,
        (OFFSET_X, OFFSET_Y + FIELD_H), (OFFSET_X + FIELD_W, OFFSET_Y + FIELD_H))

    # Kotak penalti (kolom 18–24, baris 5–13)
    px = OFFSET_X + 18 * CELL_W
    py = OFFSET_Y +  5 * CELL_H
    pygame.draw.rect(screen, WHITE, (px, py, 6 * CELL_W, 8 * CELL_H), 2)


def draw_goal():
    pygame.draw.rect(screen, CYAN,
        (OFFSET_X + FIELD_W - 10, HEIGHT // 2 - 70, 10, 140))


def draw_start_zone():
    """Gambar kotak oranye 3×3 di posisi START_GRID."""
    sx = OFFSET_X + START_GRID[0] * CELL_W
    sy = OFFSET_Y + START_GRID[1] * CELL_H
    pygame.draw.rect(screen, ORANGE, (sx, sy, 3 * CELL_W, 3 * CELL_H), 3)


def draw_trace():
    if len(trace) > 1:
        pygame.draw.lines(screen, TRACE_COLOR, False, trace, 2)


def draw_enemies():
    for e in enemies:
        p = grid_to_pixel(e)
        px, py = int(p[0]), int(p[1])
        pygame.draw.circle(screen, RED, (px, py), 16)
        pygame.draw.circle(screen, (255, 120, 120), (px, py), int(SAFE_RADIUS), 1)


def draw_ball():
    pygame.draw.circle(screen, YELLOW, (int(ball_pos[0]), int(ball_pos[1])), 12)


def draw_robot():
    pygame.draw.circle(screen, BLUE, (int(robot_pos[0]), int(robot_pos[1])), 16)


def draw_hud():
    screen.blit(font.render("MODE : " + mode, True, WHITE), (20, 10))

    if in_danger(robot_pos):
        screen.blit(font.render("SMOOTH ESCAPE", True, YELLOW), (230, 10))

    if goal_scored:
        screen.blit(font.render("GOAL!  Tekan SPACE untuk ulang…", True, YELLOW), (450, 10))

#  MAIN LOOP

reset_game()

while True:
    clock.tick(FPS)

    # --- Event ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and goal_scored:
                reset_game()

    # --- Update ---
    if not goal_scored:
        move_enemies()
        move_robot()
        update_ball()
        trace.append((robot_pos[0], robot_pos[1]))

    # --- Render ---
    screen.fill(GREEN_DARK)

    draw_field()
    draw_goal()
    draw_start_zone()
    draw_trace()
    draw_enemies()
    draw_ball()
    draw_robot()
    draw_hud()

    pygame.display.flip()