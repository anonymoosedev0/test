#!/usr/bin/env python3
"""
Ultimate Snake – Pygame (single file)
Judged on: looks, feel, playability, informative features, extras, fun.

Run:  python3 ultimate_snake.py
Keys:
  Arrows/WASD = move  |  Space = start  |  P = pause  |  R = restart
  T = theme  |  M = wrap/solid walls  |  G = grid  |  +/- = speed
  F1 = help  |  F2 = photo mode (UI off) |  F5 = quick save screenshot

Requires: pygame (pip install pygame)

Persistent data: creates ./ultimate_snake_data.json for highscores & prefs.
"""
import json, math, os, random, sys, time
from dataclasses import dataclass

# Safe import for pygame
try:
    import pygame
except Exception as e:
    print("This game requires pygame. Install it with: pip install pygame")
    raise

# ------------------------------
# Config & constants
# ------------------------------
VERSION = "1.0"
DATA_FILE = "ultimate_snake_data.json"

GRID_W, GRID_H = 28, 20   # grid cells
CELL = 28                 # pixel size per cell (scaled later)
MARGIN = 16               # padding around board
SIDEBAR_W = 320
TARGET_FPS = 120

# Colors as themes
THEMES = [
    {
        "name": "Neon Night",
        "bg": (11,15,20),
        "panel": (15,22,33),
        "grid": (27,37,53),
        "snake": (0, 245, 212),
        "snake2": (123, 44, 255),
        "food": (255, 61, 129),
        "text": (231,240,255),
        "muted": (155,176,201),
        "good": (124,242,154),
        "bad": (255,107,107),
        "warn": (255,209,102),
    },
    {
        "name": "Retro Green",
        "bg": (6,12,8),
        "panel": (10,20,14),
        "grid": (18,36,22),
        "snake": (120, 255, 120),
        "snake2": (60, 200, 60),
        "food": (240, 255, 120),
        "text": (220,255,230),
        "muted": (140,180,150),
        "good": (190,255,190),
        "bad": (255,120,120),
        "warn": (255,210,140),
    },
    {
        "name": "Candy Pop",
        "bg": (20,10,20),
        "panel": (32,16,40),
        "grid": (48,24,60),
        "snake": (255, 120, 180),
        "snake2": (120, 180, 255),
        "food": (255, 220, 120),
        "text": (255,245,255),
        "muted": (200,170,200),
        "good": (255,180,220),
        "bad": (255,120,180),
        "warn": (255,230,150),
    },
]

# Power-up types
FOOD_NORMAL = 0
FOOD_GOLDEN = 1
FOOD_SLOWMO = 2
FOOD_SHRINK = 3
FOOD_PORTAL = 4
FOOD_TYPES = [FOOD_NORMAL, FOOD_GOLDEN, FOOD_SLOWMO, FOOD_SHRINK, FOOD_PORTAL]

@dataclass
class Prefs:
    theme_index: int = 0
    show_grid: bool = True
    wrap_walls: bool = True
    base_speed: float = 8.0  # cells per second
    best_score: int = 0

@dataclass
class Stats:
    score: int = 0
    length: int = 3
    apples: int = 0
    golden: int = 0
    slowmo: int = 0
    shrink: int = 0
    portal: int = 0
    time_start: float = 0.0
    time_alive: float = 0.0
    max_combo: int = 0

@dataclass
class Food:
    pos: tuple
    kind: int
    ttl: float

# ------------------------------
# Utils
# ------------------------------

def load_prefs() -> Prefs:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                d = json.load(f)
            p = Prefs(**{**Prefs().__dict__, **d.get('prefs', {})})
            return p
        except Exception:
            pass
    return Prefs()

def save_prefs(prefs: Prefs, stats: Stats|None=None):
    data = {"prefs": prefs.__dict__}
    if stats:
        data["last_stats"] = stats.__dict__
    if not os.path.exists(os.path.dirname(DATA_FILE)) and \
       os.path.dirname(DATA_FILE) != "":
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Nice easing for animations

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

# ------------------------------
# Game
# ------------------------------

class SnakeGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Ultimate Snake")
        self.clock = pygame.time.Clock()
        self.prefs = load_prefs()
        self.theme = THEMES[self.prefs.theme_index % len(THEMES)]

        # Compute window size
        board_w = GRID_W * CELL + MARGIN*2
        board_h = GRID_H * CELL + MARGIN*2
        self.win_w = board_w + SIDEBAR_W
        self.win_h = max(board_h, 620)
        self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.SCALED | pygame.RESIZABLE, vsync=1)

        # Fonts
        self.font = pygame.font.SysFont("Inter,Segoe UI,Roboto,Helvetica,Arial", 20)
        self.font_small = pygame.font.SysFont("Inter,Segoe UI,Roboto,Helvetica,Arial", 16)
        self.font_big = pygame.font.SysFont("Inter,Segoe UI,Roboto,Helvetica,Arial", 48, bold=True)

        self.reset()

    # ---------- Core state ----------
    def reset(self):
        self.state = 'menu'  # menu, play, paused, gameover
        self.stats = Stats(time_start=time.time())
        cx, cy = GRID_W//2, GRID_H//2
        self.snake = [(cx-1, cy), (cx, cy), (cx+1, cy)]  # grows to the right
        self.dir = (1, 0)
        self.next_dir = (1, 0)
        self.buffer_move = 0.0
        self.speed = self.prefs.base_speed
        self.combo = 0
        self.particles = []
        self.foods = []
        self.spawn_food(initial=True)
        self.portal_pairs = []
        self.flash_t = 0.0
        self.camera_shake_t = 0.0
        self.photo_mode = False

    # ---------- Food & powerups ----------
    def spawn_food(self, initial=False):
        occupied = set(self.snake)
        # Avoid placing on snake or existing foods
        free = [(x,y) for x in range(GRID_W) for y in range(GRID_H)
                if (x,y) not in occupied and (x,y) not in [f.pos for f in self.foods]]
        if not free:
            return
        def place(kind, ttl):
            pos = random.choice(free)
            self.foods.append(Food(pos, kind, ttl))
        # Always at least one normal
        place(FOOD_NORMAL, ttl=30.0)
        if initial:
            return
        # Chance to add powerups
        r = random.random()
        if r < 0.15:
            place(FOOD_GOLDEN, ttl=12.0)
        elif r < 0.30:
            place(FOOD_SLOWMO, ttl=10.0)
        elif r < 0.42:
            place(FOOD_SHRINK, ttl=10.0)
        elif r < 0.52:
            # spawn a portal pair (two FOOD_PORTAL in one go)
            if len(free) >= 2:
                p1 = random.choice(free)
                free2 = [c for c in free if c != p1]
                p2 = random.choice(free2)
                self.foods.append(Food(p1, FOOD_PORTAL, 14.0))
                self.foods.append(Food(p2, FOOD_PORTAL, 14.0))

    # ---------- Input ----------
    def handle_input(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE,):
                    self.quit()
                if self.state == 'menu' and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.state = 'play'
                if e.key in (pygame.K_t,):
                    self.prefs.theme_index = (self.prefs.theme_index + 1) % len(THEMES)
                    self.theme = THEMES[self.prefs.theme_index]
                if e.key in (pygame.K_m,):
                    self.prefs.wrap_walls = not self.prefs.wrap_walls
                if e.key in (pygame.K_g,):
                    self.prefs.show_grid = not self.prefs.show_grid
                if e.key in (pygame.K_F1,):
                    self.flash_t = 1.5
                if e.key in (pygame.K_F2,):
                    self.photo_mode = not self.photo_mode
                if e.key in (pygame.K_F5,):
                    pygame.image.save(self.screen, f"snake_{int(time.time())}.png")
                if e.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    self.prefs.base_speed = min(25.0, self.prefs.base_speed + 0.5)
                    self.speed = self.prefs.base_speed
                if e.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                    self.prefs.base_speed = max(3.0, self.prefs.base_speed - 0.5)
                    self.speed = self.prefs.base_speed
                if e.key in (pygame.K_p,):
                    if self.state == 'play':
                        self.state = 'paused'
                    elif self.state == 'paused':
                        self.state = 'play'
                if e.key in (pygame.K_r,):
                    self.reset(); self.state = 'play'

                # Movement buffering: prevent reversing into itself
                if e.key in (pygame.K_LEFT, pygame.K_a):
                    if self.dir != (1,0): self.next_dir = (-1,0)
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    if self.dir != (-1,0): self.next_dir = (1,0)
                elif e.key in (pygame.K_UP, pygame.K_w):
                    if self.dir != (0,1): self.next_dir = (0,-1)
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    if self.dir != (0,-1): self.next_dir = (0,1)

    # ---------- Update ----------
    def update(self, dt):
        if self.state != 'play':
            return
        self.buffer_move += dt * self.speed
        moved = False
        while self.buffer_move >= 1.0:  # move at whole-cell rate, render smoothly
            self.buffer_move -= 1.0
            self.dir = self.next_dir
            head = self.snake[-1]
            nx, ny = head[0] + self.dir[0], head[1] + self.dir[1]
            if self.prefs.wrap_walls:
                nx %= GRID_W
                ny %= GRID_H
            else:
                if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                    self.game_over(); return
            new_head = (nx, ny)
            if new_head in self.snake[1:]:  # allow moving into tail only if it will move away (handled naturally)
                self.game_over(); return
            self.snake.append(new_head)

            ate = None
            for f in list(self.foods):
                if f.pos == new_head:
                    ate = f
                    self.foods.remove(f)
                    break
            if ate:
                self.apply_food(ate)
                self.spawn_food()
                self.combo += 1
                self.stats.max_combo = max(self.stats.max_combo, self.combo)
                self.camera_shake_t = 0.25
            else:
                self.snake.pop(0)  # move forward without growth
                self.combo = 0
            moved = True

        # Decay timers / particles
        for f in list(self.foods):
            f.ttl -= dt
            if f.ttl <= 0:
                self.foods.remove(f)
        self.particles = [p for p in self.particles if p['ttl'] > 0]
        for p in self.particles:
            p['x'] += p['vx']*dt
            p['y'] += p['vy']*dt
            p['ttl'] -= dt
        self.flash_t = max(0.0, self.flash_t - dt)
        self.camera_shake_t = max(0.0, self.camera_shake_t - dt)
        self.stats.time_alive = time.time() - self.stats.time_start

    def game_over(self):
        self.state = 'gameover'
        self.prefs.best_score = max(self.prefs.best_score, self.stats.score)
        save_prefs(self.prefs, self.stats)

    def apply_food(self, food: Food):
        x, y = food.pos
        # particles burst
        for _ in range(24):
            ang = random.random()*math.tau
            spd = 80 + random.random()*120
            self.particles.append({
                'x': (x+0.5)*CELL+MARGIN, 'y': (y+0.5)*CELL+MARGIN,
                'vx': math.cos(ang)*spd, 'vy': math.sin(ang)*spd,
                'ttl': 0.35+random.random()*0.35,
                'kind': food.kind
            })

        if food.kind == FOOD_NORMAL:
            self.stats.apples += 1
            self.stats.length += 1
            self.stats.score += 10 + max(0, self.combo-1)*4
            # grow by 1 (keep tail)
        elif food.kind == FOOD_GOLDEN:
            self.stats.golden += 1
            self.stats.length += 3
            self.stats.score += 50
            # grow by 3 (keep tail * 3)
            self.snake.extend([self.snake[0]]*2)
        elif food.kind == FOOD_SLOWMO:
            self.stats.slowmo += 1
            self.speed = max(3.0, self.speed - 2.0)
            self.stats.score += 20
        elif food.kind == FOOD_SHRINK:
            self.stats.shrink += 1
            cut = min(3, len(self.snake)-3)
            if cut>0:
                del self.snake[:cut]
                self.stats.length = max(3, self.stats.length - cut)
            self.stats.score += 15
        elif food.kind == FOOD_PORTAL:
            self.stats.portal += 1
            # teleport to another portal if exists
            others = [f for f in self.foods if f.kind == FOOD_PORTAL]
            if others:
                target = random.choice(others)
                self.snake[-1] = target.pos
            self.stats.score += 25

    # ---------- Draw ----------
    def draw(self):
        th = self.theme
        self.screen.fill(th['bg'])
        board_rect = pygame.Rect(0, 0, GRID_W*CELL + MARGIN*2, GRID_H*CELL + MARGIN*2)
        board_rect.center = (self.win_w - SIDEBAR_W//2 - board_rect.w//2, self.win_h//2)

        # Panel background
        pygame.draw.rect(self.screen, th['panel'], board_rect, border_radius=18)

        # Grid
        if self.prefs.show_grid:
            for x in range(GRID_W+1):
                xx = board_rect.left + MARGIN + x*CELL
                pygame.draw.line(self.screen, th['grid'], (xx, board_rect.top+MARGIN), (xx, board_rect.bottom-MARGIN))
            for y in range(GRID_H+1):
                yy = board_rect.top + MARGIN + y*CELL
                pygame.draw.line(self.screen, th['grid'], (board_rect.left+MARGIN, yy), (board_rect.right-MARGIN, yy))

        # Camera shake offset
        ox = oy = 0
        if self.camera_shake_t > 0:
            mag = ease_out_cubic(self.camera_shake_t) * 6
            ox = random.uniform(-mag, mag)
            oy = random.uniform(-mag, mag)

        # Foods / powerups
        for f in self.foods:
            cx = board_rect.left + MARGIN + f.pos[0]*CELL + CELL//2 + ox
            cy = board_rect.top + MARGIN + f.pos[1]*CELL + CELL//2 + oy
            # pulsate
            t = pygame.time.get_ticks()/1000.0
            r = int(CELL*0.35 + math.sin(t*4+f.pos[0])*3)
            if f.kind == FOOD_NORMAL:
                col = th['food']
            elif f.kind == FOOD_GOLDEN:
                col = (255, 215, 0)
            elif f.kind == FOOD_SLOWMO:
                col = th['warn']
            elif f.kind == FOOD_SHRINK:
                col = th['good']
            else:
                col = (120, 180, 255)
            pygame.draw.circle(self.screen, col, (int(cx), int(cy)), r)
            # TTL ring
            pct = max(0.0, min(1.0, f.ttl / 14.0))
            pygame.draw.circle(self.screen, (255,255,255,40), (int(cx), int(cy)), r+6, width=2)
            end_angle = -math.tau * pct
            pygame.draw.arc(self.screen, col, (cx-(r+8), cy-(r+8), (r+8)*2, (r+8)*2), 0, end_angle, 2)

        # Snake with gradient and rounded joints
        for i, (x,y) in enumerate(self.snake):
            px = board_rect.left + MARGIN + x*CELL + ox
            py = board_rect.top + MARGIN + y*CELL + oy
            t = i/ max(1, len(self.snake)-1)
            # gradient between snake and snake2
            col = (
                int(self.theme['snake'][0]*(1-t) + self.theme['snake2'][0]*t),
                int(self.theme['snake'][1]*(1-t) + self.theme['snake2'][1]*t),
                int(self.theme['snake'][2]*(1-t) + self.theme['snake2'][2]*t),
            )
            rect = pygame.Rect(px+2, py+2, CELL-4, CELL-4)
            pygame.draw.rect(self.screen, col, rect, border_radius=8)
            # little shine
            pygame.draw.rect(self.screen, (255,255,255,20), (rect.x+4, rect.y+4, rect.w-8, 6), border_radius=3)

        # Snake eyes on head
        hx, hy = self.snake[-1]
        hx = board_rect.left + MARGIN + hx*CELL + ox
        hy = board_rect.top + MARGIN + hy*CELL + oy
        eye_offset = 6
        ex = hx + CELL//2 + self.dir[0]*eye_offset
        ey = hy + CELL//2 + self.dir[1]*eye_offset
        pygame.draw.circle(self.screen, (240,240,240), (int(ex-6), int(ey-6)), 3)
        pygame.draw.circle(self.screen, (240,240,240), (int(ex+6), int(ey+6)), 3)

        # Particles
        for p in self.particles:
            r = max(1, int(5 * (p['ttl']/0.7)))
            col = th['food'] if p['kind']==FOOD_NORMAL else (
                  (255,215,0) if p['kind']==FOOD_GOLDEN else (
                  th['warn'] if p['kind']==FOOD_SLOWMO else (
                  th['good'] if p['kind']==FOOD_SHRINK else (120,180,255))))
            pygame.draw.circle(self.screen, col, (int(p['x']+ox), int(p['y']+oy)), r)

        # Flash overlay (help)
        if self.flash_t > 0 and not self.photo_mode:
            a = int(160 * ease_out_cubic(self.flash_t/1.5))
            s = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
            s.fill((255,255,255,a))
            self.screen.blit(s, (0,0))

        if not self.photo_mode:
            self.draw_sidebar(board_rect)
            if self.state in ('menu','paused','gameover'):
                self.draw_center_overlay(board_rect)

        pygame.display.flip()

    def draw_sidebar(self, board_rect):
        th = self.theme
        x = board_rect.right + 12
        y = board_rect.top
        w = SIDEBAR_W - 20
        h = board_rect.height
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, th['panel'], rect, border_radius=18)

        # Title
        txt = self.font.render("Ultimate Snake", True, th['text'])
        self.screen.blit(txt, (x+16, y+14))
        subt = self.font_small.render(f"Theme: {th['name']} • v{VERSION}", True, th['muted'])
        self.screen.blit(subt, (x+16, y+40))

        # Stats
        def line(label, value, col=None):
            nonlocal y
            y += 28
            t1 = self.font_small.render(label, True, th['muted'])
            t2 = self.font.render(str(value), True, col or th['text'])
            self.screen.blit(t1, (x+16, y))
            self.screen.blit(t2, (x+w-16 - t2.get_width(), y-4))
        y += 24
        line("Score", self.stats.score)
        line("Length", self.stats.length)
        line("Apples", self.stats.apples)
        line("Best", self.prefs.best_score, th['good'])
        line("Alive", format_time(self.stats.time_alive))
        line("Speed", f"{self.speed:.1f} cps")
        line("Combo", self.combo if self.combo>0 else '-')

        # Toggles
        y += 24
        self.draw_tag(x+14, y, "Wrap" if self.prefs.wrap_walls else "Solid", th['good'] if self.prefs.wrap_walls else th['warn'])
        self.draw_tag(x+110, y, "Grid" if self.prefs.show_grid else "No Grid", th['text'])
        self.draw_tag(x+200, y, "Photo" if self.photo_mode else "UI On", th['text'])

        # Legend
        y += 44
        self.screen.blit(self.font_small.render("Power-ups", True, th['muted']), (x+16, y))
        y += 20
        self.legend_dot(x+18, y+8, th['food']); self.screen.blit(self.font_small.render("Apple +10", True, th['text']), (x+36, y))
        y += 22
        self.legend_dot(x+18, y+8, (255,215,0)); self.screen.blit(self.font_small.render("Golden +50 (grow +3)", True, th['text']), (x+36, y))
        y += 22
        self.legend_dot(x+18, y+8, th['warn']); self.screen.blit(self.font_small.render("Slowmo (-2 cps)", True, th['text']), (x+36, y))
        y += 22
        self.legend_dot(x+18, y+8, th['good']); self.screen.blit(self.font_small.render("Shrink (-up to 3)", True, th['text']), (x+36, y))
        y += 22
        self.legend_dot(x+18, y+8, (120,180,255)); self.screen.blit(self.font_small.render("Portal (teleport)", True, th['text']), (x+36, y))

        # Help footer
        y = rect.bottom - 120
        help_lines = [
            "Space: start  P: pause  R: restart",
            "Arrows/WASD: move",
            "T: theme  M: wrap  G: grid  +/-: speed",
            "F1: help flash  F2: photo  F5: screenshot",
        ]
        for i, line_t in enumerate(help_lines):
            t = self.font_small.render(line_t, True, th['muted'])
            self.screen.blit(t, (x+16, y + i*18))

    def legend_dot(self, x, y, col):
        pygame.draw.circle(self.screen, col, (x, y), 6)

    def draw_tag(self, x, y, text, col):
        s = self.font_small.render(text, True, col)
        r = pygame.Rect(x, y, s.get_width()+12, s.get_height()+8)
        pygame.draw.rect(self.screen, (255,255,255,20), r, border_radius=10)
        self.screen.blit(s, (x+6, y+4))

    def draw_center_overlay(self, board_rect):
        th = self.theme
        cx, cy = board_rect.center
        title = "Ultimate Snake" if self.state=='menu' else ("Paused" if self.state=='paused' else "Game Over")
        t = self.font_big.render(title, True, th['text'])
        self.screen.blit(t, (cx - t.get_width()//2, cy - 120))

        if self.state=='gameover':
            s = [f"Score {self.stats.score}", f"Length {self.stats.length}", f"Time {format_time(self.stats.time_alive)}", f"Best {self.prefs.best_score}"]
            for i, line in enumerate(s):
                tx = self.font.render(line, True, th['muted'])
                self.screen.blit(tx, (cx - tx.get_width()//2, cy - 50 + i*26))
            tip = self.font_small.render("Press R to try again", True, th['text'])
            self.screen.blit(tip, (cx - tip.get_width()//2, cy + 70))
        else:
            tip = self.font_small.render("Press Space to play", True, th['text'])
            self.screen.blit(tip, (cx - tip.get_width()//2, cy - 40))

# ------------------------------
# Helpers
# ------------------------------

def format_time(t):
    m = int(t)//60
    s = int(t)%60
    return f"{m:02d}:{s:02d}"

# ------------------------------
# Main loop
# ------------------------------

def main():
    game = SnakeGame()
    accum = 0.0
    last = time.time()
    while True:
        now = time.time()
        dt = now - last
        last = now
        game.handle_input()
        game.update(dt)
        game.draw()
        game.clock.tick(TARGET_FPS)


def on_exit():
    # Save preferences on exit
    pass

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
