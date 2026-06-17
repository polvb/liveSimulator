import pygame
import random
import sys
import math

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 1000, 700
GRID_SIZE = 20
COLS = WIDTH // GRID_SIZE
ROWS = HEIGHT // GRID_SIZE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulación de Ecosistema - Cuadrícula")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Arial", 14)
FONT_BOLD = pygame.font.SysFont("Arial", 14, bold=True)

# Colores
COLOR_BG = (10, 25, 10)       # Negro/Verde muy oscuro para el fondo
COLOR_GRASS = (15, 40, 15)    # Dibujo del pasto
COLOR_WATER = (30, 80, 200)   # Zona de agua
COLOR_GRID = (40, 40, 40)
COLOR_TEXT = (255, 255, 255)
COLOR_MENU_BG = (30, 30, 30, 220)
COLOR_MALE = (50, 150, 255)
COLOR_FEMALE = (255, 100, 180)
COLOR_BUSH = (34, 139, 34)
COLOR_APPLE = (220, 20, 60)

# --- VARIABLES DE ESTADO GLOBALES ---
paused = False
show_grid = False
show_menu = False
selected_creature = None

# Generador de nombres aleatorios
NAMES = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Fox", "Giga", "Zeta", "Yotta", "Luna", "Sol", "Koda", "Nova", "Onyx"]

# --- CLASES ---

class Bush:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.apples = 3
        self.cooldown = 0  # Tiempo restante para regenerar manzanas (en frames)

    def update(self, dt):
        if self.apples == 0:
            self.cooldown -= dt
            if self.cooldown <= 0:
                self.apples = 3

    def draw(self, surface):
        px = self.x * GRID_SIZE
        py = self.y * GRID_SIZE
        pygame.draw.rect(surface, COLOR_BUSH, (px + 2, py + 2, GRID_SIZE - 4, GRID_SIZE - 4))
        # Dibujar manzanas
        for i in range(self.apples):
            ax = px + 5 + (i * 5)
            ay = py + 10
            pygame.draw.circle(surface, COLOR_APPLE, (ax, ay), 2)

class Creature:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.gender = random.choice(["Macho", "Hembra"])
        self.name = f"{random.choice(NAMES)}-{random.randint(100, 999)}"
        
        # Estadísticas básicas (aleatorias de 1 a 100)
        self.speed = random.randint(1, 100)       # Determina casillas por segundo
        self.vision = random.randint(1, 100)      # Rango de visión en casillas
        self.mating = random.randint(1, 100)      # Genética de apareamiento
        
        # Necesidades básicas
        self.hunger = 100.0
        self.thirst = 100.0
        
        # Control de movimiento interno
        self.move_accumulator = 0.0 
        self.target_x = x
        self.target_y = y

    def update(self, dt, bushes, water_zones, creatures, new_creatures):
        # Descenso de necesidades (5 puntos por segundo)
        self.hunger -= 5.0 * dt
        self.thirst -= 5.0 * dt

        if self.hunger <= 1 or self.thirst <= 1:
            return False # Muere

        # Comportamiento y toma de decisiones
        self.move_accumulator += dt
        # La velocidad define cuántas casillas se mueve por segundo. 
        # Convertimos velocidad (1-100) a un ratio de tiempo razonable (ej. vel 100 = 5 casillas/seg max, vel 1 = 0.5 casillas/seg)
        move_cooldown = max(0.05, 1.0 / (0.1 + (self.speed / 20.0)))

        if self.move_accumulator >= move_cooldown:
            self.move_accumulator = 0.0
            self.decide_and_move(bushes, water_zones, creatures, new_creatures)
            
        return True

    def decide_and_move(self, bushes, water_zones, creatures, new_creatures):
        # Si está sobre agua y tiene sed < 30 (o simplemente está recargando en agua)
        if (self.x, self.y) in water_zones and self.thirst < 100:
            self.thirst = min(100.0, self.thirst + 10.0) # 10 puntos por acción/segundo aprox
            return

        # Si está sobre un arbusto con manzanas y tiene hambre < 30
        for bush in bushes:
            if bush.x == self.x and bush.y == self.y and bush.apples > 0 and self.hunger < 30:
                bush.apples -= 1
                if bush.apples == 0:
                    bush.cooldown = 10.0 # 10 segundos de espera
                self.hunger = 100.0
                return

        # Lógica de búsqueda basada en visión
        target = None
        
        # 1. Buscar AGUA si la sed es crítica (< 30)
        if self.thirst < 30:
            target = self.find_nearest_tile(water_zones)
            
        # 2. Buscar COMIDA si el hambre es crítica (< 30) y no priorizó agua
        if not target and self.hunger < 30:
            available_bushes = [(b.x, b.y) for b in bushes if b.apples > 0]
            target = self.find_nearest_tile(available_bushes)

        # 3. APAREAMIENTO: Si hambre y sed están a 100
        if not target and self.hunger >= 100 and self.thirst >= 100:
            for c in creatures:
                if c != self and c.hunger >= 100 and c.thirst >= 100 and c.gender != self.gender:
                    # Verificar si está en rango de visión
                    if math.hypot(c.x - self.x, c.y - self.y) <= self.vision:
                        target = (c.x, c.y)
                        # Si están en la misma casilla o adyacente, intentar reproducirse
                        if abs(c.x - self.x) <= 1 and abs(c.y - self.y) <= 1:
                            if random.randint(1, 10) == 1: # 1 entre 10 posibilidades
                                num_children = abs(self.mating - c.mating)
                                # Limitar hijos para no romper el juego inmediatamente
                                num_children = min(num_children, 5) 
                                for _ in range(num_children):
                                    new_creatures.append(Creature(self.x, self.y))
                                # Consumir un poco de energía tras reproducirse
                                self.hunger, self.thirst = 90, 90 
                        break

        # Moverse hacia el objetivo encontrado dentro del rango de visión
        if target:
            tx, ty = target
            # Caminar en dirección al target (1 casilla por paso)
            dx = 1 if tx > self.x else -1 if tx < self.x else 0
            dy = 1 if ty > self.y else -1 if ty < self.y else 0
            self.x = max(0, min(COLS - 1, self.x + dx))
            self.y = max(0, min(ROWS - 1, self.y + dy))
        else:
            # Movimiento aleatorio si no ve nada o no tiene necesidades urgentes
            self.x = max(0, min(COLS - 1, self.x + random.choice([-1, 0, 1])))
            self.y = max(0, min(ROWS - 1, self.y + random.choice([-1, 0, 1])))

    def find_nearest_tile(self, tiles_list):
        nearest = None
        min_dist = float('inf')
        for tx, ty in tiles_list:
            dist = math.hypot(tx - self.x, ty - self.y)
            if dist <= self.vision and dist < min_dist:
                min_dist = dist
                nearest = (tx, ty)
        return nearest

    def draw(self, surface, is_selected):
        px = self.x * GRID_SIZE + GRID_SIZE // 2
        py = self.y * GRID_SIZE + GRID_SIZE // 2
        color = COLOR_MALE if self.gender == "Macho" else COLOR_FEMALE
        pygame.draw.circle(surface, color, (px, py), 7)
        if is_selected:
            pygame.draw.circle(surface, (255, 255, 255), (px, py), 9, 1)


# --- SISTEMA DE SIMULACIÓN ---
class Simulation:
    def __init__(self):
        self.creatures = []
        self.bushes = []
        self.water_zones = set()
        self.generate_map()
        self.adjust_creatures(20) # Cantidad inicial estándar

    def generate_map(self):
        # Crear una zona de agua (un lago en el medio/derecha)
        water_center_x, water_center_y = COLS // 2, ROWS // 2
        for x in range(COLS):
            for y in range(ROWS):
                if math.hypot(x - water_center_x, y - water_center_y) < 6:
                    self.water_zones.add((x, y))

        # Añadir algunos arbustos iniciales
        for _ in range(15):
            bx, by = random.randint(0, COLS-1), random.randint(0, ROWS-1)
            if (bx, by) not in self.water_zones:
                self.bushes.append(Bush(bx, by))

    def adjust_creatures(self, target_count):
        target_count = max(1, min(1000, target_count))
        while len(self.creatures) < target_count:
            x, y = random.randint(0, COLS-1), random.randint(0, ROWS-1)
            self.creatures.append(Creature(x, y))
        while len(self.creatures) > target_count:
            self.creatures.pop()

    def update(self, dt):
        new_creatures = []
        # Filtrar las criaturas que sobreviven
        self.creatures = [c for c in self.creatures if c.update(dt, self.bushes, self.water_zones, self.creatures, new_creatures)]
        self.creatures.extend(new_creatures)
        
        # Limitar el máximo por rendimiento
        if len(self.creatures) > 1000:
            self.creatures = self.creatures[:1000]

        for bush in self.bushes:
            bush.update(dt)

    def draw_background(self, surface):
        surface.fill(COLOR_BG)
        
        # Dibujo sutil de pasto (pequeñas líneas aleatorias fijas basadas en la cuadrícula)
        random.seed(42) # Semilla fija para que el dibujo no parpadee
        for x in range(COLS):
            for y in range(ROWS):
                if (x, y) not in self.water_zones:
                    if random.random() < 0.15: # 15% de probabilidad de tener pasto visual
                        px = x * GRID_SIZE + 5
                        py = y * GRID_SIZE + 5
                        pygame.draw.line(surface, COLOR_GRASS, (px, py), (px + 3, py - 3), 1)
        
        # Dibujar Agua
        for x, y in self.water_zones:
            pygame.draw.rect(surface, COLOR_WATER, (x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE))

        # Dibujar líneas de cuadrícula si está activo
        if show_grid:
            for x in range(0, WIDTH, GRID_SIZE):
                pygame.draw.line(surface, COLOR_GRID, (x, 0), (x, HEIGHT))
            for y in range(0, HEIGHT, GRID_SIZE):
                pygame.draw.line(surface, COLOR_GRID, (0, y), (WIDTH, y))


# --- INTERFAZ DE USUARIO (UI) ---
def draw_ui(surface, sim):
    # MENÚ OPCIONES (Arriba Izquierda) - Botón 'O'
    if show_menu:
        menu_rect = pygame.Rect(10, 10, 220, 160)
        # Dibujar fondo semi-transparente
        bg_surface = pygame.Surface((menu_rect.width, menu_rect.height), pygame.SRCALPHA)
        bg_surface.fill(COLOR_MENU_BG)
        surface.blit(bg_surface, (menu_rect.x, menu_rect.y))
        pygame.draw.rect(surface, (255, 255, 255), menu_rect, 1)

        # Textos y Botones conceptuales del menú
        surface.blit(FONT_BOLD.render("MENÚ OPCIONES", True, COLOR_TEXT), (20, 20))
        surface.blit(FONT.render(f"Criaturas: {len(sim.creatures)}", True, COLOR_TEXT), (20, 45))
        surface.blit(FONT.render("[1] +100 | [2] -100 | [3] Set a 500", True, (200, 200, 200)), (20, 65))
        
        pygame.draw.rect(surface, (50, 100, 50), (20, 95, 190, 25))
        surface.blit(FONT.render("[A] Añadir Arbusto Manzanas", True, COLOR_TEXT), (25, 100))
        
        surface.blit(FONT.render("Mín: 1 | Máx: 1000", True, (150, 150, 150)), (20, 135))

    # DETALLES DE CRIATURA (Abajo Izquierda) - Clic en criatura
    if selected_creature:
        # Verificar si sigue viva
        if selected_creature in sim.creatures:
            panel_rect = pygame.Rect(10, HEIGHT - 150, 250, 140)
            bg_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            bg_surface.fill(COLOR_MENU_BG)
            surface.blit(bg_surface, (panel_rect.x, panel_rect.y))
            pygame.draw.rect(surface, (255, 255, 255), panel_rect, 1)

            c = selected_creature
            surface.blit(FONT_BOLD.render(f"Nombre: {c.name}", True, COLOR_TEXT), (20, HEIGHT - 140))
            surface.blit(FONT.render(f"Género: {c.gender}", True, COLOR_TEXT), (20, HEIGHT - 120))
            surface.blit(FONT.render(f"Hambre: {int(c.hunger)}/100", True, COLOR_TEXT), (20, HEIGHT - 105))
            surface.blit(FONT.render(f"Sed: {int(c.thirst)}/100", True, COLOR_TEXT), (20, HEIGHT - 90))
            surface.blit(FONT.render(f"Velocidad: {c.speed}", True, COLOR_TEXT), (20, HEIGHT - 75))
            surface.blit(FONT.render(f"Visión: {c.vision}", True, COLOR_TEXT), (20, HEIGHT - 60))
            surface.blit(FONT.render(f"Apareamiento (Gen): {c.mating}", True, COLOR_TEXT), (20, HEIGHT - 45))
        else:
            selected_creature = None

    # Indicador de pausa
    if paused:
        surface.blit(FONT_BOLD.render("|| PAUSA", True, (255, 50, 50)), (WIDTH - 80, 20))


# --- BUCLE PRINCIPAL DEL JUEGO ---
def main():
    global paused, show_grid, show_menu, selected_creature
    sim = Simulation()

    while True:
        dt = clock.tick(30) / 1000.0 # Delta time en segundos (fijado a 30 FPS para ver mejor el comportamiento)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_c:
                    show_grid = not show_grid
                elif event.key == pygame.K_o:
                    show_menu = not show_menu
                
                # Acciones del menú usando el teclado para facilitar la interacción limpia
                if show_menu:
                    if event.key == pygame.K_1: # Aumentar criaturas
                        sim.adjust_creatures(len(sim.creatures) + 100)
                    elif event.key == pygame.K_2: # Disminuir criaturas
                        sim.adjust_creatures(len(sim.creatures) - 100)
                    elif event.key == pygame.K_3: # Personalizar (Set a valor fijo medio)
                        sim.adjust_creatures(500)
                    elif event.key == pygame.K_a: # Añadir Arbusto en posición aleatoria
                        bx, by = random.randint(0, COLS-1), random.randint(0, ROWS-1)
                        if (bx, by) not in sim.water_zones:
                            sim.bushes.append(Bush(bx, by))

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Clic izquierdo
                    mx, my = pygame.mouse.get_pos()
                    cx, cy = mx // GRID_SIZE, my // GRID_SIZE
                    
                    # Buscar si se hizo clic en una criatura
                    found = False
                    for creature in sim.creatures:
                        if creature.x == cx and creature.y == cy:
                            selected_creature = creature
                            found = True
                            break
                    if not found and not (show_menu and mx < 230 and my < 170):
                        selected_creature = None # Deseleccionar si hace clic fuera

        # Actualización de físicas/lógica
        if not paused:
            sim.update(dt)

        # Renderizado
        sim.draw_background(screen)
        
        for bush in sim.bushes:
            bush.draw(screen)
            
        for creature in sim.creatures:
            creature.draw(screen, creature == selected_creature)

        draw_ui(screen, sim)

        pygame.display.flip()