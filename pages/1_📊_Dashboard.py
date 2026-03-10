import html
from textwrap import dedent

import streamlit as st
from sqlalchemy import select, func, desc, Integer

from core.database import get_session
from models.models import Case, CaseSLA, AdminNotification

st.header("📊 Dashboard")

PAGE_SIZE = 5

if "notif_page" not in st.session_state:
    st.session_state.notif_page = 1

if "notif_filter" not in st.session_state:
    st.session_state.notif_filter = "UNREAD"


def render_html_block(content: str):
    import re
    compressed = re.sub(r'\s+', ' ', dedent(content).strip())
    st.markdown(compressed, unsafe_allow_html=True)


session = get_session()

try:
    # =========================
    # TOP METRICS
    # =========================
    c1, c2, c3, c4 = st.columns(4)

    today_status_rows = session.execute(
        select(
            Case.status,
            func.count().label("cnt")
        )
        .where(
            func.date(func.timezone("Asia/Bangkok", Case.created_at)) == func.current_date()
        )
        .group_by(Case.status)
    ).all()

    cnt = {row.status: row.cnt for row in today_status_rows}

    c1.metric("🆕 OPEN วันนี้", cnt.get("OPEN", 0))
    c2.metric("🔄 IN_PROGRESS วันนี้", cnt.get("IN_PROGRESS", 0))
    c3.metric("✅ RESOLVED วันนี้", cnt.get("RESOLVED", 0))
    c4.metric("🔒 CLOSED วันนี้", cnt.get("CLOSED", 0))

    st.divider()

    # =========================
    # TTR ALERT
    # =========================
    st.subheader("⚠ TTR Alert — เคสที่ยังไม่รับงาน ใกล้หมดเวลา")

    alerts = session.execute(
        select(
            Case.case_id,
            Case.category,
            Case.priority,
            CaseSLA.ttr_due_at,
            (
                func.extract("epoch", CaseSLA.ttr_due_at - func.now()) / 60
            ).cast(Integer).label("ttr_min_remaining")
        )
        .join(CaseSLA, Case.case_id == CaseSLA.case_id)
        .where(Case.status == "OPEN")
        .where(CaseSLA.ttr_breached == False)
        .where(CaseSLA.ttr_due_at.is_not(None))
        .order_by(CaseSLA.ttr_due_at.asc())
        .limit(10)
    ).all()

    if alerts:
        for r in alerts:
            rem = r.ttr_min_remaining if r.ttr_min_remaining is not None else 0
            icon = "🔴" if rem < 0 else ("🟡" if rem <= 20 else "🟢")
            label = f"เกิน {abs(rem)} นาทีแล้ว!" if rem < 0 else f"เหลือ {rem} นาที"

            case_code = html.escape(str(r.case_id)[-6:].upper())
            category = html.escape(str(r.category or "-"))
            priority = html.escape(str(r.priority or "-"))
            label_text = html.escape(label)

            render_html_block(f"""
<div style="border:1px solid #2a2a2a;border-radius:12px;padding:12px 14px;margin-bottom:10px;background:#111827;">
<div style="font-size:15px;color:#f9fafb;line-height:1.5;margin-bottom:4px;">
{icon} <b>#{case_code}</b> | {category} | {priority}
</div>
<div style="font-size:13px;color:#9ca3af;">
{label_text}
</div>
</div>
""")
    else:
        st.success("ไม่มีเคสที่ต้องแจ้งเตือน TTR")

    st.divider()

    # =========================
    # SLA SUMMARY
    # =========================
    st.subheader("📈 SLA Summary")

    sla = session.execute(
        select(
            func.count().filter(CaseSLA.ttr_breached == True).label("ttr_breach"),
            func.count().filter(CaseSLA.ttc_breached == True).label("ttc_breach"),
            func.round(
                func.avg(
                    func.extract("epoch", Case.acknowledged_at - Case.created_at) / 60
                ).filter(Case.acknowledged_at.is_not(None)),
                1
            ).label("avg_ttr_min")
        )
        .select_from(Case)
        .join(CaseSLA, Case.case_id == CaseSLA.case_id)
    ).one()

    avg_ttr_value = f"{float(sla.avg_ttr_min):.1f}" if sla.avg_ttr_min is not None else "-"

    a1, a2, a3 = st.columns(3)
    a1.metric("TTR Breached (ทั้งหมด)", int(sla.ttr_breach or 0))
    a2.metric("TTC Breached (ทั้งหมด)", int(sla.ttc_breach or 0))
    a3.metric("Avg TTR จริง (นาที)", avg_ttr_value)

    st.divider()

    # =========================
    # NOTIFICATIONS
    # =========================
    st.subheader("🔔 Notifications")

    # --- Filter + Page info row ---
    f1, f2 = st.columns([3, 1])

    with f1:
        selected_filter = st.radio(
            "เลือกการแสดงผล",
            ["UNREAD", "ALL"],
            horizontal=True,
            index=0 if st.session_state.notif_filter == "UNREAD" else 1,
            label_visibility="collapsed"
        )
        if selected_filter != st.session_state.notif_filter:
            st.session_state.notif_filter = selected_filter
            st.session_state.notif_page = 1
            st.rerun()

    base_count_query = select(func.count()).select_from(AdminNotification)
    base_query = select(AdminNotification)

    if st.session_state.notif_filter == "UNREAD":
        base_count_query = base_count_query.where(AdminNotification.is_read == False)
        base_query = base_query.where(AdminNotification.is_read == False)

    total_notifications = session.execute(base_count_query).scalar() or 0
    total_pages = max((total_notifications - 1) // PAGE_SIZE + 1, 1)

    if st.session_state.notif_page > total_pages:
        st.session_state.notif_page = total_pages

    offset_value = (st.session_state.notif_page - 1) * PAGE_SIZE

    notifs = session.execute(
        base_query
        .order_by(desc(AdminNotification.created_at))
        .offset(offset_value)
        .limit(PAGE_SIZE)
    ).scalars().all()

    with f2:
        render_html_block(f"""
<div style="text-align:right;color:#6b7280;font-size:13px;padding-top:8px;">
หน้า <b style="color:#d1d5db;">{st.session_state.notif_page}</b> / {total_pages}
&nbsp;·&nbsp; ทั้งหมด <b style="color:#d1d5db;">{total_notifications}</b> รายการ
</div>
""")

    if notifs:
        # --- Notification Cards ---
        for n in notifs:
            created_text = (
                n.created_at.strftime("%d/%m/%Y %H:%M")
                if getattr(n, "created_at", None) else "-"
            )

            notif_type = str(getattr(n, "type", "INFO") or "INFO")
            message_text = str(getattr(n, "message", "") or "")
            is_read = bool(getattr(n, "is_read", False))

            type_meta = {
                "SLA_ALERT":    {"color": "#dc2626", "bg": "#2d1111", "label": "⚠ SLA Alert"},
                "NEW_CASE":     {"color": "#2563eb", "bg": "#111827", "label": "📋 New Case"},
                "new_case":     {"color": "#2563eb", "bg": "#111827", "label": "📋 New Case"},
                "CASE_UPDATE":  {"color": "#16a34a", "bg": "#0f1f13", "label": "🔄 Case Update"},
                "case_update":  {"color": "#16a34a", "bg": "#0f1f13", "label": "🔄 Case Update"},
                "INFO":         {"color": "#6b7280", "bg": "#111827", "label": "ℹ Info"},
            }
            meta = type_meta.get(notif_type, {"color": "#6b7280", "bg": "#111827", "label": notif_type})

            # Unread = slightly brighter bg + left accent bar
            card_bg     = "#0f172a" if not is_read else "#111827"
            border_left = f"4px solid {meta['color']}" if not is_read else "4px solid #1f2937"
            opacity     = "1" if not is_read else "0.55"

            notif_type_label  = html.escape(meta["label"])
            created_text_safe = html.escape(created_text)
            message_safe      = html.escape(message_text)
            badge_dot         = "🔵" if not is_read else "⚪"
            badge_text        = "ยังไม่อ่าน" if not is_read else "อ่านแล้ว"

            render_html_block(f"""
<div style="
    border: 1px solid #1f2937;
    border-left: {border_left};
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    background: {card_bg};
    opacity: {opacity};
">
    <!-- Header row: badge + timestamp -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:6px;">
        <span style="
            background:{meta['color']}22;
            color:{meta['color']};
            border: 1px solid {meta['color']}55;
            padding:3px 10px;
            border-radius:999px;
            font-size:12px;
            font-weight:700;
            letter-spacing:0.03em;
        ">{notif_type_label}</span>
        <span style="font-size:12px; color:#6b7280;">🕐 {created_text_safe}</span>
    </div>

    <!-- Message body -->
    <div style="
        font-size:14px;
        color:#e5e7eb;
        line-height:1.7;
        white-space:normal;
        word-break:break-word;
        margin-bottom:10px;
    ">{message_safe}</div>

    <!-- Footer: read status -->
    <div style="font-size:11px; color:#4b5563;">
        {badge_dot} {badge_text}
    </div>
</div>
""")

        # --- Pagination + Mark-read buttons ---
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        btn_prev, btn_next, btn_mark, btn_spacer = st.columns([1, 1, 2, 1])

        with btn_prev:
            if st.button("⬅ ก่อนหน้า", disabled=st.session_state.notif_page <= 1, use_container_width=True):
                st.session_state.notif_page -= 1
                st.rerun()

        with btn_next:
            if st.button("ถัดไป ➡", disabled=st.session_state.notif_page >= total_pages, use_container_width=True):
                st.session_state.notif_page += 1
                st.rerun()

        with btn_mark:
            if st.button("✔ Mark visible as read", type="primary", use_container_width=True):
                notif_ids = [n.id for n in notifs if not n.is_read]
                if notif_ids:
                    session.query(AdminNotification).filter(
                        AdminNotification.id.in_(notif_ids)
                    ).update(
                        {AdminNotification.is_read: True},
                        synchronize_session=False
                    )
                    session.commit()
                st.rerun()

    else:
        st.success("ไม่มี notification")

finally:
    session.close()