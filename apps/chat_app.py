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

# ---------- Sidebar (settings mock) ----------
with st.sidebar:
    st.subheader("⚙️ Settings (mock)")
    tone = st.selectbox("โทนการตอบ", ["สุภาพ", "เป็นกันเอง", "สั้นๆ"], index=1)
    shop = st.selectbox("ร้าน", ["Demo Shop", "IT Shop A", "IT Shop B"], index=0)
    st.markdown("---")
    st.write("**Tip:** ตอนนี้เป็น mockup — ปุ่ม/ฟีเจอร์บางอย่างเป็นการจำลอง")

# ---------- Helper: fake bot reply ----------
def mock_reply(user_text: str) -> str:
    user_text_low = user_text.lower()

    if any(k in user_text_low for k in ["ราคา", "price"]):
        return "ได้เลย! จะดึงราคาสินค้ามาให้ได้ทันที"
    if any(k in user_text_low for k in ["สเปค", "spec"]):
        return "รับทราบ! จะเทียบสเปคให้แบบตาราง + แนะนำตัวเลือกที่คุ้มสุด"
    if any(k in user_text_low for k in ["ส่ง", "delivery", "ขนส่ง"]):
        return "เรื่องจัดส่ง : จะโชว์ตัวเลือกขนส่ง/ค่าจัดส่ง/เวลาถึงโดยประมาณได้"
    return "โอเคครับ จะตอบละเอียดขึ้นตามนโยบายร้าน + ข้อมูลสินค้าครับ"

# ---------- Render chat history ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Quick replies ----------
st.markdown("### ⚡ Quick replies")
cols = st.columns(4)
quick_list = ["เช็คราคา", "เทียบสเปค", "ดูสต็อก", "ถามการจัดส่ง"]
for i, q in enumerate(quick_list):
    if cols[i].button(q, use_container_width=True):
        st.session_state.selected_quick = q

# ---------- Chat input ----------
default_input = st.session_state.selected_quick or ""
prompt = st.chat_input("พิมพ์ข้อความ...", key="chat_input")

# ถ้ากด quick reply ให้ส่งเหมือนผู้ใช้พิมพ์
user_text = prompt if prompt else st.session_state.selected_quick
if user_text:
    st.session_state.selected_quick = None

    # show user message
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # fake typing
    with st.chat_message("assistant"):
        with st.spinner("กำลังพิมพ์..."):
            time.sleep(0.6)
        reply = mock_reply(user_text)

        # apply tone mock
        if tone == "สั้นๆ":
            reply = reply.split("—")[0].strip()
        elif tone == "สุภาพ":
            reply = reply.replace("ครับ", "ครับผม").replace("โอเค", "รับทราบ")

        st.markdown(reply)
        st.caption(f"🕒 {datetime.now().strftime('%H:%M')} • ร้าน: {shop}")

    st.session_state.messages.append({"role": "assistant", "content": reply})