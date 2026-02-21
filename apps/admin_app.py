import streamlit as st
import time
import random
from datetime import datetime, timedelta
from io import BytesIO

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None

st.set_page_config(page_title="Admin (Mock Metabase)", page_icon="📊", layout="wide")

# =========================================================
# CSS: wrap long texts + make table nicer
# =========================================================
st.markdown(
    """
    <style>
      .wrap {
        white-space: normal !important;
        word-break: break-word !important;
        overflow-wrap: anywhere !important;
        line-height: 1.25;
      }
      .mono {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 0.85rem;
      }
      .chip {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.8rem;
        border: 1px solid rgba(255,255,255,0.12);
      }
      .chip-red { background: rgba(255,0,0,0.12); border-color: rgba(255,0,0,0.25); }
      .chip-amber { background: rgba(255,165,0,0.14); border-color: rgba(255,165,0,0.25); }
      .chip-blue { background: rgba(0,153,255,0.14); border-color: rgba(0,153,255,0.25); }
      .chip-green { background: rgba(0,255,120,0.10); border-color: rgba(0,255,120,0.20); }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SLA / Handoff config (mock)
# =========================================================
SLA_MINUTES = {
    "Pending": 15,
    "Escalated": 10,
}

def parse_dt(s: str):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

def sla_state(conv: dict):
    """
    return: ("OK"|"DUE"|"BREACH", elapsed_min, sla_min)
    """
    status = conv.get("status")
    if status == "Resolved":
        return ("OK", 0, None)

    sla_min = SLA_MINUTES.get(status)
    if not sla_min:
        return ("OK", 0, None)

    created = parse_dt(conv["created_at"])
    elapsed_min = int((datetime.now() - created).total_seconds() // 60)

    if elapsed_min >= sla_min:
        return ("BREACH", elapsed_min, sla_min)
    elif elapsed_min >= int(sla_min * 0.8):
        return ("DUE", elapsed_min, sla_min)
    else:
        return ("OK", elapsed_min, sla_min)

def sla_badge(state: str):
    if state == "BREACH":
        return "🔥 SLA Breach"
    if state == "DUE":
        return "⏳ Near SLA"
    return "✅ OK"

def attention_chip(status: str, sla_state_str: str):
    # เด่นๆ สำหรับ handoff / SLA
    if status == "Escalated":
        return '<span class="chip chip-blue">📣 HANDOFF</span>'
    if sla_state_str == "BREACH":
        return '<span class="chip chip-red">🔥 SLA BREACH</span>'
    if sla_state_str == "DUE":
        return '<span class="chip chip-amber">⏳ NEAR SLA</span>'
    return '<span class="chip chip-green">✅ OK</span>'

# =========================================================
# Mock image generator (no external files)
# =========================================================
def make_mock_image(text: str, w=860, h=480):
    if Image is None:
        return None
    img = Image.new("RGB", (w, h), (245, 246, 248))
    d = ImageDraw.Draw(img)

    # header bar
    d.rectangle([0, 0, w, 70], fill=(30, 41, 59))
    d.text((20, 20), "Mock Attachment", fill=(255, 255, 255))

    # body
    d.rectangle([20, 95, w - 20, h - 20], outline=(160, 160, 160), width=2)
    d.text((40, 120), text, fill=(20, 20, 20))
    d.text((40, 160), f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(90, 90, 90))

    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

# =========================================================
# Mock: conversation messages
# =========================================================
def mock_conversation_messages(intent: str):
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
            ("assistant", "รับทราบครับ (mock) ถ้าต่อ API/DB จะเช็คสต็อกแบบเรียลไทม์ให้ได้เลย"),
        ],
        "ถามการจัดส่ง": [
            ("user", "ส่งไปต่างจังหวัดใช้เวลานานไหม"),
            ("assistant", "ได้ครับ (mock) ปกติขึ้นกับบริษัทขนส่งและพื้นที่ปลายทางครับ"),
            ("user", "เชียงใหม่ครับ"),
            ("assistant", "โอเคครับ (mock) ถ้าต่อจริงจะคำนวณ ETA + ค่าส่งให้ตามตะกร้าสินค้าครับ"),
        ],
        "เคลม/ประกัน": [
            ("user", "ขอเคลมการ์ดจอ เปิดไม่ติดครับ"),
            ("assistant", "รับทราบครับ (mock) รบกวนกรอกข้อมูล: รุ่นสินค้า / เลขออเดอร์ / Serial (ถ้ามี) + แนบรูปหลักฐาน/อาการครับ"),
            ("user", "รุ่น ASUS Dual RTX 4060 / ใบเสร็จมี / Serial มีครับ"),
            ("assistant", "ขอบคุณครับ (mock) ผมจะส่งต่อให้เจ้าหน้าที่ตรวจสอบเงื่อนไขประกันให้ทันที (handoff)"),
        ],
    }
    base = templates.get(intent, [
        ("user", "ขอรายละเอียดเพิ่มเติมหน่อย"),
        ("assistant", "ได้ครับ (mock) ถ้าต่อระบบจริงจะดึงข้อมูลให้ครบถ้วนครับ"),
    ])
    return [{"role": r, "content": c} for r, c in base]

# =========================================================
# Mock: fetch data
# =========================================================
def mock_metabase_fetch():
    time.sleep(0.5)

    today = datetime.now().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    total_chats = random.randint(120, 520)
    total_users = random.randint(35, 160)
    avg_resp_sec = round(random.uniform(1.8, 6.5), 2)
    csat = round(random.uniform(3.6, 4.8), 2)

    chats_series = [{"date": d.strftime("%Y-%m-%d"), "chats": random.randint(10, 110)} for d in days]

    intents = [
        ("เช็คราคา", random.randint(20, 140)),
        ("เทียบสเปค", random.randint(20, 140)),
        ("ดูสต็อก", random.randint(20, 140)),
        ("ถามการจัดส่ง", random.randint(10, 90)),
        ("เคลม/ประกัน", random.randint(5, 70)),
    ]
    intents.sort(key=lambda x: x[1], reverse=True)

    names = ["Somchai", "Anan", "Mint", "Ploy", "Beam", "Tee", "Nina", "Palm", "Boss", "May"]
    snippets = [
        "ขอราคา RTX 4060 หน่อย",
        "ช่วยเทียบ i5 กับ i7 ให้ที ขอแบบคุ้มๆ สำหรับทำงาน + เล่นเกม",
        "มีของพร้อมส่งไหม อยากได้ MacBook Air M2 16GB",
        "ส่งไปต่างจังหวัดใช้เวลานานไหม ขอ ETA + ค่าส่ง",
        "ขอเคลมการ์ดจอ เปิดไม่ติด แนบใบเสร็จ + รูปอาการ",
        "แนะนำโน้ตบุ๊คงบ 25k ใช้เรียน + ทำงาน",
    ]

    recents = []
    conversations = {}

    # --- สร้างเคสเคลม/ประกัน “บังคับมี 1 เคส” และทำให้เด่น + handoff
    claim_id = f"CNV-{datetime.now().strftime('%y%m%d')}-CLM001"
    claim_created = datetime.now() - timedelta(minutes=18)  # ทำให้ใกล้/เกิน SLA ได้ง่าย
    claim_status = "Escalated"  # ต้อง handoff แน่นอน
    claim_customer = random.choice(names)

    claim_row = {
        "id": claim_id,
        "time": claim_created.strftime("%H:%M"),
        "customer": claim_customer,
        "intent": "เคลม/ประกัน",
        "status": claim_status,
        "snippet": "ขอเคลมการ์ดจอ เปิดไม่ติด แนบใบเสร็จ + รูปอาการ",
    }
    recents.append(claim_row)

    conversations[claim_id] = {
        "id": claim_id,
        "customer": claim_customer,
        "intent": "เคลม/ประกัน",
        "status": claim_status,
        "created_at": claim_created.strftime("%Y-%m-%d %H:%M:%S"),
        "channel": "Web Chat",  # channel เดียว
        "messages": mock_conversation_messages("เคลม/ประกัน"),
        "ai_summary": None,
        "handoff_at": (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),
        "attachments": [
            {"name": "receipt_mock.png", "bytes": make_mock_image("Receipt / Invoice (Mock)\nOrder: OD-889911\nTotal: 12,990 THB")},
            {"name": "issue_mock.png", "bytes": make_mock_image("Product Issue (Mock)\nSymptom: No power / No display\nCustomer reported: เปิดไม่ติด")},
        ],
    }

    # --- สร้างเคสอื่นๆ ลดจำนวนลง: รวมทั้งหมด 8 เคส (1 claim + 7 random)
    for idx in range(7):
        conv_id = f"CNV-{datetime.now().strftime('%y%m%d')}-{idx+1:03d}"
        intent = random.choice([i[0] for i in intents if i[0] != "เคลม/ประกัน"])
        created_at = datetime.now() - timedelta(minutes=random.randint(1, 240))

        # bias
        status = random.choices(
            ["Resolved", "Escalated", "Pending"],
            weights=[0.45, 0.20, 0.35],
            k=1
        )[0]

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
            "channel": "Web Chat",  # channel เดียว
            "messages": mock_conversation_messages(intent),
            "ai_summary": None,
            "handoff_at": None,
            "attachments": [],
        }

    # sort by time desc
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

# =========================================================
# AI Summary (mock) — ตัด Recommended next question ออก
# =========================================================
def ai_summary_mock(conv: dict) -> dict:
    msgs = conv.get("messages", [])
    user_msgs = [m["content"] for m in msgs if m.get("role") == "user"]
    last_user = user_msgs[-1] if user_msgs else ""

    t = (last_user or "").lower()
    if any(k in t for k in ["เทียบ", "สเปค", "i5", "i7", "spec"]):
        intent = "เทียบสเปค"
        action = "สรุปเป็นตารางเทียบ + แนะนำ 2-3 รุ่นที่คุ้มสุดตามงบ"
    elif any(k in t for k in ["ราคา", "price"]):
        intent = "เช็คราคา"
        action = "แจ้งราคา + โปร/ผ่อน (ถ้ามี) + ตัวเลือกใกล้เคียง"
    elif any(k in t for k in ["สต็อก", "stock", "มีของ"]):
        intent = "ดูสต็อก"
        action = "เช็คสต็อก + แจ้ง ETA + สาขา/การจัดส่ง"
    elif any(k in t for k in ["ส่ง", "delivery", "ขนส่ง"]):
        intent = "ถามการจัดส่ง"
        action = "แจ้งตัวเลือกขนส่ง + ETA + ค่าส่ง"
    elif any(k in t for k in ["เคลม", "ประกัน", "warranty", "refund"]):
        intent = "เคลม/ประกัน"
        action = "ตรวจสอบเงื่อนไขประกัน + ขอข้อมูล/หลักฐาน + handoff ให้เจ้าหน้าที่"
    else:
        intent = conv.get("intent", "ทั่วไป")
        action = "ขอรายละเอียดเพิ่มแล้วตอบให้ตรง"

    return {
        "intent": intent,
        "customer_goal": last_user or "(ไม่พบข้อความจากลูกค้า)",
        "what_happened": "ลูกค้าสอบถาม/ขอคำแนะนำ และระบบบอทตอบเบื้องต้น (mock)",
        "recommended_action": action,
        "confidence": "Medium (mock)",
    }

# =========================================================
# UI
# =========================================================
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

if "open_dialog" not in st.session_state:
    st.session_state.open_dialog = False

data = st.session_state.mb_data

# ------------------------------
# KPIs
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
    q = st.text_input("Search (customer/snippet/id)", placeholder="พิมพ์คำค้น...")

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
# SLA banner summary
# ------------------------------
breach_ids = []
handoff_ids = []
for r in filtered:
    conv = data["conversations"].get(r["id"])
    if not conv:
        continue
    state, _, _ = sla_state(conv)
    if state == "BREACH":
        breach_ids.append(r["id"])
    if conv.get("status") == "Escalated":
        handoff_ids.append(r["id"])

if breach_ids:
    st.error(
        "🔥 SLA Breach: "
        + ", ".join(breach_ids[:3])
        + ("..." if len(breach_ids) > 3 else "")
    )

if handoff_ids:
    st.warning(
        "📣 เคสที่ต้อง Handoff: "
        + ", ".join(handoff_ids[:3])
        + ("..." if len(handoff_ids) > 3 else "")
    )

# ------------------------------
# Table-like list
# - เพิ่ม Attention ให้เด่น
# - wrap id/snippet
# ------------------------------
header = st.columns([0.9, 1.7, 1.1, 1.1, 1.2, 1.5, 3.0, 0.9])
header[0].markdown("**Time**")
header[1].markdown("**Conversation ID**")
header[2].markdown("**Customer**")
header[3].markdown("**Status**")
header[4].markdown("**Attention**")
header[5].markdown("**SLA**")
header[6].markdown("**Snippet**")
header[7].markdown("**Action**")

for row in filtered:
    conv = data["conversations"].get(row["id"])
    state, elapsed, sla_min = sla_state(conv) if conv else ("OK", 0, None)

    cols = st.columns([0.9, 1.7, 1.1, 1.1, 1.2, 1.5, 3.0, 0.9])

    cols[0].write(row["time"])

    # wrap id (แทน st.code ที่มันตัด)
    cols[1].markdown(
        f'<div class="wrap mono">{row["id"]}</div>',
        unsafe_allow_html=True
    )

    cols[2].write(row["customer"])

    # ทำ status เด่นขึ้น
    if row["status"] == "Escalated":
        cols[3].markdown("**⚠ Escalated**")
    elif row["status"] == "Pending":
        cols[3].markdown("**⏳ Pending**")
    else:
        cols[3].markdown("✅ Resolved")

    # attention chip
    cols[4].markdown(attention_chip(row["status"], state), unsafe_allow_html=True)

    # SLA text
    if sla_min:
        cols[5].markdown(f"{sla_badge(state)}<br/><span class='mono'>({elapsed}/{sla_min} min)</span>", unsafe_allow_html=True)
    else:
        cols[5].write(sla_badge(state))

    # wrap snippet ให้ลงบรรทัดใหม่
    cols[6].markdown(
        f'<div class="wrap">[{row["intent"]}] {row["snippet"]}</div>',
        unsafe_allow_html=True
    )

    if cols[7].button("👁 View", key=f"view_{row['id']}"):
        st.session_state.selected_conv_id = row["id"]
        st.session_state.open_dialog = True
        st.rerun()

# =========================================================
# Popup Dialog: Conversation detail
# =========================================================
@st.dialog("💬 Chat Detail", width="large")
def show_conversation_dialog(conv_id: str):
    conv = data["conversations"].get(conv_id)
    if conv is None:
        st.warning("ไม่พบข้อมูลแชทนี้ (อาจ refresh แล้วข้อมูลเปลี่ยน)")
        return

    # SLA / Handoff notifications
    state, elapsed, sla_min = sla_state(conv)
    if conv.get("status") == "Escalated":
        st.toast(f"📣 HANDOFF: {conv_id}", icon="📣")
        st.warning("📣 เคสนี้ถูกส่งต่อให้เจ้าหน้าที่ (handoff)")

    if state == "BREACH":
        st.toast(f"🔥 SLA Breach: {conv_id} ({elapsed}/{sla_min} นาที)", icon="🔥")
        st.error(f"SLA Breach: ผ่านไป {elapsed} นาที (SLA {sla_min} นาที)")
    elif state == "DUE":
        st.toast(f"⏳ ใกล้ครบ SLA: {conv_id} ({elapsed}/{sla_min} นาที)", icon="⏳")
        st.warning(f"ใกล้ครบ SLA: ผ่านไป {elapsed} นาที (SLA {sla_min} นาที)")

    if conv.get("handoff_at"):
        st.info(f"🕒 Handoff at: {conv['handoff_at']}")

    # Header (แก้การตัดข้อความยาว)
    st.markdown(f"### <div class='wrap mono'>{conv['id']}</div>", unsafe_allow_html=True)

    info1, info2, info3, info4 = st.columns([1.4, 1.4, 1.2, 1.6])
    info1.metric("Customer", conv["customer"])
    info2.metric("Status", conv["status"])
    info3.metric("Intent", conv["intent"])
    info4.metric("Channel", conv["channel"])
    st.caption(f"Created at: {conv['created_at']}")

    # Attachments (เคลม/ประกันจะมี)
    if conv.get("attachments"):
        st.markdown("#### 📎 Attachments (mock)")
        for att in conv["attachments"]:
            st.write(f"- {att.get('name','attachment')}")
            if att.get("bytes") is not None:
                st.image(att["bytes"], use_container_width=True)
            else:
                st.info("(ไม่มีภาพ mock ในระบบ)")

    # Transcript
    st.markdown("#### Transcript")
    for m in conv["messages"]:
        role = m["role"]
        if role == "admin":
            bubble_role = "assistant"
            label = "🧑‍💼 Admin"
        else:
            bubble_role = "user" if role == "user" else "assistant"
            label = None

        with st.chat_message(bubble_role):
            if label:
                st.caption(label)
            st.markdown(m["content"])

    # AI Summary (ตัด Recommended next question ออกแล้ว)
    st.markdown("---")
    st.subheader("🧠 AI Summary (mock)")
    if conv.get("ai_summary") is None:
        conv["ai_summary"] = ai_summary_mock(conv)
        data["conversations"][conv_id] = conv

    s = conv["ai_summary"]
    a, b, c = st.columns([1.2, 2.2, 1])
    a.metric("Intent", s["intent"])
    c.metric("Confidence", s["confidence"])
    b.write("**Customer goal (ล่าสุด):**")
    b.write(s["customer_goal"])

    st.write("**What happened:**")
    st.write(s["what_happened"])

    st.write("**Recommended action:**")
    st.success(s["recommended_action"])

    # Admin Reply (ตัดปุ่ม use suggested ออก)
    st.markdown("---")
    st.subheader("🧑‍💼 Admin Reply")
    with st.form(key=f"reply_form_{conv_id}", clear_on_submit=True):
        reply_text = st.text_area(
            "พิมพ์ข้อความตอบลูกค้า...",
            height=120,
            placeholder="เช่น รับเคสแล้วครับ รบกวนส่งเลขออเดอร์/Serial + รูปใบเสร็จเพิ่มเติมได้ไหมครับ"
        )
        send = st.form_submit_button("📨 Send reply")

        if send:
            if not reply_text.strip():
                st.warning("กรุณาพิมพ์ข้อความก่อนส่ง")
            else:
                conv["messages"].append({
                    "role": "admin",
                    "content": reply_text.strip(),
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # update snippet
                for r in data["recents"]:
                    if r["id"] == conv_id:
                        r["snippet"] = reply_text.strip()[:120]
                        break

                data["conversations"][conv_id] = conv
                st.toast("✅ ส่งข้อความแล้ว (mock)", icon="✅")
                st.success("ส่งข้อความแล้ว (mock) ✅")
                st.rerun()

    # Actions
    st.markdown("---")
    st.subheader("Actions (mock)")
    a1, a2 = st.columns(2)

    if a1.button("✅ Mark Resolved (mock)"):
        conv["status"] = "Resolved"
        data["conversations"][conv_id] = conv
        for r in data["recents"]:
            if r["id"] == conv_id:
                r["status"] = "Resolved"
                break
        st.toast("✅ ปิดเคสแล้ว (Resolved)", icon="✅")
        st.rerun()

    if a2.button("⚠ Escalate to Human (mock)"):
        conv["status"] = "Escalated"
        conv["handoff_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["conversations"][conv_id] = conv
        for r in data["recents"]:
            if r["id"] == conv_id:
                r["status"] = "Escalated"
                break
        st.toast(f"📣 Handoff ส่งต่อแล้ว: {conv_id}", icon="📣")
        st.rerun()

# Trigger dialog
if st.session_state.open_dialog and st.session_state.selected_conv_id:
    show_conversation_dialog(st.session_state.selected_conv_id)
    st.session_state.open_dialog = False