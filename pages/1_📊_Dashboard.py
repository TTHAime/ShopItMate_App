import streamlit as st
from sqlalchemy import select, func, desc, Integer
from core.database import get_session
from models.models import Case, CaseSLA, AdminNotification

st.header("📊 Dashboard")

session = get_session()

try:
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
    c2.metric("🔄 IN_PROGRESS", cnt.get("IN_PROGRESS", 0))
    c3.metric("✅ RESOLVED วันนี้", cnt.get("RESOLVED", 0))
    c4.metric("🔒 CLOSED วันนี้", cnt.get("CLOSED", 0))

    st.divider()

    st.subheader("⚠ TTR Alert — เคสที่ยังไม่รับงาน ใกล้หมดเวลา")

    alerts = session.execute(
        select(
            Case.case_id,
            Case.category,
            Case.priority,
            CaseSLA.ttr_due_at,
            (func.extract("epoch", CaseSLA.ttr_due_at - func.now()) / 60).cast(Integer).label("ttr_min_remaining")
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
            rem = r.ttr_min_remaining
            icon = "🔴" if rem < 0 else ("🟡" if rem <= 20 else "🟢")
            label = f"เกิน {abs(rem)} นาทีแล้ว!" if rem < 0 else f"เหลือ {rem} นาที"
            st.write(
                f"{icon} **#{str(r.case_id)[-6:].upper()}** — "
                f"{r.category} — {r.priority} — {label}"
            )
    else:
        st.success("ไม่มีเคสที่ต้องแจ้งเตือน TTR")

    st.divider()

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

    st.subheader("🔔 Notifications ที่ยังไม่อ่าน")

    notifs = session.execute(
        select(AdminNotification)
        .where(AdminNotification.is_read == False)
        .order_by(desc(AdminNotification.created_at))
        .limit(20)
    ).scalars().all()

    if notifs:
        for n in notifs:
            st.info(f"**[{n.type}]** {n.message}")

        if st.button("✔ Mark all as read"):
            session.query(AdminNotification).filter(
                AdminNotification.is_read == False
            ).update(
                {AdminNotification.is_read: True},
                synchronize_session=False
            )
            session.commit()
            st.rerun()
    else:
        st.success("ไม่มี notification ใหม่")

finally:
    session.close()