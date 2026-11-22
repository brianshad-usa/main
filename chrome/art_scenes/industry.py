"""Industry Perspectives: the sector and its particular technology problem."""
from art_kit import *  # noqa: F401,F403
from art_scenes import S, scene


@scene(S("2026-06-15-t84-"), alt="A tooth shown on a chairside screen beside a protected record")
def dental(r):
    out = [window(160, 130, 480, 340, "hi"), tooth(400, 320, 200, "hi")]
    out.append(line(220, 520, 560, 520, "mid", 2.4) + line(400, 470, 400, 520, "mid", 2.4))
    out.append(doc(740, 150, 210, 270, 6, 2, "hi"))
    out.append(lock(930, 440, 110, "amber", False, True))
    out.append(path("M650 300 H730", "lo", 1.8, "none", "8 8"))
    return out


@scene(S("2026-06-17-t85-"), alt="Ledger sheets and a filing calendar with the deadline marked")
def accounting(r):
    out = [table(140, 150, 430, 400, 4, 8), stack(660, 250, 210, 220, 3, 16, "lo")]
    out.append(calendar(760, 130, 270, 190, (9, 10, 17), "hi", 24) + rows_of_text(690, 300, 130, 4, 34, "lo", 2.4))
    return out


@scene(S("2026-06-21-t87-"), alt="An apartment building with one door unlocked by a tenant key")
def property_management(r):
    out = [building(200, 130, 420, 420, 6, 5, "hi", (4, 2)), key(760, 320, 190, "amber", 3, 0)]
    out.append(path("M640 400 C700 380 720 360 700 330", "lo", 1.6, "none", "7 8"))
    out.append(window(760, 420, 270, 150, "lo", 1.6) + rows_of_text(790, 474, 170, 2, 34, "lo", 2.4) + line(140, 550, 660, 550, "mid", 2))
    return out


@scene(S("2026-06-23-t88-"), alt="A tower crane over a building plan with one lifted component")
def construction(r):
    out = [crane(300, 170, 380, "hi", True)]
    out.append(rect(520, 330, 520, 230, "mid", 1.8, "none", r=2))
    for k in range(1, 5):
        out.append(line(520 + k * 104, 330, 520 + k * 104, 560, "lo", 1.4))
    for k in range(1, 3):
        out.append(line(520, 330 + k * 76, 1040, 330 + k * 76, "lo", 1.4))
    out.append(path("M600 560 V470 H700 V560 M760 560 V420 H860 V560", "hi", 2))
    out.append(dim(520, 596, 1040, 596, "lo") + dim(1068, 330, 1068, 560, "lo"))
    return out


@scene(S("2026-06-25-t89-"), alt="A policy document under a protective umbrella, with the claim clock running")
def insurance(r):
    out = [path("M240 300 C260 170 420 130 520 150 C640 120 800 180 820 300 C760 270 720 270 680 300 C640 270 590 270 560 300 C520 270 470 270 440 300 C400 270 320 270 240 300Z", "hi", 2, "rgba(255,255,255,.04)")]
    out.append(line(530, 150, 530, 480, "mid", 2.4) + path("M530 480 q0 46 -42 46 q-30 0 -30 -24", "mid", 2.4))
    out.append(doc(600, 340, 190, 220, 6, 3, "hi"))
    out.append(clock(930, 430, 92, 10, 20, "hi", True))
    out.append(path("M330 360 V520", "faint", 1.4, "none", "6 8"))
    return out


@scene(S("2026-06-27-t90-"), alt="A table setting, a card reader and the wireless link between them")
def restaurant(r):
    out = [plate(360, 340, 128, "hi"), phone(720, 210, 150, 260, "hi")]
    out.append(rect(744, 258, 102, 34, "amber", 2, AMBER_WASH, r=3) + line(744, 270, 846, 270, "amber", 3) + rows_of_text(752, 320, 88, 3, 28, "lo", 2.4))
    out.append(wifi(600, 230, 90, "mid"))
    out.append(path("M480 340 H700", "lo", 1.6, "none", "8 8"))
    out.append(line(130, 520, 1070, 520, "lo", 1.6))
    return out


@scene(S("2026-06-29-t91-"), alt="An engineering elevation with one measured dimension highlighted")
def architecture(r):
    out = [pediment(300, 180, 380, 110, "hi")]
    for k in range(5):
        out.append(column(330 + k * 72, 296, 44, 190, "hi"))
    out.append(rect(290, 490, 400, 26, "mid", 1.8) + rect(270, 518, 440, 26, "mid", 1.8))
    out.append(dim(240, 180, 240, 544, "lo"))
    out.append(dim(330, 590, 620, 590, "amber") + line(330, 552, 330, 598, "amber", 1.6) + line(620, 552, 620, 598, "amber", 1.6))
    out.append(rect(800, 150, 260, 400, "mid", 1.7, "none", r=3))
    for i in range(4):
        out.append(line(830, 210 + i * 70, 830 + [150, 190, 120, 170][i], 210 + i * 70, "lo", 2.4))
    out.append(path("M830 190 q40 -20 90 0", "lo", 1.6))
    return out


@scene(S("2026-07-01-t92-cyber"), alt="A gene sequence held inside layered protection with one marked point")
def biotech(r):
    out = [helix(390, 100, 220, 470, 3, "hi"), circ(500, 250, 26, "amber", 2.6, AMBER_WASH), dot(500, 250, 6, "amber")]
    for s_, t_ in ((260, "mid"), (180, "lo"), (100, "hi")):
        out.append(shield(850, 320, s_, t_, 1.8))
    return out


@scene(S("2026-07-03-t93-"), alt="A storyboard of campaign frames with one under review before it ships")
def marketing(r):
    out = []
    for i in range(2):
        for j in range(4):
            x, y = 140 + j * 180, 150 + i * 180
            hot = (i, j) == (1, 2)
            out.append(rect(x, y, 148, 108, "amber" if hot else "hi", 2.2 if hot else 1.7, AMBER_WASH if hot else "none", r=3))
            out.append(path("M%s %s l34 -42 l30 30 l24 -22 l28 34" % (n(x + 14), n(y + 92)), "amber" if hot else "lo", 2) + circ(x + 118, y + 24, 9, "lo", 1.5))
    out.append(clock(960, 260, 86, 10, 50, "hi", False) + stack(890, 420, 170, 110, 3, 14, "lo"))
    return out


@scene(S("2026-07-05-t94-"), alt="A paw print and an appointment calendar with one visit confirmed")
def veterinary(r):
    out = [paw(340, 340, 330, "hi"), calendar(640, 170, 380, 300, (2, 5, 8, 12, 15, 18, 22), "hi", 16)]
    out.append(path("M610 300 H520", "lo", 1.6, "none", "8 8"))
    return out


@scene(S("2026-07-23-t12-"), alt="A courthouse facade above a stack of sealed case files")
def law_ransomware(r):
    out = [pediment(220, 110, 420, 100, "hi")]
    for k in range(5):
        out.append(column(245 + k * 82, 214, 46, 176, "hi"))
    out.append(rect(205, 396, 450, 20, "mid", 1.8) + rect(190, 420, 480, 20, "mid", 1.8))
    for k in range(4):
        out.append(folder(740, 250 + k * 74, 250, 70, "lo" if k < 3 else "hi"))
    out.append(lock(865, 190, 96, "amber", False, True))
    out.append(rows_of_text(200, 480, 400, 2, 40, "lo", 2.4))
    out.append(line(560, 500, 740, 470, "lo", 1.6, "8 8"))
    return out


@scene(S("2026-07-25-t13-"), alt="A clinic screen with a heartbeat trace that never drops out")
def clinic_uptime(r):
    out = [window(150, 130, 640, 380, "hi"), cross(250, 250, 90, "lo", 1.8), ecg(330, 230, 420, 190, "hi", 3, 2)]
    out.append(rows_of_text(200, 440, 300, 2, 30, "lo", 2.4))
    out.append(server(900, 180, 160, 240, 4, "lo", 1))
    out.append(path("M800 330 H890", "lo", 1.8, "none", "8 8"))
    return out


@scene(S("2026-07-27-t14-"), alt="A law office column beside a film strip with one frame marked")
def beverly_hills(r):
    out = [column(190, 130, 130, 430, "hi"), pediment(150, 70, 210, 60, "hi")]
    out.append(rect(450, 210, 590, 230, "hi", 2, "bg", r=4))
    for k in range(14):
        out.append(rect(464 + k * 41, 220, 18, 18, "mid", 1.4, "none", r=2) + rect(464 + k * 41, 412, 18, 18, "mid", 1.4, "none", r=2))
    for k in range(4):
        hot = k == 2
        out.append(rect(470 + k * 142, 256, 124, 136, "amber" if hot else "lo", 2.2 if hot else 1.6, AMBER_WASH if hot else "none"))
        out.append(path("M%s %s l26 -40 l26 22 l34 -50" % (n(486 + k * 142), n(368)), "amber" if hot else "lo", 2))
    return out


@scene(S("2026-07-29-t15-"), alt="A high-rise with one lit floor and a riser running through every level")
def century_city(r):
    out = [building(380, 90, 260, 480, 12, 4, "hi", (3, 1)), building(140, 260, 150, 310, 7, 2, "lo"), building(720, 220, 180, 350, 8, 2, "lo")]
    out.append(line(510, 90, 510, 570, "amber", 2.8) + path("M510 340 H640", "amber", 2.4))
    for k in range(1, 12):
        out.append(dot(510, 90 + k * 40, 3.5, "amber") if k % 2 else "")
    out.append(line(100, 570, 1090, 570, "mid", 2))
    return out


@scene(S("2026-07-31-t16-"), alt="A research campus inside nested layers of protection")
def pasadena_layers(r):
    out = []
    for k, (w, h, t_) in enumerate(((880, 430, "lo"), (700, 340, "mid"), (520, 250, "hi"))):
        out.append(rect(600 - w / 2, 330 - h / 2, w, h, t_, 1.8, PANEL if k else "none", r=8))
    out.append(building(480, 270, 110, 180, 4, 2, "hi") + building(610, 310, 110, 140, 3, 2, "hi") + cross(770, 320, 90, "lo", 1.8))
    out.append(path("M250 160 C220 260 220 400 250 500", "amber", 2.6, "none", "9 8"))
    return out


@scene(S("2026-08-01-t17-"), alt="A laboratory flask whose measured level links to a data cluster")
def irvine_lab(r):
    out = [path("M330 130 H450 M360 130 V290 L240 520 Q230 560 270 560 H510 Q550 560 540 520 L420 290 V130", "hi", 2.2, "rgba(255,255,255,.03)")]
    out.append(path("M262 470 H528 M282 432 H498", "amber", 2.8) + dot(310, 516, 5, "amber") + dot(430, 500, 7, "amber"))
    pts = [(740, 160), (860, 140), (960, 220), (700, 280), (840, 300), (980, 340), (760, 420), (900, 450), (1010, 500), (700, 520)]
    out.append(mesh(pts, 190, "lo", 1.2))
    for k, p in enumerate(pts):
        out.append(node(p[0], p[1], "amber" if k == 4 else "hollow", 10))
    out.append(path("M550 480 C600 470 640 440 690 420", "lo", 1.6, "none", "8 8"))
    return out


@scene(S("2026-08-03-t18-"), alt="An aircraft over a secured perimeter with one access gate")
def el_segundo(r):
    out = [plane(560, 250, 330, "hi"), path("M150 470 H1050", "mid", 2)]
    for x in range(180, 1040, 60):
        out.append(path("M%s 470 V540" % x, "lo", 1.6) + path("M%s 480 l30 50 m-30 0 l30 -50" % (x + 2), "faint", 1.3))
    out.append(line(150, 540, 1050, 540, "mid", 2) + barrier(560, 450, 120, 110, "hi", True) + dim(300, 380, 820, 380, "lo"))
    return out


@scene(S("2026-08-07-t20-managed"), alt="A factory with a conveyor and one part under inspection")
def torrance_factory(r):
    out = [path("M150 560 V330 L270 260 V330 L390 260 V330 L510 260 V330 L630 260 V560", "hi", 2.2, "rgba(255,255,255,.03)"), line(150, 560, 1080, 560, "mid", 2)]
    for k in range(3):
        out.append(rect(190 + k * 140, 400, 70, 90, "lo", 1.6))
    out.append(line(660, 470, 1070, 470, "mid", 2.4) + line(660, 500, 1070, 500, "mid", 2.4))
    for k, x in enumerate((690, 780, 870, 960)):
        hot = k == 2
        out.append(rect(x, 420, 58, 50, "amber" if hot else "hi", 2, AMBER_WASH if hot else "bg", r=3))
    for x in range(670, 1070, 40):
        out.append(circ(x, 485, 6, "lo", 1.4))
    out.append(magnifier(890, 330, 60, "amber", 2.6, 45))
    return out


@scene(S("2026-10-03-t24-"), alt="A small office casting a large shadow of records")
def liability_shadow(r):
    out = [building(200, 330, 120, 190, 4, 2, "hi"), line(130, 520, 1080, 520, "mid", 2)]
    out.append(poly([(320, 520), (1010, 520), (1010, 150), (520, 150)], "faint", 1.4, "rgba(227,154,61,.05)", "8 8", True))
    for i in range(3):
        for j in range(4):
            out.append(doc(540 + j * 116, 190 + i * 108, 84, 88, 3, 1 if (i, j) == (1, 2) else None, "hi" if (i + j) % 2 else "lo", .2, 1.6))
    return out


@scene(S("2026-10-09-t27-"), alt="Factory machines each wired to a cloud, one connection highlighted")
def connected_machines(r):
    out = [cloud(600, 210, 190, "hi")]
    xs = [180, 400, 620, 840]
    for k, x in enumerate(xs):
        hot = k == 1
        out.append(rect(x - 70, 420, 140, 110, "hi", 2, "bg", r=6) + gear(x, 474, 32, 9, "amber" if hot else "mid") + line(x - 70, 560, x + 70, 560, "lo", 1.6))
        out.append(curve(x, 420, x, 350, 600 + (x - 510) * .3, 350, 600 + (x - 510) * .3, 290, "amber" if hot else "lo", 2.8 if hot else 1.6, None if hot else "7 8", 13 if hot else 0))
    out.append(line(120, 560, 1080, 560, "mid", 2))
    return out


