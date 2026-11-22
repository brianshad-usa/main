"""Technology Leadership: decisions, budgets, operating models."""
from art_kit import *  # noqa: F401,F403
from art_scenes import S, scene


@scene(S("2026-06-t9-what-is-a-virtual-cio"), alt="A leadership table with a roadmap and one seat highlighted")
def leadership_seat(r):
    out = [rect(330, 270, 540, 150, "hi", 2.2, "bg", r=74)]
    for k, (x, y) in enumerate(((400, 224), (600, 206), (800, 224), (400, 470), (600, 488), (800, 470), (270, 345))):
        hot = k == 1
        out.append(person(x, y, 70, "hi", 1.9, hot))
    out.append(path("M395 345 H805", "lo", 1.6))
    for k in range(5):
        x = 420 + k * 88
        out.append(dot(x, 345, 6, "amber" if k == 2 else "hi"))
    out.append(rect(940, 190, 140, 260, "mid", 1.7, "none", r=4) + linegraph(955, 220, 110, 190, [.1, .22, .34, .3, .55, .72, .9], "hi", 4))
    return out


@scene(S("2026-06-t6-how-to-choose"), alt="Three provider columns compared on the same criteria, one selected")
def provider_columns(r):
    out = []
    for k, x in enumerate((170, 480, 790)):
        hot = k == 1
        out.append(rect(x, 130, 240, 420, "amber" if hot else "mid", 2.4 if hot else 1.7, AMBER_WASH if hot else "none", r=8))
        out.append(person(x + 120, 208, 70, "hi"))
        for i in range(5):
            y = 300 + i * 46
            lens = [(.62, .86, .4, .7, .5), (.9, .72, .96, .8, .88), (.5, .6, .85, .45, .6)][k][i]
            out.append(rect(x + 30, y, 180, 12, "faint", 1.2, "none", r=6) + solid(x + 30, y, 180 * lens, 12, "amber" if hot else "lo", 6))
    return out


@scene(S("2026-06-t5-signs"), alt="Five status dials with one needle in the warning band")
def warning_dials(r):
    out = []
    for k, x in enumerate((210, 405, 600, 795, 990)):
        hot = k == 3
        out.append(gauge(x, 320, 74, .86 if hot else (.36 + .07 * k), "hi", hot))
        out.append(line(x - 70, 372, x + 70, 372, "lo", 1.8) + rows_of_text(x - 52, 400, 104, 2, 26, "lo", 2.4, k))
    out.append(line(140, 500, 1060, 500, "mid", 1.6) + path("M795 500 v-74", "amber", 2.2, "none", "6 7"))
    return out


@scene(S("2026-06-t2-how-much"), alt="Three stacks of coins of rising height with a bracket across the middle one")
def cost_stacks(r):
    out = [line(150, 540, 1050, 540, "mid", 2)]
    for k, (x, count) in enumerate(((300, 5), (600, 9), (900, 13))):
        for i in range(count):
            y = 530 - i * 24
            hot = k == 1 and i >= count - 3
            out.append('<ellipse cx="%s" cy="%s" rx="86" ry="18" stroke="%s" stroke-width="%s" fill="%s"/>' % (n(x), n(y), tone("amber" if hot else "hi"), "2.4" if hot else "1.8", BG))
    out.append(dim(464, 516, 464, 300, "amber") + line(464, 300, 506, 300, "amber", 2))
    out.append(path("M300 400 C420 320 520 260 600 300 C680 340 780 200 900 190", "lo", 1.6, "none", "7 8"))
    return out


@scene(S("2026-06-t0-why-los-angeles"), alt="A spiky line of breakdowns above a steady line of planned upkeep")
def spiky_versus_steady(r):
    out = [line(150, 330, 1060, 330, "lo", 1.5), line(150, 560, 1060, 560, "lo", 1.5), line(150, 110, 150, 560, "lo", 1.5)]
    pts = [(160, 300), (240, 296), (262, 160), (284, 296), (380, 292), (404, 130), (430, 290), (560, 288), (584, 168), (612, 286), (760, 284), (784, 120), (812, 284), (900, 282), (922, 190), (944, 282), (1040, 280)]
    out.append(poly(pts, "hi", 2.2))
    for x, y in ((262, 160), (404, 130), (584, 168), (784, 120), (922, 190)):
        out.append(cross_mark(x, y, 9, "amber", 2.4))
    out.append(path("M160 520 C300 512 420 516 560 508 C700 500 860 498 1040 486", "hi", 2.4))
    for k in range(9):
        out.append(line(190 + k * 100, 530, 190 + k * 100, 548, "lo", 1.8))
    return out


@scene(S("2026-06-09-t81-"), alt="Offices growing in height with one set of systems stretched across them")
def scaling_offices(r):
    out = []
    xs = [(180, 120), (360, 190), (560, 260), (780, 340)]
    for k, (x, h) in enumerate(xs):
        out.append(building(x, 560 - h, 130 + k * 20, h, max(2, int(h / 44)), 2 + (k > 1), "hi", (0, 0) if k == 3 else None))
    out.append(curve(220, 500, 400, 420, 600, 350, 840, 246, "amber", 2.8, None, 0))
    for x, y in ((245, 484), (425, 404), (650, 320)):
        out.append(dot(x, y, 6, "amber"))
    out.append(line(120, 560, 1080, 560, "mid", 2))
    out.append(path("M940 520 V270 M960 520 V300 M980 520 V330", "lo", 1.6))
    out.append(rect(930, 470, 110, 90, "mid", 1.6, "none", "6 6"))
    return out


@scene(S("2026-06-11-t82-"), alt="A move between two offices with a checklist, and the route highlighted")
def relocation_route(r):
    out = [building(140, 210, 190, 340, 6, 3, "hi"), building(860, 150, 220, 400, 7, 3, "hi")]
    out.append(path("M330 470 C440 360 560 520 660 400 C730 320 780 400 858 380", "amber", 2.8, "none", "11 9"))
    out.append(truck(490, 410, 180, 120, "hi"))
    out.append(doc(470, 120, 170, 210, 0, None, "hi", .14, 1.9))
    for i in range(4):
        y = 178 + i * 38
        out.append(rect(492, y - 9, 18, 18, "mid", 1.6) + line(524, y, 524 + (80 if i % 2 else 62), y, "lo", 2.4) + (check_mark(494, y + 2, 11, "hi", 2) if i < 2 else ""))
    out.append(line(120, 550, 1090, 550, "mid", 2))
    return out


@scene(S("2026-06-13-t83-"), alt="Many vendor links to an office replaced by one hub with managed links")
def vendor_hub(r):
    out = [building(150, 240, 150, 260, 5, 2, "hi")]
    pts = [(490, 130), (560, 220), (500, 330), (580, 430), (500, 540), (700, 120), (760, 240), (700, 360), (770, 480)]
    for x, y in pts:
        out.append(rect(x - 34, y - 22, 68, 44, "lo", 1.6, "none", r=4))
        if x < 600:
            out.append(line(300, 370, x - 34, y, "lo", 1.3))
        else:
            out.append(line(x + 34, y, 892, 320, "lo", 1.5))
    out.append(circ(940, 320, 62, "amber", 2.6, AMBER_WASH) + gear(940, 320, 34, 9, "amber"))
    out.append(arrow(1004, 320, 1076, 320, "hi", 2))
    return out


@scene(S("2026-09-19-t109-"), alt="Two overlapping work areas with the dividing line redrawn through the middle")
def redrawn_line(r):
    out = [rect(150, 170, 480, 360, "hi", 2, PANEL, r=6), rect(560, 170, 480, 360, "hi", 2, PANEL2, r=6)]
    for i in range(4):
        for j in range(2):
            out.append(rect(190 + j * 150, 210 + i * 76, 118, 50, "lo", 1.6) + line(206 + j * 150, 235 + i * 76, 290 + j * 150, 235 + i * 76, "lo", 2.4))
            out.append(rect(680 + j * 150, 210 + i * 76, 118, 50, "lo", 1.6) + line(696 + j * 150, 235 + i * 76, 780 + j * 150, 235 + i * 76, "lo", 2.4))
    out.append(path("M596 140 V560", "amber", 2.8, "none", "12 8"))
    out.append(path("M640 140 C560 260 690 380 590 560", "amber", 2.6))
    return out


@scene(S("2026-09-21-t110-"), alt="A contract listing devices while identities and connections sit outside the count")
def contract_counts(r):
    out = [contract(150, 120, 300, 430, "hi", False)]
    for i in range(3):
        for j in range(4):
            out.append(rect(196 + j * 58, 210 + i * 70, 40, 30, "lo", 1.6, "none", r=3) + line(204 + j * 58, 244 + i * 70, 226 + j * 58, 244 + i * 70, "lo", 2))
    pts = [(600, 160), (720, 240), (640, 350), (830, 160), (900, 290), (770, 430), (960, 420), (640, 510), (860, 530), (1030, 220), (1040, 520)]
    out.append(mesh(pts, 190, "lo", 1.2))
    for k, (x, y) in enumerate(pts):
        out.append(node(x, y, "amber" if k == 4 else "hollow", 13 if k == 4 else 10))
    out.append(path("M470 340 H548", "mid", 2, "none", "8 8") + ticks(570, 130, 500, 420, "lo", 18))
    return out


@scene(S("2026-10-21-t33-"), alt="Four clocks running at different speeds, one of them set apart")
def four_clocks(r):
    out = []
    xs = [230, 475, 720, 965]
    for k, x in enumerate(xs):
        hot = k == 2
        out.append(clock(x, 300, 104, [9, 11, 3, 5][k], [5, 35, 15, 50][k], "hi", hot))
        out.append(circ(x, 300, 126, "amber" if hot else "lo", 2.4 if hot else 1.4, "none", None if hot else "6 8"))
        out.append(line(x - 70, 466, x + 70, 466, "lo", 1.8) + rows_of_text(x - 56, 492, 112, 2, 24, "lo", 2.4, k))
    out.append(line(140, 300, 120, 300, "faint", 1.2))
    return out
