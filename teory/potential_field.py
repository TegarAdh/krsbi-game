import matplotlib.pyplot as plt
import math
import random

# KONFIGURASI
X_MAX = 12
Y_MAX = 9

start = [1, 1]
goal = [10, 7]

robot = start[:]

# obstacle (x, y)
obstacles = [
    (5, 3),
    (7, 6),
    (6, 4)
]

# parameter (ambil konsep dari main.py)
STEP = 0.2
ATTRACTIVE_GAIN = 1.0
REPULSIVE_GAIN = 50
REPULSIVE_RANGE = 2.0
SAFE_RADIUS = 1.2
ESCAPE_BLEND = 0.7

path = [tuple(robot)]

# UTIL
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def normalize(x, y):
    mag = math.hypot(x, y)
    if mag == 0:
        return 0, 0
    return x / mag, y / mag

def nearest_obstacle(pos):
    best = None
    best_d = 999
    for o in obstacles:
        d = dist(pos, o)
        if d < best_d:
            best_d = d
            best = o
    return best, best_d

def in_danger(pos):
    _, d = nearest_obstacle(pos)
    return d < SAFE_RADIUS

# POTENTIAL FIELD
def normal_vector(pos):
    # attractive
    fx = (goal[0] - pos[0]) * ATTRACTIVE_GAIN
    fy = (goal[1] - pos[1]) * ATTRACTIVE_GAIN

    # repulsive
    for o in obstacles:
        d = dist(pos, o)
        if 0.1 < d < REPULSIVE_RANGE:
            rep = REPULSIVE_GAIN / (d * d)
            fx += rep * (pos[0] - o[0]) / d
            fy += rep * (pos[1] - o[1]) / d

    return normalize(fx, fy)

# SMOOTH ESCAPE
def smooth_escape(pos):
    # ke goal
    tx = goal[0] - pos[0]
    ty = goal[1] - pos[1]
    tx, ty = normalize(tx, ty)

    # menjauh obstacle terdekat
    obs, _ = nearest_obstacle(pos)
    ex = pos[0] - obs[0]
    ey = pos[1] - obs[1]
    ex, ey = normalize(ex, ey)

    # blending
    bx = ESCAPE_BLEND * ex + (1 - ESCAPE_BLEND) * tx
    by = ESCAPE_BLEND * ey + (1 - ESCAPE_BLEND) * ty

    return normalize(bx, by)

# SIMULASI GERAK
for i in range(1000):

    if in_danger(robot):
        vx, vy = smooth_escape(robot)
    else:
        vx, vy = normal_vector(robot)

    robot[0] += STEP * vx
    robot[1] += STEP * vy

    path.append((robot[0], robot[1]))

    if dist(robot, goal) < 0.3:
        print("Goal reached!")
        break

# VISUALISASI

# path
xs = [p[0] for p in path]
ys = [p[1] for p in path]
plt.plot(xs, ys, 'b-', linewidth=2, label="Path")

# obstacle
for o in obstacles:
    circle = plt.Circle(o, 0.5, color='red')
    plt.gca().add_patch(circle)

# start & goal
plt.plot(start[0], start[1], 'go', markersize=10, label="Start")
plt.plot(goal[0], goal[1], 'ro', markersize=10, label="Goal")

plt.xlim(0, X_MAX)
plt.ylim(0, Y_MAX)
plt.grid()
plt.title("Potential Field Path Planning")
plt.legend()
plt.show()