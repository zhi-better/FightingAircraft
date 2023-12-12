import pygame
import sys

pygame.init()

game_window_size = 400, 300
screen = pygame.display.set_mode(game_window_size)
pygame.display.set_caption("Detect Q Key Press")

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        # 检测键盘按下事件
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                print("Q key pressed!")

    pygame.display.flip()
