import pygame
import sys
import math

pygame.init()
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption('My Pygame Window')

circle_pos = (1280/2, 720/2)

def check_circle_collision() -> bool:
    mouse_pos = pygame.mouse.get_pos()

    if math.sqrt((mouse_pos[0] - circle_pos[0])**2 + (mouse_pos[1] - circle_pos[1])**2) <= 50:
        return True
    return False


while True:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left mouse button
                if check_circle_collision():
                    circle_pos = (100, 100)

    screen.fill("lightblue")
    pygame.draw.circle(screen, "red", circle_pos, 50)

    pygame.display.update()