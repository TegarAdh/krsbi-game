import pygame
import math
import sys

# KONFIGURASI
WIDTH, HEIGHT = 1100, 780
FPS = 60

FIELD_W, FIELD_H = 960, 720
OFFSET_X, OFFSET_Y = 70, 30

COLS, ROWS = 24, 18
CELL_W = FIELD_W // COLS
CELL_H = FIELD_H // ROWS

# PARAMETER
BLUE_SPEED = 3.4
PURPLE_SPEED = 4.6
BALL_SPEED = 11

STEAL_RADIUS = 28
SHOOT_RADIUS = 95
STEAL_COOLDOWN_MAX = 20

# WARNA
WHITE = (255, 255, 255)
GREEN_DARK = (20, 110, 20)
GREEN_LINE = (40, 140, 40)

BLUE = (0, 120, 255)
PURPLE = (180, 0, 255)
YELLOW = (255, 220, 0)

CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)

# INIT
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Blue vs Purple Soccer")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 22)

# GLOBAL
blue_pos = [0.0, 0.0]
purple_pos = [0.0, 0.0]
ball_pos = [0.0, 0.0]
ball_vel = [0.0, 0.0]

ball_owner = "NONE"   # NONE / BLUE / PURPLE
steal_cooldown = 0

goal_pause = False
winner_text = ""

blue_score = 0
purple_score = 0

# UTILITAS
def grid_to_pixel(g):
    return [
        OFFSET_X + g[0] * CELL_W + CELL_W // 2,
        OFFSET_Y + g[1] * CELL_H + CELL_H // 2
    ]

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def normalize(x, y):
    d = math.hypot(x, y)
    if d == 0:
        return 0, 0
    return x / d, y / d

def clamp_inside(obj):
    obj[0] = max(OFFSET_X + 15, min(OFFSET_X + FIELD_W - 15, obj[0]))
    obj[1] = max(OFFSET_Y + 15, min(OFFSET_Y + FIELD_H - 15, obj[1]))

# RESET
def reset_round():
    global ball_owner, steal_cooldown
    global goal_pause, winner_text

    blue_pos[:] = grid_to_pixel([5, 8])
    purple_pos[:] = grid_to_pixel([18, 8])
    ball_pos[:] = grid_to_pixel([12, 8])

    ball_vel[0] = 0
    ball_vel[1] = 0

    ball_owner = "NONE"
    steal_cooldown = 0

    goal_pause = False
    winner_text = ""

# SHOOT
def shoot_to_left_goal():
    global ball_owner

    target = [OFFSET_X - 30, HEIGHT // 2]
    dx = target[0] - ball_pos[0]
    dy = target[1] - ball_pos[1]

    vx, vy = normalize(dx, dy)

    ball_vel[0] = vx * BALL_SPEED
    ball_vel[1] = vy * BALL_SPEED

    ball_owner = "NONE"

def shoot_to_right_goal():
    global ball_owner

    target = [OFFSET_X + FIELD_W + 30, HEIGHT // 2]
    dx = target[0] - ball_pos[0]
    dy = target[1] - ball_pos[1]

    vx, vy = normalize(dx, dy)

    ball_vel[0] = vx * BALL_SPEED
    ball_vel[1] = vy * BALL_SPEED

    ball_owner = "NONE"

# ROBOT UNGU (PLAYER)
def move_purple():
    global ball_owner, steal_cooldown

    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        purple_pos[0] -= PURPLE_SPEED
    if keys[pygame.K_RIGHT]:
        purple_pos[0] += PURPLE_SPEED
    if keys[pygame.K_UP]:
        purple_pos[1] -= PURPLE_SPEED
    if keys[pygame.K_DOWN]:
        purple_pos[1] += PURPLE_SPEED

    clamp_inside(purple_pos)

    # rebut bola
    if dist(purple_pos, ball_pos) < STEAL_RADIUS:
        if steal_cooldown == 0 or ball_owner != "PURPLE":
            ball_owner = "PURPLE"
            steal_cooldown = STEAL_COOLDOWN_MAX

    # shoot
    if keys[pygame.K_RETURN] and ball_owner == "PURPLE":
        shoot_to_left_goal()

# ROBOT BIRU (AI)
def move_blue():
    global ball_owner, steal_cooldown

    # rebut bola
    if dist(blue_pos, ball_pos) < STEAL_RADIUS:
        if steal_cooldown == 0 or ball_owner != "BLUE":
            ball_owner = "BLUE"
            steal_cooldown = STEAL_COOLDOWN_MAX

    # target
    if ball_owner == "BLUE":
        target = [OFFSET_X + FIELD_W - 20, HEIGHT // 2]

        # dekat gawang -> shoot
        if dist(blue_pos, target) < SHOOT_RADIUS:
            shoot_to_right_goal()
            return
    else:
        target = ball_pos

    # gerak ke target
    fx = target[0] - blue_pos[0]
    fy = target[1] - blue_pos[1]

    # hindari purple sedikit
    d = dist(blue_pos, purple_pos)
    if 1 < d < 90:
        rep = 6000 / (d * d)
        fx += rep * (blue_pos[0] - purple_pos[0]) / d
        fy += rep * (blue_pos[1] - purple_pos[1]) / d

    vx, vy = normalize(fx, fy)

    blue_pos[0] += vx * BLUE_SPEED
    blue_pos[1] += vy * BLUE_SPEED

    clamp_inside(blue_pos)

# UPDATE BOLA
def update_ball():
    global blue_score, purple_score
    global goal_pause, winner_text

    if ball_owner == "BLUE":
        ball_pos[:] = blue_pos[:]

    elif ball_owner == "PURPLE":
        ball_pos[:] = purple_pos[:]

    else:
        ball_pos[0] += ball_vel[0]
        ball_pos[1] += ball_vel[1]

    # goal kanan = BLUE cetak gol
    if ball_pos[0] > OFFSET_X + FIELD_W:
        blue_score += 1
        winner_text = "BLUE GOAL!"
        goal_pause = True

    # goal kiri = PURPLE cetak gol
    if ball_pos[0] < OFFSET_X:
        purple_score += 1
        winner_text = "PURPLE GOAL!"
        goal_pause = True

# DRAW
def draw_field():
    pygame.draw.rect(
        screen, WHITE,
        (OFFSET_X, OFFSET_Y, FIELD_W, FIELD_H), 3
    )

    for i in range(COLS):
        x = OFFSET_X + i * CELL_W
        pygame.draw.line(screen, GREEN_LINE,
                         (x, OFFSET_Y),
                         (x, OFFSET_Y + FIELD_H))

    for j in range(ROWS):
        y = OFFSET_Y + j * CELL_H
        pygame.draw.line(screen, GREEN_LINE,
                         (OFFSET_X, y),
                         (OFFSET_X + FIELD_W, y))

    # penalti kiri
    pygame.draw.rect(screen, WHITE,
                     (OFFSET_X,
                      OFFSET_Y + 5 * CELL_H,
                      6 * CELL_W,
                      8 * CELL_H), 2)

    # penalti kanan
    pygame.draw.rect(screen, WHITE,
                     (OFFSET_X + 18 * CELL_W,
                      OFFSET_Y + 5 * CELL_H,
                      6 * CELL_W,
                      8 * CELL_H), 2)

def draw_goals():
    pygame.draw.rect(screen, MAGENTA,
                     (OFFSET_X, HEIGHT // 2 - 70, 10, 140))

    pygame.draw.rect(screen, CYAN,
                     (OFFSET_X + FIELD_W - 10,
                      HEIGHT // 2 - 70, 10, 140))

def draw_players():
    pygame.draw.circle(screen, BLUE,
                       (int(blue_pos[0]), int(blue_pos[1])), 18)

    pygame.draw.circle(screen, PURPLE,
                       (int(purple_pos[0]), int(purple_pos[1])), 18)

def draw_ball():
    pygame.draw.circle(screen, YELLOW,
                       (int(ball_pos[0]), int(ball_pos[1])), 12)

def draw_hud():
    score = f"BLUE {blue_score} : {purple_score} PURPLE"
    screen.blit(font.render(score, True, YELLOW), (390, 10))

    owner = "BALL : " + ball_owner
    screen.blit(font.render(owner, True, WHITE), (20, 10))

    screen.blit(font.render(
        "Arrow = Move Purple | Enter = Shoot | SPACE = Reset Goal",
        True, WHITE), (20, 40))

    if goal_pause:
        screen.blit(font.render(
            winner_text + "   PRESS SPACE",
            True, YELLOW), (360, 70))

# MAIN LOOP
reset_round()

while True:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and goal_pause:
                reset_round()

    if not goal_pause:

        if steal_cooldown > 0:
            steal_cooldown -= 1

        move_purple()
        move_blue()
        update_ball()

    screen.fill(GREEN_DARK)

    draw_field()
    draw_goals()
    draw_players()
    draw_ball()
    draw_hud()

    pygame.display.flip()