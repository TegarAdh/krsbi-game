import pygame
import random
import math
import sys

# CONFIG
WIDTH = 1000
HEIGHT = 700
FPS = 60

FIELD_W = 900
FIELD_H = 600
OFFSET_X = 50
OFFSET_Y = 50

START = (100, 550)
GOAL = (820, 120)

STEP_SIZE = 22
MAX_ITER = 3000
GOAL_RADIUS = 30

ROBOT_SPEED = 2

# obstacle = x,y,r
OBSTACLES = [
    (350, 250, 45),
    (500, 420, 45),
    (650, 250, 45),
    (420, 150, 40),
]

# COLORS
WHITE = (255,255,255)
BLACK = (0,0,0)
GREEN = (0,180,0)
BLUE = (0,120,255)
RED = (220,50,50)
GRAY = (120,120,120)
YELLOW = (255,220,0)
CYAN = (0,255,255)

# INIT
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("KRSBI Motion Planning - RRT Simulation")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20)


# NODE CLASS
class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.parent = None


nodes = []
path = []
goal_node = None
robot_pos = list(START)
path_index = 0
planning_done = False


# FUNCTIONS
def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def random_point():
    return (
        random.randint(OFFSET_X, OFFSET_X + FIELD_W),
        random.randint(OFFSET_Y, OFFSET_Y + FIELD_H)
    )


def nearest_node(p):
    return min(nodes, key=lambda n: dist((n.x,n.y), p))


def steer(from_node, to_point):
    angle = math.atan2(to_point[1]-from_node.y, to_point[0]-from_node.x)
    new_x = from_node.x + STEP_SIZE * math.cos(angle)
    new_y = from_node.y + STEP_SIZE * math.sin(angle)
    new = Node(new_x, new_y)
    new.parent = from_node
    return new


def collision(node):
    # obstacle
    for ox, oy, r in OBSTACLES:
        if dist((node.x,node.y),(ox,oy)) < r + 8:
            return True

    # wall
    if node.x < OFFSET_X or node.x > OFFSET_X+FIELD_W:
        return True
    if node.y < OFFSET_Y or node.y > OFFSET_Y+FIELD_H:
        return True

    return False


def build_rrt():
    global goal_node, planning_done

    start_node = Node(*START)
    nodes.append(start_node)

    for _ in range(MAX_ITER):
        rp = random_point()
        near = nearest_node(rp)
        new = steer(near, rp)

        if not collision(new):
            nodes.append(new)

            if dist((new.x,new.y), GOAL) < GOAL_RADIUS:
                goal_node = new
                planning_done = True
                return


def extract_path():
    global path
    cur = goal_node
    rev = []

    while cur is not None:
        rev.append((cur.x, cur.y))
        cur = cur.parent

    path = rev[::-1]


def move_robot():
    global path_index

    if path_index >= len(path):
        return

    target = path[path_index]

    dx = target[0] - robot_pos[0]
    dy = target[1] - robot_pos[1]
    d = math.hypot(dx, dy)

    if d < 4:
        path_index += 1
        return

    robot_pos[0] += ROBOT_SPEED * dx / d
    robot_pos[1] += ROBOT_SPEED * dy / d


def draw_field():
    pygame.draw.rect(screen, WHITE, (OFFSET_X, OFFSET_Y, FIELD_W, FIELD_H), 3)

    # center line
    pygame.draw.line(screen, WHITE,
                     (OFFSET_X + FIELD_W//2, OFFSET_Y),
                     (OFFSET_X + FIELD_W//2, OFFSET_Y + FIELD_H), 2)


def draw_obstacles():
    for ox, oy, r in OBSTACLES:
        pygame.draw.circle(screen, RED, (int(ox),int(oy)), r)
        txt = font.render("LAWAN", True, WHITE)
        screen.blit(txt, (ox-28, oy-10))


def draw_tree():
    for n in nodes:
        if n.parent:
            pygame.draw.line(screen, GREEN,
                             (int(n.x),int(n.y)),
                             (int(n.parent.x),int(n.parent.y)), 1)


def draw_path():
    if len(path) > 1:
        for i in range(len(path)-1):
            pygame.draw.line(screen, YELLOW,
                             path[i], path[i+1], 4)


def draw_robot():
    pygame.draw.circle(screen, BLUE,
                       (int(robot_pos[0]), int(robot_pos[1])), 15)
    txt = font.render("ROBOT", True, WHITE)
    screen.blit(txt, (robot_pos[0]-28, robot_pos[1]-35))


def draw_goal():
    pygame.draw.circle(screen, CYAN, GOAL, 18)
    txt = font.render("BALL", True, BLACK)
    screen.blit(txt, (GOAL[0]-20, GOAL[1]-35))


# START PLANNING
build_rrt()

if planning_done:
    extract_path()

# MAIN LOOP
while True:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    screen.fill((20, 110, 20))

    draw_field()
    draw_obstacles()
    draw_tree()
    draw_goal()
    draw_path()

    if planning_done:
        move_robot()

    draw_robot()

    title = font.render("KRSBI Soccer Robot - RRT Motion Planning", True, WHITE)
    screen.blit(title, (20, 15))

    pygame.display.flip()