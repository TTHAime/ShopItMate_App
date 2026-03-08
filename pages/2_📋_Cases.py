import streamlit as st
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc, func, Integer
from core.database import get_session
from core.n8n_client import update_case_status
from models.models import Case, Customer, CaseSLA, CaseEvent

st.header("📋 Case Management")

f1, f2, f3 = st.columns(3)
fs = f1.selectbox("Status", ["ทั้งหมด", "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"])
fc = f2.selectbox("Category", ["ทั้งหมด", "CLAIM", "BROKEN", "SHIPPING", "RETURN",
                               "DOCUMENT", "CONTACT_ADMIN", "UNCLEAR"])
fp = f3.selectbox("Priority", ["ทั้งหมด", "urgent", "high", "medium", "low"])

session = get_session()

try:
    stmt = (
        select(
            Case,
            Customer.display_name.label("customer_name"),
            Customer.bot_mode.label("bot_mode"),
            CaseSLA.ttr_due_at,
            CaseSLA.ttc_due_at,
            CaseSLA.ttr_breached,
            CaseSLA.ttc_breached,
            CaseSLA.ttr_met_at,
            (func.extract("epoch", func.now() - Case.created_at) / 60).cast(Integer).label("age_minutes")
        )
        .join(Customer, Case.customer_id == Customer.customer_id)
        .outerjoin(CaseSLA, Case.case_id == CaseSLA.case_id)
    )

    if fs != "ทั้งหมด":
        stmt = stmt.where(Case.status == fs)

    if fc != "ทั้งหมด":
        stmt = stmt.where(Case.category == fc)

    if fp != "ทั้งหมด":
        stmt = stmt.where(Case.priority == fp)

    stmt = stmt.order_by(desc(Case.created_at)).limit(100)

    rows = session.execute(stmt).all()

    st.write(f"พบ **{len(rows)}** เคส")

    now_utc = datetime.now(timezone.utc)

    for row in rows:
        case = row.Case
        sid = str(case.case_id)[-6:].upper()

        s_ico = {
            "OPEN": "🔵",
            "IN_PROGRESS": "🟡",
            "RESOLVED": "🟢",
            "CLOSED": "⚫"
        }.get(case.status, "⚪")

        p_ico = {
            "urgent": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(case.priority, "⚪")

        sla_f = " 🚨" if (row.ttr_breached or row.ttc_breached) else ""

        with st.expander(
            f"{s_ico} #{sid} | {case.category} | {p_ico} {case.priority} | "
            f"{row.customer_name} | เปิดมา {row.age_minutes} นาที{sla_f}"
        ):
            col_l, col_r = st.columns(2)

            with col_l:
                st.write("**สรุป:**", case.summary or "—")
                st.write("**สถานะ:**", case.status)
                st.write("**สถานะบอท:**")

                BOT_BADGE = {
                    "FULL": ("🟢 FULL", "success"),
                    "LIMITED": ("🟡 LIMITED", "warning"),
                    "OFF": ("🔴 OFF", "error"),
                }

                label, kind = BOT_BADGE.get(row.bot_mode, ("❓", "info"))
                getattr(st, kind)(label)

                st.write(
                    "**สร้างเมื่อ:**",
                    case.created_at.astimezone(
                        timezone(timedelta(hours=7))
                    ).strftime("%d/%m/%Y %H:%M")
                )

                if case.acknowledged_at:
                    ttr_actual = int(
                        (case.acknowledged_at - case.created_at).total_seconds() / 60
                    )
                    st.write(f"**TTR จริง:** {ttr_actual} นาที")

            with col_r:
                if row.ttr_due_at:
                    rem = int((row.ttr_due_at - now_utc).total_seconds() / 60)
                    lbl = f"🔴 เกิน {abs(rem)} นาที" if rem < 0 else f"🟢 เหลือ {rem} นาที"
                    st.write("**TTR Deadline:**", lbl)

                if row.ttc_due_at:
                    rem2 = int((row.ttc_due_at - now_utc).total_seconds() / 60)
                    lbl2 = f"🔴 เกิน {abs(rem2)} นาที" if rem2 < 0 else f"🟢 เหลือ {rem2} นาที"
                    st.write("**TTC Deadline:**", lbl2)

            st.divider()

            cid_str = str(case.case_id)
            b1, b2, b3 = st.columns(3)

            if case.status == "OPEN":
                if b1.button("▶ รับงาน", key=f"ip_{sid}"):
                    if update_case_status(cid_str, "IN_PROGRESS"):
                        st.success("✅ อัปเดตเป็น IN_PROGRESS แล้ว")
                        st.rerun()

            if case.status in ("OPEN", "IN_PROGRESS"):
                if b2.button("✅ แก้ไขแล้ว", key=f"rv_{sid}"):
                    if update_case_status(cid_str, "RESOLVED"):
                        st.success("✅ RESOLVED แล้ว บอทเปิดกลับมาแล้ว")
                        st.rerun()

                if b3.button("🔒 ปิดเคส", key=f"cl_{sid}"):
                    if update_case_status(cid_str, "CLOSED"):
                        st.success("✅ ปิดเคสแล้ว บอทเปิดกลับมาแล้ว")
                        st.rerun()

            events = session.execute(
                select(CaseEvent)
                .where(CaseEvent.case_id == case.case_id)
                .order_by(CaseEvent.created_at.asc())
            ).scalars().all()

            if events:
                st.write("**Timeline:**")
                for e in events:
                    ts = e.created_at.astimezone(
                        timezone(timedelta(hours=7))
                    ).strftime("%d/%m %H:%M")

                    st.caption(
                        f"{ts} — [{e.event_type}] by {e.actor_type}"
                        + (f" — {e.details}" if e.details else "")
                    )

finally:
    session.close()