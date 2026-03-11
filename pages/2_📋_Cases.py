import re
import html
from textwrap import dedent
from datetime import datetime, timezone, timedelta

import streamlit as st
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


def render_html(content: str):
    compressed = re.sub(r'\s+', ' ', dedent(content).strip())
    st.markdown(compressed, unsafe_allow_html=True)


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


# =========================
# FILTERS
# =========================
f1, f2, f3 = st.columns(3)

status_options   = ["ทั้งหมด", "OPEN", "IN_PROGRESS", "CLOSED"]
category_options = ["ทั้งหมด", "CLAIM", "BROKEN", "SHIPPING", "RETURN", "DOCUMENT", "CONTACT_ADMIN", "UNCLEAR"]
priority_options = ["ทั้งหมด", "urgent", "high", "medium", "low"]

fs = f1.selectbox("Status",   status_options,   index=status_options.index(st.session_state.case_filter_status))
fc = f2.selectbox("Category", category_options, index=category_options.index(st.session_state.case_filter_category))
fp = f3.selectbox("Priority", priority_options, index=priority_options.index(st.session_state.case_filter_priority))

if (fs != st.session_state.case_filter_status or
        fc != st.session_state.case_filter_category or
        fp != st.session_state.case_filter_priority):
    st.session_state.case_filter_status   = fs
    st.session_state.case_filter_category = fc
    st.session_state.case_filter_priority = fp
    st.session_state.case_page = 1
    st.rerun()

session = get_session()

try:
    # =========================
    # QUERY
    # =========================
    def apply_filters(q):
        if fs != "ทั้งหมด":
            q = q.where(Case.status == fs)
        if fc != "ทั้งหมด":
            q = q.where(Case.category == fc)
        if fp != "ทั้งหมด":
            q = q.where(Case.priority == fp)
        return q

    count_stmt = apply_filters(
        select(func.count())
        .select_from(Case)
        .join(Customer, Case.customer_id == Customer.customer_id)
        .outerjoin(CaseSLA, Case.case_id == CaseSLA.case_id)
    )
    total_cases = session.execute(count_stmt).scalar() or 0
    total_pages = max((total_cases - 1) // PAGE_SIZE + 1, 1)

    if st.session_state.case_page > total_pages:
        st.session_state.case_page = total_pages

    offset_value = (st.session_state.case_page - 1) * PAGE_SIZE

    stmt = apply_filters(
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
            .label("age_minutes"),
        )
        .join(Customer, Case.customer_id == Customer.customer_id)
        .outerjoin(CaseSLA, Case.case_id == CaseSLA.case_id)
    ).order_by(desc(Case.created_at)).offset(offset_value).limit(PAGE_SIZE)

    rows = session.execute(stmt).all()

    # summary row
    top1, top2 = st.columns([3, 1])
    with top1:
        st.write(f"พบ **{total_cases}** เคส")
    with top2:
        render_html(f"""
        <div style="text-align:right;color:#6b7280;font-size:15px;padding-top:4px;">
            หน้า <b style="color:#d1d5db;">{st.session_state.case_page}</b> / {total_pages}
        </div>
        """)

    now_utc = datetime.now(timezone.utc)

    # =========================
    # CASE CARDS
    # =========================
    STATUS_COLOR = {
        "OPEN":        "#2563eb",
        "IN_PROGRESS": "#d97706",
        "CLOSED":      "#4b5563",
    }
    STATUS_ICON = {"OPEN": "🔵", "IN_PROGRESS": "🟡", "CLOSED": "⚫"}
    PRIORITY_COLOR = {"urgent": "#dc2626", "high": "#ea580c", "medium": "#ca8a04", "low": "#16a34a"}
    PRIORITY_ICON  = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    BOT_META = {
        "FULL":    {"label": "FULL",    "color": "#16a34a"},
        "LIMITED": {"label": "LIMITED", "color": "#d97706"},
        "OFF":     {"label": "OFF",     "color": "#dc2626"},
    }

    for row in rows:
        case         = row.Case
        sid          = str(case.case_id)[-6:].upper()
        age_text     = format_minutes_th(row.age_minutes)
        sla_breached = row.ttr_breached or row.ttc_breached

        s_color  = STATUS_COLOR.get(case.status, "#6b7280")
        s_icon   = STATUS_ICON.get(case.status, "⚪")
        p_color  = PRIORITY_COLOR.get(case.priority, "#6b7280")
        p_icon   = PRIORITY_ICON.get(case.priority, "⚪")
        bot_meta = BOT_META.get(row.bot_mode, {"label": row.bot_mode or "?", "color": "#6b7280"})

        customer_name = html.escape(row.customer_name or "-")
        category_safe = html.escape(str(case.category or "-"))
        priority_safe = html.escape(str(case.priority or "-"))
        status_safe   = html.escape(str(case.status or "-"))
        summary_safe  = html.escape(str(case.summary or "—"))

        border_left = f"4px solid #dc2626" if sla_breached else f"4px solid {s_color}"

        expander_label = (
            f"{s_icon} #{sid}  |  {case.category}  |  {p_icon} {case.priority}  |  "
            f"{row.customer_name or '-'}  |  เปิดมา {age_text}"
            + ("  🚨 SLA!" if sla_breached else "")
        )

        with st.expander(expander_label):

            # ── Header card ──────────────────────────────────────────
            render_html(f"""
            <div style="
                border:1px solid #1f2937;
                border-left:{border_left};
                border-radius:10px;
                padding:16px 18px;
                margin-bottom:14px;
                background:#0f172a;
            ">
                <!-- Row 1: ID + badges -->
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;">
                    <span style="font-size:20px;font-weight:700;color:#f9fafb;letter-spacing:0.03em;">#{html.escape(sid)}</span>

                    <span style="background:{s_color}22;color:{s_color};border:1px solid {s_color}55;
                        padding:3px 10px;border-radius:999px;font-size:14px;font-weight:700;">
                        {status_safe}
                    </span>

                    <span style="background:{p_color}22;color:{p_color};border:1px solid {p_color}55;
                        padding:3px 10px;border-radius:999px;font-size:14px;font-weight:700;">
                        {p_icon} {priority_safe}
                    </span>

                    <span style="background:{bot_meta['color']}22;color:{bot_meta['color']};border:1px solid {bot_meta['color']}55;
                        padding:3px 10px;border-radius:999px;font-size:14px;font-weight:600;">
                        🤖 {html.escape(bot_meta['label'])}
                    </span>

                    {"<span style='background:#dc262622;color:#dc2626;border:1px solid #dc262655;padding:3px 10px;border-radius:999px;font-size:14px;font-weight:700;'>🚨 SLA Breached</span>" if sla_breached else ""}
                </div>

                <!-- Row 2: Category + Customer -->
                <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:12px;">
                    <div>
                        <div style="font-size:13px;color:#6b7280;margin-bottom:2px;">CATEGORY</div>
                        <div style="font-size:16px;color:#d1d5db;font-weight:600;">{category_safe}</div>
                    </div>
                    <div>
                        <div style="font-size:13px;color:#6b7280;margin-bottom:2px;">CUSTOMER</div>
                        <div style="font-size:16px;color:#d1d5db;font-weight:600;">{customer_name}</div>
                    </div>
                    <div>
                        <div style="font-size:13px;color:#6b7280;margin-bottom:2px;">เปิดมา</div>
                        <div style="font-size:16px;color:#d1d5db;font-weight:600;">{html.escape(age_text)}</div>
                    </div>
                </div>

                <!-- Row 3: Summary -->
                <div style="font-size:16px;color:#9ca3af;line-height:1.6;">
                    <span style="color:#6b7280;font-size:13px;">SUMMARY&nbsp;&nbsp;</span>{summary_safe}
                </div>
            </div>
            """)

            # ── SLA + Times ──────────────────────────────────────────
            col_l, col_r = st.columns(2)

            with col_l:
                created_str = fmt_dt_th(case.created_at)
                closed_str  = fmt_dt_th(case.closed_at) if case.closed_at else "-"
                ack_str     = "-"
                if case.acknowledged_at:
                    ttr_actual = int((case.acknowledged_at - case.created_at).total_seconds() / 60)
                    ack_str = format_minutes_th(ttr_actual)

                render_html(f"""
                <div style="background:#111827;border:1px solid #1f2937;border-radius:10px;padding:14px 16px;">
                    <div style="font-size:13px;color:#6b7280;font-weight:700;margin-bottom:10px;letter-spacing:0.08em;">⏱ เวลา</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                        <div>
                            <div style="font-size:13px;color:#6b7280;">สร้างเมื่อ</div>
                            <div style="font-size:15px;color:#d1d5db;">{html.escape(created_str)}</div>
                        </div>
                        <div>
                            <div style="font-size:13px;color:#6b7280;">ปิดเมื่อ</div>
                            <div style="font-size:15px;color:#d1d5db;">{html.escape(closed_str)}</div>
                        </div>
                        <div>
                            <div style="font-size:13px;color:#6b7280;">TTR จริง</div>
                            <div style="font-size:15px;color:#d1d5db;">{html.escape(ack_str)}</div>
                        </div>
                    </div>
                </div>
                """)

            with col_r:
                def deadline_html(label, due_at, breached):
                    if not due_at:
                        return f"""
                        <div>
                            <div style="font-size:13px;color:#6b7280;">{label}</div>
                            <div style="font-size:15px;color:#4b5563;">-</div>
                        </div>
                        """

                    due_str = fmt_dt_th(due_at)

                    if breached:
                        clr = "#dc2626"
                        txt = f"เกิน SLA แล้ว • ครบกำหนด {due_str}"
                    else:
                        clr = "#16a34a"
                        txt = f"ครบกำหนด {due_str}"

                    return f"""
                    <div>
                        <div style="font-size:13px;color:#6b7280;">{label}</div>
                        <div style="font-size:15px;color:{clr};font-weight:600;">{html.escape(txt)}</div>
                    </div>
                    """

                ttr_html = deadline_html("TTR Deadline", row.ttr_due_at, row.ttr_breached)
                ttc_html = deadline_html("TTC Deadline", row.ttc_due_at, row.ttc_breached)
                ttr_breach_txt = "🔴 ใช่" if row.ttr_breached else "🟢 ไม่"
                ttc_breach_txt = "🔴 ใช่" if row.ttc_breached else "🟢 ไม่"

                render_html(f"""
                <div style="background:#111827;border:1px solid #1f2937;border-radius:10px;padding:14px 16px;">
                    <div style="font-size:13px;color:#6b7280;font-weight:700;margin-bottom:10px;letter-spacing:0.08em;">📊 SLA</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                        {ttr_html}
                        {ttc_html}
                        <div>
                            <div style="font-size:13px;color:#6b7280;">TTR Breached</div>
                            <div style="font-size:15px;color:#d1d5db;">{html.escape(ttr_breach_txt)}</div>
                        </div>
                        <div>
                            <div style="font-size:13px;color:#6b7280;">TTC Breached</div>
                            <div style="font-size:15px;color:#d1d5db;">{html.escape(ttc_breach_txt)}</div>
                        </div>
                    </div>
                </div>
                """)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── Action buttons ────────────────────────────────────────
            cid_str = str(case.case_id)

            if case.status in ("OPEN", "IN_PROGRESS"):
                b1, b2, b_spacer = st.columns([1, 1, 3])

                if case.status == "OPEN":
                    if b1.button("▶ รับงาน", key=f"ip_{sid}", use_container_width=True):
                        if update_case_status(cid_str, "IN_PROGRESS"):
                            st.success("อัปเดตเป็น IN_PROGRESS แล้ว")
                            st.rerun()
                        else:
                            st.error("อัปเดตสถานะไม่สำเร็จ")

                is_open = case.status == "OPEN"
                if b2.button(
                    "🔒 ปิดเคส",
                    key=f"cl_{sid}",
                    type="primary",
                    use_container_width=True,
                    disabled=is_open,
                    help="ต้องรับงานก่อนจึงจะปิดเคสได้" if is_open else None,
                ):
                    if update_case_status(cid_str, "CLOSED"):
                        st.success("ปิดเคสแล้ว")
                        st.rerun()
                    else:
                        st.error("อัปเดตสถานะไม่สำเร็จ")

            # ── Timeline ─────────────────────────────────────────────
            events = session.execute(
                select(CaseEvent)
                .where(CaseEvent.case_id == case.case_id)
                .order_by(CaseEvent.created_at.asc())
            ).scalars().all()

            if events:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                render_html("""
                <div style="font-size:13px;color:#6b7280;font-weight:700;
                    letter-spacing:0.08em;margin-bottom:6px;">📅 TIMELINE</div>
                """)
                timeline_items = ""
                for i, e in enumerate(events):
                    ts           = e.created_at.astimezone(TH_TZ).strftime("%d/%m %H:%M")
                    details_text = html.escape(f" — {e.details}" if e.details else "")
                    event_type   = html.escape(str(e.event_type or ""))
                    actor        = html.escape(str(e.actor_type or ""))
                    is_last      = i == len(events) - 1

                    timeline_items += f"""
                    <div style="display:flex;gap:12px;margin-bottom:{'0' if is_last else '8px'};">
                        <div style="display:flex;flex-direction:column;align-items:center;">
                            <div style="width:8px;height:8px;border-radius:50%;background:#374151;margin-top:4px;flex-shrink:0;"></div>
                            {"" if is_last else "<div style='width:1px;flex:1;background:#1f2937;margin-top:3px;'></div>"}
                        </div>
                        <div style="padding-bottom:{'0' if is_last else '4px'};">
                            <span style="font-size:13px;color:#6b7280;">{html.escape(ts)}</span>
                            <span style="font-size:14px;color:#9ca3af;margin-left:8px;">[{event_type}]</span>
                            <span style="font-size:14px;color:#6b7280;margin-left:4px;">by {actor}{details_text}</span>
                        </div>
                    </div>
                    """

                render_html(f"""
                <div style="background:#0d1117;border:1px solid #1f2937;border-radius:10px;
                    padding:14px 16px;margin-top:4px;">
                    {timeline_items}
                </div>
                """)
            else:
                st.caption("ไม่มี timeline")

    # =========================
    # PAGINATION
    # =========================
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    nav1, nav2, nav3 = st.columns([1, 1, 3])

    with nav1:
        if st.button("⬅ ก่อนหน้า", disabled=st.session_state.case_page <= 1, use_container_width=True):
            st.session_state.case_page -= 1
            st.rerun()

    with nav2:
        if st.button("ถัดไป ➡", disabled=st.session_state.case_page >= total_pages, use_container_width=True):
            st.session_state.case_page += 1
            st.rerun()

    with nav3:
        render_html(f"""
        <div style="color:#6b7280;font-size:15px;padding-top:8px;">
            แสดง <b style="color:#d1d5db;">{len(rows)}</b> รายการต่อหน้า
            จากทั้งหมด <b style="color:#d1d5db;">{total_cases}</b> เคส
        </div>
        """)

finally:
    session.close()