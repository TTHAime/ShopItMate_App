import streamlit as st
import time
from datetime import datetime

st.set_page_config(page_title="Mock Chatbot", page_icon="🤖", layout="centered")
st.title("🤖 ShopMate")

# ---------- Session State ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "สวัสดี! อยากให้ช่วยเรื่องอะไรดี 😊"}
    ]

if "selected_quick" not in st.session_state:
    st.session_state.selected_quick = None

# โหมดฟอร์มเคลม + สถานะการส่ง
if "show_claim_form" not in st.session_state:
    st.session_state.show_claim_form = False

if "claim_submitted" not in st.session_state:
    st.session_state.claim_submitted = False

# เก็บไฟล์แนบล่าสุด (optional) เพื่อโชว์ preview หลัง submit
if "last_attachments" not in st.session_state:
    st.session_state.last_attachments = []

# ---------- Sidebar (settings mock) ----------
with st.sidebar:
    st.subheader("⚙️ Settings (mock)")
    tone = st.selectbox("โทนการตอบ", ["สุภาพ", "เป็นกันเอง", "สั้นๆ"], index=1)
    shop = st.selectbox("ร้าน", ["Demo Shop", "IT Shop A", "IT Shop B"], index=0)
    st.markdown("---")
    st.write("**Tip:** ตอนนี้เป็น mockup — ปุ่ม/ฟีเจอร์บางอย่างเป็นการจำลอง")

# ---------- Helper: fake bot reply ----------
def mock_reply(user_text: str) -> str:
    user_text_low = (user_text or "").lower()
    if any(k in user_text_low for k in [
        "ข้อมูลสินค้า", "รายละเอียด", "สเปคโดยรวม", "รุ่น", "มีของไหม", "สต็อก",
        "สินค้า", "product", "info", "detail", "stock", "available"
    ]):
        return (
            "ได้เลยครับ ✅\n\n"
            "- ชื่อ/รุ่นสินค้า: \n"
            "- สถานะสต็อก: มีของ / สาขาใกล้เคียง\n"
            "- ไฮไลต์สเปค: \n"
            "- การรับประกัน: \n"
            "- อุปกรณ์ในกล่อง: \n\n"
            "รบกวนบอก **ยี่ห้อ/รุ่น** ที่สนใจ (หรือส่งลิงก์สินค้า) เดี๋ยวผมสรุปให้แบบอ่านง่ายครับ"
        )
    if any(k in user_text_low for k in ["ราคา", "price"]):
        return "ได้เลย! จะดึงราคาสินค้ามาให้ได้ทันที"
    if any(k in user_text_low for k in ["เทียบสเปค", "เปรียบเทียบ", "compare", "spec"]):
        return (
            "ได้เลยครับ ✅ นี่คือตารางเทียบสเปค (mock)\n\n"
            "| รุ่น | VRAM | CUDA Cores | Boost Clock | TGP | พอร์ต | เหมาะกับ |\n"
            "|---|---:|---:|---:|---:|---|---|\n"
            "| RTX 4060 (Mock A) | 8GB GDDR6 | 3072 | 2460 MHz | 115W | HDMI 2.1 + DP 1.4a | FHD 144Hz / งานทั่วไป |\n"
            "| RTX 4060 Ti (Mock B) | 8GB GDDR6 | 4352 | 2535 MHz | 160W | HDMI 2.1 + DP 1.4a | QHD / เกม AAA |\n"
            "| RTX 4070 (Mock C) | 12GB GDDR6X | 5888 | 2475 MHz | 200W | HDMI 2.1 + DP 1.4a | QHD/4K เบาๆ / สตรีม |\n\n"
            "**สรุปแนะนำ (mock):**\n"
            "- เน้นคุ้มค่าเล่น FHD → **4060**\n"
            "- อยากลื่น QHD มากขึ้น → **4060 Ti**\n"
            "- เผื่ออนาคต + VRAM มากขึ้น → **4070**\n\n"
            "ถ้าบอกงบ/เกมที่เล่น/จอ (FHD/QHD/4K) เดี๋ยวผมปรับตารางให้ตรงเคสครับ"
        )
    if any(k in user_text_low for k in ["ส่ง", "delivery", "ขนส่ง"]):
        return "เรื่องจัดส่ง: จะโชว์ตัวเลือกขนส่ง/ค่าจัดส่ง/เวลาถึงโดยประมาณได้"
    if any(k in user_text_low for k in ["เคลม", "ประกัน", "warranty", "claim"]):
        return "ได้เลยครับ รบกวนกรอกฟอร์มข้อมูลเคลม/ประกันด้านล่าง และแนบรูป (ถ้ามี) เพื่อให้ตรวจสอบได้เร็วขึ้น ✅"
    return "โอเคครับ จะตอบละเอียดขึ้นตามนโยบายร้าน + ข้อมูลสินค้าครับ"

def apply_tone(reply: str, tone: str) -> str:
    if tone == "สั้นๆ":
        return reply.split("—")[0].strip()
    if tone == "สุภาพ":
        return reply.replace("ครับ", "ครับผม").replace("โอเค", "รับทราบ")
    return reply

def is_claim_intent(text: str) -> bool:
    t = (text or "").lower()
    return (text == "เคลม/ประกัน") or any(k in t for k in ["เคลม", "ประกัน", "warranty", "claim"])

# ---------- Render chat history ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Quick replies ----------
st.markdown("### ⚡ Quick replies")
cols = st.columns(4)
quick_list = ["ข้อมูลสินค้า", "เทียบสเปค", "เคลม/ประกัน", "การจัดส่ง"]
for i, q in enumerate(quick_list):
    if cols[i].button(q, use_container_width=True):
        st.session_state.selected_quick = q

# ---------- Chat input ----------
prompt = st.chat_input("พิมพ์ข้อความ...", key="chat_input")
user_text = prompt if prompt else st.session_state.selected_quick

# ถ้ามีข้อความเข้า (พิมพ์หรือกด quick)
if user_text:
    st.session_state.selected_quick = None

    # show user message
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # assistant reply
    with st.chat_message("assistant"):
        with st.spinner("กำลังพิมพ์..."):
            time.sleep(0.6)

        reply = apply_tone(mock_reply(user_text), tone)
        st.markdown(reply)
        st.caption(f"🕒 {datetime.now().strftime('%H:%M')} • ร้าน: {shop}")

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # ถ้าเป็นเคลม/ประกัน -> เปิดฟอร์ม
    if is_claim_intent(user_text):
        st.session_state.show_claim_form = True
        st.session_state.claim_submitted = False
        st.session_state.last_attachments = []
        st.rerun()

# ---------- Claim/Warranty Form ----------
if st.session_state.show_claim_form and not st.session_state.claim_submitted:
    st.markdown("---")
    st.subheader("🧾 ฟอร์มเคลม/ประกัน")

    with st.form("claim_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input("ชื่อ-นามสกุล *")
            phone = st.text_input("เบอร์โทร *", placeholder="0xx-xxx-xxxx")
            email = st.text_input("อีเมล (ถ้ามี)")

        with col2:
            order_id = st.text_input("เลขออเดอร์/ใบเสร็จ (ถ้ามี)")
            product_name = st.text_input("ชื่อสินค้า/รุ่น *", placeholder="เช่น ASUS Dual RTX 4060")
            serial_no = st.text_input("Serial Number (ถ้ามี)")

        problem = st.text_area(
            "อาการ/ปัญหาที่พบ *",
            height=120,
            placeholder="อธิบายอาการโดยย่อ เช่น เปิดไม่ติด, มีจอฟ้า, พัดลมดังผิดปกติ"
        )

        purchase_date = st.date_input("วันที่ซื้อ (ถ้าจำได้)", value=None)
        has_receipt = st.radio("มีใบเสร็จ/หลักฐานการซื้อไหม *", ["มี", "ไม่มี"], horizontal=True)

        attachments = st.file_uploader(
            "แนบรูป/หลักฐาน (สูงสุด 3 รูป) เช่น ใบเสร็จ, อาการสินค้า",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True
        )

        # limit count
        if attachments and len(attachments) > 3:
            st.warning("แนบได้สูงสุด 3 รูปนะครับ (ตอนส่งจะรับแค่ 3 รูปแรก)")

        submitted = st.form_submit_button("✅ ส่งข้อมูลเคลม")

    if submitted:
        # validate required fields
        if not full_name.strip() or not phone.strip() or not product_name.strip() or not problem.strip():
            st.error("กรุณากรอกช่องที่มี * ให้ครบก่อนส่ง")
        else:
            # keep only first 3 files
            safe_attachments = attachments[:3] if attachments else []
            st.session_state.last_attachments = safe_attachments

            # build summary
            attach_names = ", ".join([f.name for f in safe_attachments]) if safe_attachments else "-"

            summary = (
                "📌 รับข้อมูลเคลม/ประกันแล้วครับ ✅\n\n"
                f"**ชื่อ:** {full_name}\n"
                f"**โทร:** {phone}\n"
                f"**อีเมล:** {email or '-'}\n"
                f"**สินค้า/รุ่น:** {product_name}\n"
                f"**Serial:** {serial_no or '-'}\n"
                f"**Order/ใบเสร็จ:** {order_id or '-'}\n"
                f"**วันที่ซื้อ:** {purchase_date.strftime('%Y-%m-%d') if purchase_date else '-'}\n"
                f"**มีหลักฐานการซื้อ:** {has_receipt}\n"
                f"**อาการ:** {problem}\n"
                f"**ไฟล์แนบ:** {attach_names}\n\n"
                "ขั้นต่อไป: เจ้าหน้าที่จะตรวจสอบเงื่อนไขประกัน/แนวทางดำเนินการ และติดต่อกลับเร็วที่สุดครับ"
            )

            # close form and add message
            st.session_state.claim_submitted = True
            st.session_state.show_claim_form = False
            st.session_state.messages.append({"role": "assistant", "content": summary})

            st.toast("✅ ส่งข้อมูลเคลมเรียบร้อย (mock)", icon="✅")
            st.rerun()

# ---------- Show attachment preview after submit (optional) ----------
if st.session_state.claim_submitted and st.session_state.last_attachments:
    st.markdown("---")
    st.subheader("📎 รูปที่แนบ (Preview)")

    for f in st.session_state.last_attachments:
        st.write(f"- {f.name} ({f.size/1024:.1f} KB)")
        st.image(f, use_container_width=True)