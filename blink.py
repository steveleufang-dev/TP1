from machine import Pin, PWM, ADC, I2C
import ssd1306
import time

# ==========================================
# 1. CONFIGURATION INITIALE
# ==========================================

# --- Écran OLED (I2C0 sur GP0 et GP1) ---
i2c = I2C(0, sda=Pin(0), scl=Pin(1),freq=400000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# --- LED RGB en mode PWM ---
# Mettre True si ta LED RGB est à Anode Commune (comme dans le cours), False si Cathode Commune
ANODE_COMMUNE = True 

pwm_r = PWM(Pin(13))
pwm_g = PWM(Pin(12))
pwm_b = PWM(Pin(11))

for pwm in (pwm_r, pwm_g, pwm_b):
    pwm.freq(10000)

# --- Joystick (ADC sur GP26 et GP27) ---
adc_x = ADC(26)  # Axe X -> Rouge / Paramètre
adc_y = ADC(27)  # Axe Y -> Bleu

# --- Bouton-poussoir avec interruption externe ---
bp = Pin(5, Pin.IN, Pin.PULL_UP)

# Variables globales pour les modes et l'anti-rebond
mode = 0  # 0: Fixe, 1: Clignotant, 2: Transition
MODES_NOMS = ["Fixe", "Clignotant", "Transition"]
debounce_time = 0

def bp_callback(pin):
    global mode, debounce_time
    temps_actuel = time.ticks_ms()
    # Anti-rebond de 300 ms
    if time.ticks_diff(temps_actuel, debounce_time) > 300:
        mode = (mode + 1) % 3  # Alterne entre 0, 1 et 2
        debounce_time = temps_actuel

# Déclenchement sur front descendant (appui sur le BP relié à la masse)
bp.irq(trigger=Pin.IRQ_FALLING, handler=bp_callback)

# ==========================================
# 2. FONCTIONS UTILES
# ==========================================

def set_color(r, g, b):
    """Applique les valeurs (0 à 65535) aux broches PWM de la LED RGB."""
    if ANODE_COMMUNE:
        pwm_r.duty_u16(65535 - r)
        pwm_g.duty_u16(65535 - g)
        pwm_b.duty_u16(65535 - b)
    else:
        pwm_r.duty_u16(r)
        pwm_g.duty_u16(g)
        pwm_b.duty_u16(b)

def update_oled(r, g, b, nom_mode, info_param):
    """Met à jour l'écran OLED avec les valeurs RGB (0-255), les % et le mode."""
    # Conversion 0-65535 vers 0-255 et 0-100%
    r_255, g_255, b_255 = r // 257, g // 257, b // 257
    r_pct, g_pct, b_pct = int(r * 100 / 65535), int(g * 100 / 65535), int(b * 100 / 65535)

    display.fill(0)  # Efface l'écran
    display.text(f"Mode: {nom_mode}", 0, 0)
    display.text(info_param, 0, 12)
    display.text(f"R:{r_255:3d} ({r_pct:3d}%)", 0, 28)
    display.text(f"G:{g_255:3d} ({g_pct:3d}%)", 0, 40)
    display.text(f"B:{b_255:3d} ({b_pct:3d}%)", 0, 52)
    display.show()

# ==========================================
# 3. BOUCLE PRINCIPALE
# ==========================================

# Variables pour le clignotement et la transition (sans bloquer le programme)
dernier_blink = time.ticks_ms()
led_allumee = True
r_actuel, g_actuel, b_actuel = 65535, 0, 0
etape_transition = 0
derniere_maj_oled = time.ticks_ms()

try:
    while True:
        val_x = adc_x.read_u16()
        val_y = adc_y.read_u16()
        maintenant = time.ticks_ms()
        param_texte = ""

        # --- MODE 0 : FIXE (Contrôle direct par le joystick) ---
        if mode == 0:
            r_actuel = val_x
            b_actuel = val_y
            g_actuel = (val_x + val_y) // 2  # Moyenne de X et Y pour le vert
            set_color(r_actuel, g_actuel, b_actuel)
            param_texte = "Joystick: RGB"

        # --- MODE 1 : CLIGNOTANT (Axe X règle la fréquence) ---
        elif mode == 1:
            # Fréquence entre 1 Hz et 10 Hz selon l'axe X
            freq = 1 + (val_x / 65535) * 9
            periode_ms = int(1000 / (freq * 2))
            param_texte = f"Freq: {freq:.1f} Hz"

            if time.ticks_diff(maintenant, dernier_blink) >= periode_ms:
                led_allumee = not led_allumee
                dernier_blink = maintenant
                if led_allumee:
                    set_color(r_actuel, g_actuel, b_actuel)
                else:
                    set_color(0, 0, 0)

        # --- MODE 2 : TRANSITION (Axe X règle la vitesse) ---
        elif mode == 2:
            # Vitesse du pas entre 200 et 3000 selon l'axe X
            pas = int(200 + (val_x / 65535) * 2800)
            vitesse_pct = int(val_x * 100 / 65535)
            param_texte = f"Vitesse: {vitesse_pct}%"

            # Cycle progressif : Rouge -> Vert -> Bleu -> Rouge
            if etape_transition == 0:
                r_actuel = max(0, r_actuel - pas)
                g_actuel = min(65535, g_actuel + pas)
                if r_actuel == 0: etape_transition = 1
            elif etape_transition == 1:
                g_actuel = max(0, g_actuel - pas)
                b_actuel = min(65535, b_actuel + pas)
                if g_actuel == 0: etape_transition = 2
            elif etape_transition == 2:
                b_actuel = max(0, b_actuel - pas)
                r_actuel = min(65535, r_actuel + pas)
                if b_actuel == 0: etape_transition = 0

            set_color(r_actuel, g_actuel, b_actuel)

        # --- MISE À JOUR DE L'ÉCRAN OLED (toutes les 100 ms pour rester fluide) ---
        if time.ticks_diff(maintenant, derniere_maj_oled) >= 100:
            update_oled(r_actuel, g_actuel, b_actuel, MODES_NOMS[mode], param_texte)
            derniere_maj_oled = maintenant

        time.sleep_ms(20)

except KeyboardInterrupt:
    # Extinction propre des PWM si on arrête le script
    pwm_r.deinit()
    pwm_g.deinit()
    pwm_b.deinit()
    display.fill(0)
    display.show()

