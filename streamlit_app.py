"""Advisor Performance Pulse - Burns Chevrolet of Gaffney.

Reads the Advisor Pulse workbook's main tab live and renders the advisor
performance snapshot: CSI, check-in media %, sales vs target, pay tracker,
total WIP and its dollar value, and WIP.

Deliberately excluded: the Dylan Pay / Jessica Pay tabs and the Raw WIP tab.
The month-end pay tracker summary (Current MTD vs Tracking MTD per advisor)
IS shown, sourced from the main tab only - never from the pay tabs.
WIP category tabs (Needs Attention, Aged RO 30 Days, Ready to be Closed,
Customer-VSC Approval, Parts Here No Vehicle) ARE included.
This app is READ ONLY - all editing stays in the Google Sheet.
"""

from datetime import date

import pandas as pd
import streamlit as st

SHEET_ID = "1IN_4UPkwGFv_wKl2gMF3yPSm8DDvXgFJnqGrf5fR_KY"
GID_MAIN = "0"
WIP_TABS = {
    "Needs Attention": "1050797231",
    "Aged RO 30 Days": "380213487",
    "Ready to be Closed": "639085347",
    "Customer-VSC Approval": "96286145",
    "Parts Here No Vehicle": "971355840",
}

CHEVY_BLUE = "#0B74C5"
DEEP_NAVY = "#0A2A7B"
PEACH = "#E2572B"
PEACH_DARK = "#C9471F"
GOLD = "#C89B4B"

st.set_page_config(page_title="Advisor Performance Pulse", page_icon="💼", layout="centered")

st.markdown(
    f"""
<style>
.stApp {{
    background: linear-gradient(180deg, #F4F8FD 0%, #FFF6EF 100%);
}}
.hero {{
    background: linear-gradient(135deg, {DEEP_NAVY} 0%, {CHEVY_BLUE} 100%);
    border-radius: 18px;
    padding: 1.8rem 1.4rem 1.5rem;
    text-align: center;
    color: white;
    border-bottom: 6px solid {PEACH};
    box-shadow: 0 8px 24px rgba(10, 42, 123, 0.28);
    margin-bottom: 1.2rem;
}}
.hero h1 {{
    color: white !important;
    font-weight: 800;
    margin: 0.2rem 0 0.4rem;
    font-size: 1.6rem;
}}
.hero p {{
    color: #DCE9F7;
    margin: 0;
    font-size: 0.95rem;
}}
.hero .gold-rule {{
    width: 64px; height: 3px; background: {GOLD};
    border-radius: 2px; margin: 0.8rem auto 0;
}}
.kpi {{
    background: #FFFFFF;
    border-radius: 14px;
    border-left: 5px solid {PEACH};
    box-shadow: 0 2px 10px rgba(10, 42, 123, 0.08);
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.6rem;
}}
.kpi .k-label {{
    font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: #6B7A90; font-weight: 700;
}}
.kpi .k-value {{
    font-size: 1.35rem; font-weight: 800; color: {DEEP_NAVY};
    font-variant-numeric: tabular-nums;
}}
.kpi .k-sub {{
    font-size: 0.8rem; color: #6B7A90;
}}
table.ap {{width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums;}}
table.ap th {{
    background: {DEEP_NAVY}; color: white; font-size: 0.72rem;
    letter-spacing: 0.06em; text-transform: uppercase;
    padding: 0.55rem 0.6rem; text-align: left;
}}
table.ap th.num, table.ap td.num {{text-align: right;}}
table.ap td.perf-section {{
    background: {DEEP_NAVY}; color: white; font-weight: 800; font-size: 0.78rem;
    letter-spacing: 0.08em; text-transform: uppercase; text-align: center;
    padding: 0.45rem 0.6rem;
}}
table.ap td {{
    padding: 0.5rem 0.6rem; border-top: 1px solid #E4EAF3;
    font-size: 0.88rem; background: #FFFFFF; color: #1c2733;
}}
.good {{color: #1B7F3B; font-weight: 700;}}
.bad {{color: #C0392B; font-weight: 700;}}
.section-title {{
    color: {DEEP_NAVY}; font-weight: 800; font-size: 1.1rem;
    margin: 1.4rem 0 0.6rem;
    border-bottom: 3px solid {PEACH}; padding-bottom: 0.3rem;
}}
.foot {{
    text-align: center; color: #9AA5B5; font-size: 0.78rem; margin-top: 1.6rem;
}}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def load(gid):
    """Load one workbook tab as a dataframe of strings (no header)."""
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    return pd.read_csv(url, dtype=str, header=None).fillna("")


def cell(df, r, c):
    try:
        return str(df.iat[r, c]).strip()
    except Exception:
        return ""


def parse_main(df):
    """Parse the Advisor Pulse main tab: WIP, CSI strip, pay tracker,
    Advisor Performance."""
    m = {"wip": [], "perf": [], "pay": [], "jess_csi": cell(df, 3, 4),
         "dylan_csi": cell(df, 3, 5), "dealer_csi": cell(df, 5, 5)}
    for r in range(3, 10):
        label = cell(df, r, 0)
        vals = [cell(df, r, c) for c in range(1, 4)]
        if label and any(vals):
            m["wip"].append(
                {"label": label, "dylan": vals[0],
                 "jessica": vals[1], "total": vals[2]}
            )
    # Advisor Performance block: tolerant of reformatting (extra blank rows,
    # section sub-headers). A metric row has a label AND at least one value.
    start = None
    for r in range(df.shape[0]):
        if cell(df, r, 0).strip().lower() == "advisor performance":
            start = r + 2
            break
    if start:
        for r in range(start, min(start + 60, df.shape[0])):
            label = cell(df, r, 0)
            if "OLDEST OPEN" in label.upper():
                break
            vals = [cell(df, r, c) for c in range(1, 7)]
            if not label and any(vals):
                # Section divider row, e.g. "Main Shop Performance".
                section = next((v for v in vals if v), "")
                m["perf"].append({"section": section})
                continue
            if not label or not any(vals):
                continue
            m["perf"].append(
                {"label": label, "d_mtd": vals[0], "d_tgt": vals[1],
                 "d_pct": vals[2], "j_mtd": vals[3],
                 "j_tgt": vals[4], "j_pct": vals[5]}
            )
    # Month-end pay tracker: find the marker, then read advisor rows below it.
    pay_start = None
    for r in range(df.shape[0]):
        if "MONTH-END PAY TRACKER" in cell(df, r, 6).upper():
            pay_start = r + 1
            break
    if pay_start:
        for r in range(pay_start, min(pay_start + 8, df.shape[0])):
            advisor = cell(df, r, 6)
            vals = [cell(df, r, c) for c in (7, 8, 9)]
            if not advisor or advisor.lower() == "advisor" or not any(vals):
                continue
            m["pay"].append({"advisor": advisor, "current": vals[0],
                            "tracking": vals[1], "variance": vals[2]})
    # Total WIP / open ROs and potential sales: find the marker cell, then
    # take the first non-empty value below it in the same column.
    def below_marker(marker):
        for r in range(df.shape[0]):
            for c in range(df.shape[1]):
                if marker in cell(df, r, c).upper():
                    for r2 in range(r + 1, min(r + 4, df.shape[0])):
                        v = cell(df, r2, c)
                        if v:
                            return v
                    return ""
        return ""
    m["total_wip"] = below_marker("TOTAL WIP")
    m["potential_sales"] = below_marker("POTENTIAL SALES")
    return m


def pct_float(s):
    try:
        return float(str(s).replace("%", "").strip())
    except Exception:
        return None


def pct_class(s):
    v = pct_float(s)
    if v is None:
        return ""
    return "good" if v >= 100 else "bad"


def kpi_card(label, value, sub=""):
    st.markdown(
        f'<div class="kpi"><div class="k-label">{label}</div>'
        f'<div class="k-value">{value}</div>'
        + (f'<div class="k-sub">{sub}</div>' if sub else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def perf_table(perf):
    rows = ""
    for p in perf:
        if "section" in p:
            rows += (
                f"<tr><td colspan='7' class='perf-section'>"
                f"{p['section']}</td></tr>"
            )
            continue
        rows += (
            f"<tr><td>{p['label']}</td><td class='num'>{p['d_mtd']}</td>"
            f"<td class='num'>{p['d_tgt']}</td>"
            f"<td class='num {pct_class(p['d_pct'])}'>{p['d_pct']}</td>"
            f"<td class='num'>{p['j_mtd']}</td><td class='num'>{p['j_tgt']}</td>"
            f"<td class='num {pct_class(p['j_pct'])}'>{p['j_pct']}</td></tr>"
        )
    st.markdown(
        "<table class='ap'><tr><th>Metric</th><th class='num'>Dylan MTD</th>"
        "<th class='num'>Target</th><th class='num'>% to Tgt</th>"
        "<th class='num'>Jessica MTD</th><th class='num'>Target</th>"
        "<th class='num'>% to Tgt</th></tr>" + rows + "</table>",
        unsafe_allow_html=True,
    )


def wip_table(wip):
    rows = "".join(
        f"<tr><td>{w['label']}</td><td class='num'>{w['dylan']}</td>"
        f"<td class='num'>{w['jessica']}</td><td class='num'>{w['total']}</td></tr>"
        for w in wip
    )
    st.markdown(
        "<table class='ap'><tr><th>WIP</th><th class='num'>Dylan</th>"
        "<th class='num'>Jessica</th><th class='num'>Total</th></tr>"
        f"{rows}</table>",
        unsafe_allow_html=True,
    )


def variance_class(s):
    try:
        v = float(str(s).replace("$", "").replace(",", "").strip())
    except Exception:
        return ""
    return "good" if v >= 0 else "bad"


def pay_table(pay):
    rows = "".join(
        f"<tr><td>{p['advisor']}</td><td class='num'>{p['current']}</td>"
        f"<td class='num'>{p['tracking']}</td>"
        f"<td class='num {variance_class(p['variance'])}'>{p['variance']}</td></tr>"
        for p in pay
    )
    st.markdown(
        "<table class='ap'><tr><th>Advisor</th><th class='num'>Current MTD</th>"
        "<th class='num'>Tracking MTD</th><th class='num'>Variance</th></tr>"
        f"{rows}</table>",
        unsafe_allow_html=True,
    )


def parse_wip_detail(df):
    """Parse a WIP category tab: RO#, Age, Total, Flag, Vehicle, Customer."""
    rows = []
    for r in range(1, df.shape[0]):
        ro = cell(df, r, 0)
        if not ro:
            break
        total = cell(df, r, 2)
        try:
            total = f"${float(total):,.2f}"
        except Exception:
            pass
        rows.append(
            {"ro": ro, "age": cell(df, r, 1), "total": total,
             "flag": cell(df, r, 3), "vehicle": cell(df, r, 4),
             "customer": cell(df, r, 5)}
        )
    return rows


def wip_detail_table(rows):
    body = "".join(
        f"<tr><td class='num'>{x['ro']}</td><td class='num'>{x['age']}</td>"
        f"<td class='num'>{x['total']}</td><td>{x['flag']}</td>"
        f"<td>{x['vehicle']}</td><td>{x['customer']}</td></tr>"
        for x in rows
    )
    st.markdown(
        "<table class='ap'><tr><th class='num'>RO#</th><th class='num'>Age</th>"
        "<th class='num'>Total</th><th>Flag</th><th>Vehicle</th><th>Customer</th></tr>"
        f"{body}</table>",
        unsafe_allow_html=True,
    )


try:
    main = parse_main(load(GID_MAIN))
except Exception:
    st.error(
        "Can't reach the Advisor Pulse workbook. It needs **Anyone with the link** "
        "sharing turned on (Share → General access) for this app to read it."
    )
    st.stop()

month_label = date.today().strftime("%B %Y")

st.markdown(
    f"""
<div class="hero">
  <h1>💼 Advisor Performance Pulse</h1>
  <p>Burns Chevrolet of Gaffney &middot; {month_label}</p>
  <div class="gold-rule"></div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">CSI MTD</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Jessica CSI", main["jess_csi"])
with c2:
    kpi_card("Dylan CSI", main["dylan_csi"])
with c3:
    kpi_card("Dealer CSI", main["dealer_csi"])

media = next((p for p in main["perf"] if "Media" in p["label"]), None)
if media:
    st.markdown('<div class="section-title">Check-in Media %</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        kpi_card("Dylan", f"{media['d_mtd']}",
                 f"Target {media['d_tgt']} · {media['d_pct']} to target")
    with c2:
        kpi_card("Jessica", f"{media['j_mtd']}",
                 f"Target {media['j_tgt']} · {media['j_pct']} to target")

st.markdown('<div class="section-title">Advisor performance vs target</div>',
            unsafe_allow_html=True)
perf_table(main["perf"])

if main["pay"]:
    st.markdown('<div class="section-title">Month-end pay tracker</div>',
                unsafe_allow_html=True)
    pay_table(main["pay"])

st.markdown('<div class="section-title">WIP snapshot</div>', unsafe_allow_html=True)
if main["total_wip"] or main["potential_sales"]:
    c1, c2 = st.columns(2)
    with c1:
        kpi_card("Total WIP / Open ROs", main["total_wip"])
    with c2:
        kpi_card("Potential Sales", main["potential_sales"])
wip_table(main["wip"])

st.markdown('<div class="section-title">WIP detail</div>', unsafe_allow_html=True)
wip_choice = st.selectbox("Category", list(WIP_TABS.keys()))
try:
    detail = parse_wip_detail(load(WIP_TABS[wip_choice]))
except Exception:
    detail = []
st.caption(f"{len(detail)} ROs in {wip_choice}.")
if detail:
    wip_detail_table(detail)

st.markdown(
    '<div class="foot">Reads live from the Advisor Pulse workbook · '
    "refreshes every 5 minutes · read-only</div>",
    unsafe_allow_html=True,
)
