import pygame
import sys
import random

# --- INITIERING ---
pygame.init()

WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dragon Ball Python Z - Realistic Edition")

# --- FÄRGER ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (60, 160, 255)
GROUND_COLOR = (139, 69, 19) # Jord
GRASS_COLOR = (34, 139, 34) # Gräs på toppen

# Aura färger
AURA_BASE = (255, 255, 255)
AURA_SSJ = (255, 215, 0)    
AURA_EVIL = (200, 0, 200)   
BELT_COLOR = (20, 20, 100) # Mörkblått bälte för de flesta

# --- INSTÄLLNINGAR ---
FPS = 60
GRAVITY = 0.6
FLY_SPEED = 6
WALK_SPEED = 5

# --- DATA FÖR KARAKTÄRER (NU MED HUDFÄRG) ---
stats_db = {
    "Goku":    {"color": (255, 90, 0), "skin": (255, 200, 150), "hair": (0, 0, 0), "beam": (0, 255, 255), "aura": AURA_BASE}, 
    "Vegeta":  {"color": (0, 0, 150),  "skin": (255, 200, 150), "hair": (0, 0, 0), "beam": (255, 255, 0), "aura": AURA_BASE}, 
    "Piccolo": {"color": (100, 0, 100),"skin": (100, 200, 100), "hair": (255, 255, 255),"beam": (50, 205, 50), "aura": AURA_BASE}, 
    "Frieza":  {"color": (240, 240, 240),"skin": (200, 180, 220), "hair": (139, 0, 139),"beam": (139, 0, 139), "aura": AURA_EVIL}, 
}

# --- KLASSER ---

class Beam:
    def __init__(self, x, y, direction, color, is_ultimate):
        self.direction = direction
        self.color = color
        self.is_ultimate = is_ultimate
        self.timer = 100 
        
        if is_ultimate:
            self.rect = pygame.Rect(x, y - 20, 80, 60) 
            self.speed = 25
            self.damage = 30
        else:
            self.rect = pygame.Rect(x, y, 30, 15)
            self.speed = 12
            self.damage = 5

    def move(self):
        self.rect.x += self.speed * self.direction
        self.timer -= 1
        if self.is_ultimate and self.timer > 80:
             self.rect.width += 5 # Växer snabbt i början

    def draw(self, surface):
        glow_size = 10 if self.is_ultimate else 3
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect.inflate(-glow_size, -glow_size))

class Fighter:
    def __init__(self, x, y, name, controls, stats):
        self.rect = pygame.Rect(x, y, 50, 90) # Hitboxen är fortfarande en enkel rektangel
        self.name = name
        self.controls = controls 
        
        # Stats
        self.gi_color = stats['color'] # Klädfärg
        self.skin_color = stats['skin'] # Hudfärg
        self.hair_base_color = stats['hair']
        self.hair_color = self.hair_base_color
        self.beam_color = stats['beam']
        self.aura_base_color = stats['aura']
        self.aura_color = self.aura_base_color
        
        # Fysik & Status
        self.vel_y = 0
        self.speed = WALK_SPEED
        self.facing_right = True
        self.is_flying = False
        self.on_ground = False
        self.health = 100
        self.ki = 0
        self.max_ki = 100
        self.transformed = False
        self.beaks = [] 
        self.attack_cd = 0
        self.is_shooting_ult = False # För pose

    def move(self, keys):
        dx, dy = 0, 0
        # RÖRELSE
        if keys[self.controls[2]]: dx = -self.speed; self.facing_right = False
        if keys[self.controls[3]]: dx = self.speed; self.facing_right = True
            
        # FLYGNING
        if self.is_flying:
            if keys[self.controls[0]]: dy = -self.speed
            if keys[self.controls[1]]: dy = self.speed 
        else:
            self.vel_y += GRAVITY
            dy += self.vel_y
            if keys[self.controls[0]] and self.on_ground:
                self.vel_y = -12
                self.on_ground = False

        # LADDA KI
        if keys[self.controls[6]]: 
            if self.ki < self.max_ki: self.ki += 1

        self.rect.x += dx
        self.rect.y += dy

        floor_y = HEIGHT - 100
        self.on_ground = False
        if self.rect.bottom >= floor_y:
            self.rect.bottom = floor_y
            self.vel_y = 0
            self.on_ground = True
            self.is_flying = False

        self.rect.clamp_ip(screen.get_rect())

    def toggle_fly(self):
        self.is_flying = not self.is_flying
        if self.is_flying: self.vel_y = 0

    def transform(self):
        if not self.transformed and self.ki >= 50:
            self.transformed = True
            self.ki -= 50
            self.speed = 9 
            self.aura_color = AURA_SSJ
            self.hair_color = AURA_SSJ # Gult hår
        elif self.transformed:
            self.transformed = False
            self.speed = WALK_SPEED
            self.aura_color = self.aura_base_color
            self.hair_color = self.hair_base_color

    def shoot(self, type="BLAST"):
        dir_mult = 1 if self.facing_right else -1
        start_x = self.rect.right if self.facing_right else self.rect.left
        
        if type == "BLAST":
            if self.ki >= 5 and self.attack_cd == 0:
                self.ki -= 5
                self.beaks.append(Beam(start_x, self.rect.centery - 10, dir_mult, self.beam_color, False))
                self.attack_cd = 15
        elif type == "ULTIMATE":
            if self.ki >= 40 and self.attack_cd == 0:
                self.ki -= 40
                start_x = self.rect.right if self.facing_right else self.rect.left - 80
                self.beaks.append(Beam(start_x, self.rect.centery, dir_mult, self.beam_color, True))
                self.attack_cd = 60
                self.is_shooting_ult = True # Aktivera skjut-pose

    def update(self, target):
        if self.attack_cd > 0: 
            self.attack_cd -= 1
        else:
            self.is_shooting_ult = False # Återställ pose när cooldown är klar

        if self.transformed:
            if random.randint(0, 30) == 0: self.ki -= 1
            if self.ki <= 0: self.transform()

        for b in self.beaks[:]:
            b.move()
            if b.rect.colliderect(target.rect):
                target.health -= b.damage
                self.beaks.remove(b)
                continue
            if b.rect.x < -200 or b.rect.x > WIDTH + 200:
                self.beaks.remove(b)

    # --- DEN NYA REALISTISKA RIT-FUNKTIONEN ---
    def draw(self, surface):
        rx, ry = self.rect.x, self.rect.y
        rw, rh = self.rect.width, self.rect.height

        # 1. AURA (Bakom allt)
        keys = pygame.key.get_pressed()
        charging = keys[self.controls[6]]
        if self.is_flying or self.transformed or charging:
            aura_rect = self.rect.inflate(30, 30)
            off = random.randint(-2, 2)
            pygame.draw.ellipse(surface, self.aura_color, (aura_rect.x + off, aura_rect.y + off, aura_rect.width, aura_rect.height), 4)

        # --- KROPPSDELAR ---
        
        # BEN & FÖTTER
        leg_w = 18
        foot_h = 8
        # Vänster ben (bakre)
        pygame.draw.rect(surface, self.gi_color, (rx + 5, ry + rh//2, leg_w, rh//2 - foot_h))
        pygame.draw.rect(surface, self.skin_color, (rx + 3, ry + rh - foot_h, leg_w+4, foot_h)) # Fot
        
        # Höger ben (främre)
        pygame.draw.rect(surface, self.gi_color, (rx + rw - leg_w - 5, ry + rh//2, leg_w, rh//2 - foot_h))
        pygame.draw.rect(surface, self.skin_color, (rx + rw - leg_w - 7, ry + rh - foot_h, leg_w+4, foot_h)) # Fot

        # BÅL (Torso) & BÄLTE
        torso_h = 40
        pygame.draw.rect(surface, self.gi_color, (rx, ry + 20, rw, torso_h)) # Tröja
        pygame.draw.rect(surface, BELT_COLOR, (rx, ry + 20 + torso_h - 5, rw, 5)) # Bälte

        # ARMAR & HÄNDER
        arm_w = 14
        hand_size = 9
        
        # Bestäm arm-position (lyft om man skjuter ultimate)
        arm_start_y = ry + 22
        arm_end_y = ry + 20 + torso_h - 5
        if self.is_shooting_ult:
            arm_end_y = ry + 30 # Armarna pekar framåt/uppåt

        # Bakre arm (Vänster om facing right)
        back_arm_x = rx - arm_w + 5 if self.facing_right else rx + rw - 5
        pygame.draw.rect(surface, self.gi_color, (back_arm_x, arm_start_y, arm_w, arm_end_y - arm_start_y))
        pygame.draw.circle(surface, self.skin_color, (back_arm_x + arm_w//2, arm_end_y + hand_size//2), hand_size)

        # Främre arm (Höger om facing right)
        front_arm_x = rx + rw - 5 if self.facing_right else rx - arm_w + 5
        pygame.draw.rect(surface, self.gi_color, (front_arm_x, arm_start_y, arm_w, arm_end_y - arm_start_y))
        pygame.draw.circle(surface, self.skin_color, (front_arm_x + arm_w//2, arm_end_y + hand_size//2), hand_size)

        # HUVUD & ANSIKTE
        head_center = (rx + rw//2, ry + 15)
        pygame.draw.circle(surface, self.skin_color, head_center, 18) # Huvudform
        
        # Ögon (enkla streck för riktning)
        eye_x_off = 5 if self.facing_right else -5
        pygame.draw.rect(surface, BLACK, (head_center[0] + eye_x_off, head_center[1] - 2, 6, 3))

        # HÅR (Ovanpå huvudet)
        hair_y_peak = ry - 15 if self.transformed else ry - 5
        hair_poly = [
            (rx + 5, ry + 10), # Vänster bas
            (rx + rw//2, hair_y_peak), # Toppen
            (rx + rw - 5, ry + 10)  # Höger bas
        ]
        pygame.draw.polygon(surface, self.hair_color, hair_poly)

        # --- Slut på kroppsdelar ---

        # STRÅLAR
        for b in self.beaks: b.draw(surface)

        # UI (HP och Ki)
        pygame.draw.rect(surface, (50, 0, 0), (rx, ry - 30, 50, 5))
        pygame.draw.rect(surface, (0, 255, 0), (rx, ry - 30, 50 * (self.health/100), 5))
        pygame.draw.rect(surface, (20, 20, 20), (rx, ry - 20, 50, 5))
        pygame.draw.rect(surface, (255, 255, 0), (rx, ry - 20, 50 * (self.ki/100), 5))

font = pygame.font.SysFont(None, 40)
def draw_text(text, x, y, color=WHITE):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))

# --- MENY ---
def char_select_menu():
    selected = [None, None]
    chars = ["Goku", "Vegeta", "Piccolo", "Frieza"]
    current_picker = 0
    while True:
        screen.fill(BLACK)
        draw_text("SELECT YOUR FIGHTER - REALISTIC EDITION", WIDTH//2 - 250, 50, (255, 215, 0))
        for i, name in enumerate(chars):
            stats = stats_db[name]
            # Rita en "preview" av gubben i menyn
            preview_rect = pygame.Rect(180 + i*200, 200, 50, 90)
            # Kropp
            pygame.draw.rect(screen, stats['color'], (preview_rect.x, preview_rect.y+20, 50, 40))
            # Huvud
            pygame.draw.circle(screen, stats['skin'], (preview_rect.centerx, preview_rect.y+15), 18)
            # Hår
            pygame.draw.polygon(screen, stats['hair'], [(preview_rect.x+5, preview_rect.y+10), (preview_rect.centerx, preview_rect.y-5), (preview_rect.right-5, preview_rect.y+10)])
            
            draw_text(name, 170 + i*200, 320)
            draw_text(f"[{i+1}]", 195 + i*200, 160, WHITE)

        if current_picker == 0: draw_text("PLAYER 1: Välj med 1-4", WIDTH//2 - 150, 500, SKY_BLUE)
        else: draw_text(f"P1 Valde: {selected[0]}", WIDTH//2 - 300, 450, SKY_BLUE); draw_text("PLAYER 2: Välj med 1-4", WIDTH//2 - 150, 500, (255, 50, 50))
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                idx = -1
                if event.key == pygame.K_1: idx = 0
                if event.key == pygame.K_2: idx = 1
                if event.key == pygame.K_3: idx = 2
                if event.key == pygame.K_4: idx = 3
                if idx != -1:
                    selected[current_picker] = chars[idx]
                    current_picker += 1
                    if current_picker > 1: return selected[0], selected[1]

# --- MAIN LOOP ---
p1_name, p2_name = char_select_menu()

c_p1 = [pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_f, pygame.K_g, pygame.K_c, pygame.K_t, pygame.K_SPACE]
c_p2 = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP0, pygame.K_RSHIFT]

p1 = Fighter(100, 400, p1_name, c_p1, stats_db[p1_name])
p2 = Fighter(800, 400, p2_name, c_p2, stats_db[p2_name])
p2.facing_right = False

clock = pygame.time.Clock()
running = True
winner = None

while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if not winner and event.type == pygame.KEYDOWN:
            if event.key == p1.controls[4]: p1.shoot("BLAST")
            if event.key == p1.controls[5]: p1.shoot("ULTIMATE")
            if event.key == p1.controls[7]: p1.transform()
            if event.key == p1.controls[8]: p1.toggle_fly()
            if event.key == p2.controls[4]: p2.shoot("BLAST")
            if event.key == p2.controls[5]: p2.shoot("ULTIMATE")
            if event.key == p2.controls[7]: p2.transform()
            if event.key == p2.controls[8]: p2.toggle_fly()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r and winner:
            p1.health = 100; p2.health = 100; p1.ki = 0; p2.ki = 0
            p1.rect.x = 100; p2.rect.x = 800; winner = None

    if not winner:
        keys = pygame.key.get_pressed()
        p1.move(keys)
        p2.move(keys)
        p1.update(p2)
        p2.update(p1)
        if p1.health <= 0: winner = f"{p2.name} WINS!"
        if p2.health <= 0: winner = f"{p1.name} WINS!"

    # RITA BAKGRUND
    screen.fill(SKY_BLUE)
    pygame.draw.rect(screen, GROUND_COLOR, (0, HEIGHT - 100, WIDTH, 100)) # Jord
    pygame.draw.rect(screen, GRASS_COLOR, (0, HEIGHT - 100, WIDTH, 20))  # Gräskant

    p1.draw(screen)
    p2.draw(screen)
    
    if winner:
        draw_text(winner, WIDTH//2 - 100, HEIGHT//2, (255, 0, 0))
        draw_text("Tryck R för omstart", WIDTH//2 - 120, HEIGHT//2 + 50, WHITE)
    
    draw_text(f"{p1.name} (P1)", 20, 20, WHITE)
    draw_text(f"{p2.name} (P2)", WIDTH - 150, 20, WHITE)

    pygame.display.flip()

pygame.quit()
sys.exit()