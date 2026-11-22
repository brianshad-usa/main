"""Reference scenes: the featured essays and two frequent subjects. They set the bar for every other scene."""
from art_kit import *  # noqa: F401,F403
from art_scenes import scene


@scene("2026-09-23-t111-a-one-page-technology-risk-summary-for-your-board",
       alt="A faded heat map crossed out, and a ledger of exposures with one decision row highlighted")
def board_ledger(r):
    out = []
    # the old page: a heat map, struck through
    for i in range(4):
        for j in range(4):
            out.append(rect(150 + j * 58, 210 + i * 58, 46, 46, "lo" if (i + j) % 3 else "mid", 1.3, PANEL if (i + j) % 2 else "none"))
    out.append(line(130, 450, 412, 186, "hi", 2.2))
    out.append(arrow(440, 320, 505, 320, "mid", 2))
    # the new page: exposure, consequence, cost, decision
    out.append(table(560, 130, 520, 410, 4, 6, hl_row=2, hl_cell=None))
    for i in range(1, 6):
        out.append(node(1002, 130 + (i + .5) * 410 / 6, "amber" if i == 2 else "hollow", 10))
    out.append(ticks(540, 110, 560, 450, "lo", 16))
    return out


@scene("2026-09-05-t102-modern-ransomware-is-data-theft-why-backups-alone-no-lo",
       alt="A server rack whose copied data leaves along an amber path while the backup restores beside it")
def copied_data(r):
    out = [server(170, 150, 210, 250, 4, "hi")]
    out.append(cylinder(170, 440, 210, 120, 3, "mid"))
    out.append(arrow(275, 440, 275, 408, "hi", 2))
    out.append(check_mark(300, 470, 16, "hi", 2.4))
    out.append(rect(470, 110, 8, 455, "faint", 1.4, "none"))          # the perimeter
    out.append(line(474, 110, 474, 565, "mid", 1.6, "10 9"))
    # the copy that already left
    out.append(curve(380, 300, 520, 300, 520, 220, 660, 220, "amber", 2.6))
    out.append(curve(660, 220, 760, 220, 760, 330, 860, 330, "amber", 2.6, None, 13))
    for k in range(3):
        out.append(doc(880 + k * 22, 250 + k * 26, 130, 170, 5, 1 if k == 2 else None, "hi" if k == 2 else "lo", .18, 1.8))
    out.append(dot(380, 300, 7, "amber"))
    return out


@scene("2026-08-29-t98-an-ai-acceptable-use-policy-your-los-angeles-employees-",
       alt="Rows of app windows on the left and, on the right, data held in nested layers with the innermost sealed")
def data_not_tools(r):
    out = []
    for i in range(3):
        for j in range(3):
            faded = (i + j) % 2 == 1
            out.append(window(140 + j * 118, 170 + i * 108, 98, 78, "lo" if faded else "mid", 1.5, .2))
    out.append(arrow(520, 335, 592, 335, "mid", 2))
    for k, (x, y, w, h, t) in enumerate([(640, 110, 440, 450, "lo"), (700, 170, 320, 330, "mid"), (758, 230, 204, 210, "hi")]):
        out.append(rect(x, y, w, h, t, 1.8, PANEL, r=6))
    out.append(lock(860, 330, 90, "hi"))
    out.append(line(758, 230, 758, 440, "amber", 2.8) + line(962, 230, 962, 440, "amber", 2.8) + line(758, 230, 962, 230, "amber", 2.8) + line(758, 440, 962, 440, "amber", 2.8))
    return out


@scene("2026-09-09-t104-cyber-insurance-questionnaires-answering-accurately-bef",
       alt="A questionnaire beside a system window, with one answer traced to a setting that does not match")
def insurance_form(r):
    out = [doc(170, 110, 330, 455, 0, None, "hi", .1, 2)]
    for i in range(7):
        y = 180 + i * 54
        out.append(rect(210, y - 12, 22, 22, "mid" if i != 3 else "amber", 1.8, "none"))
        if i != 3:
            out.append(check_mark(214, y, 14, "hi", 2))
        out.append(line(254, y, 254 + (170 if i % 3 else 120), y, "lo" if i != 3 else "amber", 2.6))
    out.append(window(700, 150, 370, 300, "hi", 2, .12))
    for i in range(5):
        out.append(line(740, 230 + i * 40, 740 + (200 if i % 2 else 240), 230 + i * 40, "lo", 2.4))
    out.append(curve(456, 342, 560, 342, 600, 310, 740, 310, "amber", 2.4, "7 7", 12))
    out.append(cross_mark(1030, 310, 9, "amber", 2.6))
    out.append(line(740, 310, 1000, 310, "amber", 2.4))
    out.append(rect(620, 110, 4, 455, "faint", 1, "none"))
    return out


@scene("2026-09-17-t108-technology-debt-how-deferred-it-decisions-compound-for-",
       alt="A stack of layers built up over time with one amber line compounding upward above it")
def technology_debt(r):
    out = [line(150, 560, 1070, 560, "mid", 1.8)]
    heights = [34, 40, 46, 58, 70, 86, 104, 128]
    x = 190
    for i, h in enumerate(heights):
        out.append(rect(x, 560 - h, 78, h, "hi" if i < 4 else "mid", 1.7, PANEL))
        for k in range(1, max(2, int(h / 22))):
            out.append(line(x + 10, 560 - h + k * 20, x + 10 + (40 + (k * 13 + i * 7) % 18), 560 - h + k * 20, "lo", 2))
        x += 98
    pts = [(190, 520), (290, 508), (388, 494), (486, 470), (584, 436), (682, 388), (780, 318), (878, 222), (976, 116)]
    out.append(poly(pts, "amber", 2.8))
    for p in pts[:-1:2]:
        out.append(dot(p[0], p[1], 5, "amber"))
    out.append(arrow(930, 162, 984, 108, "amber", 2.8, None, 14))
    for i in range(8):
        out.append(line(230 + i * 98, 560, 230 + i * 98, 572, "mid", 1.4))
    return out


@scene("2026-11-17-t53-security-awareness-training-turning-employees-into-your",
       alt="A suspicious message stopped at a gate, with a separate call to a known number that confirms it")
def verify_by_process(r):
    out = [envelope(130, 210, 190, 124, "hi"), line(352, 272, 448, 272, "mid", 2, "8 8")]
    out.append(barrier(470, 180, 170, 190, "hi", True))
    out.append(line(670, 272, 760, 272, "lo", 2, "8 8"))
    out.append(phone(800, 150, 110, 210, "hi"))
    out.append(curve(856, 360, 856, 470, 640, 500, 560, 500, "hi", 2, None, 12))
    out.append(person(520, 520, 92, "hi"))
    out.append(circ(856, 250, 150, "lo", 1.3, "none", "6 8"))
    out.append(check_mark(835, 242, 42, "amber", 4.4))
    out.append(rect(150, 420, 300, 120, "lo", 1.4, "none", "4 6") + rows_of_text(180, 450, 210, 3, 30, "lo", 2.4))
    return out


@scene("2026-11-20-what-a-microsoft-365-security-assessment-checks",
       alt="A ring of thirteen segments with one highlighted, feeding a findings report sorted by severity")
def assessment_ring(r):
    out = []
    cx, cy, R0, R1 = 360, 338, 118, 206
    for i in range(13):
        a0, a1 = 2 * math.pi * i / 13 - math.pi / 2 + .028, 2 * math.pi * (i + 1) / 13 - math.pi / 2 - .028
        P = lambda rr, a: (cx + rr * math.cos(a), cy + rr * math.sin(a))
        p = [P(R0, a0), P(R1, a0), P(R1, a1), P(R0, a1)]
        hot = i == 2
        d = "M%s %sL%s %sA%s %s 0 0 1 %s %sL%s %sA%s %s 0 0 0 %s %sZ" % (
            n(p[0][0]), n(p[0][1]), n(p[1][0]), n(p[1][1]), n(R1), n(R1), n(p[2][0]), n(p[2][1]), n(p[3][0]), n(p[3][1]), n(R0), n(R0), n(p[0][0]), n(p[0][1]))
        out.append(path(d, "amber" if hot else ("hi" if i % 2 else "mid"), 2.2 if hot else 1.5, AMBER_WASH if hot else "none"))
    out.append(circ(cx, cy, 74, "lo", 1.4) + shield(cx, cy + 2, 78, "hi", 2))
    out.append(arrow(580, 338, 640, 338, "mid", 2))
    out.append(doc(680, 120, 350, 440, 0, None, "hi", .14, 2))
    for i, w_ in enumerate([250, 214, 178, 152, 118, 92]):
        out.append(rect(720, 190 + i * 54, 10, 26, "amber" if i == 0 else "mid", 2, AMBER_WASH if i == 0 else "none") + solid(750, 198 + i * 54, w_ * .8, 8, "amber" if i == 0 else "lo"))
    return out
