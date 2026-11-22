"""Cloud & Infrastructure, Governance & Compliance, Business Continuity."""
from art_kit import *  # noqa: F401,F403
from art_scenes import S, scene


# ---- Cloud & Infrastructure -----------------------------------------------------------------------------------

@scene(S("2026-06-t4-microsoft-365-vs"), alt="Two platforms compared criterion by criterion, with one deciding row highlighted")
def platform_balance(r):
    out = []
    for x in (330, 870):
        out.append(cloud(x, 190, 150, "hi"))
    lens = [((.9, .62), (.7, .85)), ((.55, .78), (.8, .6)), ((.82, .7), (.66, .9)), ((.6, .9), (.9, .58))]
    for k, (a, b) in enumerate(lens):
        y = 300 + k * 62
        hot = k == 2
        for x, pair in ((170, a), (690, b)):
            out.append(rect(x, y, 340, 34, "amber" if hot else "lo", 2.2 if hot else 1.5, AMBER_WASH if hot else "none", r=4))
            for j, v in enumerate(pair):
                out.append(solid(x + 16 + j * 160, y + 12, 140 * v, 10, "amber" if hot else "mid", 5))
    out.append(line(600, 250, 600, 560, "faint", 1.6, "6 8"))
    return out


@scene(S("2026-07-19-t9-cloud"), alt="Packages crossing a bridge from a server room to the cloud, one in transit")
def migration_bridge(r):
    out = [server(140, 240, 200, 260, 5, "hi"), cloud(950, 330, 190, "hi")]
    out.append(line(350, 480, 800, 480, "mid", 2.4) + path("M350 480 Q575 330 800 480", "lo", 1.8))
    for x in (430, 500, 575, 650, 720):
        u = (x - 350) / 450
        out.append(line(x, 480, x, 480 - 2 * u * (1 - u) * 150, "faint", 1.4))
    for k, x in enumerate((405, 540, 675)):
        hot = k == 1
        out.append(rect(x, 408, 76, 60, "amber" if hot else "hi", 2.4 if hot else 1.9, AMBER_WASH if hot else "bg", r=4) + line(x + 12, 438, x + 64, 438, "amber" if hot else "lo", 2.4))
        out.append(arrow(x + 84, 438, x + 116, 438, "lo", 1.8))
    out.append(arrow(800, 400, 852, 376, "mid", 2))
    return out


@scene(S("2026-09-27-t113-"), alt="Rows of computers past an end date, with one kept in a side closet")
def unmanaged_devices(r):
    out = [calendar(150, 120, 250, 180, (3, 4, 5, 12, 13, 19), "hi", 24)]
    for i in range(3):
        for j in range(4):
            gone = (i, j) in ((0, 1), (1, 2), (2, 0))
            out.append(laptop(470 + j * 118, 150 + i * 130, 92, 64, "faint" if gone else "lo"))
    out.append(rect(980, 250, 110, 300, "mid", 2, "bg", r=2) + line(1060, 400, 1060, 416, "lo", 3))
    out.append(laptop(1000, 440, 70, 52, "amber"))
    out.append(path("M1000 420 C960 420 940 440 920 470", "amber", 2.2, "none", "7 7"))
    out.append(line(120, 350, 440, 350, "lo", 1.6, "8 8") + path("M120 350 V560 H440", "faint", 1.4) + rows_of_text(150, 390, 220, 3, 36, "lo", 2.4))
    return out


@scene(S("2026-10-11-t28-"), alt="Headcount rising in a line while identities and access curve upward faster")
def growth_curves(r):
    out = [line(170, 560, 1060, 560, "mid", 2), line(170, 130, 170, 560, "mid", 2)]
    out.append(poly([(180, 540), (360, 500), (540, 460), (720, 420), (900, 380), (1040, 348)], "hi", 2.4))
    out.append(poly([(180, 540), (360, 486), (540, 420), (720, 312), (900, 208), (1040, 120)], "amber", 2.8))
    for x in range(260, 1060, 180):
        out.append(line(x, 560, x, 574, "lo", 1.5) + path("M%s 540 V560" % x, "faint", 1.2))
    for k, x in enumerate((240, 300, 360)):
        out.append(person(x, 210, 40 + 6 * k, "lo"))
    return out


# ---- Governance & Compliance -----------------------------------------------------------------------------------

@scene(S("2026-06-t1-hipaa"), alt="A clinical checklist on a clipboard with one unfinished item")
def clinical_checklist(r):
    out = [rect(390, 100, 320, 470, "hi", 2, "bg", r=10), rect(490, 78, 120, 44, "mid", 1.9, "bg", r=8)]
    out.append(cross(550, 190, 90, "lo", 1.8))
    for i in range(5):
        y = 270 + i * 54
        hot = i == 3
        out.append(rect(430, y - 12, 24, 24, "amber" if hot else "mid", 1.9, AMBER_WASH if hot else "none"))
        if not hot:
            out.append(check_mark(435, y + 2, 15, "hi", 2.2))
        out.append(line(476, y, 476 + (150 if i % 2 else 184), y, "lo", 2.6))
    out.append(shield(900, 320, 150, "lo", 1.8) + lock(230, 320, 110, "lo", False, False))
    return out


@scene(S("2026-08-28-t97-"), alt="An empty chair beside an access key that was never returned")
def unreturned_key(r):
    out = [path("M180 300 V470 M300 300 V470 M180 390 H300 M180 300 H300 V250 H180Z M170 470 H190 M290 470 H310", "mid", 2.2)]
    out.append(path("M470 180 V560", "faint", 1.4, "none", "6 8"))
    for k in range(6):
        x, y = 620, 150 + k * 70
        hot = k == 3
        out.append(rect(x, y, 400, 50, "amber" if hot else "lo", 2.2 if hot else 1.5, AMBER_WASH if hot else "none", r=4))
        mark = key(x + 48, y + 27, 54, "amber", 2.4) if hot else dot(x + 34, y + 25, 8, "mid")
        out.append(mark + line(x + 100, y + 25, x + (310 if k % 2 else 250), y + 25, "amber" if hot else "lo", 2.6))
    out.append(curve(300, 430, 420, 470, 520, 400, 608, 386, "amber", 2.4, "9 8", 13))
    return out


@scene(S("2026-09-25-t112-"), alt="A chain link between two companies examined closely instead of either building")
def examine_link(r):
    out = [building(130, 180, 200, 370, 7, 3, "hi"), building(870, 180, 200, 370, 7, 3, "hi")]
    out.append(path("M330 360 H420 M780 360 H870", "mid", 2.2))
    out.append(chain(470, 360, 5, 74, "hi", 2))
    out.append(magnifier(600, 360, 130, "amber", 3, 45))
    for a in (1, 2, 3):
        out.append(line(530 + a * 8, 520 + a * 12, 560 + a * 8, 520 + a * 12, "faint", 1.4))
    return out


@scene(S("2026-09-29-t114-"), alt="Archive boxes piling up over time with a cut-off mark through the oldest")
def archive_cutoff(r):
    out = [line(130, 560, 1080, 560, "mid", 2)]
    for k in range(7):
        x = 170 + k * 124
        for i in range(k + 1):
            hot = k == 0 and i == 0
            out.append(rect(x, 510 - i * 50, 92, 46, "amber" if hot else ("mid" if k < 3 else "hi"), 1.9, AMBER_WASH if hot else "none", r=3) + line(x + 30, 526 - i * 50, x + 62, 526 - i * 50, "amber" if hot else "lo", 2.4))
    out.append(path("M140 480 H420", "amber", 2.6, "none", "12 8") + path("M410 470 l14 10 l-14 10", "amber", 2.4))
    out.append(hourglass(1010, 240, 130, "hi", True))
    return out


@scene(S("2026-10-01-t115-"), alt="A list of accounts where most switches are turned off by default")
def default_revoke(r):
    out = [rect(260, 110, 680, 450, "hi", 2, PANEL, r=8), line(260, 190, 940, 190, "mid", 1.7)]
    for i in range(6):
        y = 222 + i * 54
        out.append(person(310, y + 14, 26, "mid") + line(350, y + 4, 350 + (240 if i % 2 else 290), y + 4, "lo", 2.4) + line(350, y + 22, 350 + (150 if i % 2 else 190), y + 22, "faint", 2))
        out.append(toggle(830, y - 6, 72, i in (1, 3, 4)))
    for k in range(4):
        hot = k == 3
        out.append(circ(160, 230 + k * 94, 26, "amber" if hot else "lo", 2.4 if hot else 1.8, AMBER_WASH if hot else "bg"))
        if k < 3:
            out.append(line(160, 256 + k * 94, 160, 298 + k * 94, "lo", 1.4))
    return out


@scene(S("2026-10-05-t25-"), alt="A binder set aside while a live activity log is verified line by line")
def evidence_log(r):
    out = [rect(150, 180, 200, 310, "lo", 1.8, "bg", r=4), line(188, 180, 188, 490, "lo", 1.8), rect(206, 226, 110, 60, "faint", 1.4), line(150, 180, 350, 490, "mid", 2)]
    out.append(arrow(390, 330, 450, 330, "mid", 2))
    out.append(rect(490, 110, 400, 460, "hi", 2, "bg", r=6))
    for i, w_ in enumerate((230, 280, 190, 260, 300, 210, 240, 280, 180)):
        y = 160 + i * 44
        hot = i == 4
        out.append(dot(526, y, 5, "amber" if hot else "mid") + line(552, y, 552 + w_, y, "amber" if hot else "lo", 3 if hot else 2.4))
    out.append(magnifier(980, 330, 84, "hi", 2.6, 45) + path("M880 336 L912 336", "amber", 2.4))
    return out


# ---- Business Continuity ----------------------------------------------------------------------------------------

@scene(S("2026-07-17-t8-it-disaster"), alt="A primary site failing over to a second one, with the switch highlighted")
def failover(r):
    out = [server(150, 170, 210, 290, 5, "lo"), cross_mark(255, 130, 22, "amber", 3), server(840, 170, 210, 290, 5, "hi", 1)]
    out.append(cloud(600, 410, 190, "mid"))
    out.append(curve(380, 260, 460, 130, 740, 130, 830, 250, "amber", 3, None, 15))
    out.append(path("M260 480 V560 H520 M680 560 H940 V480", "lo", 1.6, "none", "8 8"))
    return out


@scene(S("2026-08-07-t20-wildfire"), alt="Power lines down beside a hillside fire while one office keeps its light on")
def shutoff_office(r):
    out = [path("M80 560 C260 470 380 520 520 480 C700 430 820 500 1120 440 V600 H80Z", "lo", 1.8, "rgba(255,255,255,.03)")]
    for x, y, h in ((190, 260, 240), (420, 250, 230), (650, 270, 200)):
        out.append(pole(x, y, h, "mid"))
    out.append(path("M220 290 C320 330 330 330 394 284 M450 282 C540 320 570 320 620 300", "lo", 1.6))
    out.append(path("M650 296 q60 60 40 120", "mid", 2, "none", "8 8") + cross_mark(690, 330, 12, "hi", 2.4))
    out.append(flame(880, 340, 150, "amber", 2.4))
    out.append(building(960, 300, 120, 200, 4, 2, "hi", (1, 0)))
    out.append(rect(930, 520, 170, 14, "mid", 1.6))
    return out


@scene(S("2026-09-07-t103-"), alt="A backup vault on a timed lock that blocks even an administrator's delete")
def timed_vault(r):
    out = [cylinder(220, 170, 260, 340, 4, "hi"), hourglass(350, 350, 130, "hi", True)]
    out.append(person(820, 330, 130, "mid") + path("M740 330 H660", "amber", 3, "none", "10 8"))
    out.append(barrier(560, 210, 120, 280, "hi", True))
    out.append(cross_mark(706, 330, 15, "amber", 2.8))
    out.append(lock(960, 250, 110, "lo", False, False) + dim(560, 540, 680, 540, "lo"))
    return out


@scene(S("2026-09-15-t107-"), alt="An emergency key sealed in a glass case beside a locked door")
def break_glass(r):
    out = [rect(180, 150, 300, 380, "hi", 2.2, "bg", r=6), rect(206, 176, 248, 328, "mid", 1.5, "rgba(255,255,255,.025)", r=3)]
    out.append(key(330, 330, 170, "amber", 3, 12) + path("M240 210 L300 290 L262 330 L320 400 M300 290 L350 250", "lo", 1.6))
    out.append(rect(600, 130, 230, 430, "hi", 2, "bg", r=3) + circ(780, 350, 11, "hi", 2) + rect(640, 180, 150, 120, "lo", 1.6) + rect(640, 340, 110, 150, "lo", 1.6))
    out.append(lock(930, 350, 120, "lo", False, False) + path("M480 350 H600", "lo", 1.8, "none", "8 8"))
    return out
