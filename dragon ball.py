import pygame
import sys
import random
import math

# --- INITIERING ---
pygame.init()

WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DBZ Python - Tournament Edition (PvP & PvCPU)")

# --- FÄRGER ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (60, 160, 255)
GROUND_COLOR = (160, 82, 45) # Sienna/Jord
GRASS_COLOR = (34, 139, 34)

# Aura färger
AURA_BASE = (200, 200, 255) # Vit/Blåaktig
AURA_SSJ = (255, 215, 0)    # Guld
AURA_EVIL = (200, 50, 200)  # Lila

# --- INSTÄLLNINGAR ---
FPS = 60
GRAVITY = 0.5
FLY_SPEED = 6
WALK_SPEED = 5

# --- DATA FÖR KARAKTÄRER ---
# Vi lägger till specifika detaljer för varje gubbe
stats_db = {
    "Goku":    {"skin": (255, 200, 150), "hair": (0, 0, 0),     "beam": (0, 255, 255), "aura": AURA_BASE}, 
    "Vegeta":  {"skin": (255, 200, 150), "hair": (0, 0, 0),     "beam": (255, 255, 0), "aura": AURA_BASE}, 
    "Piccolo": {"skin": (100, 200, 100), "hair": (255, 255, 255),"beam": (50, 205, 50), "aura": AURA_BASE}, 
    "Frieza":  {"skin": (240, 240, 240), "hair": (139, 0, 139), "beam": (139, 0, 139), "aura": AURA_EVIL}, 
}

# --- KLASSER ---

class Beam:
    def __init__(self, x, y, direction, color, is_ultimate):
        self.direction = direction
        self.color = color
        self.is_ultimate = is_ultimate
        self.timer = 100 
        
        if is_ultimate:
            self.rect = pygame.Rect(x, y - 25, 80, 70) 
            self.speed = 25
            self.damage = 1.0 # Skada per frame
        else:
            self.rect = pygame.Rect(x, y, 30, 20)
            self.speed = 15
            self.damage = 10 # Engångsskada

    def move(self):
        self.rect.x += self.speed * self.direction
        self.timer -= 1
        # Ultimate växer
        if self.is_ultimate and self.timer > 80:
             self.rect.width += 10 

    def draw(self, surface):
        glow = 10 if self.is_ultimate else 4
        # Yttre energi
        pygame.draw.ellipse(surface, self.color, self.rect)
        # Inre kärna
        core_rect = self.rect.inflate(-glow, -glow)
        pygame.draw.ellipse(surface, WHITE, core_rect)

class Fighter:
    def __init__(self, x, y, name, controls, stats):
        self.rect = pygame.Rect(x, y, 50, 90)
        self.name = name
        self.controls = controls # Om None = CPU
        self.is_cpu = (controls is None)
        
        self.skin_color = stats['skin']
        self.hair_base = stats['hair']
        self.hair_color = self.hair_base
        self.beam_color = stats['beam']
        self.aura_color = stats['aura']
        
        # Fysik
        self.vel_y = 0
        self.speed = WALK_SPEED
        self.facing_right = True
        self.is_flying = False
        self.on_ground = False
        
        # Stats
        self.health = 100
        self.ki = 0
        self.max_ki = 100
        self.transformed = False
        self.beaks = [] 
        self.attack_cd = 0
        self.pose_timer = 0 # För att hålla en pose när man skjuter

        # AI Variabler
        self.ai_timer = 0
        self.ai_action = "IDLE"

    def move(self, keys, target):
        dx, dy = 0, 0
        charge_key = False
        
        if not self.is_cpu:
            # --- MÄNSKLIG SPELARE ---
            if keys[self.controls[2]]: dx = -self.speed; self.facing_right = False
            if keys[self.controls[3]]: dx = self.speed; self.facing_right = True
            
            if self.is_flying:
                if keys[self.controls[0]]: dy = -self.speed
                if keys[self.controls[1]]: dy = self.speed 
            else:
                self.vel_y += GRAVITY
                dy += self.vel_y
                if keys[self.controls[0]] and self.on_ground:
                    self.vel_y = -12
                    self.on_ground = False
            
            charge_key = keys[self.controls[6]]
            
        else:
            # --- DATOR (AI) ---
            dx, dy, charge_key = self.ai_logic(target)

        # LADDA KI
        if charge_key: 
            if self.ki < self.max_ki: self.ki += 0.8 # Ladda lite långsammare

        # Uppdatera position
        self.rect.x += dx
        self.rect.y += dy

        # Mark-kollision
        floor_y = HEIGHT - 100
        self.on_ground = False
        if self.rect.bottom >= floor_y:
            self.rect.bottom = floor_y
            self.vel_y = 0
            self.on_ground = True
            self.is_flying = False # Landar automatiskt

        self.rect.clamp_ip(screen.get_rect())

    def ai_logic(self, target):
        # Enkel AI som försöker slåss
        dx, dy = 0, 0
        charge = False
        
        dist_x = target.rect.centerx - self.rect.centerx
        dist_y = target.rect.centery - self.rect.centery
        
        self.ai_timer -= 1
        
        # Byt beslut var 20:e frame (så den inte hackar)
        if self.ai_timer <= 0:
            self.ai_timer = 20
            
            # 1. Om låg HP och mycket Ki -> Transformera!
            if self.health < 50 and self.ki > 50 and not self.transformed:
                self.transform()
            
            # 2. Om låg Ki -> Flyg bort och Ladda
            if self.ki < 20:
                self.ai_action = "CHARGE"
            # 3. Om bra Ki och i linje -> Skjut!
            elif abs(dist_y) < 50 and self.ki > 40:
                self.ai_action = "ATTACK"
            # 4. Annars -> Jaga
            else:
                self.ai_action = "CHASE"

        # UTFÖR BESLUT
        if dist_x > 0: self.facing_right = True
        else: self.facing_right = False

        if self.ai_action == "CHARGE":
            # Flyg bort från spelaren
            if dist_x > 0: dx = -self.speed 
            else: dx = self.speed
            charge = True
            
        elif self.ai_action == "CHASE":
            # Gå mot spelaren
            if abs(dist_x) > 200: # Gå närmare
                if dist_x > 0: dx = self.speed
                else: dx = -self.speed
            
            # Matcha höjd (Flyg om spelaren flyger)
            if dist_y < -50: # Spelaren är ovanför
                if not self.is_flying: self.toggle_fly()
                dy = -self.speed
            elif dist_y > 50: # Spelaren är under
                dy = self.speed
            
        elif self.ai_action == "ATTACK":
            # Försök skjuta Ultimate eller Blast
            if self.ki >= 40 and random.randint(0, 10) > 8:
                self.shoot("ULTIMATE")
            else:
                self.shoot("BLAST")

        if not self.is_flying:
            self.vel_y += GRAVITY
            dy += self.vel_y

        return dx, dy, charge

    def toggle_fly(self):
        self.is_flying = not self.is_flying
        if self.is_flying: self.vel_y = 0

    def transform(self):
        if not self.transformed and self.ki >= 50:
            self.transformed = True
            self.ki -= 50
            self.speed = 8
            self.hair_color = AURA_SSJ # Gult hår
            # Frieza blir guld, Piccolo får ljusare aura etc
            if self.name == "Frieza": self.skin_color = (255, 215, 0) 
        elif self.transformed:
            # Detransformera
            self.transformed = False
            self.speed = WALK_SPEED
            self.hair_color = self.hair_base
            if self.name == "Frieza": self.skin_color = stats_db["Frieza"]["skin"]

    def shoot(self, type="BLAST"):
        dir_mult = 1 if self.facing_right else -1
        start_x = self.rect.right if self.facing_right else self.rect.left
        
        if type == "BLAST":
            if self.ki >= 5 and self.attack_cd == 0:
                self.ki -= 5
                self.beaks.append(Beam(start_x, self.rect.centery - 10, dir_mult, self.beam_color, False))
                self.attack_cd = 20
                self.pose_timer = 10
        elif type == "ULTIMATE":
            if self.ki >= 40 and self.attack_cd == 0:
                self.ki -= 40
                start_x = self.rect.right if self.facing_right else self.rect.left - 80
                self.beaks.append(Beam(start_x, self.rect.centery, dir_mult, self.beam_color, True))
                self.attack_cd = 80
                self.pose_timer = 40

    def update(self, target):
        if self.attack_cd > 0: self.attack_cd -= 1
        if self.pose_timer > 0: self.pose_timer -= 1
        
        if self.transformed:
            if random.randint(0, 40) == 0: self.ki -= 1
            if self.ki <= 0: self.transform()

        for b in self.beaks[:]:
            b.move()
            if b.rect.colliderect(target.rect):
                target.health -= b.damage
                if not b.is_ultimate: self.beaks.remove(b) # Ultimates går igenom
                continue
            if b.rect.x < -200 or b.rect.x > WIDTH + 200:
                self.beaks.remove(b)

    # --- KARAKTÄRS-SPECIFIK RITNING ---
    def draw(self, surface):
        rx, ry = self.rect.x, self.rect.y
        rw, rh = 50, 90
        
        # 1. AURA
        charging = False
        if not self.is_cpu:
            if pygame.key.get_pressed()[self.controls[6]]: charging = True
        else:
            if self.ai_action == "CHARGE": charging = True

        if self.is_flying or self.transformed or charging:
            color = AURA_SSJ if self.transformed else self.aura_color
            aura_rect = self.rect.inflate(30, 30)
            off = random.randint(-2, 2)
            pygame.draw.ellipse(surface, color, (aura_rect.x+off, aura_rect.y+off, aura_rect.width, aura_rect.height), 4)

        # 2. HUVUD & KROPP (Beroende på vem det är)
        
        if self.name == "Goku":
            # Orange Gi
            pygame.draw.rect(surface, (255, 90, 0), (rx, ry+20, rw, 40)) # Tröja
            pygame.draw.rect(surface, (255, 90, 0), (rx+5, ry+60, 18, 30)) # Vänster ben
            pygame.draw.rect(surface, (255, 90, 0), (rx+27, ry+60, 18, 30)) # Höger ben
            # Blå detaljer
            pygame.draw.rect(surface, (0, 0, 150), (rx, ry+55, rw, 8)) # Bälte
            pygame.draw.rect(surface, (0, 0, 150), (rx+15, ry+20, 20, 10)) # Undertröja
            pygame.draw.rect(surface, (0, 0, 150), (rx+5, ry+85, 20, 5)) # Skor
            pygame.draw.rect(surface, (0, 0, 150), (rx+25, ry+85, 20, 5)) 
            # Armband
            pygame.draw.rect(surface, (0, 0, 150), (rx-5, ry+40, 8, 8)) 
            pygame.draw.rect(surface, (0, 0, 150), (rx+rw-3, ry+40, 8, 8))

        elif self.name == "Vegeta":
            # Blå Body suit
            pygame.draw.rect(surface, (0, 0, 100), (rx, ry+20, rw, 70))
            # Vit Armor Vest
            pygame.draw.rect(surface, WHITE, (rx, ry+20, rw, 35))
            # Gula ränder på magen (Armor)
            pygame.draw.rect(surface, (200, 180, 50), (rx+10, ry+35, 30, 15)) 
            # Vita Handskar och Stövlar
            pygame.draw.rect(surface, WHITE, (rx-5, ry+40, 10, 10)) # Hand
            pygame.draw.rect(surface, WHITE, (rx+rw-5, ry+40, 10, 10)) # Hand
            pygame.draw.rect(surface, WHITE, (rx+5, ry+80, 18, 10)) # Stövel
            pygame.draw.rect(surface, WHITE, (rx+27, ry+80, 18, 10)) # Stövel

        elif self.name == "Piccolo":
            # Lila Gi
            pygame.draw.rect(surface, (100, 0, 100), (rx, ry+20, rw, 70))
            # Blått bälte
            pygame.draw.rect(surface, (50, 50, 200), (rx, ry+55, rw, 8))
            # Rosa arm-patchar (typiskt piccolo muskelmarkering)
            pygame.draw.rect(surface, (200, 100, 100), (rx+5, ry+30, 10, 10))
            pygame.draw.rect(surface, (200, 100, 100), (rx+35, ry+30, 10, 10))
            # Skor (Bruna)
            pygame.draw.rect(surface, (139, 69, 19), (rx+5, ry+85, 18, 5))
            pygame.draw.rect(surface, (139, 69, 19), (rx+27, ry+85, 18, 5))

        elif self.name == "Frieza":
            # Vit kropp
            pygame.draw.rect(surface, WHITE, (rx, ry+20, rw, 70))
            # Lila delar (Axlar, Huvud, Bröst)
            pygame.draw.circle(surface, (139, 0, 139), (rx+10, ry+25), 8) # Axel
            pygame.draw.circle(surface, (139, 0, 139), (rx+40, ry+25), 8) # Axel
            pygame.draw.rect(surface, (139, 0, 139), (rx+18, ry+35, 14, 10)) # Bröst
            # Svans!
            pygame.draw.arc(screen, WHITE, (rx-20, ry+60, 40, 40), 0, 3.14, 5)

        # 3. GEMENSAMMA DELAR (Huvud & Armar)
        # Huvud
        head_pos = (rx + rw//2, ry + 15)
        pygame.draw.circle(surface, self.skin_color, head_pos, 18)
        
        # Hår (Olika frisyrer)
        h_color = self.hair_color
        if self.name == "Goku":
            # Spretigt hår
            pygame.draw.polygon(surface, h_color, [(rx, ry+10), (rx+10, ry-5), (rx+25, ry+10), (rx+40, ry-5), (rx+rw, ry+10)])
        elif self.name == "Vegeta":
            # Rakt upp hår
            pygame.draw.polygon(surface, h_color, [(rx+10, ry+10), (rx+25, ry-15), (rx+40, ry+10)])
        elif self.name == "Piccolo":
            # Turban (Vit)
            pygame.draw.rect(surface, WHITE, (rx+10, ry, 30, 15))
            pygame.draw.circle(surface, (139, 0, 139), (rx+25, ry+5), 5) # Juvel
        elif self.name == "Frieza":
            # Lila glänsande huvud
            pygame.draw.ellipse(surface, (139, 0, 139), (rx+15, ry, 20, 15))

        # Ansikte (Ögon)
        eye_off = 5 if self.facing_right else -5
        pygame.draw.rect(surface, BLACK, (head_pos[0]+eye_off-2, head_pos[1], 5, 2))

        # Armar (Hud) - Positioneras om man skjuter Ultimate (Pose)
        arm_h = 40
        if self.pose_timer > 0: # Armar framåt för Kamehameha
            pygame.draw.rect(surface, self.skin_color, (rx+rw, ry+30, 20, 8) if self.facing_right else (rx-20, ry+30, 20, 8))
        else: # Armar längs sidan
            pygame.draw.rect(surface, self.skin_color, (rx-5, ry+25, 8, 30))
            pygame.draw.rect(surface, self.skin_color, (rx+rw-3, ry+25, 8, 30))

        # RITA STRÅLAR
        for b in self.beaks: b.draw(surface)

        # UI
        pygame.draw.rect(surface, (50, 0, 0), (rx, ry - 30, 50, 5))
        pygame.draw.rect(surface, (0, 255, 0), (rx, ry - 30, 50 * (self.health/100), 5))
        pygame.draw.rect(surface, (20, 20, 20), (rx, ry - 20, 50, 5))
        pygame.draw.rect(surface, (255, 255, 0), (rx, ry - 20, 50 * (self.ki/100), 5))

font = pygame.font.SysFont(None, 40)
def draw_text(text, x, y, color=WHITE):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))

# --- MENY SYSTEM ---
def main_menu():
    mode = "PVP"
    p1_char = "Goku"
    p2_char = "Vegeta"
    chars = ["Goku", "Vegeta", "Piccolo", "Frieza"]
    
    stage = "MODE_SELECT" # MODE_SELECT -> CHAR_SELECT -> GAME
    
    selected_idxs = [0, 1]
    
    while True:
        screen.fill(BLACK)
        
        if stage == "MODE_SELECT":
            draw_text("DRAGON BALL PYTHON Z", WIDTH//2 - 180, 100, (255, 140, 0))
            draw_text("[1] Player vs Player", WIDTH//2 - 130, 300, WHITE if mode == "CPU" else SKY_BLUE)
            draw_text("[2] Player vs Computer", WIDTH//2 - 130, 350, SKY_BLUE if mode == "CPU" else WHITE)
            draw_text("Tryck 1 eller 2", WIDTH//2 - 100, 500, (100, 100, 100))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: mode = "PVP"; stage = "CHAR_SELECT"
                    if event.key == pygame.K_2: mode = "CPU"; stage = "CHAR_SELECT"

        elif stage == "CHAR_SELECT":
            draw_text("CHOOSE YOUR FIGHTER", WIDTH//2 - 150, 50, AURA_SSJ)
            
            # Rita val
            for i, name in enumerate(chars):
                color = stats_db[name]['skin']
                rect = pygame.Rect(150 + i*200, 250, 100, 100)
                pygame.draw.rect(screen, color, rect)
                draw_text(name, 160 + i*200, 370)
                draw_text(f"[{i+1}]", 190 + i*200, 200, WHITE)

            draw_text(f"P1: {chars[selected_idxs[0]]}", 100, 500, SKY_BLUE)
            if mode == "PVP":
                draw_text(f"P2: {chars[selected_idxs[1]]}", 600, 500, (255, 100, 100))
                draw_text("P1 välj (1-4). P2 välj (Q,W,E,R). ENTER startar.", 150, 600, WHITE)
            else:
                draw_text(f"CPU: {chars[selected_idxs[1]]}", 600, 500, (100, 255, 100))
                draw_text("P1 välj (1-4). CPU slumpas om du trycker R. ENTER startar.", 100, 600, WHITE)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    # P1 Val
                    if event.key == pygame.K_1: selected_idxs[0] = 0
                    if event.key == pygame.K_2: selected_idxs[0] = 1
                    if event.key == pygame.K_3: selected_idxs[0] = 2
                    if event.key == pygame.K_4: selected_idxs[0] = 3
                    
                    # P2 Val (Om PVP)
                    if mode == "PVP":
                        if event.key == pygame.K_q: selected_idxs[1] = 0
                        if event.key == pygame.K_w: selected_idxs[1] = 1
                        if event.key == pygame.K_e: selected_idxs[1] = 2
                        if event.key == pygame.K_r: selected_idxs[1] = 3
                    elif mode == "CPU":
                         if event.key == pygame.K_r: selected_idxs[1] = random.randint(0, 3) # Slumpa CPU

                    if event.key == pygame.K_RETURN:
                        return mode, chars[selected_idxs[0]], chars[selected_idxs[1]]

        pygame.display.flip()

# --- STARTA SPELET ---
game_mode, p1_name, p2_name = main_menu()

c_p1 = [pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_f, pygame.K_g, pygame.K_c, pygame.K_t, pygame.K_SPACE]
c_p2 = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP0, pygame.K_RSHIFT]

p1 = Fighter(100, 400, p1_name, c_p1, stats_db[p1_name])

if game_mode == "PVP":
    p2 = Fighter(800, 400, p2_name, c_p2, stats_db[p2_name])
else:
    # CPU har "None" som kontroller
    p2 = Fighter(800, 400, p2_name, None, stats_db[p2_name])

p2.facing_right = False
clock = pygame.time.Clock()
running = True
winner = None

while running:
    clock.tick(FPS)
    
    # EVENT LOOP
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        
        if not winner and event.type == pygame.KEYDOWN:
            # P1 (Människa)
            if event.key == p1.controls[4]: p1.shoot("BLAST")
            if event.key == p1.controls[5]: p1.shoot("ULTIMATE")
            if event.key == p1.controls[7]: p1.transform()
            if event.key == p1.controls[8]: p1.toggle_fly()
            
            # P2 (Endast om PVP)
            if game_mode == "PVP":
                if event.key == p2.controls[4]: p2.shoot("BLAST")
                if event.key == p2.controls[5]: p2.shoot("ULTIMATE")
                if event.key == p2.controls[7]: p2.transform()
                if event.key == p2.controls[8]: p2.toggle_fly()

        if winner and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            # Reset
            p1.health = 100; p2.health = 100; p1.ki = 0; p2.ki = 0
            p1.rect.x = 100; p2.rect.x = 800; winner = None

    if not winner:
        keys = pygame.key.get_pressed()
        p1.move(keys, p2) # Skicka med motståndaren för AI
        p2.move(keys, p1)
        
        p1.update(p2)
        p2.update(p1)
        
        if p1.health <= 0: winner = f"{p2.name} WINS!"
        if p2.health <= 0: winner = f"{p1.name} WINS!"

    # RITA
    screen.fill(SKY_BLUE)
    pygame.draw.rect(screen, GROUND_COLOR, (0, HEIGHT - 100, WIDTH, 100))
    pygame.draw.rect(screen, GRASS_COLOR, (0, HEIGHT - 100, WIDTH, 20))
    
    # Berg bakgrund
    pygame.draw.polygon(screen, (100, 100, 100), [(100, 600), (300, 200), (500, 600)])
    pygame.draw.polygon(screen, (120, 120, 120), [(600, 600), (800, 300), (1000, 600)])

    p1.draw(screen)
    p2.draw(screen)
    
    # Namn skyltar
    draw_text(f"P1: {p1.name}", 50, 50, p1.aura_color)
    draw_text(f"{'CPU' if game_mode == 'CPU' else 'P2'}: {p2.name}", WIDTH - 250, 50, p2.aura_color)

    if winner:
        draw_text(winner, WIDTH//2 - 100, HEIGHT//2, (255, 0, 0))
        draw_text("Tryck R för att spela igen", WIDTH//2 - 150, HEIGHT//2 + 50, WHITE)

    pygame.display.flip()

pygame.quit()
sys.exit()