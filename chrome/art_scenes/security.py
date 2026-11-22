"""Cybersecurity & Risk: each scene shows how the specific failure or control in the article works."""
from art_kit import *  # noqa: F401,F403
from art_scenes import S, scene


@scene(S("2026-06-t3-cybersecurity-threats"), alt="Four attack paths converging on one office, one of them highlighted")
def converging_threats(r):
    out = [building(800, 120, 220, 440, 9, 4, "hi", (4, 1))]
    icons = [(230, 130, lambda x, y: envelope(x - 50, y, 100, 66, "amber")), (230, 260, lambda x, y: lock(x, y + 30, 90, "hi", False, False)),
             (230, 400, lambda x, y: chain(x - 30, y + 26, 3, 44, "hi")), (230, 500, lambda x, y: phone(x - 24, y, 50, 92, "hi"))]
    ys = [163, 290, 426, 546]
    for k, (x, y, fn) in enumerate(icons):
        out.append(fn(x, y))
        hot = k == 0
        out.append(curve(x + 90, ys[k], 480, ys[k], 560, 200 + k * 92, 790, 250 + k * 54, "amber" if hot else "lo", 2.8 if hot else 1.6, None if hot else "8 8", 14 if hot else 0))
    return out


@scene(S("2026-08-15-t91-"), alt="A cloned voice reaches a phone, while approval runs through a registered device instead")
def cloned_voice(r):
    out = [person(200, 230, 120, "hi"), person(200, 470, 120, "lo")]
    out.append(wave(310, 176, 300, 110, 22, 3, "hi"))
    out.append(wave(310, 416, 300, 110, 22, 3, "lo", .0))
    out.append(phone(690, 150, 110, 210, "hi"))
    out.append(arrow(630, 231, 676, 231, "mid", 2))
    out.append(arrow(630, 471, 676, 471, "lo", 2, "6 7"))
    out.append(barrier(720, 410, 120, 130, "lo", True))
    out.append(badge(890, 190, 180, 116, "hi"))
    out.append(arrow(815, 250, 876, 250, "hi", 2.4))
    out.append(check_mark(960, 350, 54, "amber", 4.6))
    return out


@scene(S("2026-08-17-t92-"), alt="A flawless message with one missing line, checked against a list kept outside the inbox")
def missing_context(r):
    out = [envelope(150, 170, 250, 170, "hi"), path("M180 372h190", "lo", 2.4), path("M180 402h150", "lo", 2.4), path("M180 432h170", "lo", 2.4), path("M180 462h90", "lo", 2.4)]
    out.append(rect(290, 448, 120, 28, "amber", 2.2, AMBER_WASH, "7 6"))
    out.append(arrow(440, 300, 520, 300, "mid", 2))
    out.append(doc(570, 120, 210, 420, 0, None, "hi", .12, 2))
    for i in range(6):
        out.append(rect(600, 172 + i * 58, 20, 20, "mid", 1.6) + line(640, 182 + i * 58, 640 + (90 if i % 2 else 112), 182 + i * 58, "lo", 2.4))
        if i < 4:
            out.append(check_mark(603, 184 + i * 58, 13, "hi", 2))
    out.append(arrow(800, 300, 872, 300, "mid", 2))
    out.append(phone(890, 200, 110, 210, "hi"))
    out.append(check_mark(925, 296, 36, "amber", 4))
    return out


@scene(S("2026-08-19-t93-"), alt="A strong main door with a fingerprint lock and a small side door standing open")
def front_and_side_door(r):
    out = [rect(150, 110, 900, 470, "hi", 2, PANEL, r=4)]
    out.append(rect(250, 190, 300, 390, "hi", 2.2, "bg", r=4) + circ(400, 385, 94, "hi", 2) + fingerprint(400, 372, 78, "hi", False))
    out.append(line(520, 360, 520, 420, "hi", 3))
    out.append(path("M820 250 V580 M820 250 L908 286 V580", "amber", 2.6) + line(908, 286, 1008, 250, "amber", 2) + dot(884, 420, 5, "amber"))
    out.append(path("M1060 440 C1000 440 960 430 918 430", "amber", 2.6, "none", "10 8"))
    out.append(line(150, 580, 1050, 580, "mid", 2))
    return out


@scene(S("2026-08-21-t94-"), alt="A company directory of people surrounded by unattached machine identities, one of them unowned")
def unhired_identities(r):
    out = [person(230, 180, 88, "hi"), person(150, 330, 74, "hi"), person(310, 330, 74, "hi"), person(110, 478, 64, "lo"), person(230, 478, 64, "lo"), person(350, 478, 64, "lo")]
    for a, b in (((230, 230), (150, 288)), ((230, 230), (310, 288)), ((150, 382), (110, 432)), ((150, 382), (230, 432)), ((310, 382), (350, 432))):
        out.append(line(*a, *b, "lo", 1.6))
    pts = [(560, 150), (680, 110), (790, 170), (900, 120), (1000, 190), (620, 270), (760, 300), (880, 260), (1010, 320), (560, 400), (690, 420), (820, 400), (940, 430), (1040, 480), (620, 530), (760, 540), (890, 540)]
    for i, (x, y) in enumerate(pts):
        hot = i == 7
        out.append(rect(x - 16, y - 16, 32, 32, "amber" if hot else ("hi" if i % 4 else "mid"), 2, AMBER_WASH if hot else "none", r=4))
        if not hot and i % 3 != 1:
            out.append(line(x, y, 380 + (i % 5) * 22, 250 + (i % 4) * 60, "faint", 1.3, "5 8"))
    out.append(line(436, 250, 900, 260, "faint", 1.2, "3 8"))
    return out


@scene(S("2026-08-23-t95-"), alt="A phone receiving a stack of prompts while one path goes around it")
def fatigue_bypass(r):
    out = [phone(500, 120, 170, 330, "hi")]
    for k in range(4):
        out.append(rect(440 - k * 26, 170 + k * 34, 220, 58, "mid" if k < 3 else "hi", 1.8, "bg", r=8) + dot(470 - k * 26, 199 + k * 34, 6, "lo") + line(494 - k * 26, 190 + k * 34, 610 - k * 26, 190 + k * 34, "lo", 2.4) + line(494 - k * 26, 206 + k * 34, 570 - k * 26, 206 + k * 34, "lo", 2.4))
    out.append(arrow(150, 300, 250, 300, "lo", 2))
    out.append(person(120, 300, 80, "hi"))
    out.append(curve(130, 340, 180, 560, 560, 560, 760, 520, "amber", 2.6, None, 0))
    out.append(server(820, 200, 190, 250, 4, "hi", 1))
    out.append(curve(760, 520, 900, 500, 930, 450, 920, 420, "amber", 2.6, None, 14))
    out.append(line(700, 280, 790, 280, "mid", 2, "8 7"))
    return out


@scene(S("2026-08-25-t96-"), alt="A sign-in guarded by a lock, and a session token taken along a path that skips the lock")
def stolen_session(r):
    out = [window(130, 150, 270, 190, "hi"), rows_of_text(165, 220, 170, 3, 34, "lo", 2.4)]
    out.append(lock(530, 250, 120, "hi", False, False))
    out.append(arrow(410, 250, 470, 250, "mid", 2) + arrow(590, 250, 660, 250, "mid", 2))
    out.append(server(700, 140, 190, 230, 4, "hi"))
    tx, ty = 340, 430
    out.append(circ(tx, ty, 40, "amber", 2.6, AMBER_WASH) + circ(tx, ty, 14, "amber", 2) + dot(tx + 40, ty, 5, "bg"))
    out.append(curve(380, 430, 520, 470, 640, 470, 780, 420, "amber", 2.6, None, 0))
    out.append(window(810, 400, 230, 160, "lo", 1.6))
    out.append(curve(780, 420, 800, 420, 800, 460, 812, 470, "amber", 2.6, None, 13))
    out.append(person(920, 480, 70, "lo"))
    return out


@scene(S("2026-09-03-t101-"), alt="A grid of software tiles where a cancelled tile still has a live connection to company data")
def lingering_grant(r):
    out = []
    cells = []
    for i in range(3):
        for j in range(4):
            x, y = 140 + j * 120, 150 + i * 130
            cells.append((x, y))
            cancelled = (i, j) == (1, 2)
            out.append(window(x, y, 94, 92, "lo" if cancelled else "hi", 1.6, .22))
            if cancelled:
                out.append(cross_mark(x + 47, y + 56, 17, "amber", 2.6))
    out.append(cylinder(860, 200, 190, 250, 4, "hi"))
    for k, (x, y) in enumerate(cells):
        hot = k == 6
        out.append(curve(x + 94, y + 46, 640, y + 46, 720, 320, 856, 320 + (k - 6) * 6, "amber" if hot else "faint", 2.8 if hot else 1.3, None, 12 if hot else 0))
    return out


@scene(S("2026-09-11-t105-"), alt="A boundary wall with one exposed appliance, seen only dimly from inside")
def edge_device(r):
    out = [cloud(220, 300, 170, "mid"), bricks(440, 130, 150, 440, 9, "hi", (4, 1))]
    out.append(router(404, 290, 130, 70, "hi") + dot(508, 336, 6, "amber"))
    out.append(arrow(300, 320, 392, 322, "amber", 2.8, None, 13))
    out.append(line(290, 322, 300, 322, "amber", 2.8))
    out.append(server(700, 200, 190, 280, 5, "hi"))
    out.append(arrow(560, 322, 690, 322, "mid", 2, "8 7"))
    out.append(magnifier(900, 480, 74, "mid", 2.4, 45) + line(900, 480, 760, 420, "faint", 1.3, "4 7"))
    out.append(circ(500, 322, 88, "lo", 1.4, "none", "6 8"))
    return out


@scene(S("2026-09-13-t106-"), alt="A broken key beside an application that still holds a consent link to company data")
def surviving_consent(r):
    out = [key(240, 220, 150, "hi", 2.6, 0)]
    out.append(path("M214 196 l18 22 l-14 16 l20 22", "amber", 2.6))
    out.append(arrow(330, 220, 400, 220, "lo", 2, "6 7") + cross_mark(370, 220, 12, "amber", 2.4))
    out.append(badge(140, 360, 240, 150, "hi"))
    out.append(window(520, 340, 240, 190, "hi") + rows_of_text(560, 410, 150, 3, 32, "lo", 2.4))
    out.append(cylinder(870, 310, 180, 240, 4, "hi"))
    out.append(line(380, 435, 520, 435, "mid", 2))
    out.append(curve(760, 435, 800, 435, 820, 435, 868, 435, "amber", 3, None, 14))
    out.append(chain(600, 260, 3, 46, "amber"))
    out.append(line(610, 292, 620, 340, "amber", 2.2))
    return out


@scene(S("2026-10-13-t29-"), alt="A login checkpoint followed by further checks along the life of a session")
def session_checks(r):
    out = [line(140, 420, 1070, 420, "mid", 2.2)]
    out.append(barrier(160, 250, 100, 190, "hi", False))
    out.append(dot(210, 420, 7, "hi"))
    xs = [360, 480, 600, 730, 860, 990]
    for k, x in enumerate(xs):
        hot = k == 3
        h = [66, 100, 60, 120, 84, 70][k]
        out.append(line(x, 420 - h, x, 420, "amber" if hot else "lo", 2.6 if hot else 1.8) + (circ(x, 420 - h, 22, "amber", 2.4, AMBER_WASH) if hot else circ(x, 420 - h, 18, "hi", 1.8, "bg")))
        if hot:
            out.append(cross_mark(x, 420 - h, 9, "amber", 2.6))
        else:
            out.append(check_mark(x - 8, 420 - h, 14, "hi", 2.2))
    out.append(dim(260, 500, 1050, 500, "lo"))
    out.append(path("M210 470 V500", "lo", 1.4) + path("M1050 440 V500", "lo", 1.4))
    return out


@scene(S("2026-10-20-t32-"), alt="A genuine mailbox with an uninvited reader inside sending a payment request onward")
def real_inbox(r):
    out = [envelope(140, 190, 310, 220, "hi")]
    out.append(person(295, 330, 104, "amber"))
    out.append(arrow(470, 300, 560, 300, "mid", 2))
    out.append(doc(590, 170, 170, 230, 6, 4, "hi"))
    out.append(arrow(780, 300, 846, 300, "amber", 2.6, None, 13))
    for k in range(3):
        out.append(coin(930, 380 - k * 40, 52 if k < 2 else 52, "hi", k == 2))
    out.append(ticks(880, 200, 110, 250, "lo", 16))
    out.append(barrier(560, 470, 220, 110, "lo", False))
    out.append(line(675, 400, 675, 470, "lo", 1.6, "6 7"))
    return out
