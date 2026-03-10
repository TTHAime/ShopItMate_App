import streamlit as st
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc, func, Integer
from core.database import get_session
from core.n8n_client import update_case_status
from models.models import Case, Customer, CaseSLA, CaseEvent

st.header("📋 Case Management")

PAGE_SIZE = 10
TH_TZ = timezone(timedelta(hours=7))

if "case_page" not in st.session_state:
    st.session_state.case_page = 1

if "case_filter_status" not in st.session_state:
    st.session_state.case_filter_status = "ทั้งหมด"

if "case_filter_category" not in st.session_state:
    st.session_state.case_filter_category = "ทั้งหมด"

if "case_filter_priority" not in st.session_state:
    st.session_state.case_filter_priority = "ทั้งหมด"


def format_minutes_th(total_minutes):
    if total_minutes is None:
        return "-"

    total_minutes = int(total_minutes)

    days = total_minutes // (24 * 60)
    remain = total_minutes % (24 * 60)
    hours = remain // 60
    minutes = remain % 60

    parts = []

    if days > 0:
        parts.append(f"{days} วัน")
    if hours > 0:
        parts.append(f"{hours} ชม")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} นาที")

    return " ".join(parts)


def fmt_dt_th(dt_value):
    if not dt_value:
        return "-"
    return dt_value.astimezone(TH_TZ).strftime("%d/%m/%Y %H:%M")


f1, f2, f3 = st.columns(3)

status_options = ["ทั้งหมด", "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
category_options = [
    "ทั้งหมด", "CLAIM", "BROKEN", "SHIPPING", "RETURN",
    "DOCUMENT", "CONTACT_ADMIN", "UNCLEAR"
]
priority_options = ["ทั้งหมด", "urgent", "high", "medium", "low"]

fs = f1.selectbox(
    "Status",
    status_options,
    index=status_options.index(st.session_state.case_filter_status),
)

fc = f2.selectbox(
    "Category",
    category_options,
    index=category_options.index(st.session_state.case_filter_category),
)

fp = f3.selectbox(
    "Priority",
    priority_options,
    index=priority_options.index(st.session_state.case_filter_priority),
)

filter_changed = (
    fs != st.session_state.case_filter_status
    or fc != st.session_state.case_filter_category
    or fp != st.session_state.case_filter_priority
)

if filter_changed:
    st.session_state.case_filter_status = fs
    st.session_state.case_filter_category = fc
    st.session_state.case_filter_priority = fp
    st.session_state.case_page = 1
    st.rerun()

session = get_session()

try:
    count_stmt = (
        select(func.count())
        .select_from(Case)
        .join(Customer, Case.customer_id == Customer.customer_id)
        .outerjoin(CaseSLA, Case.case_id == CaseSLA.case_id)
    )

    if fs != "ทั้งหมด":
        count_stmt = count_stmt.where(Case.status == fs)

    if fc != "ทั้งหมด":
        count_stmt = count_stmt.where(Case.category == fc)

    if fp != "ทั้งหมด":
        count_stmt = count_stmt.where(Case.priority == fp)

    total_cases = session.execute(count_stmt).scalar() or 0
    total_pages = max((total_cases - 1) // PAGE_SIZE + 1, 1)

    if st.session_state.case_page > total_pages:
        st.session_state.case_page = total_pages

    offset_value = (st.session_state.case_page - 1) * PAGE_SIZE

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
            (func.extract("epoch", func.now() - Case.created_at) / 60)
            .cast(Integer)
            .label("age_minutes")
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

    stmt = (
        stmt.order_by(desc(Case.created_at))
        .offset(offset_value)
        .limit(PAGE_SIZE)
    )

    rows = session.execute(stmt).all()

    top1, top2 = st.columns([2, 1])
    with top1:
        st.write(f"พบ **{total_cases}** เคส")
    with top2:
        st.caption(f"หน้า {st.session_state.case_page} / {total_pages}")

    now_utc = datetime.now(timezone.utc)

    for row in rows:
        case = row.Case
        sid = str(case.case_id)[-6:].upper()
        age_text = format_minutes_th(row.age_minutes)

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

        bot_label = {
            "FULL": "🟢 FULL",
            "LIMITED": "🟡 LIMITED",
            "OFF": "🔴 OFF",
        }.get(row.bot_mode, "❓ UNKNOWN")

        customer_name = row.customer_name or "-"
        sla_f = " 🚨" if (row.ttr_breached or row.ttc_breached) else ""

        with st.expander(
            f"{s_ico} #{sid} | {case.category} | {p_ico} {case.priority} | "
            f"{customer_name} | เปิดมา {age_text}{sla_f}"
        ):
            col_l, col_r = st.columns(2)

            with col_l:
                st.write(f"**สรุป:** {case.summary or '—'}")

                status_col, bot_col = st.columns(2)
                with status_col:
                    st.write(f"**สถานะ:** {case.status}")
                with bot_col:
                    st.write(f"**สถานะบอท:** {bot_label}")

                time_col1, time_col2 = st.columns(2)
                with time_col1:
                    st.write(f"**สร้างเมื่อ:** {fmt_dt_th(case.created_at)}")
                with time_col2:
                    if case.closed_at:
                        st.write(f"**ปิดเมื่อ:** {fmt_dt_th(case.closed_at)}")
                    else:
                        st.write("**ปิดเมื่อ:** -")

                if case.acknowledged_at:
                    ttr_actual = int(
                        (case.acknowledged_at - case.created_at).total_seconds() / 60
                    )
                    st.write(f"**TTR จริง:** {format_minutes_th(ttr_actual)}")

            with col_r:
                if row.ttr_due_at:
                    rem = int((row.ttr_due_at - now_utc).total_seconds() / 60)
                    if rem < 0:
                        lbl = f"🔴 เกิน {format_minutes_th(abs(rem))}"
                    else:
                        lbl = f"🟢 เหลือ {format_minutes_th(rem)}"
                    st.write(f"**TTR Deadline:** {lbl}")
                else:
                    st.write("**TTR Deadline:** -")

                if row.ttc_due_at:
                    rem2 = int((row.ttc_due_at - now_utc).total_seconds() / 60)
                    if rem2 < 0:
                        lbl2 = f"🔴 เกิน {format_minutes_th(abs(rem2))}"
                    else:
                        lbl2 = f"🟢 เหลือ {format_minutes_th(rem2)}"
                    st.write(f"**TTC Deadline:** {lbl2}")
                else:
                    st.write("**TTC Deadline:** -")

                st.write(f"**TTR Breached:** {'ใช่' if row.ttr_breached else 'ไม่'}")
                st.write(f"**TTC Breached:** {'ใช่' if row.ttc_breached else 'ไม่'}")

            st.divider()

            cid_str = str(case.case_id)
            b1, b2, b3 = st.columns(3)

            if case.status == "OPEN":
                if b1.button("▶ รับงาน", key=f"ip_{sid}"):
                    if update_case_status(cid_str, "IN_PROGRESS"):
                        st.success("อัปเดตเป็น IN_PROGRESS แล้ว")
                        st.rerun()
                    else:
                        st.error("อัปเดตสถานะไม่สำเร็จ")

            if case.status in ("OPEN", "IN_PROGRESS"):
                if b2.button("✅ แก้ไขแล้ว", key=f"rv_{sid}"):
                    if update_case_status(cid_str, "RESOLVED"):
                        st.success("อัปเดตเป็น RESOLVED แล้ว")
                        st.rerun()
                    else:
                        st.error("อัปเดตสถานะไม่สำเร็จ")

                if b3.button("🔒 ปิดเคส", key=f"cl_{sid}"):
                    if update_case_status(cid_str, "CLOSED"):
                        st.success("ปิดเคสแล้ว")
                        st.rerun()
                    else:
                        st.error("อัปเดตสถานะไม่สำเร็จ")

            events = session.execute(
                select(CaseEvent)
                .where(CaseEvent.case_id == case.case_id)
                .order_by(CaseEvent.created_at.asc())
            ).scalars().all()

            if events:
                st.write("**Timeline:**")
                for e in events:
                    ts = e.created_at.astimezone(TH_TZ).strftime("%d/%m %H:%M")
                    details_text = f" — {e.details}" if e.details else ""
                    st.caption(f"{ts} — [{e.event_type}] by {e.actor_type}{details_text}")
            else:
                st.caption("ไม่มี timeline")

    nav1, nav2, nav3 = st.columns([1, 1, 3])

    with nav1:
        if st.button("⬅ ก่อนหน้า", disabled=st.session_state.case_page <= 1):
            st.session_state.case_page -= 1
            st.rerun()

    with nav2:
        if st.button("ถัดไป ➡", disabled=st.session_state.case_page >= total_pages):
            st.session_state.case_page += 1
            st.rerun()

    with nav3:
        st.caption(f"แสดง {len(rows)} รายการต่อหน้า จากทั้งหมด {total_cases} เคส")

finally:
    session.close()