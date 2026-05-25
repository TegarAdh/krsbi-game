import pygame
import math
import random
import sys

pygame.init()

# CONFIG
WIDTH, HEIGHT = 1280, 800
FPS = 60

FIELD_X = 60
FIELD_Y = 40
FIELD_W = 1160
FIELD_H = 720

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Robot Soccer Full Game")

clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 22)

# COLOR
WHITE   = (255,255,255)
GREEN   = (20,120,20)
LINE    = (40,170,40)

BLUE    = (0,120,255)
PURPLE  = (180,0,255)
YELLOW  = (255,220,0)
RED     = (255,70,70)

CYAN    = (0,255,255)
MAGENTA = (255,0,255)

# PARAMETER
ROBOT_R = 18
BALL_R  = 10

AI_SPEED = 2.4
PLAYER_SPEED = 4.0
BALL_SPEED = 10

STEAL_RANGE = 30
STEAL_COOLDOWN = 12
SHOOT_RANGE = 180

REPULSE_RADIUS = 60
REPULSE_GAIN = 2.2

# GLOBAL
blue_score = 0
purple_score = 0

blue_team = []
purple_team = []

ball_x = 0
ball_y = 0
ball_vx = 0
ball_vy = 0

owner_team = None
owner_idx = None

steal_timer = 0

game_stop = False
status_text = ""

# UTIL
def dist(a,b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def normalize(dx,dy):
    d = math.hypot(dx,dy)
    if d == 0:
        return 0,0
    return dx/d, dy/d

def clamp(r):
    r["x"] = max(FIELD_X+20, min(FIELD_X+FIELD_W-20, r["x"]))
    r["y"] = max(FIELD_Y+20, min(FIELD_Y+FIELD_H-20, r["y"]))

def make_robot(x,y,color,name,team,manual=False):
    return {
        "x":x,
        "y":y,
        "color":color,
        "name":name,
        "team":team,
        "manual":manual
    }

# RESET
def reset_game():
    global blue_team, purple_team
    global ball_x, ball_y, ball_vx, ball_vy
    global owner_team, owner_idx
    global steal_timer
    global game_stop, status_text

    blue_team = [
        make_robot(220,220,BLUE,"B1","BLUE",True),
        make_robot(220,400,BLUE,"B2","BLUE"),
        make_robot(220,580,BLUE,"B3","BLUE")
    ]

    purple_team = [
        make_robot(1060,220,PURPLE,"P1","PURPLE"),
        make_robot(1060,400,PURPLE,"P2","PURPLE"),
        make_robot(1060,580,PURPLE,"P3","PURPLE")
    ]

    ball_x = WIDTH//2
    ball_y = HEIGHT//2
    ball_vx = 0
    ball_vy = 0

    owner_team = None
    owner_idx = None

    steal_timer = 0

    game_stop = False
    status_text = ""

# TEAM HELPER
def get_team(name):
    return blue_team if name == "BLUE" else purple_team

# POSSESSION
def set_owner(team, idx):
    global owner_team, owner_idx
    global ball_vx, ball_vy
    global steal_timer

    owner_team = team
    owner_idx = idx
    ball_vx = 0
    ball_vy = 0
    steal_timer = STEAL_COOLDOWN

def release_ball():
    global owner_team, owner_idx
    owner_team = None
    owner_idx = None

# BALL
def attach_ball(robot):
    global ball_x, ball_y
    ball_x = robot["x"]
    ball_y = robot["y"]

def kick_to(tx,ty):
    global ball_vx, ball_vy

    dx = tx - ball_x
    dy = ty - ball_y
    vx, vy = normalize(dx,dy)

    ball_vx = vx * BALL_SPEED
    ball_vy = vy * BALL_SPEED

    release_ball()

# BEST TEAMMATE
def best_teammate(team, idx):
    me = team[idx]

    best = None
    best_score = -99999

    for i,r in enumerate(team):
        if i == idx:
            continue

        d = dist((me["x"],me["y"]), (r["x"],r["y"]))

        if me["team"] == "BLUE":
            score = r["x"] - d * 0.5
        else:
            score = (WIDTH-r["x"]) - d * 0.5

        if score > best_score:
            best_score = score
            best = i

    return best

# POTENTIAL FIELD
def repulsive_force(robot, robots):
    fx = 0
    fy = 0

    for other in robots:
        if other is robot:
            continue

        dx = robot["x"] - other["x"]
        dy = robot["y"] - other["y"]

        d = math.hypot(dx,dy)

        if 0 < d < REPULSE_RADIUS:
            power = REPULSE_GAIN * (REPULSE_RADIUS - d) / REPULSE_RADIUS
            ux, uy = normalize(dx,dy)

            fx += ux * power
            fy += uy * power

    return fx, fy

# PLAYER CONTROL
def control_player():
    global steal_timer

    p = blue_team[0]

    keys = pygame.key.get_pressed()

    dx = 0
    dy = 0

    if keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_RIGHT]:
        dx += 1
    if keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_DOWN]:
        dy += 1

    vx, vy = normalize(dx,dy)

    fx, fy = repulsive_force(p, blue_team + purple_team)

    move_x = vx * PLAYER_SPEED + fx
    move_y = vy * PLAYER_SPEED + fy

    ux, uy = normalize(move_x, move_y)

    p["x"] += ux * PLAYER_SPEED
    p["y"] += uy * PLAYER_SPEED

    clamp(p)

    if steal_timer == 0:
        if dist((p["x"],p["y"]), (ball_x,ball_y)) < STEAL_RANGE:
            set_owner("BLUE",0)

# AI TEAM
def update_team(team, team_name, goal_x, skip_manual=False):
    global steal_timer

    robots = blue_team + purple_team

    for i,r in enumerate(team):

        if skip_manual and r["manual"]:
            continue

        if owner_team == team_name and owner_idx == i:

            if abs(r["x"] - goal_x) < SHOOT_RANGE:
                kick_to(goal_x, HEIGHT//2)
                return

            mate = best_teammate(team, i)
            if mate is not None and random.randint(0,100) < 2:
                kick_to(team[mate]["x"], team[mate]["y"])
                return

            if team_name == "BLUE":
                tx = r["x"] + 70
            else:
                tx = r["x"] - 70
            ty = r["y"]

        else:
            tx = ball_x
            ty = ball_y

        dx = tx - r["x"]
        dy = ty - r["y"]

        vx, vy = normalize(dx,dy)

        fx, fy = repulsive_force(r, robots)

        move_x = vx * AI_SPEED + fx
        move_y = vy * AI_SPEED + fy

        ux, uy = normalize(move_x, move_y)

        r["x"] += ux * AI_SPEED
        r["y"] += uy * AI_SPEED

        clamp(r)

        if steal_timer == 0:
            if dist((r["x"],r["y"]), (ball_x,ball_y)) < STEAL_RANGE:
                set_owner(team_name, i)

# THROW IN
def throw_in():
    global ball_x, ball_y
    global ball_vx, ball_vy
    global game_stop, status_text
    global owner_team, owner_idx

    ball_x = WIDTH // 2

    if ball_y < FIELD_Y:
        ball_y = FIELD_Y + 15
    else:
        ball_y = FIELD_Y + FIELD_H - 15

    ball_vx = random.choice([-4,4])
    ball_vy = random.choice([-2,2])

    owner_team = None
    owner_idx = None

    game_stop = True
    status_text = "BALL OUT - PRESS R"

# BALL UPDATE
def update_ball():
    global ball_x, ball_y
    global ball_vx, ball_vy
    global blue_score, purple_score
    global game_stop, status_text

    if owner_team is not None:
        holder = get_team(owner_team)[owner_idx]
        attach_ball(holder)
    else:
        ball_x += ball_vx
        ball_y += ball_vy

        ball_vx *= 0.99
        ball_vy *= 0.99

    # goal kiri
    if ball_x < FIELD_X:
        purple_score += 1
        game_stop = True
        status_text = "PURPLE GOAL! PRESS R"

    # goal kanan
    if ball_x > FIELD_X + FIELD_W:
        blue_score += 1
        game_stop = True
        status_text = "BLUE GOAL! PRESS R"

    # out atas bawah
    if ball_y < FIELD_Y or ball_y > FIELD_Y + FIELD_H:
        throw_in()

# DRAW
def draw_field():
    pygame.draw.rect(screen, WHITE,
        (FIELD_X,FIELD_Y,FIELD_W,FIELD_H),3)

    for x in range(FIELD_X, FIELD_X+FIELD_W, 60):
        pygame.draw.line(screen, LINE,
            (x,FIELD_Y),(x,FIELD_Y+FIELD_H))

    for y in range(FIELD_Y, FIELD_Y+FIELD_H, 60):
        pygame.draw.line(screen, LINE,
            (FIELD_X,y),(FIELD_X+FIELD_W,y))

    pygame.draw.circle(screen, WHITE,
        (WIDTH//2,HEIGHT//2),90,2)

    pygame.draw.rect(screen, MAGENTA,
        (FIELD_X-10, HEIGHT//2-80,10,160))

    pygame.draw.rect(screen, CYAN,
        (FIELD_X+FIELD_W, HEIGHT//2-80,10,160))

def draw_team(team):
    for idx,r in enumerate(team):

        pygame.draw.circle(screen, r["color"],
            (int(r["x"]),int(r["y"])), ROBOT_R)

        if r["manual"]:
            pygame.draw.circle(screen, RED,
                (int(r["x"]),int(r["y"])), ROBOT_R+4,2)

        if owner_team == r["team"] and owner_idx == idx:
            pygame.draw.circle(screen, YELLOW,
                (int(r["x"]),int(r["y"])), ROBOT_R+7,2)

        txt = font.render(r["name"], True, WHITE)
        screen.blit(txt,(r["x"]-14,r["y"]-34))

def draw_ball():
    pygame.draw.circle(screen, YELLOW,
        (int(ball_x),int(ball_y)), BALL_R)

def draw_hud():
    txt = f"BLUE {blue_score} : {purple_score} PURPLE"
    screen.blit(font.render(txt,True,YELLOW),(500,10))

    screen.blit(font.render(
        "Arrow=Move B1 | SPACE=Shoot | R=Reset",
        True,WHITE),(430,40))

    if status_text != "":
        screen.blit(font.render(
            status_text, True, RED),(470,70))

# MAIN LOOP
reset_game()

while True:
    clock.tick(FPS)

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_r:
                reset_game()

            if event.key == pygame.K_SPACE:
                if owner_team == "BLUE" and owner_idx == 0 and not game_stop:
                    kick_to(FIELD_X + FIELD_W + 50, HEIGHT//2)

    if not game_stop:

        if steal_timer > 0:
            steal_timer -= 1

        control_player()
        update_team(blue_team, "BLUE", FIELD_X+FIELD_W+40, True)
        update_team(purple_team, "PURPLE", FIELD_X-40)

        update_ball()

    screen.fill(GREEN)

    draw_field()
    draw_team(blue_team)
    draw_team(purple_team)
    draw_ball()
    draw_hud()

    pygame.display.flip()