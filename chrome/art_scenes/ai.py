"""Artificial Intelligence & Automation: what the model can see, do and keep."""
from art_kit import *  # noqa: F401,F403
from art_scenes import S, scene


@scene(S("2026-06-19-t86-"), alt="A five-step process in which one manual step is replaced by a gear")
def automated_step(r):
    out = []
    xs = [150, 350, 550, 750, 950]
    for k, x in enumerate(xs):
        if k == 2:
            out.append(gear(x + 60, 325, 62, 10, "amber"))
        else:
            out.append(rect(x, 270, 120, 110, "hi", 1.9, "bg", r=6) + rows_of_text(x + 24, 308, 70, 3, 24, "lo", 2.4, k))
        if k < 4:
            out.append(arrow(x + 128, 325, x + 190, 325, "mid", 2))
    out.append(person(610, 530, 74, "lo") + path("M610 476 V400", "lo", 1.8, "none", "6 7") + path("M610 476 C520 470 470 450 420 408", "lo", 1.6, "none", "6 8"))
    out.append(dim(190, 190, 1010, 190, "lo"))
    return out


@scene(S("2026-07-07-t0-ai-tools"), alt="A workspace with six tools around it and one of them adopted")
def six_tools(r):
    out = [laptop(450, 250, 300, 200, "hi")]
    pos = [(200, 130), (530, 110), (860, 130), (200, 480), (530, 500), (860, 480)]
    for k, (x, y) in enumerate(pos):
        hot = k == 2
        out.append(window(x, y, 150, 96, "amber" if hot else "hi", 2, .22))
        out.append(rows_of_text(x + 22, y + 48, 90, 2, 22, "amber" if hot else "lo", 2.6, k))
        cx, cy = x + 75, y + 48
        out.append(line(cx + (40 if cx < 600 else -40), cy + (46 if cy < 300 else -46), 600 + (cx - 600) * .28, 350 + (cy - 350) * .38, "amber" if hot else "faint", 2.4 if hot else 1.3, None if hot else "6 8"))
    return out


@scene(S("2026-07-21-t10-"), alt="A readiness dial beside a checklist with two items still open")
def ai_readiness(r):
    out = [speedo(360, 400, 170, 8, "hi", 5)]
    out.append(path("M360 400 L470 300", "amber", 3) + dot(360, 400, 9, "hi"))
    out.append(path("M170 420 A190 190 0 0 1 550 420", "lo", 1.6))
    out.append(doc(690, 110, 330, 450, 0, None, "hi", .12, 2))
    for i in range(6):
        y = 176 + i * 58
        done = i not in (2, 4)
        out.append(rect(726, y - 12, 26, 26, "amber" if not done else "mid", 1.9, AMBER_WASH if not done else "none"))
        if done:
            out.append(check_mark(730, y + 2, 17, "hi", 2.2))
        out.append(line(778, y + 1, 778 + (170 if i % 2 else 206), y + 1, "lo", 2.6))
    return out


@scene(S("2026-08-05-t19-"), alt="A question asked of a library, and one answer drawn from a highlighted shelf")
def knowledge_assistant(r):
    out = [bookshelf(150, 150, 330, 400, 4, "mid")]
    out.append(rect(160, 252, 310, 96, "amber", 2.2, AMBER_WASH))
    out.append(magnifier(590, 320, 80, "hi", 2.4, 45))
    out.append(arrow(500, 300, 512, 306, "lo", 2) + line(490, 300, 540, 306, "mid", 2))
    out.append(balloon(790, 180, 250, 150, "hi", "left"))
    out.append(rows_of_text(826, 232, 170, 3, 30, "lo", 2.6) + line(826, 322 - 30, 826 + 60, 292, "amber", 3))
    out.append(arrow(680, 270, 774, 250, "mid", 2, "8 7"))
    out.append(balloon(850, 400, 170, 110, "lo", "right"))
    return out


@scene(S("2026-08-09-t88-"), alt="Applications inside and outside a company boundary, with a consent key linking one outside")
def shadow_apps(r):
    out = [rect(140, 120, 560, 450, "hi", 2, PANEL, "14 10", 18)]
    for i in range(2):
        for j in range(3):
            x, y = 190 + j * 168, 180 + i * 170
            out.append(window(x, y, 128, 104, "hi", 1.8, .2))
    out.append(person(420, 490, 70, "hi"))
    outside = [(780, 130), (930, 250), (800, 380), (950, 480)]
    for k, (x, y) in enumerate(outside):
        hot = k == 1
        out.append(window(x, y, 140, 100, "amber" if hot else "lo", 1.9, .2))
        out.append(key(x + 70, y + 64, 84, "amber" if hot else "lo", 2.2))
        if hot:
            out.append(curve(690, 300, 760, 300, 800, 290, 928, 296, "amber", 2.8, None, 13))
    return out


@scene(S("2026-08-11-t89-"), alt="A tenant of folders where a search beam exposes the ones everyone could already open")
def tenant_search(r):
    out = []
    k = 0
    for i in range(4):
        for j in range(5):
            x, y = 140 + j * 130, 160 + i * 104
            hot = k in (7, 8, 12)
            out.append(folder(x, y, 98, 76, "amber" if hot else ("lo" if k % 3 else "mid")))
            k += 1
    out.append(poly([(900, 140), (1060, 210), (860, 560), (690, 440)], "lo", 1.6, "rgba(255,255,255,.03)", None, True))
    out.append(magnifier(920, 300, 96, "hi", 2.6, 45))
    out.append(path("M760 250 C700 250 660 260 610 280", "amber", 2.4, "none"))
    return out


@scene(S("2026-08-13-t90-"), alt="A beam passing over a field of documents and lighting one of them")
def permission_beam(r):
    out = []
    for i in range(3):
        for j in range(7):
            hot = (i, j) == (1, 4)
            out.append(doc(168 + j * 128, 236 + i * 108, 66, 82, 2, None, "amber" if hot else "lo", .2, 1.7))
    out.append(dot(600, 92, 12, "hi"))
    out.append(poly([(600, 92), (340, 590), (940, 590)], "faint", 1.3, "rgba(255,255,255,.035)", None, True))
    out.append(path("M600 92 L712 344", "amber", 2.4, "none", "8 8"))
    return out


@scene(S("2026-08-31-t99-"), alt="A vendor holding a key that opens a customer's data store")
def vendor_key(r):
    out = [building(150, 200, 230, 350, 7, 3, "hi")]
    out.append(cylinder(820, 230, 220, 290, 4, "hi"))
    out.append(key(380, 370, 170, "amber", 3, -8))
    out.append(curve(460, 372, 560, 380, 680, 380, 806, 376, "amber", 2.6, "10 8", 14))
    out.append(shield(930, 150, 90, "mid", 1.8))
    out.append(path("M380 250 H500", "lo", 1.5, "none", "6 8"))
    return out


@scene(S("2026-09-01-t100-"), alt="A meeting around a table whose spoken lines flow into a searchable archive")
def meeting_archive(r):
    out = [rect(150, 290, 330, 150, "hi", 2, "bg", r=70)]
    for x, y in ((190, 220), (315, 196), (440, 220), (190, 500), (315, 526), (440, 500)):
        out.append(person(x, y, 62, "hi"))
    out.append(balloon(520, 180, 150, 76, "mid", "left") + rows_of_text(546, 212, 96, 2, 20, "lo", 2.4))
    out.append(arrow(690, 220, 760, 220, "mid", 2))
    out.append(doc(780, 140, 130, 180, 6, 3, "hi"))
    out.append(cylinder(930, 340, 150, 210, 4, "hi"))
    out.append(arrow(845, 330, 930, 400, "lo", 2, "7 7"))
    out.append(magnifier(1000, 260, 52, "amber", 2.6, 45))
    return out


@scene(S("2026-10-07-t26-"), alt="A fork between building on a company's own pipes and renting a cloud model")
def build_versus_buy(r):
    out = [node(230, 335, "hi", 14), line(150, 335, 216, 335, "mid", 2.2)]
    out.append(curve(244, 335, 380, 335, 380, 200, 520, 200, "mid", 2.2))
    out.append(curve(244, 335, 380, 335, 380, 490, 520, 490, "amber", 2.8))
    out.append(cloud(680, 210, 150, "mid") + window(900, 150, 140, 110, "lo", 1.6, .2) + line(770, 210, 894, 210, "lo", 1.8))
    for k in range(5):
        x = 530 + k * 106
        out.append(rect(x, 444, 94, 96, "hi", 1.9, PANEL if k % 2 else "bg"))
        if k < 4:
            out.append(line(x + 94, 492, x + 106, 492, "amber" if k == 1 else "mid", 2.4))
    out.append(lock(577, 498, 46, "hi", False, False) + rows_of_text(744, 482, 56, 2, 20, "lo", 2.4) + cylinder(956, 464, 46, 60, 3, "hi"))
    out.append(ticks(514, 428, 560, 128, "lo", 16))
    return out


@scene(S("2026-11-10-t49-"), alt="A staged rollout climbing steps, with access cleaned up at each level")
def staged_rollout(r):
    out = [stairs(150, 150, 700, 400, 5, "hi", 3)]
    for k in range(5):
        x = 150 + 700 * k / 5 + 70
        y = 150 + 400 - 400 * (k + 1) / 5 - 56
        if k < 2:
            out.append(check_mark(x - 10, y + 26, 26, "hi", 3))
        elif k == 2:
            out.append(check_mark(x - 10, y + 26, 26, "amber", 3.4))
        else:
            out.append(lock(x + 4, y + 20, 54, "mid", False, False))
    out.append(person(1000, 470, 80, "hi") + path("M1000 540V560", "lo", 1.6))
    out.append(shield(1000, 220, 120, "lo", 1.8))
    return out
