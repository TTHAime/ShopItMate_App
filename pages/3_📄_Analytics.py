# ══════════════════════════════════════════════════════════════
# Shop IT Mate — Analytics Page
# วางไว้ใน pages/Analytics.py
# Dependencies: pip install pandas plotly psycopg2-binary
# ══════════════════════════════════════════════════════════════

import streamlit as st
import psycopg2, psycopg2.extras
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import calendar, os

# ── DB Connection ─────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host     = os.getenv('DB_HOST', 'localhost'),
        port     = os.getenv('DB_PORT', 5432),
        dbname   = os.getenv('DB_NAME', 'shopitmate'),
        user     = os.getenv('DB_USER', 'postgres'),
        password = os.getenv('DB_PASSWORD', ''),
    )

def q(sql, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def qdf(sql, params=None):
    rows = q(sql, params)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── Color maps ────────────────────────────────────────────────
CAT_COLOR = {
    'CLAIM':         '#C00000',
    'BROKEN':        '#E36C09',
    'RETURN':        '#7030A0',
    'SHIPPING':      '#2E75B6',
    'DOCUMENT':      '#70AD47',
    'FAQ':           '#70AD47',
    'CONTACT_ADMIN': '#D6B656',
    'UNCLEAR':       '#808080',
}

MONTH_TH = {
    1:'มกราคม', 2:'กุมภาพันธ์', 3:'มีนาคม',     4:'เมษายน',
    5:'พฤษภาคม', 6:'มิถุนายน',  7:'กรกฎาคม',   8:'สิงหาคม',
    9:'กันยายน', 10:'ตุลาคม',   11:'พฤศจิกายน', 12:'ธันวาคม',
}

# ══════════════════════════════════════════════════════════════
# PAGE START
# ══════════════════════════════════════════════════════════════
st.header('📈 Analytics & Insights')

# ── Filter Bar ────────────────────────────────────────────────
today = date.today()

# ดึงปีที่มีข้อมูลจาก DB
years_raw = qdf("""
    SELECT DISTINCT EXTRACT(YEAR FROM created_at AT TIME ZONE 'Asia/Bangkok')::INT AS yr
    FROM Cases ORDER BY yr DESC
""")
year_list = years_raw['yr'].tolist() if not years_raw.empty else [today.year]

# ── Row 1: ปี + เดือน (หลัก) ──────────────────────────────────
fc1, fc2, fc3 = st.columns([1.2, 1.8, 3])

with fc1:
    sel_year = st.selectbox('ปี', year_list, index=0)

with fc2:
    # เดือนที่เลือกได้ = เฉพาะเดือนที่ผ่านมาแล้ว (หรือเดือนปัจจุบัน) ในปีที่เลือก
    if sel_year < today.year:
        available_months = list(range(1, 13))          # ปีที่แล้ว → 12 เดือนครบ
    else:
        available_months = list(range(1, today.month + 1))  # ปีนี้ → ถึงเดือนปัจจุบัน

    month_options = ['ทั้งปี'] + [f"{MONTH_TH[m]} ({m:02d})" for m in available_months]
    sel_month_label = st.selectbox('เดือน', month_options, index=0)
    sel_month = None if sel_month_label == 'ทั้งปี' else int(sel_month_label.split('(')[1].replace(')', ''))

with fc3:
    st.write('')  # spacer

# ── Row 2: Custom range (optional) ────────────────────────────
use_custom = st.checkbox('กำหนดช่วงวันเองแทน (Custom Range)', value=False)

if use_custom:
    cr1, cr2 = st.columns(2)
    with cr1:
        date_from = st.date_input('ตั้งแต่', value=date(sel_year, sel_month or 1, 1),
                                   min_value=date(2020, 1, 1), max_value=today)
    with cr2:
        if sel_month:
            last_day_def = calendar.monthrange(sel_year, sel_month)[1]
            default_to   = date(sel_year, sel_month, last_day_def)
        else:
            default_to = date(sel_year, 12, 31) if sel_year < today.year else today
        date_to = st.date_input('ถึง', value=min(default_to, today),
                                 min_value=date(2020, 1, 1), max_value=today)
    # validate
    if date_from > date_to:
        st.error('วันที่เริ่มต้องไม่เกินวันที่สิ้นสุด')
        st.stop()
    range_label = f"{date_from} — {date_to}"
else:
    # คำนวณ date_from / date_to จาก ปี + เดือน ที่เลือก
    if sel_month:
        last_day = calendar.monthrange(sel_year, sel_month)[1]
        date_from = date(sel_year, sel_month, 1)
        # เดือนปัจจุบัน → ถึงวันนี้ ไม่ใช่วันสุดท้ายของเดือน
        if sel_year == today.year and sel_month == today.month:
            date_to = today
        else:
            date_to = date(sel_year, sel_month, last_day)
        range_label = f"{MONTH_TH[sel_month]} {sel_year}"
    else:
        date_from = date(sel_year, 1, 1)
        # ปีปัจจุบัน → ถึงวันนี้
        date_to = today if sel_year == today.year else date(sel_year, 12, 31)
        range_label = f"ปี {sel_year}"

# ── Derived values ────────────────────────────────────────────
date_to_excl = date_to + timedelta(days=1)
where_clause = f"created_at >= '{date_from}' AND created_at < '{date_to_excl}'"
sla_where    = f"c.created_at >= '{date_from}' AND c.created_at < '{date_to_excl}'"

span_days = (date_to - date_from).days
vol_group = 'hour' if span_days == 0 else ('month' if span_days > 60 else 'day')

# warn เดือนยังไม่สิ้นสุด
if not use_custom and sel_month and sel_year == today.year and sel_month == today.month:
    st.info(f"⚠️ {MONTH_TH[sel_month]} {sel_year} ยังไม่สิ้นสุด — แสดงข้อมูลถึงวันนี้ ({today})")

show_mom = st.checkbox('เปรียบเทียบกับช่วงก่อนหน้า', value=False)
st.caption(f"📅 กำลังดู: **{range_label}**")
st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 1 — KPI Summary
# ══════════════════════════════════════════════════════════════
st.subheader('📊 Summary')

kpi = qdf(f"""
    SELECT
        COUNT(*)                                                         AS total,
        COUNT(*) FILTER (WHERE status = 'OPEN')                         AS open,
        COUNT(*) FILTER (WHERE status = 'IN_PROGRESS')                  AS in_progress,
        COUNT(*) FILTER (WHERE status IN ('RESOLVED','CLOSED'))         AS closed,
        (SELECT COUNT(*) FROM Rag_Reply_Log
         WHERE {where_clause})                                           AS bot_handled,
        COUNT(*) FILTER (WHERE category NOT IN ('FAQ','UNCLEAR'))       AS admin_handled,
        ROUND(AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at))/60)
              FILTER (WHERE acknowledged_at IS NOT NULL), 0)            AS avg_ttr_min,
        ROUND(AVG(EXTRACT(EPOCH FROM (closed_at - created_at))/60)
              FILTER (WHERE closed_at IS NOT NULL), 0)                  AS avg_ttc_min
    FROM Cases
    WHERE {where_clause}
""")

if not kpi.empty:
    r = kpi.iloc[0]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric('📥 Total Cases',   int(r['total']         or 0))
    c2.metric('🔵 Open',          int(r['open']          or 0))
    c3.metric('🟡 In Progress',   int(r['in_progress']   or 0))
    c4.metric('✅ Closed',        int(r['closed']        or 0))
    c5.metric('🤖 Bot Handled',   int(r['bot_handled']   or 0))
    c6.metric('👤 Admin Handled', int(r['admin_handled'] or 0))
    st.caption(
        f"⏱ Avg TTR: **{int(r['avg_ttr_min'] or 0)} นาที** &nbsp;|&nbsp; "
        f"⏱ Avg TTC: **{int(r['avg_ttc_min'] or 0)} นาที**"
    )

st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 2 — Case Volume + Category Breakdown
# ══════════════════════════════════════════════════════════════
col_left, col_right = st.columns(2)

with col_left:
    st.subheader('📅 Case Volume')

    if vol_group == 'hour':
        vol_sql = f"""
            SELECT TO_CHAR(DATE_TRUNC('hour', created_at AT TIME ZONE 'Asia/Bangkok'), 'HH24:00') AS period,
                   COUNT(*) AS total
            FROM Cases WHERE {where_clause} GROUP BY period ORDER BY period"""
    elif vol_group == 'month':
        vol_sql = f"""
            SELECT TO_CHAR(DATE_TRUNC('month', created_at AT TIME ZONE 'Asia/Bangkok'), 'YYYY-MM') AS period,
                   COUNT(*) AS total
            FROM Cases WHERE {where_clause} GROUP BY period ORDER BY period"""
    else:
        vol_sql = f"""
            SELECT DATE(created_at AT TIME ZONE 'Asia/Bangkok') AS period,
                   COUNT(*) AS total
            FROM Cases WHERE {where_clause} GROUP BY period ORDER BY period"""

    df_vol = qdf(vol_sql)
    if not df_vol.empty:
        fig = px.bar(df_vol, x='period', y='total',
                     color_discrete_sequence=['#2E75B6'],
                     labels={'period': '', 'total': 'จำนวน Case'})
        fig.update_layout(margin=dict(t=10, b=10), height=280)
        st.plotly_chart(fig, width='stretch')
    else:
        st.info('ไม่มีข้อมูลในช่วงเวลานี้')

with col_right:
    st.subheader('🏷 Category Breakdown')
    df_cat = qdf(f"""
        SELECT category, COUNT(*) AS cnt
        FROM Cases WHERE {where_clause}
        GROUP BY category ORDER BY cnt DESC
    """)
    if not df_cat.empty:
        fig = px.pie(df_cat, names='category', values='cnt',
                     color='category', color_discrete_map=CAT_COLOR, hole=0.45)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=10, b=10), height=280, showlegend=False)
        st.plotly_chart(fig, width='stretch')
    else:
        st.info('ไม่มีข้อมูล')

st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 3 — SLA Breach Rate
# ══════════════════════════════════════════════════════════════
st.subheader('🚨 SLA Breach Rate')

df_sla = qdf(f"""
    SELECT
        c.category,
        COUNT(*)                                                         AS total,
        COUNT(*) FILTER (WHERE cs.ttr_breached)                         AS ttr_breach,
        COUNT(*) FILTER (WHERE cs.ttc_breached)                         AS ttc_breach,
        ROUND(100.0 * COUNT(*) FILTER (WHERE cs.ttr_breached)
              / NULLIF(COUNT(*),0), 1)                                  AS ttr_pct,
        ROUND(100.0 * COUNT(*) FILTER (WHERE cs.ttc_breached)
              / NULLIF(COUNT(*),0), 1)                                  AS ttc_pct,
        ROUND(AVG(EXTRACT(EPOCH FROM (c.acknowledged_at - c.created_at))/60)
              FILTER (WHERE c.acknowledged_at IS NOT NULL), 0)          AS avg_ttr_min
    FROM Cases c
    JOIN CASE_SLA cs ON c.case_id = cs.case_id
    WHERE {sla_where}
    GROUP BY c.category ORDER BY ttr_pct DESC NULLS LAST
""")

if not df_sla.empty:
    scol1, scol2 = st.columns(2)
    with scol1:
        fig_ttr = px.bar(df_sla.dropna(subset=['ttr_pct']),
                         x='category', y='ttr_pct', color='ttr_pct',
                         color_continuous_scale=['#70AD47','#D6B656','#C00000'],
                         range_color=[0,100], title='TTR Breach % ต่อ Category',
                         labels={'category':'','ttr_pct':'TTR Breach %'})
        fig_ttr.update_layout(margin=dict(t=40,b=10), height=300, coloraxis_showscale=False)
        fig_ttr.add_hline(y=20, line_dash='dash', line_color='orange', annotation_text='20%')
        st.plotly_chart(fig_ttr, width='stretch')

    with scol2:
        fig_ttc = px.bar(df_sla.dropna(subset=['ttc_pct']),
                         x='category', y='ttc_pct', color='ttc_pct',
                         color_continuous_scale=['#70AD47','#D6B656','#C00000'],
                         range_color=[0,100], title='TTC Breach % ต่อ Category',
                         labels={'category':'','ttc_pct':'TTC Breach %'})
        fig_ttc.update_layout(margin=dict(t=40,b=10), height=300, coloraxis_showscale=False)
        fig_ttc.add_hline(y=20, line_dash='dash', line_color='orange', annotation_text='20%')
        st.plotly_chart(fig_ttc, width='stretch')

    st.dataframe(
        df_sla[['category','total','ttr_breach','ttr_pct','ttc_breach','ttc_pct','avg_ttr_min']]
        .rename(columns={
            'category':'Category','total':'Total Cases',
            'ttr_breach':'TTR Breach','ttr_pct':'TTR Breach %',
            'ttc_breach':'TTC Breach','ttc_pct':'TTC Breach %',
            'avg_ttr_min':'Avg TTR (นาที)',
        }),
        width='stretch', hide_index=True,
    )

st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 4 — Bot vs Admin + Response Time Trend
# ══════════════════════════════════════════════════════════════
col_a, col_b = st.columns(2)

with col_a:
    st.subheader('🤖 Bot / Admin Workload')
    df_work = qdf(f"""
        SELECT handled_by, cnt FROM (
            SELECT 'Bot (FAQ/Product)' AS handled_by, COUNT(*) AS cnt
            FROM Rag_Reply_Log WHERE {where_clause}
            UNION ALL
            SELECT 'Admin' AS handled_by, COUNT(*) AS cnt
            FROM Cases WHERE {where_clause} AND category NOT IN ('FAQ','UNCLEAR')
        ) t
    """)
    if not df_work.empty:
        fig_work = px.pie(df_work, names='handled_by', values='cnt',
                          color='handled_by',
                          color_discrete_map={'Bot (FAQ/Product)':'#70AD47','Admin':'#2E75B6'},
                          hole=0.5)
        fig_work.update_traces(textinfo='percent+label')
        fig_work.update_layout(margin=dict(t=10,b=10), height=280, showlegend=False)
        st.plotly_chart(fig_work, width='stretch')
        total_w = df_work['cnt'].sum()
        for _, row in df_work.iterrows():
            pct = round(100 * row['cnt'] / total_w, 1) if total_w > 0 else 0
            st.caption(f"{row['handled_by']}: **{int(row['cnt'])} ครั้ง ({pct}%)**")

with col_b:
    st.subheader('⏱ Response Time Trend (Avg TTR)')
    if vol_group == 'hour':
        rt_sql = f"""
            SELECT TO_CHAR(DATE_TRUNC('hour', created_at AT TIME ZONE 'Asia/Bangkok'),'HH24:00') AS period,
                   ROUND(AVG(EXTRACT(EPOCH FROM (acknowledged_at-created_at))/60)
                         FILTER (WHERE acknowledged_at IS NOT NULL),0) AS avg_ttr
            FROM Cases WHERE {where_clause} GROUP BY period ORDER BY period"""
    else:
        rt_sql = f"""
            SELECT DATE(created_at AT TIME ZONE 'Asia/Bangkok') AS period,
                   ROUND(AVG(EXTRACT(EPOCH FROM (acknowledged_at-created_at))/60)
                         FILTER (WHERE acknowledged_at IS NOT NULL),0) AS avg_ttr
            FROM Cases WHERE {where_clause} GROUP BY period ORDER BY period"""

    df_rt = qdf(rt_sql)
    if not df_rt.empty and df_rt['avg_ttr'].notna().any():
        fig_rt = px.line(df_rt.dropna(subset=['avg_ttr']), x='period', y='avg_ttr',
                         markers=True, color_discrete_sequence=['#2E75B6'],
                         labels={'period':'','avg_ttr':'นาที'})
        fig_rt.update_layout(margin=dict(t=10,b=10), height=280)
        st.plotly_chart(fig_rt, width='stretch')
    else:
        st.info('ยังไม่มีข้อมูล TTR')

st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 5 — เปรียบเทียบช่วงก่อนหน้า (MoM)
# ══════════════════════════════════════════════════════════════
if show_mom:
    st.subheader('📆 เปรียบเทียบกับช่วงก่อนหน้า')

    span       = date_to_excl - date_from
    prev_from  = date_from - span
    prev_to_ex = date_from  # exclusive

    prev_where     = f"created_at >= '{prev_from}' AND created_at < '{prev_to_ex}'"
    prev_sla_where = f"c.created_at >= '{prev_from}' AND c.created_at < '{prev_to_ex}'"

    def get_kpi(w, sw):
        return qdf(f"""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE cs.ttr_breached) AS ttr_breach,
                   COUNT(*) FILTER (WHERE cs.ttc_breached) AS ttc_breach,
                   ROUND(AVG(EXTRACT(EPOCH FROM (c.acknowledged_at-c.created_at))/60)
                         FILTER (WHERE c.acknowledged_at IS NOT NULL),0) AS avg_ttr,
                   ROUND(AVG(EXTRACT(EPOCH FROM (c.closed_at-c.created_at))/60)
                         FILTER (WHERE c.closed_at IS NOT NULL),0) AS avg_ttc
            FROM Cases c LEFT JOIN CASE_SLA cs ON c.case_id=cs.case_id
            WHERE {sw}
        """)

    kpi_prev = get_kpi(prev_where, prev_sla_where)
    kpi_curr = get_kpi(where_clause, sla_where)

    if not kpi_prev.empty and not kpi_curr.empty:
        p, c = kpi_prev.iloc[0], kpi_curr.iloc[0]
        st.caption(f"**{range_label}** vs **{prev_from} — {prev_to_ex - timedelta(days=1)}**")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric('Total Cases',   int(c['total'] or 0),
                  delta=int((c['total'] or 0)-(p['total'] or 0)))
        m2.metric('TTR Breach',    int(c['ttr_breach'] or 0),
                  delta=int((c['ttr_breach'] or 0)-(p['ttr_breach'] or 0)), delta_color='inverse')
        m3.metric('TTC Breach',    int(c['ttc_breach'] or 0),
                  delta=int((c['ttc_breach'] or 0)-(p['ttc_breach'] or 0)), delta_color='inverse')
        m4.metric('Avg TTR (นาที)', int(c['avg_ttr'] or 0),
                  delta=int((c['avg_ttr'] or 0)-(p['avg_ttr'] or 0)), delta_color='inverse')
        m5.metric('Avg TTC (นาที)', int(c['avg_ttc'] or 0),
                  delta=int((c['avg_ttc'] or 0)-(p['avg_ttc'] or 0)), delta_color='inverse')

        df_cmp = pd.DataFrame({
            'ช่วงเวลา':   [f'ก่อนหน้า',       f'ปัจจุบัน'],
            'Total':      [int(p['total'] or 0),      int(c['total'] or 0)],
            'TTR Breach': [int(p['ttr_breach'] or 0), int(c['ttr_breach'] or 0)],
            'TTC Breach': [int(p['ttc_breach'] or 0), int(c['ttc_breach'] or 0)],
        })
        df_melt = df_cmp.melt(id_vars='ช่วงเวลา', var_name='metric', value_name='value')
        fig_cmp = px.bar(df_melt, x='metric', y='value', color='ช่วงเวลา', barmode='group',
                         color_discrete_sequence=['#808080','#2E75B6'],
                         labels={'metric':'','value':'จำนวน'})
        fig_cmp.update_layout(margin=dict(t=10,b=10), height=300)
        st.plotly_chart(fig_cmp, width='stretch')

    st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 6 — Off-Hours Pattern
# ══════════════════════════════════════════════════════════════
st.subheader('🌙 Off-Hours Contact Pattern')

df_oh = qdf(f"""
    SELECT EXTRACT(HOUR FROM notified_at AT TIME ZONE 'Asia/Bangkok')::INT AS hour,
           COUNT(*) AS contacts
    FROM Off_Hours_Notified
    WHERE notified_date >= '{date_from}' AND notified_date < '{date_to_excl}'
    GROUP BY hour ORDER BY hour
""")

if not df_oh.empty:
    all_hours = pd.DataFrame({'hour': range(0, 24)})
    df_oh = all_hours.merge(df_oh, on='hour', how='left').fillna(0)
    df_oh['contacts'] = df_oh['contacts'].astype(int)
    df_oh['label'] = df_oh['hour'].apply(lambda h: f"{h:02d}:00")
    fig_oh = px.bar(df_oh, x='label', y='contacts', color='contacts',
                    color_continuous_scale=['#1F4E79','#2E75B6','#D6B656','#C00000'],
                    labels={'label':'ชั่วโมง','contacts':'ครั้ง'})
    fig_oh.update_layout(margin=dict(t=10,b=10), height=250, coloraxis_showscale=False)
    st.plotly_chart(fig_oh, width='stretch')
    st.caption(f'ช่วงเวลา: {range_label}')
else:
    st.info('ไม่มีข้อมูล Off-Hours ในช่วงเวลานี้')