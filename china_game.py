import pygame, sys, math, random, os

pygame.init()

DIR = os.path.dirname(os.path.abspath(__file__))

def load_img(filename, size):
    path = os.path.join(DIR, filename)
    return pygame.transform.smoothscale(pygame.image.load(path), (size, size))

info = pygame.display.Info()
W, H = info.current_w, info.current_h
screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
pygame.display.set_caption("TD Game")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 16)
big_font = pygame.font.SysFont("consolas", 30, bold=True)
sm_font = pygame.font.SysFont("consolas", 14)

GOLD  = (255, 215, 0)
RED   = (220, 50, 50)
GREEN = (50, 200, 80)
WHITE = (255, 255, 255)
GRAY  = (120, 120, 120)
BG    = (40, 45, 35)

BAR_H = 180
MAPH  = H - BAR_H
CELL  = 64
GRID_COLS = W // CELL
GRID_ROWS = MAPH // CELL

ENEMY_IMGS = {
    "barbarian": load_img("barbarians.jpg", 48),
    "raider":    load_img("secondhardest.jpeg", 52),
    "shield":    load_img("thirdhardest.jpg", 56),
    "siege":     load_img("fourthhardest.jpg", 60),
    "general":   load_img("hardestenemy.jpg", 68),
}

TOWER_IMGS = {
    "bowman":   load_img("bowman.jpg", 64),
    "crossbow": load_img("crossbowman.jpg", 56),
    "guard":    load_img("gaurd.jpg", 52),
}

TOWER_SHOP_IMGS = {
    "bowman":   load_img("bowman.jpg", 52),
    "crossbow": load_img("crossbowman.jpg", 52),
    "guard":    load_img("gaurd.jpg", 52),
}

CASTLE_IMG = load_img("castle.jpg", 150)

WAYPOINTS = [
    (0.0, 0.50), (0.30, 0.50), (0.30, 0.15),
    (0.65, 0.15), (0.65, 0.75), (0.95, 0.75),
]

path_grid = []
for px, py in WAYPOINTS:
    c = max(0, min(GRID_COLS - 1, round(px * (GRID_COLS - 1))))
    r = max(0, min(GRID_ROWS - 1, round(py * (GRID_ROWS - 1))))
    path_grid.append((c, r))

path_cells = set()
for i in range(len(path_grid) - 1):
    c1, r1 = path_grid[i]
    c2, r2 = path_grid[i + 1]
    if r1 == r2:
        for c in range(min(c1, c2), max(c1, c2) + 1):
            path_cells.add((c, r1))
    else:
        for r in range(min(r1, r2), max(r1, r2) + 1):
            path_cells.add((c1, r))

PATH = []
for c, r in path_grid:
    PATH.append((c * CELL + CELL // 2, r * CELL + CELL // 2))
PATH[0] = (0, PATH[0][1])
PATH[-1] = (W, PATH[-1][1])

grid_occupied = [[False] * GRID_ROWS for _ in range(GRID_COLS)]

def snap_to_grid(px, py):
    col = max(0, min(GRID_COLS - 1, px // CELL))
    row = max(0, min(GRID_ROWS - 1, py // CELL))
    return col * CELL + CELL // 2, row * CELL + CELL // 2, col, row

def can_place(col, row):
    if col < 0 or col >= GRID_COLS or row < 0 or row >= GRID_ROWS:
        return False
    if grid_occupied[col][row]:
        return False
    if (col, row) in path_cells:
        return False
    return True

ENEMIES = {
    "barbarian": {"hp": 40,   "speed": 2.5, "reward": 10,   "leak": 1},
    "raider":    {"hp": 70,   "speed": 3.5, "reward": 15,  "leak": 2},
    "shield":    {"hp": 180,  "speed": 2.5, "reward": 20,  "leak": 3},
    "siege":     {"hp": 400,  "speed": 1.8, "reward": 35,  "leak": 5},
    "general":   {"hp": 900,  "speed": 2.2, "reward": 120, "leak": 8},
}

class Enemy:
    def __init__(self, kind, hp_scale=1.0):
        data = ENEMIES[kind]
        self.kind = kind
        self.max_hp = int(data["hp"] * hp_scale)
        self.hp = self.max_hp
        self.speed = data["speed"]
        self.reward = data["reward"]
        self.leak_dmg = data["leak"]
        self.seg = 0
        self.t = 0.0
        self.x = float(PATH[0][0])
        self.y = float(PATH[0][1])
        self.alive = True
        self.leaked = False

    def update(self):
        if not self.alive:
            return
        a = PATH[self.seg]
        b = PATH[self.seg + 1]
        length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        self.t += self.speed / length
        while self.t >= 1:
            self.t -= 1
            self.seg += 1
            if self.seg >= len(PATH) - 1:
                self.alive = False
                self.leaked = True
                return
        a = PATH[self.seg]
        b = PATH[self.seg + 1]
        self.x = a[0] + (b[0] - a[0]) * self.t
        self.y = a[1] + (b[1] - a[1]) * self.t

    def progress(self):
        return self.seg + self.t

    def draw(self):
        ix = int(self.x)
        iy = int(self.y)
        img = ENEMY_IMGS[self.kind]
        screen.blit(img, (ix - img.get_width() // 2, iy - img.get_height() // 2))
        bw = max(img.get_width(), 20)
        bx = ix - bw // 2
        by = iy - img.get_height() // 2 - 6
        pygame.draw.rect(screen, RED, (bx, by, bw, 4))
        pygame.draw.rect(screen, GREEN, (bx, by, int(bw * self.hp / self.max_hp), 4))

TOWERS = {
    "bowman": {
        "name": "Bowman", "cost": 40, "rng": CELL * 3 + CELL // 2, "dmg": 18, "rate": 30,
        "col": (80, 180, 80), "upg_cost": 30,
        "desc": "Fast, Single Target",
    },
    "crossbow": {
        "name": "Crossbow", "cost": 90, "rng": CELL * 2 + CELL // 2, "dmg": 50, "rate": 55,
        "col": (180, 100, 60), "upg_cost": 50, "splash": 50,
        "desc": "Slower, Splash Damage",
    },
    "guard": {
        "name": "Guard", "cost": 60, "rng": CELL * 2 + CELL // 2, "dmg": 10, "rate": 35,
        "col": (100, 180, 230), "upg_cost": 40, "slow": 0.45,
        "desc": "Slows all enemies in range",
    },
}

RANGE_COLORS = {
    "bowman":   (80, 180, 80, 25),
    "crossbow": (180, 100, 60, 25),
    "guard":    (100, 180, 230, 30),
}

class Tower:
    def __init__(self, kind, x, y):
        data = TOWERS[kind]
        self.kind = kind
        self.x = x
        self.y = y
        self.lv = 1
        self.dmg = data["dmg"]
        self.rng = data["rng"]
        self.rate = data["rate"]
        self.col = data["col"]
        self.splash = data.get("splash", 0)
        self.slow = data.get("slow", 0)
        self.cd = 0

    def upg_cost(self):
        return TOWERS[self.kind]["upg_cost"] + 20 * (self.lv - 1)

    def upgrade(self):
        self.lv += 1
        if self.slow:
            self.rng += CELL
            self.slow = max(0.15, self.slow - 0.06)
        else:
            self.dmg += 10
            self.rng += CELL
            self.rate = max(10, self.rate - 4)

    def update(self, enemies, bullets):
        if self.slow:
            for e in enemies:
                if not e.alive:
                    continue
                if max(abs(e.x - self.x), abs(e.y - self.y)) <= self.rng:
                    slowed = ENEMIES[e.kind]["speed"] * self.slow
                    if slowed < e.speed:
                        e.speed = slowed
            return

        self.cd = max(0, self.cd - 1)
        if self.cd > 0:
            return
        best = None
        best_prog = -1
        for e in enemies:
            if not e.alive:
                continue
            prog = e.progress()
            if max(abs(e.x - self.x), abs(e.y - self.y)) <= self.rng and prog > best_prog:
                best = e
                best_prog = prog
        if best:
            bullets.append(Bullet(self.x, self.y, best, self.dmg, self.splash))
            self.cd = self.rate

    def draw(self, is_selected=False):
        ix = int(self.x)
        iy = int(self.y)
        rc = RANGE_COLORS[self.kind]
        s = pygame.Surface((self.rng * 2, self.rng * 2), pygame.SRCALPHA)
        s.fill(rc)
        pygame.draw.rect(s, (*rc[:3], 60), s.get_rect(), 1)
        screen.blit(s, (ix - self.rng, iy - self.rng))
        img = TOWER_IMGS[self.kind]
        screen.blit(img, (ix - img.get_width() // 2, iy - img.get_height() // 2))
        if self.lv > 1:
            lv_text = font.render(str(self.lv), True, GOLD)
            screen.blit(lv_text, (ix + img.get_width() // 2 - 4, iy - img.get_height() // 2 - 2))
        if is_selected:
            pygame.draw.circle(screen, WHITE, (ix, iy), img.get_width() // 2 + 3, 2)

class Bullet:
    def __init__(self, x, y, target, dmg, splash=0):
        self.x = float(x)
        self.y = float(y)
        self.target = target
        self.dmg = dmg
        self.splash = splash
        self.alive = True

    def update(self, enemies):
        if not self.target.alive:
            self.alive = False
            return
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 8:
            if self.splash > 0:
                for e in enemies:
                    if e.alive and math.hypot(e.x - self.target.x, e.y - self.target.y) < self.splash:
                        e.hp -= self.dmg
                        if e.hp <= 0:
                            e.alive = False
            else:
                self.target.hp -= self.dmg
                if self.target.hp <= 0:
                    self.target.alive = False
            self.alive = False
            return
        self.x += dx / dist * 9
        self.y += dy / dist * 9

    def draw(self):
        pygame.draw.circle(screen, (255, 255, 180), (int(self.x), int(self.y)), 3)

WAVES = [
    [("barbarian", 6, 18)],
    [("barbarian", 10, 15)],
    [("barbarian", 8, 14), ("raider", 3, 20)],
    [("raider", 6, 16), ("barbarian", 8, 12)],
    [("shield", 3, 25), ("barbarian", 10, 12)],
    [("raider", 8, 14), ("shield", 4, 22), ("general", 1, 0)],
    [("barbarian", 12, 10), ("raider", 6, 14), ("shield", 4, 20)],
    [("raider", 10, 12), ("shield", 5, 18), ("siege", 2, 30)],
    [("barbarian", 15, 8), ("shield", 6, 16), ("siege", 3, 25)],
    [("raider", 12, 10), ("siege", 4, 22), ("shield", 5, 16)],
    [("shield", 8, 14), ("siege", 5, 20), ("general", 1, 0)],
    [("raider", 15, 8), ("siege", 6, 18), ("shield", 8, 12), ("general", 2, 0)],
]

def build_spawn_list(wave_idx):
    if wave_idx < len(WAVES):
        defs = WAVES[wave_idx]
    else:
        defs = [
            (random.choice(["barbarian", "raider", "shield"]), 10 + wave_idx, random.randint(12, 25)),
            ("siege", wave_idx // 3, 40),
        ]
        if wave_idx % 5 == 0:
            defs.append(("general", 1, 0))
    hp_scale = 1.0 + wave_idx * 0.15
    queue = []
    for kind, count, delay in defs:
        for i in range(count):
            queue.append((kind, delay, hp_scale))
    return queue

MAX_LIVES = 20
gold = 200
lives = MAX_LIVES
score = 0
wave_num = 0
towers = []
enemies = []
bullets = []
spawn_queue = []
spawn_timer = 0
state = "build"
placing = None
selected = None

def reset_game():
    global gold, lives, score, wave_num
    global towers, enemies, bullets
    global spawn_queue, spawn_timer
    global state, placing, selected, grid_occupied
    gold = 200
    lives = MAX_LIVES
    score = 0
    wave_num = 0
    towers = []
    enemies = []
    bullets = []
    spawn_queue = []
    spawn_timer = 0
    state = "build"
    placing = None
    selected = None
    grid_occupied = [[False] * GRID_ROWS for _ in range(GRID_COLS)]

def draw_grid():
    for c in range(GRID_COLS + 1):
        pygame.draw.line(screen, (55, 60, 50), (c * CELL, 0), (c * CELL, MAPH))
    for r in range(GRID_ROWS + 1):
        pygame.draw.line(screen, (55, 60, 50), (0, r * CELL), (W, r * CELL))

def draw_path():
    for c, r in path_cells:
        rect = pygame.Rect(c * CELL, r * CELL, CELL, CELL)
        pygame.draw.rect(screen, (170, 150, 100), rect)
        pygame.draw.rect(screen, (140, 120, 75), rect, 1)
    sx, sy = PATH[0]
    pygame.draw.circle(screen, GREEN, (sx + 10, sy), 10)
    screen.blit(font.render("START", True, WHITE), (sx + 24, sy - 8))
    ex, ey = PATH[-1]
    screen.blit(CASTLE_IMG, (ex - CASTLE_IMG.get_width() - 4, ey - CASTLE_IMG.get_height() // 2))

def draw_hud():
    bar = pygame.Surface((W, 44), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 180))
    screen.blit(bar, (0, 0))
    screen.blit(font.render(f"Gold: {gold}", True, GOLD), (10, 13))

    lx = 150
    screen.blit(font.render("Lives:", True, WHITE), (lx, 13))
    bx = lx + 58
    bw = 100
    bh = 14
    by = 15
    pygame.draw.rect(screen, (60, 20, 20), (bx, by, bw, bh), border_radius=3)
    fill = max(0, int(bw * lives / MAX_LIVES))
    if lives > MAX_LIVES * 0.5:
        col = GREEN
    elif lives > MAX_LIVES * 0.25:
        col = GOLD
    else:
        col = RED
    if fill > 0:
        pygame.draw.rect(screen, col, (bx, by, fill, bh), border_radius=3)
    pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), 1, border_radius=3)
    lt = sm_font.render(f"{lives}/{MAX_LIVES}", True, WHITE)
    screen.blit(lt, (bx + bw // 2 - lt.get_width() // 2, by))

    screen.blit(font.render(f"Wave: {wave_num + 1}", True, WHITE), (320, 13))
    screen.blit(font.render(f"Score: {score}", True, WHITE), (460, 13))
    if state == "build":
        screen.blit(font.render("BUILD PHASE  [SPACE = Start Wave]", True, GREEN), (600, 13))
    elif state == "wave":
        screen.blit(font.render("WAVE IN PROGRESS...", True, RED), (620, 13))

def draw_bottom_bar():
    bar_y = MAPH
    panel = pygame.Surface((W, BAR_H), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 200))
    screen.blit(panel, (0, bar_y))
    pygame.draw.line(screen, GRAY, (0, bar_y), (W, bar_y), 2)

    rects = {}
    x = 15
    screen.blit(font.render("SHOP", True, GOLD), (x, bar_y + 6))
    btn_y = bar_y + 28
    btn_w = 240
    btn_h = 120

    for key in ["bowman", "crossbow", "guard"]:
        d = TOWERS[key]
        can_buy = gold >= d["cost"] and state == "build"
        color = d["col"] if can_buy else (60, 60, 60)
        rect = pygame.Rect(x, btn_y, btn_w, btn_h)
        rects[key] = rect
        pygame.draw.rect(screen, color, rect, border_radius=5)
        if placing == key:
            pygame.draw.rect(screen, WHITE, rect, 2, border_radius=5)
        img = TOWER_SHOP_IMGS[key]
        screen.blit(img, (rect.x + (btn_w - img.get_width()) // 2, rect.y + 4))
        name_s = font.render(d["name"], True, WHITE)
        screen.blit(name_s, (rect.x + (btn_w - name_s.get_width()) // 2, rect.y + 56))
        mid = rect.x + btn_w // 2
        desc_s = sm_font.render(d["desc"], True, WHITE)
        screen.blit(desc_s, (mid - desc_s.get_width() // 2, rect.y + 74))
        if d.get("slow"):
            slow_pct = int((1 - d["slow"]) * 100)
            stat = sm_font.render(f"Slow: {slow_pct}%  Range: {d['rng']//CELL}", True, (200, 220, 255))
        elif d.get("splash"):
            stat = sm_font.render(f"Damage: {d['dmg']}  Range: {d['rng']//CELL}  AoE", True, (255, 200, 150))
        else:
            stat = sm_font.render(f"Damage: {d['dmg']}  Range: {d['rng']//CELL}", True, (200, 255, 200))
        screen.blit(stat, (mid - stat.get_width() // 2, rect.y + 88))
        cost_s = font.render(f"{d['cost']}g", True, GOLD)
        screen.blit(cost_s, (mid - cost_s.get_width() // 2, rect.y + 102))
        x += btn_w + 10

    act_x = x + 20
    if selected and selected.lv < 5:
        cost = selected.upg_cost()
        can_upg = gold >= cost and state == "build"
        upg_rect = pygame.Rect(act_x, bar_y + 30, 170, 40)
        pygame.draw.rect(screen, (60, 180, 60) if can_upg else (60, 60, 60), upg_rect, border_radius=5)
        screen.blit(font.render(f"Upgrade ({cost}g)", True, WHITE), (upg_rect.x + 12, upg_rect.y + 10))
        rects["upgrade"] = upg_rect
    elif selected and selected.lv >= 5:
        upg_rect = pygame.Rect(act_x, bar_y + 30, 170, 40)
        pygame.draw.rect(screen, (60, 60, 60), upg_rect, border_radius=5)
        screen.blit(font.render("MAX LEVEL", True, GRAY), (upg_rect.x + 12, upg_rect.y + 10))

    quit_rect = pygame.Rect(W - 110, bar_y + 30, 95, 40)
    pygame.draw.rect(screen, (180, 50, 50), quit_rect, border_radius=5)
    screen.blit(font.render("QUIT", True, WHITE), (quit_rect.x + 22, quit_rect.y + 10))
    rects["quit"] = quit_rect

    if selected:
        ix = W - 420
        pygame.draw.line(screen, GRAY, (ix - 10, bar_y + 10), (ix - 10, bar_y + BAR_H - 10))
        d = TOWERS[selected.kind]
        screen.blit(font.render(f"{d['name']} Lv{selected.lv}", True, WHITE), (ix, bar_y + 10))
        screen.blit(sm_font.render(d["desc"], True, WHITE), (ix, bar_y + 28))
        if selected.slow:
            slow_pct = int((1 - selected.slow) * 100)
            screen.blit(sm_font.render(f"Slow: {slow_pct}%   Range: {selected.rng//CELL}", True, WHITE), (ix, bar_y + 44))
        else:
            screen.blit(sm_font.render(f"Damage: {selected.dmg}   Range: {selected.rng//CELL}   Rate: {selected.rate}f", True, WHITE), (ix, bar_y + 44))
        if selected.lv < 5:
            if selected.slow:
                ns = max(0.15, selected.slow - 0.06)
                nr = selected.rng + CELL
                screen.blit(sm_font.render(f"Next: Slow {int((1-ns)*100)}%  Range {nr//CELL}", True, GREEN), (ix, bar_y + 60))
            else:
                nd = selected.dmg + 10
                nr = selected.rng + CELL
                nt = max(10, selected.rate - 4)
                screen.blit(sm_font.render(f"Next: Damage {nd}  Range {nr//CELL}  Rate {nt}f", True, GREEN), (ix, bar_y + 60))
        else:
            screen.blit(font.render("MAX LEVEL", True, GRAY), (ix, bar_y + 60))

    return rects

def draw_placement(mx, my):
    if placing is None or state != "build" or my >= MAPH:
        return
    d = TOWERS[placing]
    cx, cy, col, row = snap_to_grid(mx, my)
    ok = can_place(col, row)
    cs = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    if ok:
        cs.fill((100, 255, 100, 50))
    else:
        cs.fill((255, 100, 100, 50))
    screen.blit(cs, (col * CELL, row * CELL))
    if ok:
        pygame.draw.rect(screen, (200, 255, 200), (col * CELL, row * CELL, CELL, CELL), 2)
    else:
        pygame.draw.rect(screen, (255, 120, 120), (col * CELL, row * CELL, CELL, CELL), 2)
    s = pygame.Surface((d["rng"] * 2, d["rng"] * 2), pygame.SRCALPHA)
    if ok:
        s.fill((100, 255, 100, 35))
    else:
        s.fill((255, 100, 100, 35))
    screen.blit(s, (cx - d["rng"], cy - d["rng"]))
    img = TOWER_IMGS[placing]
    screen.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))

def draw_overlay(text1, text2, col):
    o = pygame.Surface((W, H), pygame.SRCALPHA)
    o.fill((0, 0, 0, 160))
    screen.blit(o, (0, 0))
    t1 = big_font.render(text1, True, col)
    screen.blit(t1, (W // 2 - t1.get_width() // 2, H // 2 - 50))
    t2 = font.render(text2, True, WHITE)
    screen.blit(t2, (W // 2 - t2.get_width() // 2, H // 2 + 10))

last_shop_rects = {}

while True:
    mx, my = pygame.mouse.get_pos()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if ev.type == pygame.KEYDOWN:
            if state == "gameover" and ev.key == pygame.K_r:
                reset_game()
            elif state == "build":
                if ev.key == pygame.K_SPACE:
                    spawn_queue = build_spawn_list(wave_num)
                    spawn_timer = 0
                    state = "wave"
                    placing = None
                    selected = None
                elif ev.key == pygame.K_1:
                    placing = "bowman" if placing != "bowman" else None
                    selected = None
                elif ev.key == pygame.K_2:
                    placing = "crossbow" if placing != "crossbow" else None
                    selected = None
                elif ev.key == pygame.K_3:
                    placing = "guard" if placing != "guard" else None
                    selected = None
                elif ev.key == pygame.K_ESCAPE:
                    placing = None
                    selected = None
                elif ev.key == pygame.K_u and selected and selected.lv < 5:
                    cost = selected.upg_cost()
                    if gold >= cost:
                        gold -= cost
                        selected.upgrade()

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if "quit" in last_shop_rects and last_shop_rects["quit"].collidepoint(mx, my):
                pygame.quit()
                sys.exit()

            if state == "build":
                if my >= MAPH:
                    if "upgrade" in last_shop_rects and last_shop_rects["upgrade"].collidepoint(mx, my):
                        if selected and selected.lv < 5:
                            cost = selected.upg_cost()
                            if gold >= cost:
                                gold -= cost
                                selected.upgrade()
                    else:
                        for key, rect in last_shop_rects.items():
                            if key in ("upgrade", "quit"):
                                continue
                            if rect.collidepoint(mx, my):
                                placing = key if placing != key else None
                                selected = None
                                break
                elif placing:
                    d = TOWERS[placing]
                    cx, cy, col, row = snap_to_grid(mx, my)
                    if gold >= d["cost"] and can_place(col, row):
                        towers.append(Tower(placing, cx, cy))
                        grid_occupied[col][row] = True
                        gold -= d["cost"]
                        placing = None
                else:
                    selected = None
                    for t in towers:
                        if math.hypot(t.x - mx, t.y - my) <= 25:
                            selected = t
                            break

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            placing = None

    if state == "wave":
        if spawn_queue:
            spawn_timer -= 1
            if spawn_timer <= 0:
                kind, delay, hp_s = spawn_queue.pop(0)
                enemies.append(Enemy(kind, hp_s))
                spawn_timer = delay

        for e in enemies:
            e.update()
            if e.leaked:
                lives -= e.leak_dmg
                if lives <= 0:
                    state = "gameover"

        for e in enemies:
            if e.alive:
                e.speed = ENEMIES[e.kind]["speed"]

        for t in towers:
            t.update(enemies, bullets)

        for b in bullets:
            b.update(enemies)

        for e in enemies:
            if not e.alive and not e.leaked:
                gold += e.reward
                score += e.reward
        enemies = [e for e in enemies if e.alive]
        bullets = [b for b in bullets if b.alive]

        if not spawn_queue and not enemies and state == "wave":
            wave_num += 1
            gold += 30 + wave_num * 8
            state = "build"

    screen.fill(BG)
    draw_grid()
    draw_path()
    for e in enemies:
        e.draw()
    for b in bullets:
        b.draw()
    for t in towers:
        t.draw(t is selected)
    draw_placement(mx, my)
    draw_hud()
    last_shop_rects = draw_bottom_bar()
    if state == "gameover":
        draw_overlay(f"GAME OVER  -  Score: {score}", "Press R to restart", RED)

    pygame.display.flip()
    clock.tick(60)
