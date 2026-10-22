#!/usr/bin/env python3
"""
Catalyst Capital Management, EB-5 Construction Administration and Loan Servicing.
Static site generator, built the same way as catalystcd.com.

No dependencies. Run:  python3 build.py
Output:                dist/

Content lives in content/*.json. Photography lives in static/img/ and is
produced by tools-process-images.py.
"""
import json, os, shutil, html, datetime, re

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
STATIC = os.path.join(ROOT, "static")
DIST = os.path.join(ROOT, "dist")


def load(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as f:
        return json.load(f)


def visible(records):
    """Records with "visible": false are dropped from the site entirely,
    including from every total. Omitting the field means visible."""
    return [r for r in records if r.get("visible", True)]


SITE = load("site.json")
SVC = load("services.json")
LOANS = visible(load("loans.json"))
TEAM = visible(load("team.json"))
DEV = load("developer.json")
INFO = load("info.json")
CATS = INFO["categories"]
CAT_NAME = {c["slug"]: c["name"] for c in CATS}
ARTICLES = visible(INFO["articles"])
BY_ART = {a["slug"]: a for a in ARTICLES}

TRACK = [l for l in LOANS if not l.get("current")]
TRACK_TOTAL = sum(l["amount"] for l in TRACK)
STATES = sorted({l["state"] for l in LOANS})

e = lambda s: html.escape(str(s or ""), quote=True)
YEAR = datetime.date.today().year
TODAY = datetime.date.today().isoformat()

MANIFEST_PATH = os.path.join(STATIC, "img", "manifest.json")
MANIFEST = {}
if os.path.exists(MANIFEST_PATH):
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        MANIFEST = json.load(f)

SIZES = {
    "hero":    "100vw",
    "card":    "(max-width:760px) 100vw, 50vw",
    "row":     "(max-width:1024px) 100vw, 58vw",
    "third":   "(max-width:760px) 100vw, 33vw",
    "quarter": "(max-width:760px) 100vw, 25vw",
}


def has_media(slug, role):
    return slug in MANIFEST and role in MANIFEST[slug]


def pic(slug, role, alt, sizes_key="card", eager=False, prefix=None):
    """Responsive <picture> with WebP srcset and a JPEG fallback.
    Photo sets live at /assets/img/<slug>/<role>-<w>; the deck groups
    (loans, team) live at /assets/img/<group>/<name>-<w>."""
    if not has_media(slug, role):
        return placeholder(alt or "Catalyst")
    m = MANIFEST[slug][role]
    base = f"/assets/img/{slug}/{role}"
    srcset = ", ".join(f"{base}-{w}.webp {w}w" for w in m["widths"])
    fb = f"{base}-{m['fallback']}.jpg"
    load_ = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<picture>'
            f'<source type="image/webp" srcset="{srcset}" sizes="{SIZES[sizes_key]}">'
            f'<img src="{fb}" alt="{e(alt)}" {load_} decoding="async">'
            f'</picture>')


def placeholder(name, label="Image"):
    return (f'<div class="ph"><svg viewBox="0 0 32 32">'
            f'<circle cx="16" cy="16" r="13" fill="none" stroke="#B79A4F" stroke-width="2"/>'
            f'<circle cx="16" cy="16" r="7" fill="none" stroke="#B79A4F" stroke-width="2"/></svg>'
            f'<div class="pn">{e(name)}</div><div class="pl">{e(label)}</div></div>')


def money(m):
    """11.45 -> $11.45M, 32 -> $32M"""
    s = f"{m:.2f}".rstrip("0").rstrip(".")
    return f"${s}M"


# ----------------------------------------------------------------- shell

def og_image(slug="liberty"):
    if has_media(slug, "hero"):
        m = MANIFEST[slug]["hero"]
        return f"{SITE['url']}/assets/img/{slug}/hero-{m['fallback']}.jpg"
    return ""


def head(title, desc, path, image=None, jsonld=None, extra=""):
    url = SITE["url"].rstrip("/") + path
    img = image or og_image()
    ld = f'\n<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(SITE['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(img)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(img)}">
<meta name="theme-color" content="#0E1A3D">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/styles.css">{extra}
<link rel="icon" href="/assets/img/brand/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="/assets/img/brand/mark-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="/assets/img/brand/apple-touch-icon.png">{ld}
</head>
<body>"""


LOGO_SRCSET = ", ".join(
    f"/assets/img/brand/logo-{{c}}-{w}.png {w}w" for w in (240, 360, 480))


def lockup(colour, cls="", alt="", w=150):
    """Catalyst lockup. Aspect is 1518x362, so height = width / 4.193."""
    a = f'alt="{e(alt)}"' if alt else 'alt="" aria-hidden="true"'
    return (f'<img class="{cls}" src="/assets/img/brand/logo-{colour}-360.png" '
            f'srcset="{LOGO_SRCSET.format(c=colour)}" sizes="{w}px" '
            f'width="1518" height="362" {a} decoding="async">')


def header(active):
    items = "".join(
        '<li><a href="{}"{}>{}</a></li>'.format(
            e(u), ' class="active"' if active == u else '', e(n))
        for n, u in SITE["nav"])
    mitems = "".join(f'<a href="{e(u)}">{e(n)}</a>' for n, u in SITE["nav"])
    return f"""
<a class="skip" href="#main">Skip to content</a>
<header id="hdr">
  <div class="wide hdr">
    <a href="/" class="logo" aria-label="{e(SITE['name'])} EB-5 home">
      {lockup('white', 'lw', SITE['name'])}{lockup('navy', 'ln')}
      <span class="sublogo">EB-5 Services</span>
    </a>
    <nav aria-label="Primary"><ul>{items}</ul></nav>
    <div class="hdr-cta">
      <a href="/contact/?type=proposal" class="portal">Request a Proposal</a>
      <button class="burger" id="burger" aria-label="Open menu" aria-expanded="false" aria-controls="mnav">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>
<div class="mnav" id="mnav">
  <a href="/">Home</a>{mitems}
  <a href="/contact/?type=proposal">Request a Proposal</a>
</div>
<main id="main">"""


def stat_band(stats):
    return "\n  ".join(
        f'<div class="stat rv"><div class="n">{e(t["value"])}</div>'
        f'<div class="l">{e(t["label"])}</div></div>' for t in stats)


def pre_footer():
    return f"""<section class="prefoot">
  <div class="bg">{pic('capitol-night', 'hero', '', 'hero')}</div>
  <div class="wide"><div class="inner">
    <div>
      <span class="eyebrow on-dark">Next Steps</span>
      <h2>Let’s work together</h2>
    </div>
    <div class="btns" style="margin:0">
      <a class="btn light" href="/contact/">Start a Conversation <span class="ar">&rarr;</span></a>
      <a class="btn gold" href="/contact/?type=proposal">Request a Proposal <span class="ar">&rarr;</span></a>
    </div>
  </div></div>
</section>"""


def footer(scripts=""):
    a = SITE["address"]
    nav = "".join(f'<li><a href="{e(u)}">{e(n)}</a></li>' for n, u in SITE["nav"])
    return f"""</main>
<footer>
  <div class="wide">
    <div class="fgrid">
      <div>
        <div class="flogo">{lockup('white', '', SITE['name'], 168)}</div>
        <p style="max-width:36ch;font-size:14.5px">{e(SITE['description'])}</p>
      </div>
      <div>
        <h6>Office</h6>
        <ul>
          <li>{e(a['street'])}<br>{e(a['city'])}, {e(a['state'])} {e(a['zip'])}</li>
          <li style="margin-top:16px"><a href="tel:{e(SITE['phoneRaw'])}">{e(SITE['phone'])}</a></li>
          <li><a href="mailto:{e(SITE['email'])}">{e(SITE['email'])}</a></li>
        </ul>
      </div>
      <div><h6>Navigate</h6><ul>{nav}</ul></div>
      <div>
        <h6>Connect</h6>
        <ul>
          <li><a href="/contact/?type=proposal">Request a Proposal</a></li>
          <li><a href="{e(SITE['ccm'])}" target="_blank" rel="noopener">Catalyst Capital Management</a></li>
          <li><a href="{e(SITE['cd'])}" target="_blank" rel="noopener">Catalyst Community Development</a></li>
          <li><a href="{e(SITE['linkedin'])}" target="_blank" rel="noopener">LinkedIn</a></li>
        </ul>
      </div>
    </div>
    <p class="fdisc">{e(SITE['disclaimer'])}</p>
    <div class="fbar">
      <div>&copy; {YEAR} {e(SITE['name'])}. All rights reserved.</div>
      <div><a href="/privacy/">Privacy Policy</a> &middot; <a href="/terms/">Terms of Use</a></div>
    </div>
  </div>
</footer>
<script src="/assets/app.js" defer></script>{scripts}
</body>
</html>"""


def hero(eyebrow, h1, sub, slug, alt="", full=False, buttons=""):
    cls = "hero" if full else "phero"
    cue = '<div class="scroll-cue">Scroll</div>' if full else ""
    subhtml = f'<p class="sub">{sub}</p>' if sub else ""
    return f"""<section class="{cls}">
  <div class="hero-media">{pic(slug, 'hero', alt, 'hero', eager=True)}</div>
  <div class="scrim"></div>
  <div class="hero-content"><div class="wide">
    <span class="eyebrow on-dark">{eyebrow}</span>
    <h1>{h1}</h1>{subhtml}{buttons}
  </div></div>{cue}
</section>"""


def lead(text, rule=True):
    r = '<div class="rule-gold"></div>' if rule else ""
    return f"""<section><div class="container rv" style="max-width:1000px">
  {r}<p class="lead">{text}</p>
</div></section>"""


# ----------------------------------------------------------------- pieces

def risk_cards():
    return "".join(
        f'<div class="risk {"hi" if r.get("highlight") else ""}"><h4>{e(r["name"])}</h4>'
        f'<p>{e(r["description"])}</p></div>' for r in SITE["risks"])


def flow_diagram():
    """Where Catalyst sits in the EB-5 capital flow (deck slide 3)."""
    return """<div class="flow rv" role="img" aria-label="Regional center sponsors EB-5 investors, who invest in the NCE. The fund administrator controls the flow of funds from the NCE to the JCE. Catalyst works with the JCE and sends verified draw packages, deployment notices and EB-5 evidence to the fund administrator.">
  <div class="fl-rc fbox dk">Regional Center</div>
  <div class="fl-fa fbox dk">Fund Administrator</div>
  <div class="fl-a1 farr v"><span>Sponsors</span></div>
  <div class="fl-a2 farr v"><span>Controls flow of funds</span></div>
  <div class="fl-inv fbox">EB-5 Investors</div>
  <div class="fl-a3 farr h"></div>
  <div class="fl-nce fbox">NCE <small>EB-5 Fund</small></div>
  <div class="fl-a4 farr h"></div>
  <div class="fl-jce fbox">JCE <small>Project</small></div>
  <div class="fl-a5 farr h gold both"></div>
  <div class="fl-cat">
    <span class="eyebrow on-dark" style="margin-bottom:10px">Catalyst</span>
    <h4>Construction Admin &amp; Loan Servicer</h4>
    <p>Reviews every draw, manages inspections, collects lien waivers and verifies deployment.</p>
  </div>
  <div class="fl-back">
    <span class="back-line"></span>
    <span class="back-lbl">Verified draw packages, deployment notices and EB-5 evidence to the fund administrator</span>
  </div>
</div>"""


def draw_cycle():
    return "".join(
        f'<div class="dstep {"hi" if s.get("highlight") else ""}"><div class="dn">{e(s["n"])}</div>'
        f'<h4>{e(s["name"])}</h4><p>{e(s["description"])}</p></div>' for s in SVC["drawCycle"])


def stage_grid(stages):
    out = ""
    for i, s in enumerate(stages):
        li = "".join(f"<li>{e(x)}</li>" for x in s["items"])
        out += (f'<div class="stage {"mid" if i == 2 else ""}"><div class="sn">{e(s["step"])}</div>'
                f'<h4>{e(s["name"])}</h4><ul>{li}</ul></div>')
    return out


def engagement_cards():
    out = ""
    for g in SVC["engagements"]:
        li = "".join(f"<li>{e(x)}</li>" for x in g["items"])
        out += f"""<div class="eng {'hi' if g.get('highlight') else ''} rv">
  <span class="eyebrow">{e(g['tier'])}</span>
  <h3>{e(g['name'])}</h3>
  <p>{e(g['description'])}</p>
  <ul>{li}</ul>
</div>"""
    return out


def value_cols():
    def col(title, items):
        rows = "".join(f'<p><strong>{e(v["name"])}</strong> {e(v["description"])}</p>' for v in items)
        return f'<div class="vcol rv"><div class="vh">{e(title)}</div><div class="vb">{rows}</div></div>'
    return (col("For Fund Administrators", SVC["valueFundAdmin"])
            + col("For Regional Centers", SVC["valueRegionalCenter"]))


def loan_card(l, i=0):
    tag = f'<span class="lc-tag">{e(l["note"])}</span>' if l.get("note") else ""
    return f"""<div class="lcard rv" style="transition-delay:{(i % 4) * 70}ms">
  <div class="lim">{pic('loans', l['slug'], l['name'] + ', ' + l['city'], 'quarter')}{tag}</div>
  <h4>{e(l['name'])}</h4>
  <div class="lmeta"><strong>{money(l['amount'])}</strong> &middot; {e(l['city'])}, {e(l['state'])}</div>
  <div class="ltype">{e(l['type'])}</div>
</div>"""


def dev_table():
    rows = "".join(f'<tr><td><a href="{e(p["url"])}" target="_blank" rel="noopener">{e(p["name"])}</a></td>'
                   f'<td>{e(p["program"])}</td><td class="r">{e(p["cost"])}</td></tr>'
                   for p in DEV["projects"])
    return f'<table class="dtable"><thead><tr><th>Project</th><th>Program</th><th class="r">Cost</th></tr></thead><tbody>{rows}</tbody></table>'


def developer_band():
    stats = "".join(f'<div class="dstat"><div class="n">{e(s["value"])}</div><div class="l">{e(s["label"])}</div></div>'
                    for s in DEV["stats"])
    return f"""<section class="dark"><div class="wide" style="padding:110px 32px">
  <div class="devgrid">
    <div class="rv">
      <span class="eyebrow on-dark">A Developer’s Perspective</span>
      <h2>We understand how developers operate.</h2>
      <p style="margin-top:22px;font-size:18px;line-height:1.6">{e(DEV['intro'])}</p>
      <div style="margin-top:34px">{dev_table()}</div>
      <div class="btns"><a class="btn light" href="{e(SITE['cd'])}" target="_blank" rel="noopener">Visit catalystcd.com <span class="ar">&rarr;</span></a></div>
    </div>
    <div class="dstats rv">{stats}</div>
  </div>
</div></section>"""


def icard(a, i=0, show_summary=True):
    s = f'<p>{e(a["summary"])}</p>' if show_summary else ""
    d = f'<div class="dt">{e(a["date"])}</div>' if a.get("date") else ""
    return f"""<a class="icard rv" data-cat="{e(a['category'])}" href="/info-center/{e(a['slug'])}/" style="transition-delay:{(i % 3) * 80}ms">
  <div class="cat">{e(CAT_NAME[a['category']])}</div>
  <h4>{e(a['title'])}</h4>{s}{d}
  <span class="more">Read <span class="ar">&rarr;</span></span>
</a>"""


def timeline_html(compact=False):
    out = ""
    for s in INFO["timeline"]:
        flag = '<span class="tl-flag">Catalyst verifies</span>' if s.get("catalyst") else ""
        out += (f'<li class="{"cat" if s.get("catalyst") else ""}"><div class="tn">{e(s["n"])}</div>'
                f'<div><h4>{e(s["name"])} {flag}</h4><p>{e(s["description"])}</p></div></li>')
    return f'<ol class="tl {"compact" if compact else ""}">{out}</ol>'


def render_blocks(blocks):
    out = []
    for b in blocks:
        if "p" in b:
            out.append(f'<p>{e(b["p"])}</p>')
        elif "h" in b:
            out.append(f'<h3>{e(b["h"])}</h3>')
        elif "ul" in b:
            out.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in b["ul"]) + "</ul>")
        elif "table" in b:
            t = b["table"]
            th = "".join(f"<th>{e(x)}</th>" for x in t["head"])
            tr = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in t["rows"])
            out.append(f'<div class="tscroll"><table class="atable"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>')
        elif "callout" in b:
            out.append(f'<div class="callout">{e(b["callout"])}</div>')
        elif b.get("timeline"):
            out.append(timeline_html(compact=True))
    return "\n".join(out)


# ----------------------------------------------------------------- pages

def page_home():
    ld = {"@context": "https://schema.org", "@type": "FinancialService",
          "name": f"{SITE['name']}, {SITE['product']}", "url": SITE["url"],
          "description": SITE["description"], "telephone": SITE["phone"], "email": SITE["email"],
          "address": {"@type": "PostalAddress", "streetAddress": SITE["address"]["street"],
                      "addressLocality": SITE["address"]["city"], "addressRegion": SITE["address"]["state"],
                      "postalCode": SITE["address"]["zip"], "addressCountry": "US"},
          "sameAs": [SITE["ccm"], SITE["cd"]]}
    btns = ('<div class="btns"><a class="btn light" href="/services/">Our Services <span class="ar">&rarr;</span></a>'
            '<a class="btn gold" href="/contact/?type=proposal">Request a Proposal <span class="ar">&rarr;</span></a></div>')
    loans = "".join(loan_card(l, i) for i, l in enumerate(LOANS[:8]))
    latest = [a for a in ARTICLES if a.get("featured")] + [a for a in ARTICLES if not a.get("featured")]
    news = "".join(icard(a, i) for i, a in enumerate(latest[:3]))
    eng = engagement_cards()
    return (head(f"EB-5 Construction Administration and Loan Servicing | {SITE['name']}",
                 "Construction administration, draw verification and loan servicing for EB-5 fund administrators, "
                 "regional centers and EB-5 funds. Every dollar verified before it moves.",
                 "/", jsonld=ld)
        + header("/")
        + hero("Catalyst Capital Management", "EB-5 Construction Admin &amp; Loan Servicing",
               "Construction administration for fund administrators, regional centers and EB-5 funds.",
               "liberty", "The Statue of Liberty against a clear sky", full=True, buttons=btns)
        + f"""
<div class="s1"></div>
{lead("Construction monitoring helps protect EB-5 funds from the risks inherent in construction lending. Catalyst works with fund administrators and regional centers to mitigate these risks by providing construction loan administration and monitoring services, including cost reviews, construction loan inspections, schedule of values tracking, lien waiver collection and title updates, and recommendations on disbursement of funds.")}

<div class="s1"></div>
<section class="stats"><div class="wide"><div class="stats-grid">
  {stat_band(SITE['stats'])}
</div></div></section>

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:760px;margin-bottom:48px">
    <span class="eyebrow">Construction Risk Management</span>
    <h2>The importance of effective oversight.</h2>
  </div>
  <div class="risk-grid rv">{risk_cards()}</div>
</div></section>

<div class="s2"></div>
<section class="paperband"><div class="wide" style="padding:110px 32px">
  <div class="rv" style="max-width:760px;margin-bottom:56px">
    <span class="eyebrow">Where We Fit</span>
    <h2>An extension of your team.</h2>
    <p class="muted" style="margin-top:18px">Catalyst works on behalf of the fund, lender and/or NCE and reports to the fund administrator and regional center. We complement your team; we do not replace it.</p>
  </div>
  {flow_diagram()}
</div></section>

<div class="s2"></div>
<section><div class="container"><div class="row2 rv">
  <div class="hoverimg">{pic('draw-review', 'card', 'A reviewer marking up a construction pay application', 'row')}</div>
  <div class="cta-col">
    <span class="eyebrow">The Draw Cycle</span>
    <h2>Every dollar verified before it moves.</h2>
    <p class="muted" style="margin-top:20px">Each request is tested against budget, invoices and contracts, inspected in the field, reconciled against lien waivers and title, and packaged with a recommendation. The fund administrator keeps release authority. Catalyst makes each release defensible, with a complete package and a clean audit trail behind it.</p>
    <ul class="svc-list">
      <li><a href="/services/#draw-cycle"><span class="t">Request, review, inspect</span><span class="ar">&rarr;</span></a></li>
      <li><a href="/services/#draw-cycle"><span class="t">Reconcile, recommend, verify</span><span class="ar">&rarr;</span></a></li>
      <li><a href="/services/#compliance"><span class="t">Documented compliance record</span><span class="ar">&rarr;</span></a></li>
    </ul>
  </div>
</div></div></section>

<div class="s2"></div>
<section class="dark"><div class="wide" style="padding:110px 32px">
  <div class="rv" style="max-width:760px">
    <span class="eyebrow on-dark">Ways to Work Together</span>
    <h2>Three engagement models.</h2>
  </div>
  <div class="eng-grid on-dark">{eng}</div>
  <div class="btns rv"><a class="btn light" href="/services/">Full Scope of Services <span class="ar">&rarr;</span></a></div>
</div></section>

<div class="s2"></div>
<section><div class="wide">
  <div class="rv sechead">
    <h2>Representative EB-5 construction loans</h2>
    <a class="small-caps ul" href="/track-record/">Full track record &rarr;</a>
  </div>
  <div class="loan-grid">{loans}</div>
</div></section>

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:700px;margin-bottom:48px">
    <span class="eyebrow">EB-5 Tools</span>
    <h2>Resources for sponsors and regional centers.</h2>
  </div>
  <div class="tools2">
    <a class="tool rv" href="/tea-map/">
      <div class="tim">{pic('flags', 'card', 'American flags on a row of flagpoles', 'card')}</div>
      <div class="tbody"><span class="eyebrow">Interactive Tool</span><h3>TEA Map</h3>
        <p class="muted">Check whether a project site may qualify as a high-unemployment or rural targeted employment area, with live census tract data and adjacent-tract combinations.</p>
        <span class="more">Open the map <span class="ar">&rarr;</span></span></div>
    </a>
    <a class="tool rv" href="/info-center/">
      <div class="tim">{pic('capitol-day', 'card', 'The U.S. Capitol dome', 'card')}</div>
      <div class="tbody"><span class="eyebrow">Library</span><h3>EB-5 Info Center</h3>
        <p class="muted">Plain-language guides on EB-5 structure, requirements, timelines, construction deployment and the latest program updates.</p>
        <span class="more">Browse articles <span class="ar">&rarr;</span></span></div>
    </a>
  </div>
</div></section>

<div class="s2"></div>
<section class="newsband"><div class="wide" style="padding:110px 32px">
  <div class="rv sechead" style="border-color:var(--line)">
    <h2>From the Info Center</h2>
    <a class="small-caps ul" href="/info-center/">All articles &rarr;</a>
  </div>
  <div class="igrid">{news}</div>
</div></section>

{pre_footer()}""" + footer())


def page_services():
    return (head(f"Services | {SITE['name']} EB-5",
                 "Pre-closing diligence, draw administration, site monitoring, Section Q verification, closeout and "
                 "ongoing loan servicing for EB-5 construction loans.",
                 "/services/", og_image("earthwork"))
        + header("/services/")
        + hero("Scope of Services", "Pre-construction through repayment.",
               "Construction administration and loan servicing built around the way EB-5 capital is raised, deployed and documented.",
               "earthwork", "Wheel loaders on an active site work project")
        + f"""
<div class="s1"></div>
{lead("Catalyst reviews every draw, manages inspections, collects lien waivers and verifies deployment, then carries the loan through servicing and repayment. Each step produces a record the fund administrator, regional center and investors can rely on.")}

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:760px;margin-bottom:44px">
    <span class="eyebrow">Construction Administration</span>
    <h2>Pre-construction through completion.</h2>
  </div>
  <div class="stage-grid rv">{stage_grid(SVC['constructionAdmin'])}</div>
</div></section>

<div class="s2"></div>
<section class="paperband" id="draw-cycle"><div class="wide" style="padding:110px 32px">
  <div class="rv" style="max-width:760px;margin-bottom:48px">
    <span class="eyebrow">The Draw Cycle</span>
    <h2>Every dollar verified before it moves.</h2>
  </div>
  <div class="dsteps rv">{draw_cycle()}</div>
  <p class="lead rv" style="margin-top:48px;max-width:60ch;font-size:21px">The fund administrator keeps release authority. Catalyst makes each release defensible, with a complete package and a clean audit trail behind it.</p>
</div></section>

<div class="s2"></div>
<section><div class="container"><div class="row2 rv">
  <div class="hoverimg">{pic('documents', 'card', 'Two people reviewing loan documents', 'row')}</div>
  <div class="cta-col">
    <span class="eyebrow">Ongoing Loan Servicing</span>
    <h2>Loan closing through repayment.</h2>
    <p class="muted" style="margin-top:20px">After closing, Catalyst boards the loan, administers payments, reserves and escrows, monitors covenants and collateral, and coordinates payoff and release. For construction loans, servicing and draw administration run as one process, so the lender sees one consistent record.</p>
  </div>
</div></div></section>

<div class="s1"></div>
<section><div class="wide">
  <div class="stage-grid rv">{stage_grid(SVC['loanServicing'])}</div>
</div></section>

<div class="s2"></div>
<section class="dark" id="compliance"><div class="wide" style="padding:110px 32px">
  <div class="rv" style="max-width:760px">
    <span class="eyebrow on-dark">EB-5 Compliance and Loan Management Support</span>
    <h2>A documented compliance record.</h2>
  </div>
  <div class="comp rv">
    <div>
      <div class="comp-h">Construction Administration</div>
      <div class="comp-grid">{''.join(f'<div class="ci"><h4>{e(c["name"])}</h4><p>{e(c["description"])}</p></div>' for c in SVC['complianceConstruction'])}</div>
    </div>
    <div>
      <div class="comp-h">Ongoing Loan Servicing</div>
      <div class="comp-side">{''.join(f'<div class="ci"><h4>{e(c["name"])}</h4><p>{e(c["description"])}</p></div>' for c in SVC['complianceServicing'])}</div>
    </div>
  </div>
</div></section>

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:760px;margin-bottom:44px">
    <span class="eyebrow">Ways to Work Together</span>
    <h2>Three engagement models.</h2>
  </div>
  <div class="eng-grid">{engagement_cards()}</div>
</div></section>

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:760px;margin-bottom:44px">
    <span class="eyebrow">The Value to You</span>
    <h2>A stronger offering without new overhead.</h2>
  </div>
  <div class="vgrid">{value_cols()}</div>
</div></section>

<div class="s2"></div>
{pre_footer()}""" + footer())


def page_track():
    loans = "".join(loan_card(l, i) for i, l in enumerate(LOANS))
    stats = [{"value": SITE["stats"][0]["value"], "label": "EB-5 Funded Construction Loans"},
             {"value": str(len(LOANS)), "label": "Representative Loans Shown"},
             {"value": str(len(STATES)), "label": "States Represented Here"},
             {"value": SITE["stats"][1]["value"], "label": "Loans Led by Catalyst’s Principal"}]
    return (head(f"Track Record | {SITE['name']} EB-5",
                 "Representative EB-5 funded construction loans originated, funded and serviced by the Catalyst team, "
                 "from hotels and seniors housing to self storage and mixed-use.",
                 "/track-record/", og_image("cranes"))
        + header("/track-record/")
        + hero("Track Record", "Loan servicing by experienced lenders.",
               "The Catalyst team has originated, funded and serviced hundreds of construction, SBA, USDA and bridge loans.",
               "cranes", "Tower cranes over buildings under construction")
        + f"""
<div class="s1"></div>
{lead("The Catalyst team has originated, funded and serviced hundreds of construction, SBA, USDA and bridge loans, including $180 million of ground-up construction loans funded by EB-5 investors through a regional center partnership.")}

<div class="s1"></div>
<section class="stats"><div class="wide"><div class="stats-grid">
  {stat_band(stats)}
</div></div></section>

<div class="s2"></div>
<section><div class="container rv" style="max-width:1100px">
  <div class="mandate">
    <span class="eyebrow on-dark">Current EB-5 Mandate</span>
    <p>{e(SITE['currentMandate'])}</p>
  </div>
</div></section>

<div class="s2"></div>
<section><div class="wide">
  <div class="rv sechead">
    <h2>Representative EB-5 construction loans</h2>
    <div class="small-caps muted">{len(LOANS)} loans &middot; {len(STATES)} states</div>
  </div>
  <div class="loan-grid">{loans}</div>
</div></section>

<div class="s2"></div>
{developer_band()}
{pre_footer()}""" + footer())


def page_about():
    members = ""
    for i, t in enumerate(TEAM):
        bio = "".join(f'<p class="muted">{e(b)}</p>' for b in t["bio"])
        members += f"""<div class="tcard rv" style="transition-delay:{i*80}ms">
  <details><summary>
    <div class="por">{pic('team', t['slug'], t['name'], 'third')}</div>
    <h5>{e(t['name'])}</h5><div class="ti">{e(t['title'])}</div><div class="dp">{e(t['dept'])}</div>
  </summary><div class="biobox">{bio}</div></details>
</div>"""
    pillars = [("Lenders First", "We have originated, funded and serviced hundreds of construction, SBA, USDA and bridge loans. We read a loan agreement for what it requires of the servicer, and we hold every draw to it."),
               ("Developers Too", "Our affiliate builds large-scale multifamily and mixed-use projects. We know how budgets, schedules and change orders behave in the field because we manage them ourselves."),
               ("EB-5 Native", "We have financed $180 million of EB-5 funded construction loans through a regional center partnership. Deployment, sustainment and I-829 evidence are built into how we work.")]
    pcards = "".join(f'<div class="pillar rv" style="transition-delay:{i*80}ms"><div class="pi">{["01","02","03"][i]}</div>'
                     f'<h4>{e(k)}</h4><p class="muted">{e(v)}</p></div>' for i, (k, v) in enumerate(pillars))
    ld = {"@context": "https://schema.org", "@type": "AboutPage", "url": SITE["url"] + "/about/",
          "mainEntity": {"@type": "Organization", "name": SITE["name"],
                         "employee": [{"@type": "Person", "name": t["name"], "jobTitle": t["title"]} for t in TEAM]}}
    return (head(f"About | {SITE['name']} EB-5",
                 "Catalyst Capital Management is a Tampa-based investment management firm focused on commercial real estate "
                 "loans and private credit, with a construction administration and servicing practice for EB-5.",
                 "/about/", og_image("capitol-day"), ld)
        + header("/about/")
        + hero("About Us", "Let’s get to know each other.",
               "A Tampa-based lending and development team that brings construction discipline to EB-5 capital.",
               "capitol-day", "The U.S. Capitol dome under a blue sky")
        + f"""
<div class="s1"></div>
{lead("Catalyst Capital Management is a Tampa-based investment management firm focused on commercial real estate loans and private credit. Our EB-5 practice gives fund administrators and regional centers the construction expertise to verify every deployment, without building a construction department of their own.")}

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:760px;margin-bottom:48px">
    <span class="eyebrow">What Sets Us Apart</span>
    <h2>Built by lenders and developers.</h2>
  </div>
  <div class="pillars">{pcards}</div>
</div></section>

<div class="s2"></div>
<section><div class="container"><div class="row2 rev rv">
  <div class="hoverimg">{pic('family', 'card', 'A family on a video call at home', 'row')}</div>
  <div class="cta-col">
    <span class="eyebrow">Why It Matters</span>
    <h2>Behind every draw is a family.</h2>
    <p class="muted" style="margin-top:20px">EB-5 investors commit their capital and their family’s future to a project they rarely see. Their path to permanent residence depends on that capital being deployed as planned and documented as it goes. Capital preservation and immigration compliance come first in everything we do, and that is the standard we hold every construction draw to.</p>
  </div>
</div></div></section>

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:640px;margin-bottom:52px">
    <span class="eyebrow">Management Team</span><h2>The project team.</h2>
    <p class="muted" style="margin-top:18px">Select a name to read more.</p>
  </div>
  <div class="tgrid three">{members}</div>
</div></section>

<div class="s2"></div>
<section class="paperband"><div class="wide" style="padding:110px 32px">
  <div class="tlwrap">
    <div class="rv tl-intro">
      <span class="eyebrow">EB-5 Requirements and Timeline</span>
      <h2>The investor’s path, and where we protect it.</h2>
      <p class="muted" style="margin-top:18px">From subscription to permanent residence, the investor’s outcome is decided by what happens to the money in between. The steps marked below are where Catalyst verifies and documents deployment.</p>
      <div class="btns"><a class="btn" href="/info-center/">EB-5 Info Center <span class="ar">&rarr;</span></a></div>
    </div>
    <div class="rv">{timeline_html()}</div>
  </div>
</div></section>

<div class="s2"></div>
{developer_band()}

<div class="s2"></div>
<section><div class="wide">
  <div class="rv" style="max-width:760px;margin-bottom:44px">
    <span class="eyebrow">The Value to You</span>
    <h2>A stronger offering without new overhead.</h2>
  </div>
  <div class="vgrid">{value_cols()}</div>
</div></section>

<div class="s2"></div>
{pre_footer()}""" + footer())


def page_tea():
    leaflet = ('\n<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">')
    scripts = ('\n<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" defer></script>'
               '\n<script src="/assets/tea-map.js" defer></script>')
    rules = [("High Unemployment", "The project tract, alone or combined with any or all directly adjacent tracts, has a weighted average unemployment rate of at least 150% of the national average."),
             ("Rural", "Outside a metropolitan statistical area and outside the boundary of any city or town with a population of 20,000 or more, based on the most recent decennial census."),
             ("Infrastructure", "A qualifying infrastructure project receives the reduced investment amount regardless of location. This tool does not test infrastructure status.")]
    rcards = "".join(f'<div class="cap"><div class="k">{e(k)}</div><div class="d">{e(v)}</div></div>' for k, v in rules)
    return (head(f"EB-5 TEA Map | {SITE['name']}",
                 "Check whether a project address may qualify as an EB-5 targeted employment area. Census tract "
                 "unemployment, adjacent-tract weighted averages and a rural test, on one map.",
                 "/tea-map/", og_image("flags"), extra=leaflet)
        + header("/tea-map/")
        + hero("EB-5 Tools", "TEA Map.",
               "Check whether a project site may qualify as a high-unemployment or rural targeted employment area.",
               "flags", "American flags on a row of flagpoles")
        + f"""
<div class="s1"></div>
<section><div class="wide">
  <div class="tea rv" id="tea">
    <div class="tea-side">
      <form class="tea-search" id="teaForm" autocomplete="off">
        <label for="teaAddr" class="small-caps muted">Project address</label>
        <div class="tea-in">
          <input id="teaAddr" type="text" placeholder="e.g. 2000 Main St, Fort Myers, FL" required>
          <button class="btn solid" type="submit">Check <span class="ar">&rarr;</span></button>
        </div>
        <p class="tea-hint">Or click anywhere on the map. Click shaded neighbors to add or remove them from the combination.</p>
      </form>
      <div id="teaOut" class="tea-out" aria-live="polite">
        <div class="tea-empty">
          <h4>How it works</h4>
          <ol>
            <li>Enter an address or click the map.</li>
            <li>We find the census tract and every directly adjacent tract.</li>
            <li>We compare each tract, and the best combination, to 150% of the national unemployment rate.</li>
            <li>We test the rural definition using metro area boundaries and 2020 Census city populations.</li>
          </ol>
        </div>
      </div>
    </div>
    <div class="tea-map-wrap">
      <div id="teaMap" class="tea-map" role="application" aria-label="TEA map"></div>
      <div class="tea-legend">
        <span><i class="lg q"></i>Qualifies alone</span>
        <span><i class="lg s"></i>In combination</span>
        <span><i class="lg n"></i>Adjacent, not selected</span>
        <span><i class="lg p"></i>Project tract</span>
      </div>
    </div>
  </div>
  <p class="tea-note rv">Indicative only. Under the EB-5 Reform and Integrity Act of 2022, USCIS determines TEA status at the I-956F or I-526E stage. Unemployment data are American Community Survey 5-year estimates; boundaries and city populations are from the U.S. Census Bureau TIGERweb service. Use a professional TEA report for any filing.</p>
</div></section>

<div class="s2"></div>
<section class="dark"><div class="wide" style="padding:110px 32px">
  <div class="rv" style="max-width:760px">
    <span class="eyebrow on-dark">Targeted Employment Areas</span>
    <h2>Three ways to the reduced investment amount.</h2>
  </div>
  <div class="cap-grid three rv">{rcards}</div>
  <div class="btns rv"><a class="btn light" href="/info-center/targeted-employment-areas/">Read the TEA guide <span class="ar">&rarr;</span></a></div>
</div></section>

<div class="s2"></div>
<section><div class="container"><div class="row2 rv">
  <div class="hoverimg">{pic('main-street', 'card', 'An American flag on a small-town main street', 'row')}</div>
  <div class="cta-col">
    <span class="eyebrow">Reserved Visas</span>
    <h2>Why TEA status matters to investors.</h2>
    <p class="muted" style="margin-top:20px">Beyond the lower investment amount, RIA reserves 20% of EB-5 visas each year for rural projects, 10% for high-unemployment projects and 2% for infrastructure. For investors from backlogged countries, a reserved category can be the difference between a short wait and a long one. Designations generally last two years, so the timing of the project application matters.</p>
    <div class="btns"><a class="btn" href="/contact/?type=proposal">Discuss a Project <span class="ar">&rarr;</span></a></div>
  </div>
</div></div></section>

<div class="s2"></div>
{pre_footer()}""" + footer(scripts))


def page_info():
    chips = '<a class="chip on" href="/info-center/" data-cat="all">All</a>' + "".join(
        f'<a class="chip" href="/info-center/?category={e(c["slug"])}" data-cat="{e(c["slug"])}">{e(c["name"])}</a>'
        for c in CATS if any(a["category"] == c["slug"] for a in ARTICLES))
    order = [a for a in ARTICLES if a["category"] == "updates"] + [a for a in ARTICLES if a["category"] != "updates"]
    cards = "".join(icard(a, i) for i, a in enumerate(order))
    gl = "".join(f'<div class="gi"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in INFO["glossary"])
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "EB-5 Info Center",
          "url": SITE["url"] + "/info-center/",
          "hasPart": [{"@type": "Article", "headline": a["title"],
                       "url": f"{SITE['url']}/info-center/{a['slug']}/"} for a in ARTICLES]}
    return (head(f"EB-5 Info Center | {SITE['name']}",
                 "Plain-language EB-5 guides on program basics, regional center structure, investment and funding, "
                 "requirements, timelines, construction deployment, risk and current program updates.",
                 "/info-center/", og_image("capitol-day"), ld)
        + header("/info-center/")
        + hero("EB-5 Info Center", "Your guide to EB-5 capital.",
               "Program basics, requirements and timelines, with a lender’s view of how construction deployment protects investor outcomes.",
               "capitol-day", "The U.S. Capitol dome under a blue sky")
        + f"""
<div class="s1"></div>
<section><div class="wide">
  <div class="chips rv" id="chips" role="navigation" aria-label="Filter articles by category">{chips}</div>
  <div class="igrid" id="igrid">{cards}</div>
  <p class="muted rv" id="iempty" style="display:none;margin-top:30px">No articles in this category yet.</p>
</div></section>

<div class="s2"></div>
<section class="paperband"><div class="wide" style="padding:110px 32px">
  <div class="gwrap">
    <div class="rv">
      <span class="eyebrow">Glossary</span>
      <h2>Terms of the trade.</h2>
      <p class="muted" style="margin-top:18px">The EB-5 and construction lending vocabulary used across this site.</p>
    </div>
    <dl class="gloss rv">{gl}</dl>
  </div>
</div></section>

<div class="s2"></div>
<section><div class="container"><div class="row2 rv">
  <div class="cta-col">
    <span class="eyebrow">EB-5 Updates</span>
    <h2>Program changes, in your inbox.</h2>
    <p class="muted" style="margin-top:20px">Short notes when fees, investment amounts, reauthorization or USCIS policy change, written for fund administrators, regional centers and sponsors.</p>
    <form class="subform" name="updates" method="POST" data-netlify="true" netlify-honeypot="company-website" action="/thank-you/">
      <input type="hidden" name="form-name" value="updates">
      <p class="hp"><label>Do not fill this in: <input name="company-website"></label></p>
      <label for="ue" class="small-caps muted">Email</label>
      <div class="tea-in"><input id="ue" type="email" name="email" required placeholder="you@firm.com">
      <button class="btn solid" type="submit">Subscribe <span class="ar">&rarr;</span></button></div>
    </form>
  </div>
  <div class="hoverimg">{pic('capitol-night', 'card', 'The U.S. Capitol at night reflected in the pool', 'row')}</div>
</div></div></section>

<div class="s2"></div>
{pre_footer()}""" + footer())


def page_article(a):
    same = [x for x in ARTICLES if x["category"] == a["category"] and x["slug"] != a["slug"]]
    other = [x for x in ARTICLES if x["category"] != a["category"] and x["slug"] != a["slug"]]
    related = (same + other)[:3]
    img = ""
    if a.get("image") and has_media(a["image"], "card"):
        img = f'<div class="aimg">{pic(a["image"], "card", a["title"], "row")}</div>'
    date = a.get("date") or f"Reviewed {SITE['asOf']}"
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"],
          "description": a["summary"], "url": f"{SITE['url']}/info-center/{a['slug']}/",
          "publisher": {"@type": "Organization", "name": SITE["name"]}}
    return (head(f"{a['title']} | EB-5 Info Center", a["summary"], f"/info-center/{a['slug']}/",
                 jsonld=ld)
        + header("/info-center/")
        + f"""<section class="ahead"><div class="wide">
  <nav class="crumbs" aria-label="Breadcrumb">
    <a href="/">Home</a> <span>/</span> <a href="/info-center/">Info Center</a> <span>/</span>
    <a href="/info-center/?category={e(a['category'])}">{e(CAT_NAME[a['category']])}</a>
  </nav>
  <div class="ahead-in">
    <span class="eyebrow">{e(CAT_NAME[a['category']])}</span>
    <h1>{e(a['title'])}</h1>
    <p class="lead" style="margin-top:22px;max-width:52ch">{e(a['summary'])}</p>
    <div class="small-caps muted" style="margin-top:22px">{e(date)}</div>
  </div>
</div></section>

<section><div class="wide"><div class="art">
  <article class="prose rv">{img}{render_blocks(a['body'])}
    <p class="adisc">{e(SITE['disclaimer'])}</p>
  </article>
  <aside class="aside rv">
    <div class="abox dk">
      <span class="eyebrow on-dark">Catalyst EB-5 Services</span>
      <h4>Construction oversight for your next EB-5 loan.</h4>
      <p>Draw administration, deployment verification and loan servicing for fund administrators and regional centers.</p>
      <a class="btn light" href="/contact/?type=proposal">Request a Proposal <span class="ar">&rarr;</span></a>
    </div>
    <div class="abox">
      <span class="eyebrow">Tool</span>
      <h4>Check a TEA</h4>
      <p class="muted">Test a project address against the high-unemployment and rural definitions.</p>
      <a class="btn" href="/tea-map/">Open the TEA Map <span class="ar">&rarr;</span></a>
    </div>
  </aside>
</div></div></section>

<div class="s2"></div>
<section class="newsband"><div class="wide" style="padding:96px 32px">
  <div class="rv sechead" style="border-color:var(--line)">
    <h2>Related articles</h2>
    <a class="small-caps ul" href="/info-center/">All articles &rarr;</a>
  </div>
  <div class="igrid">{''.join(icard(r, i) for i, r in enumerate(related))}</div>
</div></section>
{pre_footer()}""" + footer())


def page_contact():
    roles = ["Fund administrator", "Regional center", "EB-5 fund or NCE manager", "Developer or JCE",
             "Immigration or securities counsel", "EB-5 investor", "Other"]
    models = ["Core: Construction Administration", "Expanded: Loan Servicing and NCE Support",
              "Full Cycle: Origination and Servicing", "Not sure yet"]
    ro = "".join(f'<option>{e(x)}</option>' for x in roles)
    mo = "".join(f'<option>{e(x)}</option>' for x in models)
    a = SITE["address"]
    ld = {"@context": "https://schema.org", "@type": "ContactPage", "url": SITE["url"] + "/contact/"}
    return (head(f"Contact | {SITE['name']} EB-5",
                 f"Catalyst Capital Management, {a['street']}, {a['city']}, {a['state']} {a['zip']}. "
                 f"Call {SITE['phone']} or request a proposal for EB-5 construction administration and loan servicing.",
                 "/contact/", og_image("capitol-night"), jsonld=ld)
        + header("/contact/")
        + hero("Contact", "Let’s work together.",
               "Tell us about the fund, the project and the loan. We will come back with a scope and a fee proposal.",
               "capitol-night", "The U.S. Capitol at night")
        + f"""
<div class="s1"></div>
<section><div class="container"><div class="row2 contact rv">
  <div>
    <span class="eyebrow">Tampa Headquarters</span>
    <h2>100 South<br>Ashley Drive.</h2>
    <p class="muted" style="margin-top:20px">Suite 275<br>{e(a['city'])}, {e(a['state'])} {e(a['zip'])}</p>
    <p class="muted" style="margin-top:18px">{e(SITE['contactName'])}<br>
      <a href="tel:{e(SITE['phoneRaw'])}" class="ul">{e(SITE['phone'])}</a><br>
      <a href="mailto:{e(SITE['email'])}" class="ul">{e(SITE['email'])}</a>
    </p>
    <div class="notebox" style="margin-top:40px">
      <span class="eyebrow">Helpful to include</span>
      <ul class="plainlist muted">
        <li>Project type, location and construction budget</li>
        <li>EB-5 loan size and position in the capital stack</li>
        <li>Fund administrator and regional center involved</li>
        <li>Expected closing date and construction start</li>
      </ul>
    </div>
  </div>
  <div class="formwrap">
    <span class="eyebrow">Send a Message</span>
    <form name="contact" method="POST" data-netlify="true" netlify-honeypot="company-website" action="/thank-you/">
      <input type="hidden" name="form-name" value="contact">
      <p class="hp"><label>Do not fill this in: <input name="company-website"></label></p>
      <div class="f2">
        <div class="field"><label for="fn">First Name</label><input id="fn" type="text" name="firstName" required></div>
        <div class="field"><label for="ln">Last Name</label><input id="ln" type="text" name="lastName" required></div>
      </div>
      <div class="f2">
        <div class="field"><label for="em">Email</label><input id="em" type="email" name="email" required></div>
        <div class="field"><label for="ph">Phone</label><input id="ph" type="tel" name="phone"></div>
      </div>
      <div class="f2">
        <div class="field"><label for="org">Organization</label><input id="org" type="text" name="organization"></div>
        <div class="field"><label for="ro">I am a</label><select id="ro" name="role">{ro}</select></div>
      </div>
      <div class="field"><label for="ty">Engagement of interest</label><select id="ty" name="engagement">{mo}</select></div>
      <div class="f2">
        <div class="field"><label for="loc">Project location</label><input id="loc" type="text" name="projectLocation"></div>
        <div class="field"><label for="amt">EB-5 loan amount</label><input id="amt" type="text" name="loanAmount" placeholder="$"></div>
      </div>
      <div class="field"><label for="ms">Message</label><textarea id="ms" name="message" rows="5" required></textarea></div>
      <button class="btn solid" type="submit">Send <span class="ar">&rarr;</span></button>
    </form>
  </div>
</div></div></section>
<div class="s2"></div>""" + footer())


def page_simple(title, heading, body, path):
    return (head(f"{title} | {SITE['name']} EB-5", body[:150], path)
        + header("")
        + f"""<section class="plain"><div class="container rv">
  <div class="rule-gold"></div>
  <h1>{e(heading)}</h1>
  <p class="muted" style="margin-top:24px;max-width:70ch">{e(body)}</p>
  <div class="btns"><a class="btn" href="/">Back to Home <span class="ar">&rarr;</span></a></div>
</div></section>""" + footer())


# ----------------------------------------------------------------- write

def write(path, content):
    full = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def checks():
    """Non-fatal content checks, printed at build time."""
    notes = []
    stated = int(re.sub(r"[^0-9]", "", SITE["stats"][0]["value"]))
    if abs(TRACK_TOTAL - stated) > 1:
        notes.append(f"representative loans (excluding current mandate) total {money(TRACK_TOTAL)}, "
                     f"stat tile says {SITE['stats'][0]['value']}")
    for a in ARTICLES:
        if a["category"] not in CAT_NAME:
            notes.append(f'article {a["slug"]} has unknown category {a["category"]}')
    return notes


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    pages = [("index.html", page_home(), "/", "1.0"),
             ("services/index.html", page_services(), "/services/", "0.9"),
             ("track-record/index.html", page_track(), "/track-record/", "0.8"),
             ("tea-map/index.html", page_tea(), "/tea-map/", "0.9"),
             ("info-center/index.html", page_info(), "/info-center/", "0.9"),
             ("about/index.html", page_about(), "/about/", "0.8"),
             ("contact/index.html", page_contact(), "/contact/", "0.7")]
    for a in ARTICLES:
        pages.append((f"info-center/{a['slug']}/index.html", page_article(a),
                      f"/info-center/{a['slug']}/", "0.6"))

    for path, content, _, _ in pages:
        write(path, content)

    write("404.html", page_simple("Page Not Found", "That page has moved.",
          "Use the navigation above, or head back to the homepage.", "/404.html"))
    write("thank-you/index.html", page_simple("Thank You", "Message received.",
          "Thank you for reaching out. Someone from Catalyst will respond shortly.", "/thank-you/"))
    write("privacy/index.html", page_simple("Privacy Policy", "Privacy Policy",
          "Placeholder. Replace with counsel-approved privacy language before launch.", "/privacy/"))
    write("terms/index.html", page_simple("Terms of Use", "Terms of Use",
          "Placeholder. Replace with counsel-approved terms before launch.", "/terms/"))

    urls = "".join(f"  <url><loc>{SITE['url']}{u}</loc><lastmod>{TODAY}</lastmod>"
                   f"<priority>{pr}</priority></url>\n" for _, _, u, pr in pages)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE['url']}/sitemap.xml\n")

    for f in os.listdir(STATIC):
        src = os.path.join(STATIC, f)
        if f.endswith((".css", ".js")):
            os.makedirs(os.path.join(DIST, "assets"), exist_ok=True)
            shutil.copy2(src, os.path.join(DIST, "assets", f))
        elif f == "img":
            shutil.copytree(src, os.path.join(DIST, "assets", "img"),
                            ignore=shutil.ignore_patterns("manifest.json"))
        elif os.path.isfile(src):
            shutil.copy2(src, os.path.join(DIST, f))

    for n in checks():
        print(f"  NOTE  {n}")
    n = sum(len(files) for _, _, files in os.walk(DIST))
    print(f"Built {len(pages)} pages ({len(ARTICLES)} info center articles), {n} files total -> dist/")


if __name__ == "__main__":
    main()
