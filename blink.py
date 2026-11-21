from machine import Pin, PWM, ADC, I2C  # import des classes materiel du pico
import ssd1306                          # import de la lib pour l'ecran oled
import time                             # import du module temps

i2c = I2C(0, sda=Pin(20), scl=Pin(21), freq=400000)  # init bus i2c 0 sur GP20 et GP21
oled = ssd1306.SSD1306_I2C(128, 64, i2c)             # creation de l'objet ecran 128x64

led_r = PWM(Pin(13))                    # pwm rouge sur GP13
led_g = PWM(Pin(12))                    # pwm vert sur GP12
led_b = PWM(Pin(11))                    # pwm bleu sur GP11

led_r.freq(10000)                       # frequence pwm rouge a 10kHz
led_g.freq(10000)                       # frequence pwm vert a 10kHz
led_b.freq(10000)                       # frequence pwm bleu a 10kHz

joy_x = ADC(26)                         # axe X du joystick sur ADC0 (GP26)
joy_y = ADC(27)                         # axe Y du joystick sur ADC1 (GP27)

bp = Pin(5, Pin.IN, Pin.PULL_UP)        # bouton poussoir sur GP5 en pull-up

mode = 0                                # 0 = fixe, 1 = clignotant, 2 = transition
noms_modes = ["Fixe", "Clignotant", "Transition"]  # noms des modes pour l'oled
dernier_appui = 0                       # temps du dernier appui pour l'anti-rebond

def changer_mode(pin):                  # fonction appelee par l'interruption du bouton
    global mode, dernier_appui          # on modifie les variables globales
    t = time.ticks_ms()                 # recupere le temps actuel en ms
    if time.ticks_diff(t, dernier_appui) > 300:  # anti-rebond de 300ms
        mode = (mode + 1) % 3           # passe au mode suivant (0 -> 1 -> 2 -> 0)
        dernier_appui = t               # met a jour le temps du dernier appui

bp.irq(trigger=Pin.IRQ_FALLING, handler=changer_mode)  # interruption sur front descendant

def couleur(r, g, b):                   # regle la couleur de la led rgb
    led_r.duty_u16(65535 - r)           # inverse la valeur pour anode commune (rouge)
    led_g.duty_u16(65535 - g)           # inverse la valeur pour anode commune (vert)
    led_b.duty_u16(65535 - b)           # inverse la valeur pour anode commune (bleu)

def afficher_oled(r, g, b, texte_mode, info):  # met a jour le texte sur l'oled
    r255 = r // 257                     # convertit rouge de 0-65535 vers 0-255
    g255 = g // 257                     # convertit vert de 0-65535 vers 0-255
    b255 = b // 257                     # convertit bleu de 0-65535 vers 0-255

    rp = int(r * 100 / 65535)           # pourcentage de rouge
    gp = int(g * 100 / 65535)           # pourcentage de vert
    bp_val = int(b * 100 / 65535)       # pourcentage de bleu

    oled.fill(0)                        # efface l'ecran
    oled.text("Mode: " + texte_mode, 0, 0)      # affiche le mode en haut
    oled.text(info, 0, 12)                      # affiche le parametre du mode
    oled.text(f"R: {r255} ({rp}%)", 0, 28)      # affiche valeur et % rouge
    oled.text(f"G: {g255} ({gp}%)", 0, 40)      # affiche valeur et % vert
    oled.text(f"B: {b255} ({bp_val}%)", 0, 52)  # affiche valeur et % bleu
    oled.show()                         # envoie l'affichage a l'ecran

t_blink = time.ticks_ms()               # chrono pour le clignotement
t_oled = time.ticks_ms()                # chrono pour le rafraichissement oled
etat_led = True                         # etat actuel de la led en mode clignotant
r, g, b = 65535, 0, 0                   # couleur de depart (rouge)
etape = 0                               # etape actuelle du cycle de transition

try:                                    # permet de gerer l'arret proprement
    while True:                         # boucle principale infinie
        x = joy_x.read_u16()            # lecture de l'axe X (0 a 65535)
        y = joy_y.read_u16()            # lecture de l'axe Y (0 a 65535)
        t_now = time.ticks_ms()         # temps actuel en ms
        info = ""                       # texte d'info par defaut

        if mode == 0:                   # mode fixe
            r = x                       # axe X controle le rouge
            b = y                       # axe Y controle le bleu
            g = (x + y) // 2            # vert = moyenne de X et Y
            couleur(r, g, b)            # applique la couleur sur la led
            info = "Joystick: RGB"      # texte a afficher sur l'oled

        elif mode == 1:                 # mode clignotant
            freq = 1 + (x / 65535) * 9  # X regle la frequence entre 1 et 10 Hz
            delai = int(1000 / (freq * 2))  # calcul de la demi-periode en ms
            info = f"Freq: {freq:.1f} Hz"   # texte de la frequence pour l'oled

            if time.ticks_diff(t_now, t_blink) >= delai:  # verifie si le delai est passe
                etat_led = not etat_led # inverse l'etat allume/eteint
                t_blink = t_now         # remet le chrono a zero
                if etat_led:            # si la led doit s'allumer
                    couleur(r, g, b)    # remet la couleur memorisee
                else:                   # sinon
                    couleur(0, 0, 0)    # eteint la led

        elif mode == 2:                 # mode transition de couleurs
            pas = int(200 + (x / 65535) * 2800)  # X regle la vitesse du degrade
            vit = int(x * 100 / 65535)           # vitesse en pourcentage
            info = f"Vitesse: {vit}%"            # texte de la vitesse pour l'oled

            if etape == 0:              # transition rouge vers vert
                r = max(0, r - pas)     # diminue le rouge jusqu'a 0
                g = min(65535, g + pas) # augmente le vert jusqu'a 65535
                if r == 0:              # si le rouge est a 0
                    etape = 1           # passe a l'etape suivante
            elif etape == 1:            # transition vert vers bleu
                g = max(0, g - pas)     # diminue le vert jusqu'a 0
                b = min(65535, b + pas) # augmente le bleu jusqu'a 65535
                if g == 0:              # si le vert est a 0
                    etape = 2           # passe a l'etape suivante
            elif etape == 2:            # transition bleu vers rouge
                b = max(0, b - pas)     # diminue le bleu jusqu'a 0
                r = min(65535, r + pas) # augmente le rouge jusqu'a 65535
                if b == 0:              # si le bleu est a 0
                    etape = 0           # recommence le cycle

            couleur(r, g, b)            # applique la nouvelle couleur

        if time.ticks_diff(t_now, t_oled) >= 100:  # maj de l'oled toutes les 100ms
            afficher_oled(r, g, b, noms_modes[mode], info)  # appelle la fonction d'affichage
            t_oled = t_now              # remet le chrono oled a zero

        time.sleep_ms(20)               # petite pause de 20ms

except KeyboardInterrupt:               # si on arrete le programme (Ctrl+C)
    led_r.deinit()                      # coupe le pwm rouge
    led_g.deinit()                      # coupe le pwm vert
    led_b.deinit()                      # coupe le pwm bleu
    oled.fill(0)                        # efface l'ecran oled
    oled.show()                         # valide l'extinction de l'ecran