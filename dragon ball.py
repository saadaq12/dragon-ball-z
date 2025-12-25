import pygame
import sys
import random

# --- INITIERING ---
pygame.init()

WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dragon Ball Python Z - Budokai")

# --- FÄRGER ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (50, 150, 255)
GROUND_COLOR = (139, 69, 19) # Jord/Klippor

# Aura färger
AURA_BASE = (255, 255, 255)  # Vit aura
AURA_SSJ = (255, 215, 0)     # Guld (Super Saiyan)
AURA_EVIL = (200, 0, 200)    # Lila (Frieza)

# --- INSTÄLLNINGAR ---
FPS = 60
GRAVITY = 0.6
FLY_SPEED = 6
WALK_SPEED = 5

# --- KLASSER ---

class Beam:
    def __init__(self, x, y, direction, color, is_ultimate):
        self.direction = direction
        self.color = color
        self.is_ultimate = is_ultimate
        self.timer = 100 # Hur länge den lever
        
        if is_ultimate:
            # En enorm stråle (Kamehameha)
            self.rect = pygame.Rect(x, y - 20, 100, 60) 
            self.speed = 25
            self.damage = 30
        else:
            # Liten Ki-blast
            self.rect = pygame.Rect(x, y, 30, 15)
            self.speed = 12
            self.damage = 5

    def move(self):
        self.rect.x += self.speed * self.direction
        self.timer -= 1
        
        # Ultimates växer när de flyger för effekt
        if self.is_ultimate:
            self.rect.width += 2 # Strålen blir längre

    def draw(self, surface):
        # Rita glödande effekt
        glow_size = 10 if self.is_ultimate else 3
        # Yttre färg
        pygame.draw.rect(surface, self.color, self.rect)
        # Inre vit kärna (för energi-look)
        pygame.draw.rect(surface, WHITE, self.rect.inflate(-glow_size, -glow_size))

class Fighter:
    def __init__(self, x, y, name, controls, stats):
        self.rect = pygame.Rect(x, y, 50, 90)
        self.name = name
        self.controls = controls # [UP, DOWN, LEFT, RIGHT, ATTACK, SPECIAL, CHARGE, TRANSFORM, FLY]
        
        # Hämta stats från menyn (Färger, Attacker)
        self.base_color = stats['color']
        self.hair_color = stats['hair']
        self.beam_color = stats['beam']
        self.aura_color = stats['aura']
        
        # Fysik
        self.vel_y = 0
        self.speed = WALK_SPEED
        self.facing_right = True
        self.is_flying = False # Kan flyga!
        
        # Status
        self.health = 100
        self.ki = 0
        self.max_ki = 100
        self.transformed = False # Super Saiyan?
        self.beaks = [] # Lista för skott
        
        # Cooldowns
        self.attack_cd = 0
        self.transform_cd = 0

    def move(self, keys):
        # Återställ
        dx, dy = 0, 0
        
        # --- RÖRELSE ---
        if keys[self.controls[2]]: # LEFT
            dx = -self.speed
            self.facing_right = False
        if keys[self.controls[3]]: # RIGHT
            dx = self.speed
            self.facing_right = True
            
        # FLYGNING vs GOLV
        if keys[self.controls[8]]: # Toggle Flight Key (Tryck en gång logic hanteras i main loop, detta är state)
             pass 

        if self.is_flying:
            # Fri rörelse i luften
            if keys[self.controls[0]]: dy = -self.speed # UP
            if keys[self.controls[1]]: dy = self.speed  # DOWN
        else:
            # Markbunden
            self.vel_y += GRAVITY
            dy += self.vel_y
            
            # Hoppa
            if keys[self.controls[0]] and self.on_ground:
                self.vel_y = -12
                self.on_ground = False

        # --- SPECIALS ---
        # Ladda Ki
        if keys[self.controls[6]]: 
            if self.ki < self.max_ki:
                self.ki += 1
                # Skapa partikeleffekt genom att rita aura senare

        # Uppdatera position
        self.rect.x += dx
        self.rect.y += dy

        # Kollision med marken
        floor_y = HEIGHT - 100
        self.on_ground = False
        if self.rect.bottom >= floor_y:
            self.rect.bottom = floor_y
            self.vel_y = 0
            self.on_ground = True
            self.is_flying = False # Landar om man nuddar marken

        # Håll inom skärmen
        self.rect.clamp_ip(screen.get_rect())

    def toggle_fly(self):
        # Byt mellan att flyga och falla
        self.is_flying = not self.is_flying
        if self.is_flying:
            self.vel_y = 0 # Stanna i luften direkt

    def transform(self):
        # Man måste ha 50 Ki för att bli Super Saiyan
        if not self.transformed and self.ki >= 50:
            self.transformed = True
            self.ki -= 50
            # Buffa stats
            self.speed = 9 
            self.aura_color = AURA_SSJ
            self.hair_color = AURA_SSJ # Gult hår
            print(f"{self.name} is now SUPER SAIYAN!")
        elif self.transformed:
            # Gå tillbaka till basform
            self.transformed = False
            self.speed = WALK_SPEED
            self.aura_color = stats_db[self.name]['aura']
            self.hair_color = stats_db[self.name]['hair']

    def shoot(self, type="BLAST"):
        dir_mult = 1 if self.facing_right else -1
        
        if type == "BLAST":
            # Vanlig Ki blast (Kostar 5 Ki)
            if self.ki >= 5 and self.attack_cd == 0:
                self.ki -= 5
                start_x = self.rect.right if self.facing_right else self.rect.left
                b = Beam(start_x, self.rect.centery - 10, dir_mult, self.beam_color, False)
                self.beaks.append(b)
                self.attack_cd = 15

        elif type == "ULTIMATE":
            # Kamehameha (Kostar 40 Ki)
            if self.ki >= 40 and self.attack_cd == 0:
                self.ki -= 40
                start_x = self.rect.right if self.facing_right else self.rect.left - 50
                b = Beam(start_x, self.rect.centery, dir_mult, self.beam_color, True)
                self.beaks.append(b)
                self.attack_cd = 60

    def update(self, target):
        if self.attack_cd > 0: self.attack_cd -= 1
        
        # Minska Ki långsamt om man är transformerad
        if self.transformed:
            if random.randint(0, 20) == 0: 
                self.ki -= 1
            if self.ki <= 0: # Slut på energi -> Detransformera
                self.transform()

        # Hantera skott
        for b in self.beaks[:]:
            b.move()
            
            # Träff?
            if b.rect.colliderect(target.rect):
                target.health -= b.damage
                self.beaks.remove(b)
                continue
            
            # Utanför skärm?
            if b.rect.x < -200 or b.rect.x > WIDTH + 200:
                self.beaks.remove(b)

    def draw(self, surface):
        # 1. RITA AURA (Om man flyger, laddar eller är SSJ)
        keys = pygame.key.get_pressed()
        charging = keys[self.controls[6]]
        
        if self.is_flying or self.transformed or charging:
            aura_rect = self.rect.inflate(30, 30)
            offset = random.randint(-2, 2)
            pygame.draw.ellipse(surface, self.aura_color, (aura_rect.x + offset, aura_rect.y + offset, aura_rect.width, aura_rect.height), 3)

        # 2. RITA GUBBEN (Kropp)
        pygame.draw.rect(surface, self.base_color, self.rect)
        
        # 3. RITA HUVUD
        head_rect = pygame.Rect(self.rect.centerx - 15, self.rect.top - 25, 30, 30)
        pygame.draw.circle(surface, (255, 200, 150), head_rect.center, 15) # Hudfärg

        # 4. RITA HÅR (Viktigt för DBZ-look!)
        # Om transformed = Håret står upp och är gult
        hair_y_offset = -35 if self.transformed else -25
        hair_poly = [
            (head_rect.left, head_rect.top + 5),
            (head_rect.centerx, head_rect.top + hair_y_offset - 10), # Toppen
            (head_rect.right, head_rect.top + 5)
        ]
        pygame.draw.polygon(surface, self.hair_color, hair_poly)

        # 5. RITA STRÅLAR
        for b in self.beaks:
            b.draw(surface)

        # 6. UI (HP och Ki)
        pygame.draw.rect(surface, (50, 0, 0), (self.rect.x, self.rect.y - 30, 50, 5))
        pygame.draw.rect(surface, (0, 255, 0), (self.rect.x, self.rect.y - 30, 50 * (self.health/100), 5))
        
        pygame.draw.rect(surface, (20, 20, 20), (self.rect.x, self.rect.y - 20, 50, 5))
        pygame.draw.rect(surface, (255, 255, 0), (self.rect.x, self.rect.y - 20, 50 * (self.ki/100), 5))

# --- DATA FÖR KARAKTÄRER ---
stats_db = {
    "Goku":    {"color": (255, 140, 0), "hair": (0, 0, 0),    "beam": (0, 255, 255), "aura": (255, 255, 255)}, # Orange dräkt, Svart hår, Blå stråle
    "Vegeta":  {"color": (0, 0, 150),   "hair": (0, 0, 0),    "beam": (255, 255, 0), "aura": (255, 255, 255)}, # Blå dräkt, Gul stråle (Final Flash)
    "Piccolo": {"color": (128, 0, 128), "hair": (255, 255, 255),"beam": (50, 205, 50), "aura": (255, 255, 255)}, # Lila dräkt, Grön stråle
    "Frieza":  {"color": (240, 240, 240),"hair": (200, 0, 200),"beam": (139, 0, 139), "aura": (200, 0, 200)}, # Vit kropp, Lila huvud, Lila stråle
}

font = pygame.font.SysFont(None, 40)

def draw_text(text, x, y, color=WHITE):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))

# --- MENY SYSTEM ---
def char_select_menu():
    selected = [None, None] # P1 val, P2 val
    chars = ["Goku", "Vegeta", "Piccolo", "Frieza"]
    
    current_picker = 0 # 0 = P1 väljer, 1 = P2 väljer
    
    while True:
        screen.fill(BLACK)
        draw_text("SELECT YOUR FIGHTER", WIDTH//2 - 150, 50, (255, 215, 0))
        
        for i, name in enumerate(chars):
            col = stats_db[name]['color']
            # Rita en enkel box för varje gubbe
            rect = pygame.Rect(150 + i*200, 200, 100, 150)
            pygame.draw.rect(screen, col, rect)
            draw_text(name, 160 + i*200, 360)
            
            # Rita tangent-guide
            key_num = i + 1
            draw_text(f"[{key_num}]", 180 + i*200, 160, WHITE)

        if current_picker == 0:
            draw_text("PLAYER 1: Välj med 1-4", WIDTH//2 - 150, 500, (50, 150, 255))
        else:
            draw_text(f"P1 Valde: {selected[0]}", WIDTH//2 - 300, 450, (50, 150, 255))
            draw_text("PLAYER 2: Välj med 1-4", WIDTH//2 - 150, 500, (255, 50, 50))

        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                idx = -1
                if event.key == pygame.K_1: idx = 0
                if event.key == pygame.K_2: idx = 1
                if event.key == pygame.K_3: idx = 2
                if event.key == pygame.K_4: idx = 3
                
                if idx != -1:
                    selected[current_picker] = chars[idx]
                    current_picker += 1
                    if current_picker > 1:
                        return selected[0], selected[1] # Starta spelet!

# --- MAIN LOOP ---

# Kör menyn först
p1_name, p2_name = char_select_menu()

# Kontroller: [UP, DOWN, LEFT, RIGHT, ATTACK(Blast), SPECIAL(Ult), CHARGE, TRANSFORM, FLY]
c_p1 = [pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_f, pygame.K_g, pygame.K_c, pygame.K_t, pygame.K_SPACE]
c_p2 = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP0, pygame.K_RSHIFT]
# P2 ALTERNATIV (Om man inte har Numpad): O, L, K, M

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
        
        if not winner:
            if event.type == pygame.KEYDOWN:
                # P1 Actions
                if event.key == p1.controls[4]: p1.shoot("BLAST")
                if event.key == p1.controls[5]: p1.shoot("ULTIMATE")
                if event.key == p1.controls[7]: p1.transform()
                if event.key == p1.controls[8]: p1.toggle_fly()
                
                # P2 Actions
                if event.key == p2.controls[4]: p2.shoot("BLAST")
                if event.key == p2.controls[5]: p2.shoot("ULTIMATE")
                if event.key == p2.controls[7]: p2.transform()
                if event.key == p2.controls[8]: p2.toggle_fly()
                
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r and winner:
                # Enkel omstart behövs egentligen en loop, men vi gör en snabb återställning här
                p1.health = 100; p2.health = 100; p1.ki = 0; p2.ki = 0
                p1.rect.x = 100; p2.rect.x = 800
                winner = None

    if not winner:
        keys = pygame.key.get_pressed()
        p1.move(keys)
        p2.move(keys)
        p1.update(p2)
        p2.update(p1)
        
        if p1.health <= 0: winner = f"{p2.name} WINS!"
        if p2.health <= 0: winner = f"{p1.name} WINS!"

    # --- RITA VÄRLDEN ---
    screen.fill(SKY_BLUE)
    # Rita berg i bakgrunden
    pygame.draw.polygon(screen, (100, 100, 100), [(100, 600), (300, 300), (500, 600)])
    pygame.draw.polygon(screen, (120, 120, 120), [(400, 600), (700, 200), (900, 600)])
    # Marken
    pygame.draw.rect(screen, GROUND_COLOR, (0, HEIGHT - 100, WIDTH, 100))

    p1.draw(screen)
    p2.draw(screen)
    
    if winner:
        draw_text(winner, WIDTH//2 - 100, HEIGHT//2, (255, 0, 0))
        draw_text("Tryck R för omstart", WIDTH//2 - 120, HEIGHT//2 + 50, WHITE)
    
    # Instruktioner
    draw_text(f"{p1.name}: WASD | Fly: Space | Charge: C | Trans: T | Blast: F/G", 20, 20, WHITE)
    draw_text(f"{p2.name}: Arrows | Fly: Shift | Charge: 3 | Trans: 0 | Blast: 1/2", 20, 50, WHITE)

    pygame.display.flip()

pygame.quit()
sys.exit()