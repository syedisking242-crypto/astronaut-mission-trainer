import random

from PIL import Image, ImageDraw


def run_navigation() -> tuple[bool, int, str]:
    """Run the keyboard-controlled Pygame navigation challenge and return its result."""
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((900, 600))
    pygame.display.set_caption("Orbital Navigation | Junior Astronaut Mission Trainer")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)
    background_image = Image.new("RGB", (900, 600), (5, 15, 31))
    background_draw = ImageDraw.Draw(background_image)
    for _ in range(150):
        x, y = random.randrange(900), random.randrange(600)
        shade = random.randrange(100, 190)
        background_draw.point((x, y), fill=(shade // 2, shade, min(220, shade + 25)))
    background_draw.ellipse((650, 310, 1000, 660), fill=(20, 48, 73), outline=(46, 109, 137), width=3)
    background_draw.arc((635, 295, 1015, 675), 205, 335, fill=(81, 180, 193), width=2)
    background = pygame.image.fromstring(background_image.tobytes(), background_image.size, "RGB")
    ship = pygame.Rect(430, 460, 38, 38)
    beacon = pygame.Rect(420, 42, 60, 42)
    asteroids = [pygame.Rect(random.randrange(20, 850), random.randrange(-600, 0), 30, 30) for _ in range(9)]
    hits = 0
    elapsed = 0
    success = False
    running = True
    while running:
        dt = clock.tick(60) / 1000
        elapsed += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        keys = pygame.key.get_pressed()
        ship.x += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 300 * dt
        ship.y += (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * 300 * dt
        ship.clamp_ip(screen.get_rect())
        screen.blit(background, (0, 0))
        pygame.draw.rect(screen, (73, 218, 227), beacon, border_radius=8)
        for asteroid in asteroids:
            asteroid.y += 170 * dt
            if asteroid.top > 600:
                asteroid.update(random.randrange(20, 850), random.randrange(-280, -30), 30, 30)
            pygame.draw.circle(screen, (210, 117, 76), asteroid.center, 16)
            if ship.colliderect(asteroid):
                hits += 1
                asteroid.y = 700
        pygame.draw.polygon(screen, (239, 242, 235), [(ship.centerx, ship.top), (ship.left, ship.bottom), (ship.right, ship.bottom)])
        screen.blit(font.render(f"Reach the beacon  |  Collision alerts: {hits}  |  ESC: exit", True, (227, 236, 241)), (18, 18))
        if ship.colliderect(beacon):
            success = True
            running = False
        if hits >= 3:
            running = False
        pygame.display.flip()
    pygame.quit()
    return success, max(0, 100 - hits * 20), f"{hits} collision alert(s), {elapsed:.1f} seconds"