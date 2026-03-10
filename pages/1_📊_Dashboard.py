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
    st.markdown(dedent(content).strip(), unsafe_allow_html=True)


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

    a1, a2, a3 = st.columns(3)
    a1.metric("TTR Breached (ทั้งหมด)", sla.ttr_breach or 0)
    a2.metric("TTC Breached (ทั้งหมด)", sla.ttc_breach or 0)
    a3.metric("Avg TTR จริง (นาที)", sla.avg_ttr_min or "-")

    st.divider()

    # =========================
    # NOTIFICATIONS
    # =========================
    st.subheader("🔔 Notifications")

    f1, f2 = st.columns([2, 1])

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
<div style="text-align:right;color:#9ca3af;font-size:14px;padding-top:6px;">
หน้า {st.session_state.notif_page} / {total_pages}
</div>
""")

    if notifs:
        for n in notifs:
            created_text = (
                n.created_at.strftime("%d/%m/%Y %H:%M")
                if getattr(n, "created_at", None) else "-"
            )

            notif_type = str(getattr(n, "type", "INFO") or "INFO")
            message_text = str(getattr(n, "message", "") or "")
            is_read = bool(getattr(n, "is_read", False))

            type_color = {
                "SLA_ALERT": "#dc2626",
                "NEW_CASE": "#2563eb",
                "CASE_UPDATE": "#16a34a",
                "INFO": "#6b7280",
                "new_case": "#2563eb",
                "case_update": "#16a34a",
            }.get(notif_type, "#6b7280")

            read_badge = "⚪ Read" if is_read else "🔵 Unread"

            notif_type_safe = html.escape(notif_type)
            created_text_safe = html.escape(created_text)
            message_safe = html.escape(message_text)
            read_badge_safe = html.escape(read_badge)

            render_html_block(f"""
<div style="border:1px solid #2a2a2a;border-radius:14px;padding:14px 16px;margin-bottom:12px;background:#111827;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:8px;flex-wrap:wrap;">
<div>
<span style="background:{type_color};color:white;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600;">
{notif_type_safe}
</span>
</div>
<div style="font-size:12px;color:#9ca3af;">
{created_text_safe}
</div>
</div>

<div style="font-size:15px;color:#f9fafb;line-height:1.6;margin-bottom:8px;white-space:pre-wrap;word-break:break-word;">
{message_safe}
</div>

<div style="font-size:12px;color:#9ca3af;">
{read_badge_safe}
</div>
</div>
""")

        p1, p2, p3 = st.columns([1, 1, 2])

        with p1:
            if st.button("⬅ ก่อนหน้า", disabled=st.session_state.notif_page <= 1):
                st.session_state.notif_page -= 1
                st.rerun()

        with p2:
            if st.button("ถัดไป ➡", disabled=st.session_state.notif_page >= total_pages):
                st.session_state.notif_page += 1
                st.rerun()

        with p3:
            if st.button("✔ Mark visible as read"):
                notif_ids = [n.notification_id for n in notifs if not n.is_read]
                if notif_ids:
                    session.query(AdminNotification).filter(
                        AdminNotification.notification_id.in_(notif_ids)
                    ).update(
                        {AdminNotification.is_read: True},
                        synchronize_session=False
                    )
                    session.commit()
                st.rerun()

        if st.session_state.notif_filter == "UNREAD":
            if st.button("✔ Mark all unread as read"):
                session.query(AdminNotification).filter(
                    AdminNotification.is_read == False
                ).update(
                    {AdminNotification.is_read: True},
                    synchronize_session=False
                )
                session.commit()
                st.session_state.notif_page = 1
                st.rerun()
    else:
        st.success("ไม่มี notification")

finally:
    session.close()