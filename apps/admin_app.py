import streamlit as st
import time
import random
from datetime import datetime, timedelta

st.set_page_config(page_title="Admin (Mock Metabase)", page_icon="📊", layout="wide")

# ------------------------------
# Mock: simulate Metabase query results + conversation details
# ------------------------------
def mock_conversation_messages(intent: str):
    """สร้าง transcript จำลองสำหรับแชท 1 เคส"""
    templates = {
        "เช็คราคา": [
            ("user", "ขอราคา RTX 4060 หน่อย"),
            ("assistant", "ได้เลยครับ (mock) รบกวนบอกยี่ห้อ/รุ่นที่สนใจ เช่น ASUS / MSI ได้ไหมครับ"),
            ("user", "เอา ASUS Dual ครับ"),
            ("assistant", "รับทราบครับ (mock) ถ้าต่อฐานข้อมูลแล้ว ผมจะดึงราคาล่าสุด + โปรโมชั่นให้ทันที"),
        ],
        "เทียบสเปค": [
            ("user", "ช่วยเทียบ i5 กับ i7 ให้หน่อย"),
            ("assistant", "ได้ครับ (mock) ใช้งานหลัก ๆ เล่นเกม / เรียน / ทำงานอะไรครับ"),
            ("user", "ทำงาน + เล่นเกมนิดหน่อย"),
            ("assistant", "โอเคครับ (mock) ถ้าต่อระบบจริงจะสรุปเป็นตาราง + แนะนำตัวเลือกคุ้มสุดให้ครับ"),
        ],
        "ดูสต็อก": [
            ("user", "มีของพร้อมส่งไหม"),
            ("assistant", "ได้ครับ (mock) รบกวนบอกรุ่น/สาขาที่ต้องการเช็คสต็อกครับ"),
            ("user", "อยากได้ MacBook Air M2"),
            ("assistant", "รับทราบครับ (mock) ถ้าต่อ API/DB จะเช็คสต็อกเรียลไทม์ให้ได้เลย"),
        ],
        "ถามการจัดส่ง": [
            ("user", "ส่งไปต่างจังหวัดใช้เวลานานไหม"),
            ("assistant", "ได้ครับ (mock) ปกติขึ้นกับบริษัทขนส่งและพื้นที่ปลายทางครับ"),
            ("user", "เชียงใหม่ครับ"),
            ("assistant", "โอเคครับ (mock) ถ้าต่อจริงจะคำนวณ ETA + ค่าส่งให้ตามตะกร้าสินค้าครับ"),
        ],
        "นโยบายคืน/เคลม": [
            ("user", "เคลมยังไง ต้องใช้ใบเสร็จไหม"),
            ("assistant", "ได้ครับ (mock) โดยทั่วไปต้องใช้หลักฐานการซื้อ/Serial ครับ"),
            ("user", "ถ้ากล่องหายทำไง"),
            ("assistant", "รับทราบครับ (mock) ถ้าต่อ policy docs จะตอบตามเงื่อนไขร้านแบบเป๊ะ ๆ ได้ครับ"),
        ],
    }
    base = templates.get(intent, [
        ("user", "ขอรายละเอียดเพิ่มเติมหน่อย"),
        ("assistant", "ได้ครับ (mock) ถ้าต่อระบบจริงจะดึงข้อมูลให้ครบถ้วนครับ"),
    ])
    return [{"role": r, "content": c} for r, c in base]

def mock_metabase_fetch():
    """จำลองว่าเรียก Metabase API แล้วได้ทั้ง KPI/Charts/Recent conversations"""
    time.sleep(0.6)

    today = datetime.now().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    # KPI
    total_chats = random.randint(120, 520)
    total_users = random.randint(35, 160)
    avg_resp_sec = round(random.uniform(1.8, 6.5), 2)
    csat = round(random.uniform(3.6, 4.8), 2)

    # Time series
    chats_series = [{"date": d.strftime("%Y-%m-%d"), "chats": random.randint(10, 110)} for d in days]

    # Top intents
    intents = [
        ("เช็คราคา", random.randint(20, 140)),
        ("เทียบสเปค", random.randint(20, 140)),
        ("ดูสต็อก", random.randint(20, 140)),
        ("ถามการจัดส่ง", random.randint(10, 90)),
        ("นโยบายคืน/เคลม", random.randint(5, 70)),
    ]
    intents.sort(key=lambda x: x[1], reverse=True)

    # Recent conversations
    names = ["Somchai", "Anan", "Mint", "Ploy", "Beam", "Tee", "Nina", "Palm", "Boss", "May"]
    snippets = [
        "ขอราคา RTX 4060 หน่อย",
        "ช่วยเทียบ i5 กับ i7 ให้ที",
        "มีของพร้อมส่งไหม",
        "ส่งไปต่างจังหวัดใช้เวลานานไหม",
        "เคลมยังไง ต้องใช้ใบเสร็จไหม",
        "แนะนำโน้ตบุ๊คงบ 25k",
    ]

    recents = []
    conversations = {}  # id -> details
    for idx in range(12):
        conv_id = f"CNV-{datetime.now().strftime('%y%m%d')}-{idx+1:03d}"
        intent = random.choice([i[0] for i in intents])
        created_at = datetime.now() - timedelta(minutes=random.randint(1, 240))
        status = random.choice(["Resolved", "Escalated", "Pending"])

        row = {
            "id": conv_id,
            "time": created_at.strftime("%H:%M"),
            "customer": random.choice(names),
            "intent": intent,
            "status": status,
            "snippet": random.choice(snippets),
        }
        recents.append(row)

        conversations[conv_id] = {
            "id": conv_id,
            "customer": row["customer"],
            "intent": intent,
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "channel": random.choice(["Web Chat", "LINE OA", "Facebook", "Call Center"]),
            "messages": mock_conversation_messages(intent),
        }

    recents.sort(key=lambda x: x["time"], reverse=True)

    return {
        "kpi": {
            "total_chats": total_chats,
            "total_users": total_users,
            "avg_resp_sec": avg_resp_sec,
            "csat": csat,
        },
        "chats_series": chats_series,
        "intents": intents,
        "recents": recents,
        "conversations": conversations,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

# ------------------------------
# UI
# ------------------------------
st.title("📊 Admin Panel (Mock) — Simulate Metabase Data")
st.caption("หน้านี้เป็น mockup: จำลองการดึงข้อมูลจาก Metabase (ยังไม่ต่อจริง)")

with st.sidebar:
    st.subheader("⚙️ Controls")
    shop = st.selectbox("ร้าน", ["Demo Shop", "IT Shop A", "IT Shop B"], index=0)
    range_opt = st.selectbox("ช่วงเวลา", ["7 วันล่าสุด", "30 วันล่าสุด", "วันนี้"], index=0)
    st.markdown("---")
    refresh = st.button("🔄 Refresh (mock)", use_container_width=True)

# session state
if "mb_data" not in st.session_state or refresh:
    with st.spinner("กำลังดึงข้อมูลจาก Metabase... (mock)"):
        st.session_state.mb_data = mock_metabase_fetch()

if "selected_conv_id" not in st.session_state:
    st.session_state.selected_conv_id = None

data = st.session_state.mb_data

# ------------------------------
# Top KPIs
# ------------------------------
kpi = data["kpi"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Chats", f"{kpi['total_chats']}")
c2.metric("Unique Users", f"{kpi['total_users']}")
c3.metric("Avg Response (s)", f"{kpi['avg_resp_sec']}")
c4.metric("CSAT (1-5)", f"{kpi['csat']}")

st.markdown("")

# ------------------------------
# Charts
# ------------------------------
left, right = st.columns([1.4, 1])

with left:
    st.subheader("Chats over time")
    series = {row["date"]: row["chats"] for row in data["chats_series"]}
    st.line_chart(series)

with right:
    st.subheader("Top intents")
    bar = {name: count for name, count in data["intents"]}
    st.bar_chart(bar)

st.markdown("---")

# ------------------------------
# Filters
# ------------------------------
st.subheader("Recent conversations (mock)")
st.caption(f"Fetched at: {data['fetched_at']} • Shop: {shop} • Range: {range_opt}")

colf1, colf2, colf3 = st.columns([1, 1, 1.2])
with colf1:
    status_filter = st.multiselect(
        "Filter status",
        ["Resolved", "Escalated", "Pending"],
        default=["Resolved", "Escalated", "Pending"],
    )
with colf2:
    intent_filter = st.multiselect(
        "Filter intent",
        [i[0] for i in data["intents"]],
        default=[i[0] for i in data["intents"]],
    )
with colf3:
    q = st.text_input("Search (customer/snippet)", placeholder="พิมพ์คำค้น...")

def match_query(row, qtxt: str):
    if not qtxt:
        return True
    qtxt = qtxt.lower()
    return (qtxt in row["customer"].lower()) or (qtxt in row["snippet"].lower()) or (qtxt in row["id"].lower())

filtered = [
    r for r in data["recents"]
    if r["status"] in status_filter
    and r["intent"] in intent_filter
    and match_query(r, q)
]

# ------------------------------
# Table-like list with View buttons
# ------------------------------
header = st.columns([1.1, 1.2, 1.2, 1.2, 2.8, 0.9])
header[0].markdown("**Time**")
header[1].markdown("**Conversation ID**")
header[2].markdown("**Customer**")
header[3].markdown("**Status**")
header[4].markdown("**Snippet**")
header[5].markdown("**Action**")

for row in filtered:
    cols = st.columns([1.1, 1.2, 1.2, 1.2, 2.8, 0.9])
    cols[0].write(row["time"])
    cols[1].code(row["id"], language=None)
    cols[2].write(row["customer"])
    cols[3].write(row["status"])
    cols[4].write(f"[{row['intent']}] {row['snippet']}")
    if cols[5].button("👁 View", key=f"view_{row['id']}"):
        st.session_state.selected_conv_id = row["id"]
        st.rerun()

st.markdown("---")

# ------------------------------
# Conversation detail (mock)
# ------------------------------
if st.session_state.selected_conv_id:
    conv_id = st.session_state.selected_conv_id
    conv = data["conversations"].get(conv_id)

    if conv is None:
        st.warning("ไม่พบข้อมูลแชทนี้ (อาจ refresh แล้วข้อมูลเปลี่ยน)")
    else:
        top = st.columns([1, 6, 1.2])
        top[0].markdown("### 💬 Chat Detail")
        top[2].button("⬅ Back", on_click=lambda: st.session_state.update({"selected_conv_id": None}))

        info1, info2, info3, info4, info5 = st.columns([1.2, 1.2, 1.2, 1.2, 1.2])
        info1.metric("Conversation", conv["id"])
        info2.metric("Customer", conv["customer"])
        info3.metric("Status", conv["status"])
        info4.metric("Intent", conv["intent"])
        info5.metric("Channel", conv["channel"])

        st.caption(f"Created at: {conv['created_at']}")

        st.markdown("#### Transcript")
        # แสดง transcript แบบ chat bubble ของ streamlit
        for m in conv["messages"]:
            role = "user" if m["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(m["content"])

        st.markdown("#### Actions (mock)")
        a1, a2, a3 = st.columns(3)
        if a1.button("✅ Mark Resolved (mock)"):
            st.success("อัปเดตสถานะเป็น Resolved (mock) — ถ้าต่อจริงจะยิง API ไปอัปเดตในระบบ")
        if a2.button("⚠ Escalate to Human (mock)"):
            st.warning("ส่งต่อให้เจ้าหน้าที่ (mock) — ถ้าต่อจริงจะสร้าง ticket/notify ได้")
        if a3.button("📋 Copy summary (mock)"):
            st.info("สรุปแชท: (mock) ลูกค้าถามเรื่อง " + conv["intent"])