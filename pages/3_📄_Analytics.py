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
from datetime import datetime, timezone, timedelta
import os

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

STATUS_COLOR = {
    'OPEN':        '#2E75B6',
    'IN_PROGRESS': '#D6B656',
    'RESOLVED':    '#70AD47',
    'CLOSED':      '#595959',
}

# ══════════════════════════════════════════════════════════════
# PAGE START
# ══════════════════════════════════════════════════════════════
st.header('📈 Analytics & Insights')

# ── Timeframe selector ────────────────────────────────────────
tf_col, _, _ = st.columns([2, 3, 3])
with tf_col:
    timeframe = st.selectbox(
        'ช่วงเวลา',
        ['วันนี้', '7 วันล่าสุด', '30 วันล่าสุด', 'Month-over-Month'],
        index=1,
    )

TF_MAP = {
    'วันนี้':             ("DATE(created_at AT TIME ZONE 'Asia/Bangkok') = CURRENT_DATE", 'วันนี้'),
    '7 วันล่าสุด':       ("created_at >= NOW() - INTERVAL '7 days'",  '7 วัน'),
    '30 วันล่าสุด':      ("created_at >= NOW() - INTERVAL '30 days'", '30 วัน'),
    'Month-over-Month':  ("created_at >= NOW() - INTERVAL '60 days'", '60 วัน'),
}
where_clause, tf_label = TF_MAP[timeframe]

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
        (SELECT COUNT(*) FROM Rag_Reply_Log r2
         WHERE r2.created_at >= NOW() - INTERVAL '30 days')             AS bot_handled,
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
    c1.metric('📥 Total Cases',   int(r['total']        or 0))
    c2.metric('🔵 Open',          int(r['open']         or 0))
    c3.metric('🟡 In Progress',   int(r['in_progress']  or 0))
    c4.metric('✅ Closed',        int(r['closed']       or 0))
    c5.metric('🤖 Bot Handled',   int(r['bot_handled']  or 0))
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

    if timeframe == 'Month-over-Month':
        df_vol = qdf("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', created_at AT TIME ZONE 'Asia/Bangkok'), 'YYYY-MM') AS period,
                COUNT(*) AS total
            FROM Cases
            WHERE created_at >= NOW() - INTERVAL '60 days'
            GROUP BY period ORDER BY period
        """)
    elif timeframe == 'วันนี้':
        df_vol = qdf("""
            SELECT
                TO_CHAR(DATE_TRUNC('hour', created_at AT TIME ZONE 'Asia/Bangkok'), 'HH24:00') AS period,
                COUNT(*) AS total
            FROM Cases
            WHERE DATE(created_at AT TIME ZONE 'Asia/Bangkok') = CURRENT_DATE
            GROUP BY period ORDER BY period
        """)
    else:
        df_vol = qdf(f"""
            SELECT
                DATE(created_at AT TIME ZONE 'Asia/Bangkok') AS period,
                COUNT(*) AS total
            FROM Cases
            WHERE {where_clause}
            GROUP BY period ORDER BY period
        """)

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
        FROM Cases
        WHERE {where_clause}
        GROUP BY category ORDER BY cnt DESC
    """)

    if not df_cat.empty:
        fig = px.pie(df_cat, names='category', values='cnt',
                     color='category',
                     color_discrete_map=CAT_COLOR,
                     hole=0.45)
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

# แก้ where_clause ให้มี alias c. สำหรับ query ที่ JOIN
if 'DATE(' in where_clause:
    sla_where = where_clause.replace('created_at', 'c.created_at')
else:
    sla_where = where_clause.replace('created_at', 'c.created_at')

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
    GROUP BY c.category
    ORDER BY ttr_pct DESC NULLS LAST
""")

if not df_sla.empty:
    scol1, scol2 = st.columns(2)

    with scol1:
        fig_ttr = px.bar(
            df_sla.dropna(subset=['ttr_pct']),
            x='category', y='ttr_pct',
            color='ttr_pct',
            color_continuous_scale=['#70AD47', '#D6B656', '#C00000'],
            range_color=[0, 100],
            labels={'category': '', 'ttr_pct': 'TTR Breach %'},
            title='TTR Breach % ต่อ Category'
        )
        fig_ttr.update_layout(margin=dict(t=40, b=10), height=300, coloraxis_showscale=False)
        fig_ttr.add_hline(y=20, line_dash='dash', line_color='orange',
                          annotation_text='20% threshold')
        st.plotly_chart(fig_ttr, width='stretch')

    with scol2:
        fig_ttc = px.bar(
            df_sla.dropna(subset=['ttc_pct']),
            x='category', y='ttc_pct',
            color='ttc_pct',
            color_continuous_scale=['#70AD47', '#D6B656', '#C00000'],
            range_color=[0, 100],
            labels={'category': '', 'ttc_pct': 'TTC Breach %'},
            title='TTC Breach % ต่อ Category'
        )
        fig_ttc.update_layout(margin=dict(t=40, b=10), height=300, coloraxis_showscale=False)
        fig_ttc.add_hline(y=20, line_dash='dash', line_color='orange',
                          annotation_text='20% threshold')
        st.plotly_chart(fig_ttc, width='stretch')

    st.dataframe(
        df_sla[['category', 'total', 'ttr_breach', 'ttr_pct',
                'ttc_breach', 'ttc_pct', 'avg_ttr_min']].rename(columns={
            'category':    'Category',
            'total':       'Total Cases',
            'ttr_breach':  'TTR Breach',
            'ttr_pct':     'TTR Breach %',
            'ttc_breach':  'TTC Breach',
            'ttc_pct':     'TTC Breach %',
            'avg_ttr_min': 'Avg TTR (นาที)',
        }),
        width='stretch',
        hide_index=True,
    )

st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 4 — Bot vs Admin Workload + Response Time
# ══════════════════════════════════════════════════════════════
col_a, col_b = st.columns(2)

with col_a:
    st.subheader('🤖 Bot vs Admin Workload')

    # Bot = ตอบจาก Rag_Reply_Log (FAQ + PRODUCT), Admin = case จริงที่ต้องดูแล
    df_work = qdf(f"""
        SELECT handled_by, cnt FROM (
            SELECT 'Bot (FAQ/Product)' AS handled_by,
                   COUNT(*) AS cnt
            FROM Rag_Reply_Log
            WHERE {where_clause.replace('created_at', 'created_at')}
            UNION ALL
            SELECT 'Admin' AS handled_by,
                   COUNT(*) AS cnt
            FROM Cases
            WHERE {where_clause}
            AND category NOT IN ('FAQ','UNCLEAR')
        ) t
    """)

    if not df_work.empty:
        fig_work = px.pie(df_work, names='handled_by', values='cnt',
                          color='handled_by',
                          color_discrete_map={
                              'Bot (FAQ/Product)': '#70AD47',
                              'Admin':             '#2E75B6',
                          },
                          hole=0.5)
        fig_work.update_traces(textinfo='percent+label')
        fig_work.update_layout(margin=dict(t=10, b=10), height=280, showlegend=False)
        st.plotly_chart(fig_work, width='stretch')

        total_w = df_work['cnt'].sum()
        for _, row in df_work.iterrows():
            pct = round(100 * row['cnt'] / total_w, 1) if total_w > 0 else 0
            st.caption(f"{row['handled_by']}: **{int(row['cnt'])} ครั้ง ({pct}%)**")

with col_b:
    st.subheader('⏱ Response Time Trend (Avg TTR)')

    if timeframe == 'วันนี้':
        df_rt = qdf("""
            SELECT
                TO_CHAR(DATE_TRUNC('hour', created_at AT TIME ZONE 'Asia/Bangkok'),
                        'HH24:00') AS period,
                ROUND(AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at))/60)
                      FILTER (WHERE acknowledged_at IS NOT NULL), 0) AS avg_ttr
            FROM Cases
            WHERE DATE(created_at AT TIME ZONE 'Asia/Bangkok') = CURRENT_DATE
            GROUP BY period ORDER BY period
        """)
    else:
        df_rt = qdf(f"""
            SELECT
                DATE(created_at AT TIME ZONE 'Asia/Bangkok') AS period,
                ROUND(AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at))/60)
                      FILTER (WHERE acknowledged_at IS NOT NULL), 0) AS avg_ttr
            FROM Cases
            WHERE {where_clause}
            GROUP BY period ORDER BY period
        """)

    if not df_rt.empty and df_rt['avg_ttr'].notna().any():
        fig_rt = px.line(df_rt.dropna(subset=['avg_ttr']),
                         x='period', y='avg_ttr',
                         markers=True,
                         color_discrete_sequence=['#2E75B6'],
                         labels={'period': '', 'avg_ttr': 'นาที'})
        fig_rt.update_layout(margin=dict(t=10, b=10), height=280)
        st.plotly_chart(fig_rt, width='stretch')
    else:
        st.info('ยังไม่มีข้อมูล TTR (ยังไม่มี case ที่ acknowledge)')

st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 5 — Month-over-Month (เฉพาะ MoM mode)
# ══════════════════════════════════════════════════════════════
if timeframe == 'Month-over-Month':
    st.subheader('📆 Month-over-Month Comparison')

    df_mom = qdf("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', created_at AT TIME ZONE 'Asia/Bangkok'),
                    'YYYY-MM') AS month,
            COUNT(*)                                                     AS total,
            COUNT(*) FILTER (WHERE cs.ttr_breached)                     AS ttr_breach,
            COUNT(*) FILTER (WHERE cs.ttc_breached)                     AS ttc_breach,
            ROUND(AVG(EXTRACT(EPOCH FROM (c.acknowledged_at - c.created_at))/60)
                  FILTER (WHERE c.acknowledged_at IS NOT NULL), 0)      AS avg_ttr,
            ROUND(AVG(EXTRACT(EPOCH FROM (c.closed_at - c.created_at))/60)
                  FILTER (WHERE c.closed_at IS NOT NULL), 0)            AS avg_ttc
        FROM Cases c
        LEFT JOIN CASE_SLA cs ON c.case_id = cs.case_id
        WHERE c.created_at >= NOW() - INTERVAL '60 days'
        GROUP BY month ORDER BY month
    """)

    if not df_mom.empty and len(df_mom) >= 2:
        prev = df_mom.iloc[0]
        curr = df_mom.iloc[1]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Total Cases',
                  int(curr['total'] or 0),
                  delta=f"{int((curr['total'] or 0) - (prev['total'] or 0))} vs เดือนก่อน")
        m2.metric('TTR Breach',
                  int(curr['ttr_breach'] or 0),
                  delta=f"{int((curr['ttr_breach'] or 0) - (prev['ttr_breach'] or 0))} vs เดือนก่อน")
        m3.metric('Avg TTR (นาที)',
                  int(curr['avg_ttr'] or 0),
                  delta=f"{int((curr['avg_ttr'] or 0) - (prev['avg_ttr'] or 0))} นาที")
        m4.metric('Avg TTC (นาที)',
                  int(curr['avg_ttc'] or 0),
                  delta=f"{int((curr['avg_ttc'] or 0) - (prev['avg_ttc'] or 0))} นาที")

        df_mom_melt = df_mom.melt(id_vars='month',
                                  value_vars=['total', 'ttr_breach', 'ttc_breach'],
                                  var_name='metric', value_name='value')
        fig_mom = px.bar(df_mom_melt, x='month', y='value',
                         color='metric', barmode='group',
                         color_discrete_map={
                             'total':      '#2E75B6',
                             'ttr_breach': '#D6B656',
                             'ttc_breach': '#C00000',
                         },
                         labels={'month': '', 'value': 'จำนวน', 'metric': ''})
        fig_mom.update_layout(margin=dict(t=10, b=10), height=300)
        st.plotly_chart(fig_mom, width='stretch')
    else:
        st.info('ต้องการข้อมูลอย่างน้อย 2 เดือนสำหรับ Month-over-Month')

    st.divider()

# ══════════════════════════════════════════════════════════════
# ROW 6 — Off-Hours Pattern
# ══════════════════════════════════════════════════════════════
st.subheader('🌙 Off-Hours Contact Pattern')

df_oh = qdf("""
    SELECT
        EXTRACT(HOUR FROM notified_at AT TIME ZONE 'Asia/Bangkok')::INT AS hour,
        COUNT(*) AS contacts
    FROM Off_Hours_Notified
    WHERE notified_date >= CURRENT_DATE - 30
    GROUP BY hour ORDER BY hour
""")

if not df_oh.empty:
    all_hours = pd.DataFrame({'hour': range(0, 24)})
    df_oh = all_hours.merge(df_oh, on='hour', how='left').fillna(0)
    df_oh['contacts'] = df_oh['contacts'].astype(int)
    df_oh['label'] = df_oh['hour'].apply(lambda h: f"{h:02d}:00")

    fig_oh = px.bar(df_oh, x='label', y='contacts',
                    color='contacts',
                    color_continuous_scale=['#1F4E79', '#2E75B6', '#D6B656', '#C00000'],
                    labels={'label': 'ชั่วโมง', 'contacts': 'ครั้ง'})
    fig_oh.update_layout(margin=dict(t=10, b=10), height=250, coloraxis_showscale=False)
    st.plotly_chart(fig_oh, width='stretch')
    st.caption('ข้อมูล 30 วันล่าสุด — แสดงว่าช่วงไหนลูกค้าทักนอกเวลาเยอะที่สุด')
else:
    st.info('ยังไม่มีข้อมูล Off-Hours')