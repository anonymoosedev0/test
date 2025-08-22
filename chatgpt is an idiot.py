import pygame, sys, random, time

pygame.init()

# Window setup
WIDTH, HEIGHT = 1000, 600
PLAY_WIDTH, PLAY_HEIGHT = 700, 600
INFO_WIDTH = WIDTH - PLAY_WIDTH
CELL = 20

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Segoe UI", 18)
big_font = pygame.font.SysFont("Segoe UI", 28, bold=True)

BG = (11, 15, 20)
GRID = (27, 37, 53)
TEXT = (231, 240, 255)
MUTED = (155, 176, 201)
APPLE = (255, 77, 77)
GOLD = (255, 215, 0)
SLOW = (150, 200, 255)
SHRINK = (144, 238, 144)
PORTAL = (173, 132, 255)

snake = [(10, 10)]
direction = (1, 0)
apple = (random.randint(0, PLAY_WIDTH//CELL-1), random.randint(0, PLAY_HEIGHT//CELL-1))
score = 0

best_score = 0
alive_time = 0
start_time = time.time()


def draw_board():
    screen.fill(BG)
    # Grid
    for x in range(0, PLAY_WIDTH, CELL):
        pygame.draw.line(screen, GRID, (x, 0), (x, PLAY_HEIGHT))
    for y in range(0, PLAY_HEIGHT, CELL):
        pygame.draw.line(screen, GRID, (0, y), (PLAY_WIDTH, y))


def draw_snake():
    for (x, y) in snake:
        rect = pygame.Rect(x*CELL, y*CELL, CELL-2, CELL-2)
        pygame.draw.rect(screen, (110, 231, 255), rect, border_radius=6)


def draw_apple():
    rect = pygame.Rect(apple[0]*CELL, apple[1]*CELL, CELL, CELL)
    pygame.draw.rect(screen, APPLE, rect, border_radius=6)


def move_snake():
    global snake, apple, score, best_score
    head = (snake[0][0]+direction[0], snake[0][1]+direction[1])
    if head[0] < 0 or head[0] >= PLAY_WIDTH//CELL or head[1] < 0 or head[1] >= PLAY_HEIGHT//CELL:
        reset_game()
        return
    if head in snake:
        reset_game()
        return
    snake.insert(0, head)
    if head == apple:
        score += 10
        apple = (random.randint(0, PLAY_WIDTH//CELL-1), random.randint(0, PLAY_HEIGHT//CELL-1))
        best_score = max(best_score, score)
    else:
        snake.pop()


def draw_info():
    panel = pygame.Rect(PLAY_WIDTH, 0, INFO_WIDTH, HEIGHT)
    pygame.draw.rect(screen, (15, 22, 33), panel)


    screen.blit(big_font.render("Ultimate Snake", True, TEXT), (PLAY_WIDTH+20, 20))


    stats = [
        ("Score", score),
        ("Best", best_score),
        ("Alive", int(time.time()-start_time)),
        ("Length", len(snake))
    ]
    y = 70
    for label, val in stats:
        screen.blit(font.render(f"{label}: {val}", True, MUTED), (PLAY_WIDTH+20, y))
        y += 30


    y += 20
    screen.blit(font.render("Power-ups", True, TEXT), (PLAY_WIDTH+20, y))
    y += 30
    legend = [(APPLE, "Apple +10"), (GOLD, "Golden +50"), (SLOW, "Slowmo"), (SHRINK, "Shrink"), (PORTAL, "Portal")]
    for color, text in legend:
        pygame.draw.circle(screen, color, (PLAY_WIDTH+30, y+7), 6)
        screen.blit(font.render(text, True, MUTED), (PLAY_WIDTH+50, y))
        y += 24


    y += 20
    controls = ["Space: start/restart", "Arrows: move", "P: pause"]
    for c in controls:
        screen.blit(font.render(c, True, MUTED), (PLAY_WIDTH+20, y))
        y += 24


def reset_game():
    global snake, direction, apple, score, start_time
    snake = [(10, 10)]
    direction = (1, 0)
    apple = (random.randint(0, PLAY_WIDTH//CELL-1), random.randint(0, PLAY_HEIGHT//CELL-1))
    score = 0
    start_time = time.time()



paused = False
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: direction = (0,-1)
            elif event.key == pygame.K_DOWN: direction = (0,1)
            elif event.key == pygame.K_LEFT: direction = (-1,0)
            elif event.key == pygame.K_RIGHT: direction = (1,0)
            elif event.key == pygame.K_p: paused = not paused
            elif event.key == pygame.K_SPACE: reset_game()

    if not paused:
        move_snake()

    draw_board()
    draw_snake()
    draw_apple()
    draw_info()

    pygame.display.flip()
    clock.tick(10)
