#!/usr/bin/env python3
"""
Generate industry landing pages batch 1 of 5.
Pages: financial-services-it-los-angeles.html
       real-estate-it-services.html
Run:   python build_industries_1.py
"""
import os, json, re

OUT = r"C:\Users\brian.shad\prolink-landing-page\main"

# ─── CSS (identical to healthcare-it-services.html) ──────────────────────────
CSS = r"""
    /* -- INDUSTRY HERO ------------------------------------------------- */
    .hero {
      background: linear-gradient(135deg, #06141d 0%, #082638 55%, #093550 100%);
      min-height: calc(100dvh - 72px);
      display: flex; align-items: stretch;
      position: relative; overflow: hidden;
    }
    .hero::before {
      content: '';
      position: absolute; inset: 0;
      background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.025'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
      pointer-events: none;
    }
    .hero::after {
      content: '';
      position: absolute; bottom: -150px; left: -100px;
      width: 500px; height: 500px; border-radius: 50%;
      background: radial-gradient(circle, rgba(245,166,35,0.07) 0%, transparent 70%);
      pointer-events: none;
    }
    .hero-inner {
      flex: 1; max-width: 1400px; margin: 0 auto;
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 32px; padding: 36px 28px;
      align-items: start; position: relative; z-index: 1;
    }
    .hero-left { display: flex; flex-direction: column; gap: 20px; }
    .industry-badge {
      display: inline-flex; align-items: center; gap: 8px;
      background: rgba(245,166,35,.12); border: 1px solid rgba(245,166,35,.35);
      color: var(--gold); font-size: .72rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: .1em;
      padding: 5px 14px; border-radius: 100px; align-self: flex-start;
    }
    .hero-title {
      font-size: clamp(1.8rem, 3vw, 2.6rem);
      font-weight: 800; color: #fff; line-height: 1.15; letter-spacing: -.03em; margin: 0;
    }
    .hero-title em { font-style: normal; color: var(--gold); }
    .hero-subtitle { font-size: 1rem; color: rgba(255,255,255,.72); line-height: 1.7; max-width: 480px; }
    .value-list { display: flex; flex-direction: column; gap: 10px; }
    .value-item {
      display: flex; align-items: flex-start; gap: 12px;
      background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1);
      border-radius: var(--r-md); padding: 14px 16px;
    }
    .value-icon {
      width: 36px; height: 36px; flex-shrink: 0; border-radius: 8px;
      background: rgba(245,166,35,.15); display: flex; align-items: center; justify-content: center;
    }
    .value-icon svg { color: var(--gold); }
    .value-text h4 { font-size: .88rem; font-weight: 700; color: #fff; margin-bottom: 2px; }
    .value-text p { font-size: .78rem; color: rgba(255,255,255,.6); line-height: 1.5; }
    /* -- VIDEO ---------------------------------------------------------- */
    .video-block {
      position: relative; border-radius: var(--r-lg);
      overflow: hidden; background: #000; aspect-ratio: 16/9;
    }
    .video-block video { width: 100%; height: 100%; display: block; object-fit: cover; }
    .video-overlay {
      position: absolute; bottom: 0; left: 0; right: 0;
      background: linear-gradient(transparent, rgba(0,0,0,.75));
      padding: 20px 16px 14px;
    }
    .video-client-badge {
      display: inline-flex; align-items: center; gap: 7px;
      background: rgba(245,166,35,.2); border: 1px solid rgba(245,166,35,.4);
      color: var(--gold); font-size: .68rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: .07em;
      padding: 3px 10px; border-radius: 4px; margin-bottom: 6px;
    }
    .video-client-name { color: #fff; font-size: .82rem; font-weight: 600; }
    .video-client-sub { color: rgba(255,255,255,.65); font-size: .75rem; margin-top: 1px; }
    .vid-loading {
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      background: rgba(6,20,29,.8); opacity: 0; transition: opacity .2s; pointer-events: none;
    }
    .vid-loading.show { opacity: 1; }
    .vid-spinner {
      width: 36px; height: 36px; border: 3px solid rgba(255,255,255,.2);
      border-top-color: var(--gold); border-radius: 50%; animation: spin .7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .unmute-btn {
      position: absolute; bottom: 10px; right: 10px;
      display: flex; align-items: center; gap: 6px;
      background: rgba(0,0,0,.6); backdrop-filter: blur(6px);
      border: 1.5px solid rgba(255,255,255,.25); border-radius: 100px;
      color: rgba(255,255,255,.9); font-size: .72rem; font-weight: 600;
      padding: 5px 12px; cursor: pointer; transition: background .2s; z-index: 10;
    }
    .unmute-btn:hover { background: rgba(0,0,0,.85); }
    /* -- FORM ----------------------------------------------------------- */
    .hero-right { position: sticky; top: 20px; }
    .form-card {
      background: #fff; border-radius: var(--r-xl); padding: 28px 26px;
      box-shadow: 0 24px 64px rgba(0,0,0,.28), 0 8px 20px rgba(0,0,0,.12);
    }
    .form-card-head { margin-bottom: 18px; }
    .form-card-head h2 { font-size: 1.05rem; font-weight: 800; color: var(--text); letter-spacing: -.02em; margin-bottom: 4px; }
    .form-card-head p { font-size: .78rem; color: var(--text-muted); line-height: 1.5; }
    .form-badge {
      display: inline-flex; align-items: center; gap: 5px;
      background: #fff8ed; border: 1px solid #fdd28a;
      color: #92400e; font-size: .68rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: .06em;
      padding: 3px 10px; border-radius: 4px; margin-bottom: 10px;
    }
    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .form-group { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
    .form-group label { font-size: .72rem; font-weight: 600; color: var(--text); letter-spacing: .02em; }
    .form-group label .req { color: var(--gold-dark); margin-left: 1px; }
    .form-group input, .form-group select, .form-group textarea {
      font-family: 'Inter', sans-serif; font-size: .82rem; color: var(--text);
      background: var(--off-white); border: 1.5px solid var(--border);
      border-radius: var(--r-sm); padding: 9px 11px;
      transition: border-color .2s, box-shadow .2s; outline: none; width: 100%;
    }
    .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
      border-color: var(--navy-light); box-shadow: 0 0 0 3px rgba(23,98,168,.12); background: var(--white);
    }
    .form-group textarea { resize: vertical; min-height: 68px; line-height: 1.55; }
    .form-group select {
      cursor: pointer; appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='11' height='11' viewBox='0 0 24 24' fill='none' stroke='%235a6a80' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right 11px center; padding-right: 28px;
    }
    .form-error { font-size: .7rem; color: #dc2626; margin-top: 1px; display: none; }
    .form-group.has-error input, .form-group.has-error select, .form-group.has-error textarea { border-color: #dc2626; }
    .form-group.has-error .form-error { display: block; }
    .submit-btn {
      width: 100%; padding: 12px 20px; border-radius: var(--r-md);
      background: var(--navy); color: #fff;
      font-family: 'Inter', sans-serif; font-size: .875rem; font-weight: 700;
      border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 8px;
      transition: background .2s, transform .15s;
    }
    .submit-btn:hover:not(:disabled) { background: var(--navy-light); transform: translateY(-1px); }
    .submit-btn:disabled { opacity: .7; cursor: not-allowed; }
    .submit-btn .spinner {
      width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3);
      border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; display: none;
    }
    .submit-btn.loading .btn-label, .submit-btn.loading .btn-arrow { display: none; }
    .submit-btn.loading .spinner { display: block; }
    .form-privacy { font-size: .68rem; color: var(--text-muted); text-align: center; margin-top: 8px; line-height: 1.4; }
    .form-success { display: none; text-align: center; padding: 32px 16px 24px; animation: fsUp .45s ease; }
    .form-success.show { display: block; }
    .form-body.hide { display: none; }
    @keyframes fsUp { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:none; } }
    .success-orbit {
      width: 64px; height: 64px;
      background: linear-gradient(135deg, #0b3d6b, #1762a8);
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
      margin: 0 auto 14px;
      animation: successPop .5s cubic-bezier(.34,1.56,.64,1);
    }
    @keyframes successPop { from { transform:scale(0); opacity:0; } to { transform:scale(1); opacity:1; } }
    .success-pill {
      display: inline-flex; align-items: center; gap: 6px;
      background: #f0fdf4; border: 1px solid #86efac;
      color: #166534; font-size: .72rem; font-weight: 700;
      padding: 4px 12px; border-radius: 100px; margin-bottom: 12px;
    }
    .success-pill-dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; }
    .form-success h3 { font-size: 1.1rem; font-weight: 800; color: var(--text); margin-bottom: 6px; }
    .form-success p { font-size: .82rem; color: var(--text-muted); line-height: 1.6; margin-bottom: 16px; }
    .success-cta-phone {
      display: inline-flex; align-items: center; gap: 8px;
      background: var(--navy); color: #fff;
      font-size: .85rem; font-weight: 700;
      padding: 10px 22px; border-radius: var(--r-md);
      text-decoration: none; transition: background .2s;
    }
    .success-cta-phone:hover { background: var(--navy-light); }
    /* -- COMPLIANCE BAR ------------------------------------------------ */
    .compliance-bar {
      background: #040f17;
      padding: 16px 32px;
      display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 32px;
    }
    .comp-item {
      display: flex; align-items: center; gap: 8px;
      color: rgba(255,255,255,.85); font-size: .8rem; font-weight: 600;
    }
    .comp-item svg { color: var(--gold); flex-shrink: 0; }
    /* -- CHALLENGES ---------------------------------------------------- */
    .challenge-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: start; }
    .challenge-list { display: flex; flex-direction: column; gap: 16px; }
    .challenge-item {
      display: flex; align-items: flex-start; gap: 14px;
      padding: 18px 20px; border-radius: var(--r-md);
      background: #fff; border: 1px solid var(--border); box-shadow: var(--sh-sm);
    }
    .challenge-icon {
      width: 40px; height: 40px; flex-shrink: 0; border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
    }
    .challenge-icon.risk { background: #fef2f2; }
    .challenge-icon.risk svg { color: #dc2626; }
    .challenge-icon.solved { background: #f0fdf4; }
    .challenge-icon.solved svg { color: #16a34a; }
    .challenge-item h4 { font-size: .9rem; font-weight: 700; color: var(--text); margin-bottom: 4px; }
    .challenge-item p { font-size: .82rem; color: var(--text-muted); line-height: 1.55; }
    .challenge-side-head { margin-bottom: 28px; }
    /* -- SERVICES ------------------------------------------------------ */
    .service-card {
      background: var(--white); border: 1px solid var(--border);
      border-radius: var(--r-lg); padding: 30px 28px;
      box-shadow: var(--sh-sm); transition: transform .2s, box-shadow .2s;
      display: flex; flex-direction: column; gap: 12px;
    }
    .service-card:hover { transform: translateY(-4px); box-shadow: var(--sh-md); }
    .service-card-icon {
      width: 48px; height: 48px; border-radius: var(--r-sm);
      background: rgba(245,166,35,.1); display: flex; align-items: center; justify-content: center;
    }
    .service-card-icon svg { color: var(--navy); }
    .service-card h3 { font-size: 1rem; font-weight: 700; color: var(--text); }
    .service-card p { font-size: .875rem; color: var(--text-muted); line-height: 1.65; flex: 1; }
    .service-card ul { padding-left: 16px; display: flex; flex-direction: column; gap: 4px; }
    .service-card ul li { font-size: .82rem; color: var(--text-muted); line-height: 1.5; }
    /* -- TESTIMONIAL --------------------------------------------------- */
    .testimonial-block {
      background: linear-gradient(135deg, #06141d, #093550);
      border-radius: var(--r-xl); padding: 48px 40px;
      display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: center;
    }
    .testimonial-quote { font-size: 1.1rem; font-weight: 500; color: #fff; line-height: 1.75; font-style: italic; margin-bottom: 24px; }
    .testimonial-quote::before { content: '\201C'; font-size: 3rem; color: var(--gold); line-height: 0; vertical-align: -0.5em; margin-right: 4px; }
    .testimonial-author { display: flex; align-items: center; gap: 14px; }
    .testimonial-avatar {
      width: 48px; height: 48px; border-radius: 50%;
      background: var(--gold); display: flex; align-items: center; justify-content: center;
      font-size: 1.1rem; font-weight: 800; color: var(--navy-dark); flex-shrink: 0;
    }
    .testimonial-name { font-weight: 700; color: #fff; font-size: .9rem; }
    .testimonial-role { font-size: .8rem; color: rgba(255,255,255,.6); margin-top: 2px; }
    .testimonial-stars { display: flex; gap: 3px; margin-bottom: 12px; }
    .testimonial-stars svg { color: var(--gold); }
    /* -- FAQ ------------------------------------------------------------ */
    .faq-list { display: flex; flex-direction: column; gap: 12px; max-width: 800px; margin: 0 auto; }
    .faq-item { border: 1px solid var(--border); border-radius: var(--r-md); overflow: hidden; background: var(--white); }
    .faq-question {
      width: 100%; text-align: left; padding: 18px 22px;
      background: none; border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      font-family: 'Inter', sans-serif; font-size: .92rem; font-weight: 700;
      color: var(--text); transition: background .15s;
    }
    .faq-question:hover { background: var(--off-white); }
    .faq-question svg { flex-shrink: 0; transition: transform .2s; color: var(--navy); }
    .faq-question.open svg { transform: rotate(180deg); }
    .faq-answer { display: none; padding: 0 22px 18px; font-size: .875rem; color: var(--text-muted); line-height: 1.7; }
    .faq-answer.open { display: block; }
    /* -- RESPONSIVE ---------------------------------------------------- */
    @media (max-width: 1024px) {
      .hero-inner { grid-template-columns: 1fr; }
      .hero-right { position: static; }
      .challenge-grid { grid-template-columns: 1fr; }
      .testimonial-block { grid-template-columns: 1fr; }
    }
    @media (max-width: 768px) {
      .hero-inner { padding: 24px 20px; }
      .compliance-bar { gap: 16px; padding: 14px 20px; }
      .form-row { grid-template-columns: 1fr; }
    }
"""

# ─── SHARED SVG SNIPPETS ──────────────────────────────────────────────────────
PHONE_PATH = '<path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 11a19.79 19.79 0 01-3-8.57A2 2 0 012.04 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/>'
STAR_PATH  = '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>'
CHEVRON    = '<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>'
ARROW_R    = '<svg class="btn-arrow" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>'
CHECK_G    = '<svg width="20" height="20" fill="none" stroke="var(--green)" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>'

def stars():
    s = '<svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24">' + STAR_PATH + '</svg>'
    return '<div class="testimonial-stars">' + s * 5 + '</div>'

def shield16():
    return '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'

def clock16():
    return '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'

def check16():
    return '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>'

# Risk icons (20x20 for challenge items)
RISK_TRI  = '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
RISK_CIRC = '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
RISK_LOCK = '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>'
RISK_MON  = '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>'
SOLV_CHK  = '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>'

# Service card icons (24x24)
def ico24(path):
    return '<svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">' + path + '</svg>'

ICO = {
    'shield':    ico24('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'),
    'activity':  ico24('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'),
    'lock':      ico24('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>'),
    'wifi':      ico24('<path d="M1.42 9a16 16 0 0121.16 0"/><path d="M5 12.55a11 11 0 0114.08 0"/><path d="M10.54 16.1a6 6 0 012.92 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>'),
    'refresh':   ico24('<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>'),
    'phone':     ico24(PHONE_PATH),
    'server':    ico24('<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>'),
    'cloud':     ico24('<path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z"/>'),
    'home':      ico24('<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'),
    'dollar':    ico24('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>'),
}

# Value-item icons (18x18)
def ico18(path):
    return '<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' + path + '</svg>'

VICO = {
    'shield':   ico18('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'),
    'activity': ico18('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'),
    'clock':    ico18('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'),
    'home':     ico18('<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'),
    'wifi':     ico18('<path d="M1.42 9a16 16 0 0121.16 0"/><path d="M5 12.55a11 11 0 0114.08 0"/><path d="M10.54 16.1a6 6 0 012.92 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>'),
    'lock':     ico18('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>'),
    'dollar':   ico18('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>'),
    'server':   ico18('<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>'),
}

# ─── HTML BUILDERS ───────────────────────────────────────────────────────────

def comp_icon(kind):
    return shield16() if kind == 'shield' else (clock16() if kind == 'clock' else check16())

def comp_item(kind, text):
    return '<div class="comp-item">' + comp_icon(kind) + '\n    ' + text + '\n  </div>'

def value_item(ico_key, h4, p):
    return (
        '<div class="value-item"><div class="value-icon">' + VICO[ico_key] + '</div>'
        '<div class="value-text"><h4>' + h4 + '</h4><p>' + p + '</p></div></div>'
    )

def risk_item(ico, h4, p):
    return (
        '<div class="challenge-item"><div class="challenge-icon risk">' + ico + '</div>'
        '<div><h4>' + h4 + '</h4><p>' + p + '</p></div></div>'
    )

def solv_item(h4, p):
    return (
        '<div class="challenge-item"><div class="challenge-icon solved">' + SOLV_CHK + '</div>'
        '<div><h4>' + h4 + '</h4><p>' + p + '</p></div></div>'
    )

def svc_card(ico_key, h3, p, bullets):
    lis = ''.join('<li>' + b + '</li>' for b in bullets)
    return (
        '<div class="service-card"><div class="service-card-icon">' + ICO[ico_key] + '</div>'
        '<h3>' + h3 + '</h3><p>' + p + '</p>'
        '<ul>' + lis + '</ul></div>'
    )

def faq_item_html(q, a):
    return (
        '<div class="faq-item"><button class="faq-question" onclick="toggleFaq(this)">'
        + q + '\n          ' + CHEVRON +
        '</button><div class="faq-answer">' + a + '</div></div>'
    )

def bullet_item(text):
    return '<div style="display:flex;align-items:center;gap:12px;">' + CHECK_G + '<span style="font-size:.9rem;color:var(--text);">' + text + '</span></div>'

def stat_box(num, label, gold=False):
    if gold:
        bg = 'background:#fff8ed;border:1px solid #fdd28a;'
        nc = '#92400e'
    else:
        bg = 'background:var(--off-white);'
        nc = 'var(--navy)'
    return (
        '<div style="' + bg + 'border-radius:var(--r-lg);padding:28px 20px;text-align:center;">'
        '<div style="font-size:2.2rem;font-weight:800;color:' + nc + ';line-height:1;">' + num + '</div>'
        '<div style="font-size:.8rem;color:var(--text-muted);margin-top:6px;">' + label + '</div></div>'
    )

# ─── PAGE BUILDER ────────────────────────────────────────────────────────────

def build_page(d):
    can = 'https://prolinksystems.com/' + d['can']

    # ── Schema (string concat to avoid f-string {} conflicts) ──
    offers_json = ',\n        '.join(
        '{"@type":"Offer","itemOffered":{"@type":"Service","name":"' + o + '"}}' for o in d['offers']
    )
    faq_entities = ',\n      '.join(
        '{"@type":"Question","name":' + json.dumps(q['q_plain']) +
        ',"acceptedAnswer":{"@type":"Answer","text":' + json.dumps(q['a_plain']) + '}}'
        for q in d['faq']
    )

    schema_lb = (
        '  <script type="application/ld+json">\n'
        '  {\n'
        '    "@context": "https://schema.org",\n'
        '    "@type": "LocalBusiness",\n'
        '    "name": "Pro Link Systems",\n'
        '    "url": "' + can + '",\n'
        '    "logo": "https://prolinksystems.com/logo.png",\n'
        '    "description": ' + json.dumps(d['schema_desc']) + ',\n'
        '    "foundingDate": "1999",\n'
        '    "telephone": "+18008906133",\n'
        '    "email": "info@prolinksystems.com",\n'
        '    "address": {\n'
        '      "@type": "PostalAddress",\n'
        '      "streetAddress": "21241 Ventura Boulevard",\n'
        '      "addressLocality": "Woodland Hills",\n'
        '      "addressRegion": "CA",\n'
        '      "postalCode": "91364",\n'
        '      "addressCountry": "US"\n'
        '    },\n'
        '    "areaServed": [\n'
        '      {"@type":"City","name":"Los Angeles"},\n'
        '      {"@type":"City","name":"Woodland Hills"},\n'
        '      {"@type":"City","name":"Burbank"},\n'
        '      {"@type":"City","name":"Glendale"},\n'
        '      {"@type":"City","name":"Santa Monica"},\n'
        '      {"@type":"City","name":"Torrance"},\n'
        '      {"@type":"City","name":"Pasadena"}\n'
        '    ],\n'
        '    "priceRange": "$$",\n'
        '    "hasOfferCatalog": {\n'
        '      "@type": "OfferCatalog",\n'
        '      "name": "' + d['offers_label'] + '",\n'
        '      "itemListElement": [\n        ' + offers_json + '\n      ]\n'
        '    },\n'
        '    "sameAs": ["https://www.linkedin.com/company/pro-link-systems"]\n'
        '  }\n'
        '  </script>\n'
    )
    schema_bc = (
        '  <script type="application/ld+json">\n'
        '  {\n'
        '    "@context": "https://schema.org",\n'
        '    "@type": "BreadcrumbList",\n'
        '    "itemListElement": [\n'
        '      {"@type":"ListItem","position":1,"name":"Home","item":"https://prolinksystems.com/"},\n'
        '      {"@type":"ListItem","position":2,"name":"' + d['bc_name'] + '","item":"' + can + '"}\n'
        '    ]\n'
        '  }\n'
        '  </script>\n'
    )
    schema_faq = (
        '  <script type="application/ld+json">\n'
        '  {\n'
        '    "@context": "https://schema.org",\n'
        '    "@type": "FAQPage",\n'
        '    "mainEntity": [\n      ' + faq_entities + '\n    ]\n'
        '  }\n'
        '  </script>\n'
    )

    # ── Form dropdowns ──
    org_opts = '<option value="">Select&hellip;</option>' + ''.join('<option>' + o + '</option>' for o in d['org_opts'])
    ch_opts  = '<option value="">Select&hellip;</option>' + ''.join('<option>' + o + '</option>' for o in d['ch_opts'])

    # ── Compliance bar ──
    comp_bar = '\n  '.join(comp_item(k, t) for k, t in d['compliance'])

    # ── Stats strip ──
    stat_items = '\n  '.join(
        '<div class="stat-item"><span class="stat-number">' + s[0] + '</span>'
        '<div class="stat-label">' + s[1] + '</div></div>'
        for s in d['stats']
    )

    # ── Challenge items ──
    risk_icons = [RISK_TRI, RISK_CIRC, RISK_LOCK]
    risks_html = '\n          '.join(risk_item(risk_icons[i], h4, p) for i, (h4, p) in enumerate(d['risks']))
    solv_html  = '\n          '.join(solv_item(h4, p) for h4, p in d['solutions'])

    # ── Service cards ──
    cards_html = '\n\n      '.join(svc_card(ico, h3, p, bul) for ico, h3, p, bul in d['services'])

    # ── Why bullets + stats ──
    bullets_html = '\n          '.join(bullet_item(b) for b in d['why_bullets'])
    wstats = d['why_stats']
    why_stats_html = (
        stat_box(wstats[0][0], wstats[0][1]) +
        stat_box(wstats[1][0], wstats[1][1]) +
        stat_box(wstats[2][0], wstats[2][1]) +
        stat_box(wstats[3][0], wstats[3][1], gold=True)
    )

    # ── FAQ ──
    faq_html = '\n      '.join(faq_item_html(q['q'], q['a']) for q in d['faq'])

    # ── Footer col links ──
    fc_links = '\n      '.join('<a href="#">' + lk + '</a>' for lk in d['fc_links'])

    vid  = d['vid_id']
    form = d['form_id']

    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <link rel="icon" type="image/x-icon" href="favicon.ico">\n'
        '  <link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">\n'
        '  <link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">\n'
        '  <title>' + d['title'] + '</title>\n'
        '  <meta name="description" content="' + d['meta_desc'] + '">\n'
        '  <meta name="robots" content="index, follow">\n'
        '  <link rel="canonical" href="' + can + '">\n'
        '  <meta property="og:type" content="website">\n'
        '  <meta property="og:url" content="' + can + '">\n'
        '  <meta property="og:title" content="' + d['title'] + '">\n'
        '  <meta property="og:description" content="' + d['meta_desc'] + '">\n'
        '  <meta property="og:image" content="https://prolinksystems.com/logo.png">\n'
        '  <meta name="twitter:card" content="summary_large_image">\n'
        '  <meta name="twitter:image" content="https://prolinksystems.com/logo.png">\n'
        + schema_lb + schema_bc + schema_faq +
        '  <script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>\n'
        '  <link rel="stylesheet" href="_shared.css">\n'
        '  <style>\n' + CSS + '  </style>\n'
        '</head>\n<body>\n\n'
        '<!-- NAV -->\n'
        '<nav class="site-nav">\n'
        '  <a href="https://prolinksystems.com/" class="nav-logo"><img src="logo.png" alt="Pro Link Systems"></a>\n'
        '  <div class="nav-links">\n'
        '    <a href="https://prolinksystems.com/">Home</a>\n'
        '    <a href="https://prolinksystems.com/services">Services</a>\n'
        '    <a href="https://prolinksystems.com/about">About</a>\n'
        '    <a href="https://prolinksystems.com/contact" class="nav-cta">\n'
        '      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' + PHONE_PATH + '</svg>\n'
        '      Free IT Assessment\n'
        '    </a>\n'
        '  </div>\n'
        '  <button class="nav-hamburger" id="hamburger" aria-label="Menu"><span></span><span></span><span></span></button>\n'
        '</nav>\n'
        '<div class="mobile-menu" id="mobileMenu">\n'
        '  <a href="https://prolinksystems.com/">Home</a>\n'
        '  <a href="https://prolinksystems.com/services">Services</a>\n'
        '  <a href="https://prolinksystems.com/about">About</a>\n'
        '  <a href="https://prolinksystems.com/contact">Free IT Assessment</a>\n'
        '  <a href="tel:18008906133" style="color:var(--gold);font-weight:700;">1-800-890-6133</a>\n'
        '</div>\n\n'
        '<!-- HERO -->\n'
        '<section class="hero">\n'
        '  <div class="hero-inner">\n'
        '    <div class="hero-left">\n'
        '      <div class="industry-badge">\n'
        '        ' + d['badge_icon'] + '\n'
        '        ' + d['badge_text'] + '\n'
        '      </div>\n'
        '      <h1 class="hero-title">' + d['hero_title'] + '</h1>\n'
        '      <p class="hero-subtitle">' + d['hero_sub'] + '</p>\n'
        '      <div class="value-list">\n'
        '        ' + '\n        '.join(value_item(i, h, p) for i, h, p in d['value_items']) + '\n'
        '      </div>\n'
        '      <div class="video-block">\n'
        '        <video id="' + vid + '" autoplay muted playsinline loop preload="metadata">\n'
        '          <source src="https://videos.prolinksystems.com/snitzer.mp4" type="video/mp4">\n'
        '        </video>\n'
        '        <div class="vid-loading" id="vidLoading"><div class="vid-spinner"></div></div>\n'
        '        <div class="video-overlay">\n'
        '          <div class="video-client-badge">\n'
        '            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">' + STAR_PATH + '</svg>\n'
        '            Client Testimonial\n'
        '          </div>\n'
        '          <div class="video-client-name">Pro Link Systems &mdash; ' + d['vid_client'] + '</div>\n'
        '          <div class="video-client-sub">Long-term IT partnership &middot; Greater Los Angeles</div>\n'
        '        </div>\n'
        '        <button class="unmute-btn" id="unmuteBtn" aria-label="Toggle audio">\n'
        '          <svg id="muteIcon" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>\n'
        '          <svg id="unmuteIcon" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="display:none"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/></svg>\n'
        '          <span id="muteLabel">Tap to Unmute</span>\n'
        '        </button>\n'
        '      </div>\n'
        '    </div>\n\n'
        '    <div class="hero-right">\n'
        '      <div class="form-card">\n'
        '        <div class="form-card-head">\n'
        '          <div class="form-badge">\n'
        '            <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>\n'
        '            ' + d['form_badge'] + '\n'
        '          </div>\n'
        '          <h2>' + d['form_h2'] + '</h2>\n'
        '          <p>' + d['form_p'] + '</p>\n'
        '        </div>\n'
        '        <div class="form-body" id="formBody">\n'
        '          <form id="' + form + '" novalidate>\n'
        '            <div class="form-row">\n'
        '              <div class="form-group" id="fg-fname"><label>First Name <span class="req">*</span></label><input type="text" name="first_name" placeholder="Sarah" autocomplete="given-name"><span class="form-error">Required</span></div>\n'
        '              <div class="form-group" id="fg-lname"><label>Last Name <span class="req">*</span></label><input type="text" name="last_name" placeholder="Chen" autocomplete="family-name"><span class="form-error">Required</span></div>\n'
        '            </div>\n'
        '            <div class="form-group" id="fg-company"><label>Organization Name <span class="req">*</span></label><input type="text" name="firm_name" placeholder="' + d['co_placeholder'] + '" autocomplete="organization"><span class="form-error">Required</span></div>\n'
        '            <div class="form-group" id="fg-email"><label>Work Email <span class="req">*</span></label><input type="email" name="email" placeholder="' + d['email_placeholder'] + '" autocomplete="email"><span class="form-error">Valid email required</span></div>\n'
        '            <div class="form-group" id="fg-phone"><label>Phone <span class="req">*</span></label><input type="tel" name="phone" placeholder="(818) 555-0100" autocomplete="tel"><span class="form-error">Required</span></div>\n'
        '            <div class="form-row">\n'
        '              <div class="form-group"><label>' + d['org_label'] + '</label><select name="firm_size">' + org_opts + '</select></div>\n'
        '              <div class="form-group"><label>Primary IT Challenge</label><select name="challenge">' + ch_opts + '</select></div>\n'
        '            </div>\n'
        '            <div class="form-group"><label>Tell us about your IT situation</label><textarea name="message" placeholder="' + d['ta_placeholder'] + '"></textarea></div>\n'
        '            <button type="submit" class="submit-btn" id="submitBtn">\n'
        '              <span class="btn-label">' + d['submit_label'] + '</span>\n'
        '              ' + ARROW_R + '\n'
        '              <div class="spinner"></div>\n'
        '            </button>\n'
        '            <p class="form-privacy">&#128274; ' + d['privacy_text'] + '</p>\n'
        '          </form>\n'
        '        </div>\n'
        '        <div class="form-success" id="formSuccess">\n'
        '          <div class="success-orbit"><svg width="28" height="28" fill="none" stroke="#fff" stroke-width="2.5" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg></div>\n'
        '          <div class="success-pill"><div class="success-pill-dot"></div>Inquiry Confirmed</div>\n'
        '          <h3>You\'re in good hands.</h3>\n'
        '          <p>Thank you, <strong id="successName"></strong>. We\'ll reach out within 1 business day to schedule your free IT assessment.</p>\n'
        '          <a href="tel:18008906133" class="success-cta-phone"><svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' + PHONE_PATH + '</svg>Call Now: 1-800-890-6133</a>\n'
        '        </div>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<!-- COMPLIANCE BAR -->\n'
        '<div class="compliance-bar">\n'
        '  ' + comp_bar + '\n'
        '</div>\n\n'
        '<!-- STATS STRIP -->\n'
        '<div class="stats-strip">\n'
        '  ' + stat_items + '\n'
        '</div>\n\n'
        '<!-- CHALLENGES / SOLUTIONS -->\n'
        '<section class="section section-off">\n'
        '  <div class="container">\n'
        '    <div class="challenge-grid">\n'
        '      <div>\n'
        '        <div class="challenge-side-head">\n'
        '          <span class="section-label">' + d['ch_left_label'] + '</span>\n'
        '          <h2 class="section-heading">' + d['ch_left_h2'] + '</h2>\n'
        '          <p class="section-sub">' + d['ch_left_p'] + '</p>\n'
        '        </div>\n'
        '        <div class="challenge-list">\n'
        '          ' + risks_html + '\n'
        '        </div>\n'
        '      </div>\n'
        '      <div>\n'
        '        <div class="challenge-side-head">\n'
        '          <span class="section-label">The Pro Link Difference</span>\n'
        '          <h2 class="section-heading">' + d['ch_right_h2'] + '</h2>\n'
        '          <p class="section-sub">' + d['ch_right_p'] + '</p>\n'
        '        </div>\n'
        '        <div class="challenge-list">\n'
        '          ' + solv_html + '\n'
        '        </div>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<!-- SERVICES GRID -->\n'
        '<section class="section">\n'
        '  <div class="container">\n'
        '    <div class="centered" style="margin-bottom:48px;">\n'
        '      <span class="section-label">' + d['svc_label'] + '</span>\n'
        '      <h2 class="section-heading">' + d['svc_h2'] + '</h2>\n'
        '      <p class="section-sub">' + d['svc_p'] + '</p>\n'
        '    </div>\n'
        '    <div class="card-grid-3">\n'
        '      ' + cards_html + '\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<!-- TESTIMONIAL -->\n'
        '<section class="section" style="background:var(--off-white);">\n'
        '  <div class="container">\n'
        '    <div class="testimonial-block">\n'
        '      <div>\n'
        '        ' + stars() + '\n'
        '        <p class="testimonial-quote">' + d['test_quote'] + '</p>\n'
        '        <div class="testimonial-author">\n'
        '          <div class="testimonial-avatar">' + d['test_avatar'] + '</div>\n'
        '          <div><div class="testimonial-name">' + d['test_name'] + '</div>'
        '<div class="testimonial-role">' + d['test_role'] + '</div></div>\n'
        '        </div>\n'
        '      </div>\n'
        '      <div style="border-radius:var(--r-lg);overflow:hidden;aspect-ratio:16/9;background:#000;">\n'
        '        <video autoplay muted playsinline loop preload="metadata" style="width:100%;height:100%;object-fit:cover;">\n'
        '          <source src="https://videos.prolinksystems.com/snitzer.mp4" type="video/mp4">\n'
        '        </video>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<!-- WHY PRO LINK -->\n'
        '<section class="section">\n'
        '  <div class="container">\n'
        '    <div style="display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center;">\n'
        '      <div>\n'
        '        <span class="section-label">Why Pro Link Systems</span>\n'
        '        <h2 class="section-heading">' + d['why_h2'] + '</h2>\n'
        '        <p class="section-sub" style="margin-bottom:28px;">' + d['why_p'] + '</p>\n'
        '        <div style="display:flex;flex-direction:column;gap:14px;">\n'
        '          ' + bullets_html + '\n'
        '        </div>\n'
        '      </div>\n'
        '      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">\n'
        '        ' + why_stats_html + '\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<!-- FAQ -->\n'
        '<section class="section section-off">\n'
        '  <div class="container">\n'
        '    <div class="centered" style="margin-bottom:40px;">\n'
        '      <span class="section-label">Common Questions</span>\n'
        '      <h2 class="section-heading">' + d['faq_h2'] + '</h2>\n'
        '    </div>\n'
        '    <div class="faq-list">\n'
        '      ' + faq_html + '\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n\n'
        '<!-- CTA BAND -->\n'
        '<div class="cta-band">\n'
        '  <span class="section-label" style="color:var(--gold);">' + d['cta_label'] + '</span>\n'
        '  <h2>' + d['cta_h2'] + '</h2>\n'
        '  <p>' + d['cta_p'] + '</p>\n'
        '  <div class="cta-buttons">\n'
        '    <a href="https://prolinksystems.com/contact" class="btn btn-gold">Schedule Free Assessment ' + ARROW_R.replace('class="btn-arrow" ', '') + '</a>\n'
        '    <a href="tel:18008906133" class="btn btn-outline-white"><svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' + PHONE_PATH + '</svg>1-800-890-6133</a>\n'
        '  </div>\n'
        '</div>\n\n'
        '<!-- FOOTER -->\n'
        '<footer class="site-footer">\n'
        '  <div class="footer-grid">\n'
        '    <div class="footer-brand">\n'
        '      <img src="logo.png" alt="Pro Link Systems">\n'
        '      <p>' + d['footer_p'] + '</p>\n'
        '    </div>\n'
        '    <div class="footer-col">\n'
        '      <h4>' + d['fc_h4'] + '</h4>\n'
        '      ' + fc_links + '\n'
        '    </div>\n'
        '    <div class="footer-col">\n'
        '      <h4>Company</h4>\n'
        '      <a href="https://prolinksystems.com/">Home</a>\n'
        '      <a href="https://prolinksystems.com/services">All Services</a>\n'
        '      <a href="https://prolinksystems.com/about">About Us</a>\n'
        '      <a href="https://prolinksystems.com/contact">Contact</a>\n'
        '      <a href="https://prolinksystems.com/legal">Legal</a>\n'
        '    </div>\n'
        '    <div class="footer-col">\n'
        '      <h4>Contact</h4>\n'
        '      <div class="footer-contact-item"><svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">' + PHONE_PATH + '</svg><a href="tel:18008906133">1-800-890-6133</a></div>\n'
        '      <div class="footer-contact-item"><svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg><a href="mailto:info@prolinksystems.com">info@prolinksystems.com</a></div>\n'
        '      <div class="footer-contact-item"><svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg><span>21241 Ventura Blvd<br>Woodland Hills, CA 91364</span></div>\n'
        '    </div>\n'
        '  </div>\n'
        '  <div class="footer-bottom">\n'
        '    <span>&copy; 2026 Pro Link Systems. All rights reserved.</span>\n'
        '    <div style="display:flex;gap:20px;"><a href="https://prolinksystems.com/legal">Privacy Policy</a><a href="https://prolinksystems.com/legal">Terms of Service</a></div>\n'
        '  </div>\n'
        '</footer>\n\n'
        '<script>\n'
        '  document.getElementById(\'hamburger\').addEventListener(\'click\', function() {\n'
        '    document.getElementById(\'mobileMenu\').classList.toggle(\'open\');\n'
        '  });\n\n'
        '  (function() {\n'
        '    var vid = document.getElementById(\'' + vid + '\');\n'
        '    var loading = document.getElementById(\'vidLoading\');\n'
        '    var unmuteBtn = document.getElementById(\'unmuteBtn\');\n'
        '    var muteIcon = document.getElementById(\'muteIcon\');\n'
        '    var unmuteIcon = document.getElementById(\'unmuteIcon\');\n'
        '    var muteLabel = document.getElementById(\'muteLabel\');\n'
        '    var muted = true; var stallTimer = null; var stallAtTime = -1;\n'
        '    function showSpinner() { loading.classList.add(\'show\'); }\n'
        '    function hideSpinner() { loading.classList.remove(\'show\'); }\n'
        '    function clearStall() { if (stallTimer) { clearTimeout(stallTimer); stallTimer = null; } }\n'
        '    function recover() {\n'
        '      clearStall(); var t = vid.currentTime;\n'
        '      var stuck = (t <= 0.5) || (stallAtTime >= 0 && t === stallAtTime);\n'
        '      stallAtTime = -1;\n'
        '      if (stuck) { vid.load(); }\n'
        '      vid.play().catch(function(){});\n'
        '    }\n'
        '    vid.addEventListener(\'waiting\', function() { showSpinner(); clearStall(); stallAtTime = vid.currentTime; stallTimer = setTimeout(recover, 15000); });\n'
        '    vid.addEventListener(\'stalled\', function() { clearStall(); stallAtTime = vid.currentTime; stallTimer = setTimeout(recover, 12000); });\n'
        '    vid.addEventListener(\'playing\', function() { hideSpinner(); clearStall(); stallAtTime = -1; });\n'
        '    vid.addEventListener(\'timeupdate\', function() { if (loading.classList.contains(\'show\') && !vid.paused) { hideSpinner(); clearStall(); stallAtTime = -1; } });\n'
        '    vid.addEventListener(\'error\', function() { hideSpinner(); clearStall(); setTimeout(function(){ vid.load(); vid.play().catch(function(){}); }, 3000); });\n'
        '    document.addEventListener(\'visibilitychange\', function() { if (!document.hidden && vid.paused) { vid.play().catch(function(){}); } });\n'
        '    unmuteBtn.addEventListener(\'click\', function() {\n'
        '      muted = !muted; vid.muted = muted;\n'
        '      muteIcon.style.display = muted ? \'\' : \'none\';\n'
        '      unmuteIcon.style.display = muted ? \'none\' : \'\';\n'
        '      muteLabel.textContent = muted ? \'Tap to Unmute\' : \'Mute\';\n'
        '    });\n'
        '  })();\n\n'
        '  function toggleFaq(btn) {\n'
        '    var answer = btn.nextElementSibling;\n'
        '    var isOpen = btn.classList.contains(\'open\');\n'
        '    document.querySelectorAll(\'.faq-question.open\').forEach(function(q) {\n'
        '      q.classList.remove(\'open\'); q.nextElementSibling.classList.remove(\'open\');\n'
        '    });\n'
        '    if (!isOpen) { btn.classList.add(\'open\'); answer.classList.add(\'open\'); }\n'
        '  }\n\n'
        '  var EMAILJS_PUBLIC_KEY  = \'S8d9nu1H2bUKdf_mf\';\n'
        '  var EMAILJS_SERVICE_ID  = \'service_j8nf0bs\';\n'
        '  var EMAILJS_TEMPLATE_ID = \'template_yz71bhl\';\n'
        '  emailjs.init({ publicKey: EMAILJS_PUBLIC_KEY });\n\n'
        '  document.getElementById(\'' + form + '\').addEventListener(\'submit\', function(e) {\n'
        '    e.preventDefault();\n'
        '    var f = e.target; var valid = true;\n'
        '    [\'fg-fname\',\'fg-lname\',\'fg-company\',\'fg-phone\'].forEach(function(id) {\n'
        '      var fg = document.getElementById(id);\n'
        '      if (fg) { var inp = fg.querySelector(\'input\'); if (!inp.value.trim()) { fg.classList.add(\'has-error\'); valid = false; } else fg.classList.remove(\'has-error\'); }\n'
        '    });\n'
        '    var eFg = document.getElementById(\'fg-email\'); var eInp = eFg.querySelector(\'input\');\n'
        '    if (!eInp.value.trim() || !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(eInp.value)) { eFg.classList.add(\'has-error\'); valid = false; } else eFg.classList.remove(\'has-error\');\n'
        '    if (!valid) return;\n'
        '    var btn = document.getElementById(\'submitBtn\');\n'
        '    btn.classList.add(\'loading\'); btn.disabled = true;\n'
        '    var fn = f.first_name.value.trim();\n'
        '    var params = {\n'
        '      first_name: fn, last_name: f.last_name.value.trim(),\n'
        '      email: f.email.value.trim(), phone: f.phone.value.trim(),\n'
        '      company: f.firm_name.value.trim(),\n'
        '      service: \'' + d['form_service'] + '\',\n'
        '      message: (f.message.value.trim() || \'No details provided.\') +\n'
        '               \'\\n\\nOrg Type: \' + (f.firm_size.value || \'Not specified\') +\n'
        '               \'\\nChallenge: \' + (f.challenge.value || \'Not specified\') +\n'
        '               \'\\nSource: ' + d['bc_name'] + ' Landing Page\'\n'
        '    };\n'
        '    var ejsDone = false, w3fDone = false;\n'
        '    function maybeShow() {\n'
        '      if (!ejsDone || !w3fDone) return;\n'
        '      btn.classList.remove(\'loading\'); btn.disabled = false;\n'
        '      document.getElementById(\'successName\').textContent = fn;\n'
        '      document.getElementById(\'formBody\').classList.add(\'hide\');\n'
        '      document.getElementById(\'formSuccess\').classList.add(\'show\');\n'
        '    }\n'
        '    emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, params, { publicKey: EMAILJS_PUBLIC_KEY })\n'
        '      .then(function(){ ejsDone = true; maybeShow(); }).catch(function(){ ejsDone = true; maybeShow(); });\n'
        '    fetch(\'https://api.web3forms.com/submit\', {\n'
        '      method: \'POST\', headers: {\'Content-Type\': \'application/json\'},\n'
        '      body: JSON.stringify({\n'
        '        access_key: \'3691dac3-0e33-48fd-9dfc-c7c7e21dc5a0\',\n'
        '        subject: \'' + d['bc_name'] + ' Lead: \' + fn + \' -- \' + params.company,\n'
        '        from_name: fn + \' \' + params.last_name,\n'
        '        email: params.email,\n'
        '        message: \'Phone: \' + params.phone + \'\\nCompany: \' + params.company + \'\\n\\n\' + params.message\n'
        '      })\n'
        '    }).then(function(){ w3fDone = true; maybeShow(); }).catch(function(){ w3fDone = true; maybeShow(); });\n'
        '  });\n'
        '</script>\n'
        '</body>\n</html>\n'
    )

# ─── INDUSTRY DATA ────────────────────────────────────────────────────────────

INDUSTRIES = [

# ════════════════════════════════════════════════════════════════════════════════
# 1. FINANCIAL SERVICES
# ════════════════════════════════════════════════════════════════════════════════
{
  'filename':   'financial-services-it-los-angeles.html',
  'vid_id':     'finVid',
  'form_id':    'finForm',
  'can':        'financial-services-it-los-angeles',
  'bc_name':    'Financial Services IT Los Angeles',
  'title':      'Financial Services IT Los Angeles | SEC &amp; FINRA Compliance IT | Pro Link Systems',
  'meta_desc':  'Pro Link Systems delivers SEC/FINRA-compliant managed IT for Los Angeles financial firms. Trading system support, cybersecurity, secure remote work, and 24/7 help desk since 1999. Call 1-800-890-6133.',
  'schema_desc':'SEC/FINRA-compliant managed IT for Los Angeles financial firms since 1999. Trading system support, financial cybersecurity, disaster recovery, and 24/7 help desk.',
  'offers_label':'Financial IT Services',
  'offers':     ['SEC/FINRA Compliance IT','Trading System Support','Financial Cybersecurity','Secure Remote Work','Disaster Recovery','24/7 IT Help Desk'],
  'badge_icon': '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
  'badge_text': 'Financial Industry IT',
  'hero_title': 'IT That Keeps Your Firm<br><em>Compliant. Secure. Profitable.</em><br>SEC-Ready. Always On.',
  'hero_sub':   'A data breach at a financial firm isn&rsquo;t just a regulatory crisis &mdash; it&rsquo;s a client trust crisis you may never recover from. Pro Link Systems has been the trusted IT backbone for Los Angeles financial firms since 1999, delivering SEC/FINRA-compliant infrastructure, trading system uptime, and cyber protection that meets examiner expectations.',
  'value_items': [
    ('shield',   'SEC &amp; FINRA Compliance Documentation',  'Audit-ready IT policies, access controls, risk assessments, and documentation that satisfy SEC/FINRA exam requirements &mdash; built in from day one, not scrambled together before an exam.'),
    ('activity', 'Trading System &amp; Application Uptime',   'Bloomberg, Reuters, Pershing, Schwab Advisor Services, and proprietary platforms need bulletproof connectivity. We manage the infrastructure and monitoring that keeps your systems running.'),
    ('clock',    '24/7 IT Response &amp; Monitoring',         'Markets don&rsquo;t close at 5 PM. Our help desk provides under-15-minute response around the clock for trading system issues, connectivity failures, and security incidents.'),
  ],
  'vid_client':  'Financial Services Client',
  'form_badge':  'Financial IT Specialists &middot; Since 1999',
  'form_h2':     'Get a Free Financial IT Assessment',
  'form_p':      'We&rsquo;ll review your SEC/FINRA compliance posture, trading system infrastructure, and cybersecurity controls &mdash; and give you a clear roadmap. No pressure, no commitment.',
  'co_placeholder':    'Westside Capital Advisors',
  'email_placeholder': 'john@westsidecapital.com',
  'org_label':         'Firm Type',
  'org_opts':    ['RIA / Investment Adviser','Broker-Dealer','Family Office','Hedge Fund / Private Equity','Insurance (Financial Products)','Accounting / CPA Firm','Financial Planning Practice'],
  'ch_opts':     ['SEC/FINRA Compliance','Cybersecurity / Data Security','Trading Platform Support','Secure Remote Work','Business Continuity / DR','Cloud Migration','General IT Management'],
  'ta_placeholder': 'e.g. We manage $200M in AUM, run on Pershing, and need help with SEC exam prep and our cybersecurity posture…',
  'form_service':   'Financial Services IT Assessment Request',
  'submit_label':   'Request Free Assessment',
  'privacy_text':   'Secure &amp; confidential. We never share your information. Response within 1 business day.',
  'compliance': [
    ('shield','SEC &amp; FINRA Regulations'),
    ('shield','SOX Compliance Support'),
    ('shield','PCI-DSS Aligned'),
    ('shield','Cyber Insurance Ready'),
    ('clock', '24/7 Threat Monitoring'),
  ],
  'stats': [
    ('25+',   'Years Supporting LA Firms'),
    ('99.9%', 'Network Uptime Delivered'),
    ('&lt;15m','Help Desk Response Time'),
    ('SOC 2', 'Aligned Infrastructure'),
  ],
  'ch_left_label': 'The Financial IT Problem',
  'ch_left_h2':    'Financial IT Failures Trigger Regulatory Action &mdash; Not Just Downtime.',
  'ch_left_p':     'Financial firms are prime ransomware targets and hold high-value client data. But the threat isn&rsquo;t only external &mdash; missed SEC/FINRA requirements, inadequate audit trails, and poor access controls can trigger exam deficiencies and enforcement actions. Generic IT providers don&rsquo;t know what regulators are looking for.',
  'risks': [
    ('Ransomware Targeting Client Financial Data',      'Financial firms hold PII and account data that commands premium ransom payments. A single successful attack can freeze operations, expose client data, and trigger mandatory regulatory notification.'),
    ('Wire Fraud and Business Email Compromise',        'BEC attacks targeting financial transactions have resulted in millions in losses per incident. Attackers compromise email accounts and intercept wire instructions &mdash; redirecting funds before anyone notices.'),
    ('SEC/FINRA Exam Deficiencies from IT Gaps',        'Inadequate access controls, missing audit logs, unencrypted data, and poor records retention are among the most common IT-related exam findings. Most IT providers don&rsquo;t know what regulators look for until it&rsquo;s too late.'),
  ],
  'ch_right_h2': 'IT Infrastructure Built for Financial Compliance and Security.',
  'ch_right_p':  'We&rsquo;ve been supporting financial firms since 1999. We understand that your audit trail is as important as your network uptime, that client data must be encrypted at rest and in transit, and that a BEC attack can cost more than a year of IT fees. We bring regulatory context to every IT decision we make.',
  'solutions': [
    ('Financial-Grade Cybersecurity &amp; BEC Prevention',     'Advanced email security with DMARC/DKIM/SPF, multi-factor authentication on all systems, and security awareness training specifically targeting financial wire fraud scenarios.'),
    ('SEC/FINRA-Ready Compliance Documentation',               'We build and maintain the access control policies, data retention schedules, audit logging, and risk assessment documentation that satisfy SEC/FINRA and state regulator requirements.'),
    ('Immutable Backup &amp; Rapid Recovery',                  'WORM-compliant encrypted backups with tested recovery procedures. If ransomware hits, we restore operations fast &mdash; with the documentation needed for any required breach notification.'),
  ],
  'svc_label': 'Financial IT Services',
  'svc_h2':    'Comprehensive IT for Every Layer of Your Firm',
  'svc_p':     'From the trading desk to the back office &mdash; managed, monitored, and SEC/FINRA-compliant.',
  'services': [
    ('shield',   'SEC &amp; FINRA Compliance IT',
     'We build the complete IT compliance framework your firm needs for SEC and FINRA examinations &mdash; risk assessments, access control documentation, audit logging, encryption inventories, and records retention policies that are exam-ready at all times.',
     ['SEC/FINRA risk assessment &amp; remediation','FINRA Rule 4370 business continuity planning','Electronic records retention compliance','Reg S-ID and cybersecurity program documentation']),
    ('activity', 'Trading Platform &amp; Application Support',
     'Bloomberg, Reuters Eikon, Pershing, Schwab Advisor Services, and proprietary trading platforms need bulletproof uptime. We manage the server infrastructure, network redundancy, and 24/7 monitoring that keeps your trading and advisory systems running.',
     ['Dedicated trading infrastructure management','API and market data feed support','Low-latency network optimization','Performance monitoring and capacity planning']),
    ('lock',     'Financial Cybersecurity',
     'Purpose-built threat protection for firms that hold client financial data and execute transactions. We stop ransomware, BEC attacks, and insider threats without disrupting the fast-moving workflows of financial professionals.',
     ['Advanced email security &amp; BEC prevention','Multi-factor authentication (MFA) on all systems','Privileged access management (PAM)','Security awareness training for financial staff']),
    ('wifi',     'Secure Remote &amp; Hybrid Work',
     'Advisors, analysts, and back-office staff need secure access from anywhere. We deploy encrypted endpoints, zero-trust network access, and managed devices that keep your team productive and your client data protected from any location.',
     ['Zero-trust network access (ZTNA)','Encrypted endpoint management','Secure VPN with split tunneling','BYOD security policies and MDM']),
    ('refresh',  'Disaster Recovery &amp; Business Continuity',
     'FINRA Rule 4370 requires documented business continuity plans. We design, test, and maintain DR infrastructure with WORM-compliant encrypted backups and documented RTOs that satisfy both regulators and your clients.',
     ['FINRA Rule 4370-compliant BCP documentation','WORM-compliant encrypted backup architecture','Tested recovery with documented RTO','Failover connectivity and offsite redundancy']),
    ('phone',    '24/7 IT Help Desk &amp; Support',
     'Market hours don&rsquo;t end at 5 PM, and neither do we. Our help desk provides under-15-minute response 24/7/365, with dedicated support for trading system issues and security incidents that can&rsquo;t wait until morning.',
     ['Under-15-minute guaranteed response 24/7/365','Trading system priority escalation protocols','On-site dispatch &mdash; Greater Los Angeles','Dedicated account manager for your firm']),
  ],
  'test_quote':  'Pro Link has been managing our IT for years. They understand that when our systems go down or our client portal has issues, every minute matters. When we went through our last SEC exam, they had all our IT documentation ready &mdash; access controls, audit logs, the works. They didn&rsquo;t just keep our systems running. They helped us pass our exam.',
  'test_avatar': 'LA',
  'test_name':   'Los Angeles Financial Services Client',
  'test_role':   'Operations Director &middot; Registered Investment Adviser &middot; Greater Los Angeles',
  'why_h2':      'Fortune 1000 IT Experience. Built for LA Financial Firms.',
  'why_p':       'We started supporting financial services firms when most advisors were still running paper files. 25 years later, we understand SEC/FINRA requirements, the weight of client data responsibility, and the complexity of modern financial technology better than any general IT provider.',
  'why_bullets': [
    'Woodland Hills &mdash; serving Greater Los Angeles financial firms',
    'SEC/FINRA-ready compliance documentation built into every engagement',
    'Trading platform expertise &mdash; Bloomberg, Pershing, Schwab, and more',
    'Flat-rate pricing &mdash; IT costs that don&rsquo;t spike during incidents',
    'On-site dispatch across Greater LA &mdash; not just remote support tickets',
  ],
  'why_stats': [('25+','Years in Financial IT'),('99.9%','Network Uptime'),('&lt;15m','Response &mdash; 24/7/365'),('SEC','Exam Ready')],
  'faq_h2':  'Financial IT Questions We Hear Every Day',
  'faq': [
    { 'q': 'Can Pro Link Systems help us prepare for an SEC or FINRA examination?',
      'q_plain': 'Can Pro Link Systems help us prepare for an SEC or FINRA examination?',
      'a': 'Yes. We build and maintain the IT documentation portfolio your examiners expect: written access control policies, audit trail documentation, encryption inventories, records retention schedules, and a cybersecurity program document. We&rsquo;ve helped RIAs and broker-dealers walk into exams confident that their technology controls are documented and defensible.',
      'a_plain': 'Yes. We build and maintain the IT documentation portfolio your examiners expect: written access control policies, audit trail documentation, encryption inventories, records retention schedules, and a cybersecurity program document. We\'ve helped RIAs and broker-dealers walk into exams confident that their technology controls are documented and defensible.' },
    { 'q': 'How does Pro Link protect against wire fraud and business email compromise?',
      'q_plain': 'How does Pro Link protect against wire fraud and business email compromise?',
      'a': 'We deploy multi-layer email security including DMARC/DKIM/SPF enforcement, advanced threat filtering, and simulated BEC attack training for your staff. For wire transfer workflows, we help you implement out-of-band verification procedures and technical controls that prevent email-based payment redirection. Wire fraud is the highest-dollar cyber risk for financial firms &mdash; we treat it accordingly.',
      'a_plain': 'We deploy multi-layer email security including DMARC/DKIM/SPF enforcement, advanced threat filtering, and simulated BEC attack training for your staff. For wire transfer workflows, we help you implement out-of-band verification procedures and technical controls that prevent email-based payment redirection.' },
    { 'q': 'Is cloud computing compliant with SEC/FINRA regulations for financial firms?',
      'q_plain': 'Is cloud computing compliant with SEC/FINRA regulations for financial firms?',
      'a': 'Yes, with proper configuration and documentation. Many cloud services can satisfy SEC/FINRA records retention and security requirements &mdash; but the compliance responsibility remains with your firm. We handle vendor due diligence, service agreements, encryption configuration, access controls, and the documentation you need to demonstrate to examiners that your cloud usage is compliant.',
      'a_plain': 'Yes, with proper configuration and documentation. Many cloud services can satisfy SEC/FINRA records retention and security requirements, but the compliance responsibility remains with your firm. We handle vendor due diligence, encryption configuration, access controls, and the documentation examiners expect.' },
    { 'q': 'How quickly can Pro Link respond if our trading systems go down?',
      'q_plain': 'How quickly can Pro Link respond if our trading systems go down?',
      'a': 'Under 15 minutes, 24/7/365. Trading system outages and client-facing portal failures receive immediate priority escalation. We maintain on-site dispatch capability across Greater Los Angeles for issues that cannot be resolved remotely. We also help financial firms maintain documented business continuity procedures per FINRA Rule 4370.',
      'a_plain': 'Under 15 minutes, 24/7/365. Trading system outages receive immediate priority escalation. We maintain on-site dispatch capability across Greater Los Angeles for issues that cannot be resolved remotely, and help firms maintain documented BCP per FINRA Rule 4370.' },
    { 'q': 'Can Pro Link help after a ransomware attack or data breach at our firm?',
      'q_plain': 'Can Pro Link help after a ransomware attack or data breach at our firm?',
      'a': 'Yes. We provide immediate containment, forensic analysis, system recovery, and documentation support for any required regulatory notification or client disclosure. Post-incident, we harden your environment with the controls that would have prevented the attack &mdash; and use the experience to build a more resilient infrastructure.',
      'a_plain': 'Yes. We provide immediate containment, forensic analysis, system recovery, and documentation support for required regulatory notification. Post-incident, we harden your environment and build a more resilient infrastructure.' },
  ],
  'cta_label': 'Ready to Protect Your Firm?',
  'cta_h2':    'A Data Breach at a Financial Firm<br>Is Your Most Expensive IT Problem.',
  'cta_p':     'Free financial IT assessment. We review your SEC/FINRA compliance posture, trading system infrastructure, and cybersecurity controls &mdash; and give you a clear roadmap. No pressure. No commitment.',
  'fc_h4':     'Financial IT',
  'fc_links':  ['SEC/FINRA Compliance','Trading System Support','Financial Cybersecurity','Secure Remote Work','Business Continuity','24/7 Help Desk'],
  'footer_p':  'Managed IT, cybersecurity, and SEC/FINRA-compliant infrastructure for Los Angeles financial firms since 1999. Trusted by investment advisers, broker-dealers, and financial planning practices across Greater LA.',
},

# ════════════════════════════════════════════════════════════════════════════════
# 2. REAL ESTATE
# ════════════════════════════════════════════════════════════════════════════════
{
  'filename':   'real-estate-it-services.html',
  'vid_id':     'reVid',
  'form_id':    'reForm',
  'can':        'real-estate-it-services',
  'bc_name':    'Real Estate IT Services Los Angeles',
  'title':      'Real Estate IT Services Los Angeles | MLS &amp; CRM IT Support | Pro Link Systems',
  'meta_desc':  'Pro Link Systems delivers managed IT for Los Angeles real estate firms. MLS/CRM support, wire fraud prevention, transaction security, agent mobility, and 24/7 help desk since 1999. Call 1-800-890-6133.',
  'schema_desc':'Managed IT for Los Angeles real estate firms since 1999. MLS/CRM support, wire fraud prevention, transaction security, agent mobility, and 24/7 help desk.',
  'offers_label':'Real Estate IT Services',
  'offers':     ['MLS & CRM System Support','Wire Fraud & Transaction Security','Real Estate Cybersecurity','Agent Mobility & Device Management','Cloud & Collaboration Tools','24/7 IT Help Desk'],
  'badge_icon': '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  'badge_text': 'Real Estate Industry IT',
  'hero_title': 'IT That Moves as Fast<br><em>as Your Transactions Do.</em><br>MLS-Ready. Secure. Always On.',
  'hero_sub':   'A system outage during a close can cost you a deal. A wire fraud attack can cost your client their life savings. Pro Link Systems has been the trusted IT partner for Los Angeles real estate firms since 1999, delivering reliable MLS infrastructure, transaction security, and 24/7 support for agents and offices.',
  'value_items': [
    ('home',   'MLS &amp; CRM System Reliability',       'We manage the infrastructure behind your MLS, CRM, and transaction management platforms so your agents always have access when they need it most &mdash; especially at closing time.'),
    ('shield', 'Wire Fraud &amp; Transaction Security',  'Real estate wire fraud has cost buyers and agents millions. We deploy email security, MFA, and secure communication protocols that protect every transaction from interception.'),
    ('wifi',   'Agent Mobility &amp; Remote Access',     'Your agents work from offices, open houses, and everywhere in between. We ensure fast, secure access to all systems from any device, anywhere they work.'),
  ],
  'vid_client':  'Real Estate Client',
  'form_badge':  'Real Estate IT Specialists &middot; Since 1999',
  'form_h2':     'Get a Free Real Estate IT Assessment',
  'form_p':      'We&rsquo;ll review your MLS infrastructure, transaction security, and cybersecurity posture &mdash; and give you a clear roadmap. No pressure, no commitment.',
  'co_placeholder':    'Westside Premier Realty',
  'email_placeholder': 'sarah@westsiderealty.com',
  'org_label':         'Firm Type',
  'org_opts':    ['Real Estate Brokerage','Property Management Company','Commercial Real Estate Firm','Real Estate Investment Trust (REIT)','Title Company','Mortgage Broker / Lender','Real Estate Attorney'],
  'ch_opts':     ['Wire Fraud / Transaction Security','MLS / CRM Reliability','Cybersecurity / Data Security','Agent Mobility / Remote Work','Cloud &amp; Collaboration Tools','Business Continuity / DR','General IT Management'],
  'ta_placeholder': 'e.g. We have 40 agents across 3 offices, our CRM keeps going down during busy periods, and we&rsquo;re worried about wire fraud targeting our transactions…',
  'form_service':   'Real Estate IT Assessment Request',
  'submit_label':   'Request Free Assessment',
  'privacy_text':   'Secure &amp; confidential. We never share your information. Response within 1 business day.',
  'compliance': [
    ('shield','CCPA Compliant'),
    ('shield','Transaction Data Security'),
    ('shield','MLS System Reliability'),
    ('check', 'NAR Cybersecurity Guidelines'),
    ('clock', '24/7 Agent Support'),
  ],
  'stats': [
    ('25+',   'Years Supporting LA Firms'),
    ('99.9%', 'Network Uptime Delivered'),
    ('&lt;15m','Help Desk Response Time'),
    ('CCPA',  'Ready'),
  ],
  'ch_left_label': 'The Real Estate IT Problem',
  'ch_left_h2':    'Unreliable IT and Wire Fraud Risk<br>Are Costing You Deals.',
  'ch_left_p':     'Real estate firms face a perfect storm of IT risk: high transaction volumes, agents working from everywhere, sensitive client financial data, and wire fraud attackers who specifically target real estate transactions. A single wire fraud incident can permanently damage client trust. A system outage at the wrong moment can lose a deal.',
  'risks': [
    ('Wire Fraud Targeting Real Estate Transactions',   'Real estate wire fraud losses exceed $400 million annually in the US. Attackers compromise agent or attorney email accounts and redirect wire instructions &mdash; often just hours before closing. By the time anyone notices, the funds are gone.'),
    ('MLS and CRM Outages at Critical Moments',         'Agents losing access to the MLS or CRM during an open house, offer negotiation, or closing creates real deal risk. If your systems are unreliable, your agents are unprofessional &mdash; even if the technology is the problem.'),
    ('Client Data Breaches and CCPA Exposure',          'California real estate firms collect significant client PII and are subject to CCPA. An unencrypted laptop, a misconfigured cloud folder, or a phishing attack can expose client data and trigger notification obligations.'),
  ],
  'ch_right_h2': 'IT Infrastructure Built for Real Estate Speed and Security.',
  'ch_right_p':  'We&rsquo;ve been supporting real estate firms since 1999. We understand that deals move fast, that agents need reliable access from anywhere, and that wire fraud is an existential risk for any firm that processes real estate transactions. We bring real estate context to every IT decision we make.',
  'solutions': [
    ('Wire Fraud Prevention Built into Every Engagement',  'Advanced email security with DMARC/DKIM/SPF enforcement, BEC filtering, and wire fraud awareness training so your agents and staff recognize and resist the most dangerous attacks targeting real estate.'),
    ('MLS &amp; CRM Uptime with Proactive Monitoring',     'We manage the infrastructure behind your systems with 24/7 monitoring and fast escalation so outages are caught and resolved before they affect your agents &mdash; not after a deal falls through.'),
    ('Agent Mobility with Proper Security Controls',       'Encrypted endpoints, zero-trust remote access, and mobile device management so your agents work securely from anywhere without creating gaps in your client data security or CCPA compliance.'),
  ],
  'svc_label': 'Real Estate IT Services',
  'svc_h2':    'Comprehensive IT for Every Layer of Your Brokerage',
  'svc_p':     'From the front office to the field &mdash; managed, monitored, and built for real estate speed.',
  'services': [
    ('server',   'MLS &amp; CRM System Support',
     'We manage the server infrastructure, network connectivity, and 24/7 monitoring that keep your MLS, CRM, and transaction management platforms running. Your agents need reliable access &mdash; we make sure they have it, especially during high-volume periods.',
     ['CRMLS, SoCal MLS, Salesforce, Follow Up Boss, KvCore','Dedicated CRM infrastructure management','Performance monitoring and uptime guarantees','Integration support for DocuSign, Dotloop, SkySlope']),
    ('lock',     'Wire Fraud &amp; Transaction Security',
     'Real estate is the #1 target for wire fraud. We deploy the email security stack, multi-factor authentication, and communication controls that protect your clients&rsquo; most important financial transactions from interception and fund redirection.',
     ['Advanced email security with BEC prevention','DMARC/DKIM/SPF enforcement on all domains','Secure transaction communication protocols','Wire fraud awareness training for agents &amp; staff']),
    ('shield',   'Real Estate Cybersecurity',
     'Ransomware, phishing, and data theft targeting real estate firms have increased sharply. We protect offices, agents, and client data with layered security that operates transparently so your team stays productive without compromising safety.',
     ['Endpoint detection &amp; response (EDR)','Email security and phishing simulation training','Client data encryption at rest and in transit','CCPA compliance documentation and controls']),
    ('wifi',     'Agent Mobility &amp; Device Management',
     'Your agents work from anywhere &mdash; offices, open houses, client homes, and on the road. We manage laptops, tablets, and mobile devices with secure remote access so your team stays connected and your data stays protected wherever they work.',
     ['Secure VPN and zero-trust remote access','Mobile device management (MDM) for agents','Encrypted endpoint management','BYOD security policies for agent devices']),
    ('cloud',    'Cloud &amp; Collaboration Tools',
     'Microsoft 365, Google Workspace, Dropbox Business, or any combination &mdash; we manage, secure, and optimize your cloud tools so your team collaborates efficiently without exposing client data or creating compliance gaps.',
     ['Microsoft 365 and Google Workspace management','Secure cloud storage and document management','SharePoint and Teams configuration','Cloud backup and data retention policies']),
    ('phone',    '24/7 IT Help Desk &amp; Support',
     'Deals don&rsquo;t close during business hours only. Our help desk provides under-15-minute response 24/7/365 for agents and staff who need immediate help with systems, connectivity, or security issues that can&rsquo;t wait until Monday morning.',
     ['Under-15-minute guaranteed response 24/7/365','Priority support for active transaction issues','On-site dispatch &mdash; Greater Los Angeles','Dedicated account manager for your brokerage']),
  ],
  'test_quote':  'Pro Link has made our technology completely reliable. Before them, agents were constantly dealing with system outages at the worst possible times. Now everything just works &mdash; and when there&rsquo;s an issue, they&rsquo;re on it immediately. They&rsquo;ve also given us peace of mind on the security side, especially around our transaction emails. I&rsquo;d never go back to a generic IT provider.',
  'test_avatar': 'LA',
  'test_name':   'Los Angeles Real Estate Client',
  'test_role':   'Brokerage Owner &middot; Multi-Office Real Estate Firm &middot; Greater Los Angeles',
  'why_h2':      'Fortune 1000 IT Experience. Built for LA Real Estate.',
  'why_p':       'Los Angeles real estate moves fast and the deals are high-stakes. We understand that system reliability, transaction security, and fast agent support aren&rsquo;t nice-to-haves &mdash; they&rsquo;re how you stay competitive in one of the world&rsquo;s most active real estate markets.',
  'why_bullets': [
    'Woodland Hills &mdash; serving Greater Los Angeles real estate firms',
    'Wire fraud prevention built into every engagement',
    'MLS, CRM, and transaction management platform expertise',
    'Flat-rate pricing &mdash; predictable IT costs every month',
    'On-site dispatch across Greater LA &mdash; not just remote support',
  ],
  'why_stats': [('25+','Years in Real Estate IT'),('99.9%','Network Uptime'),('&lt;15m','Response &mdash; 24/7/365'),('CCPA','Ready')],
  'faq_h2': 'Real Estate IT Questions We Hear Every Day',
  'faq': [
    { 'q': 'How does Pro Link prevent wire fraud in real estate transactions?',
      'q_plain': 'How does Pro Link prevent wire fraud in real estate transactions?',
      'a': 'We deploy multi-layer email security including DMARC/DKIM/SPF enforcement and advanced BEC filtering that detects impersonation attempts before they reach your agents&rsquo; inboxes. We also provide security training specifically focused on real estate wire fraud scenarios, including recognizing spoofed emails and safe wire instruction verification practices. Wire fraud is the highest-cost cyber threat in real estate &mdash; we treat it accordingly.',
      'a_plain': 'We deploy multi-layer email security including DMARC/DKIM/SPF enforcement and advanced BEC filtering. We also provide security training focused on real estate wire fraud scenarios, including recognizing spoofed emails and safe wire verification practices.' },
    { 'q': 'What MLS and CRM systems does Pro Link Systems support?',
      'q_plain': 'What MLS and CRM systems does Pro Link Systems support?',
      'a': 'We support all major real estate platforms including CRMLS, SoCal MLS, Salesforce, Follow Up Boss, KvCore, Chime, BoomTown, DocuSign, Dotloop, SkySlope, and proprietary brokerage systems. We manage the underlying infrastructure, network connectivity, integrations, and 24/7 uptime monitoring so your agents always have access when they need it.',
      'a_plain': 'We support CRMLS, SoCal MLS, Salesforce, Follow Up Boss, KvCore, Chime, BoomTown, DocuSign, Dotloop, SkySlope, and proprietary brokerage systems. We manage underlying infrastructure, connectivity, integrations, and 24/7 uptime monitoring.' },
    { 'q': 'Does Pro Link help with CCPA compliance for real estate firms?',
      'q_plain': 'Does Pro Link help with CCPA compliance for real estate firms?',
      'a': 'Yes. Real estate firms collect significant client PII and are subject to the California Consumer Privacy Act (CCPA). We implement data classification, access controls, encryption, and the policy documentation you need to demonstrate CCPA compliance &mdash; including vendor due diligence for your cloud tools and transaction platforms.',
      'a_plain': 'Yes. Real estate firms collect significant client PII and are subject to CCPA. We implement data classification, access controls, encryption, and the documentation needed to demonstrate compliance, including vendor due diligence for cloud and transaction platforms.' },
    { 'q': 'How quickly can Pro Link respond when our systems go down?',
      'q_plain': 'How quickly can Pro Link respond when our systems go down?',
      'a': 'Under 15 minutes, 24/7/365. System outages affecting active transactions receive immediate priority escalation. We maintain on-site dispatch capability across Greater Los Angeles for issues that cannot be resolved remotely. Your agents won&rsquo;t lose a deal because IT was slow to respond.',
      'a_plain': 'Under 15 minutes, 24/7/365. System outages affecting active transactions receive immediate priority escalation. We maintain on-site dispatch capability across Greater Los Angeles for issues that cannot be resolved remotely.' },
    { 'q': 'Can Pro Link support a real estate firm with multiple offices across LA?',
      'q_plain': 'Can Pro Link support a real estate firm with multiple offices across LA?',
      'a': 'Yes &mdash; multi-office real estate operations are where we excel. We manage standardized security, connectivity, and system access across all your locations so agents have a consistent experience whether they&rsquo;re in your Beverly Hills office, your West Hollywood office, or working remotely. We handle the complexity so you don&rsquo;t have to.',
      'a_plain': 'Yes. We manage standardized security, connectivity, and system access across multiple locations so agents have a consistent experience at every office and when working remotely.' },
  ],
  'cta_label': 'Ready to Close Deals Faster?',
  'cta_h2':    'Unreliable IT and Wire Fraud Risk<br>Are Costing You Deals.',
  'cta_p':     'Free real estate IT assessment. We review your MLS infrastructure, transaction security, and cybersecurity posture &mdash; and give you a clear roadmap. No pressure. No commitment.',
  'fc_h4':     'Real Estate IT',
  'fc_links':  ['MLS / CRM Support','Wire Fraud Prevention','Agent Mobility','Cybersecurity','Cloud Tools','24/7 Help Desk'],
  'footer_p':  'Managed IT, cybersecurity, and transaction-secure infrastructure for Los Angeles real estate firms since 1999. Trusted by brokerages, property managers, and commercial real estate firms across Greater LA.',
},

] # end INDUSTRIES

# ─── WRITE FILES ─────────────────────────────────────────────────────────────
for d in INDUSTRIES:
    path = os.path.join(OUT, d['filename'])
    html = build_page(d)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  Written: {d["filename"]}  ({len(html):,} bytes)')

# ─── UPDATE SITEMAP ───────────────────────────────────────────────────────────
sitemap_path = os.path.join(OUT, 'sitemap.xml')
with open(sitemap_path, 'r', encoding='utf-8') as f:
    sm = f.read()

new_entries = {
    'financial-services-it-los-angeles': '2026-05-28',
    'real-estate-it-services':           '2026-05-28',
}
for slug, date in new_entries.items():
    url = 'https://prolinksystems.com/' + slug
    if url not in sm:
        entry = (
            '  <url>\n'
            '    <loc>' + url + '</loc>\n'
            '    <lastmod>' + date + '</lastmod>\n'
            '    <changefreq>monthly</changefreq>\n'
            '    <priority>0.9</priority>\n'
            '  </url>\n'
        )
        sm = sm.replace('</urlset>', entry + '</urlset>')
        print(f'  Sitemap: added {slug}')
    else:
        print(f'  Sitemap: already has {slug}')

with open(sitemap_path, 'w', encoding='utf-8') as f:
    f.write(sm)

# ─── UPDATE INDEX.HTML CHIPS ─────────────────────────────────────────────────
index_path = os.path.join(OUT, 'index.html')
with open(index_path, 'r', encoding='utf-8') as f:
    idx = f.read()

chip_map = {
    '<div class="industry-chip"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>Financial Services</div>':
        '<a href="financial-services-it-los-angeles.html" class="industry-chip" style="text-decoration:none;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>Financial Services</a>',
    '<div class="industry-chip"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>Real Estate</div>':
        '<a href="real-estate-it-services.html" class="industry-chip" style="text-decoration:none;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>Real Estate</a>',
}

changes = 0
for old, new in chip_map.items():
    if old in idx:
        idx = idx.replace(old, new)
        changes += 1
        print(f'  index.html: updated chip for {new.split(".html")[0].split('href="')[1]}')
    else:
        print(f'  index.html: chip not found (may already be a link)')

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(idx)
if changes:
    print(f'  index.html: {changes} chip(s) converted to links')

print('\nDone. 2 pages generated.')
