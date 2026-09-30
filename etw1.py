import os
import json
import base64
import requests
from datetime import datetime
import streamlit as st

# ==============================================================================
# SAYFA VE TEMA YAPILANDIRMASI
# ==============================================================================
st.set_page_config(
    page_title="eTwinning Sohbet Botu",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Anahtarı (Streamlit Secrets üzerinden veya yerel env'den okunur)
API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
AKTIF_MODEL = "gemini-3.1-flash-lite"
GUNLUK_TOKEN_LIMITI = 150000

# CSS: eTwinning Sarı-Mavi Kurumsal Tema & Maskot
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #002B54 0%, #001A33 100%);
        color: #F8FAFC;
    }
    header, .stDeployButton { display: none !important; }
    
    .main-title {
        color: #FFCC00;
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 2px;
    }
    .sub-title {
        color: #CBD5E1;
        font-size: 13px;
        margin-bottom: 20px;
    }
    .mascot-container {
        display: flex;
        align-items: center;
        gap: 15px;
        background: rgba(0, 51, 102, 0.6);
        border: 2px solid #FFCC00;
        border-radius: 16px;
        padding: 12px 18px;
        margin-bottom: 18px;
    }
    .mascot-img {
        width: 75px;
        height: 75px;
        border-radius: 50%;
        border: 2px solid #FFCC00;
        object-fit: cover;
    }
    .stChatMessage {
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BİLGİ BANKASI VE MODEL
# ==============================================================================
ETWINNING_KORPUSU = """
T.C. MİLLÎ EĞİTİM BAKANLIĞI - eTWINNING & ESEP RESMİ ÇALIŞMA ESASLARI VE KALİTE ETİKETİ RUBRİĞİ:
1. PROJE FİKRİ VE ORTAK ÜRÜN REHBERLİĞİ:
- Öğretmenler projelerini sunduğunda onlara somut ortak ürün fikirleri (e-kitap, sanal sergi, dijital poster, ortak video, interaktif oyunlar) önerilir.
2. KALİTE ETİKETİ 5 ANA RUBRİK KRİTERİ:
- 1. Pedagojik Yenilik, 2. Müfredat Entegrasyonu, 3. Ortaklar Arası İşbirliği (karma takımlar), 4. Teknoloji Kullanımı ve e-Güvenlik, 5. Sonuçlar, Etki ve Belgeleme.
3. GÜNCEL KURALLAR:
- Türkiye ortaklık sınırı: En fazla 6 okul, okul başına en fazla 4 ortak (toplamda ~20 ortak).
- Üyelik tipi mutlaka "Teacher" olmalıdır.
"""

def gemini_cevap_uret(soru, gecmis):
    if not API_KEY:
        return "⚠️ Lütfen Gemini API anahtarınızı Streamlit Secrets alanına ekleyin."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{AKTIF_MODEL}:generateContent?key={API_KEY}"
    gecmis_metni = "".join([f"{m['role']}: {m['content']}\n" for m in gecmis[-3:]])

    system_instruction = (
        "Sen Millî Eğitim Bakanlığı eTwinning ve ESEP resmi akıllı koç yapay zekâ asistanısın. Adın 'Twin'. "
        "Karşındaki öğretmenlere 'Hocam' veya 'Değerli Öğretmenim' diyerek saygılı, net ve ilham verici rehberlik et.\n"
        "Kalite Etiketi rubrikine uygun eksikleri belirt, ortak ürün fikirleri öner.\n"
        f"KAYNAK:\n{ETWINNING_KORPUSU}\n"
    )

    prompt = f"{system_instruction}\n{gecmis_metni}\nKullanıcı: {soru}\nTwin:"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 800}
    }

    try:
        r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
        if r.status_code == 200:
            veri = r.json()
            cevap = veri["candidates"][0]["content"]["parts"][0]["text"].strip()
            harcanan = veri.get("usageMetadata", {}).get("totalTokenCount", 300)
            st.session_state["toplam_token"] += harcanan
            return cevap
        return f"Hata oluştu (Kod: {r.status_code})."
    except Exception as e:
        return f"Bağlantı hatası: {str(e)}"

# ==============================================================================
# OTURUM DURUMU (SESSION STATE)
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Merhaba Değerli Öğretmenim! 👋 Ben **Twin**, eTwinning koçunuz. Proje fikrinizi bana anlatın; Kalite Etiketi kriterlerine göre birlikte inceleyelim!"
    }]
if "toplam_token" not in st.session_state:
    st.session_state.toplam_token = 0

# Maskot base64 dönüştürücü
maskot_b64 = ""
if os.path.exists("twin.maskot.jpg"):
    with open("twin.maskot.jpg", "rb") as img_f:
        maskot_b64 = base64.b64encode(img_f.read()).decode()

# ==============================================================================
# YAN PANEL (SIDEBAR) - ÇEVİRİ & KOTA TAKİBİ
# ==============================================================================
with st.sidebar:
    st.markdown("### 📊 Sistem Durumu")
    st.metric(label="Harcanan Token", value=f"{st.session_state.toplam_token:,} / {GUNLUK_TOKEN_LIMITI:,}")
    
    st.markdown("---")
    st.markdown("### 🌍 Akıllı Çift Yönlü Çevirmen")
    st.caption("Türkçe yazın İngilizce olsun, İngilizce yazın Türkçe olsun!")
    cevir_metni = st.text_area("Çevrilecek metni yazın:", height=100)
    
    if st.button("Çevir ⚡", use_container_width=True):
        if cevir_metni.strip():
            with st.spinner("Çevriliyor..."):
                prompt = f"Detect language (TR/EN) and translate to the other language. Return ONLY translation: {cevir_metni}"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{AKTIF_MODEL}:generateContent?key={API_KEY}"
                res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
                if res.status_code == 200:
                    sonuc = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    st.success(sonuc)
        else:
            st.warning("Lütfen bir metin girin.")

# ==============================================================================
# ANA PANEL - SOHBET ALANI
# ==============================================================================
maskot_html = f'<img src="data:image/jpeg;base64,{maskot_b64}" class="mascot-img">' if maskot_b64 else '🤖'

st.markdown(f"""
<div class="mascot-container">
    {maskot_html}
    <div>
        <div class="main-title">eTwinning Sohbet Botu</div>
        <div class="sub-title">T.C. Millî Eğitim Bakanlığı • eTwinning & ESEP Proje Asistanı</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Hızlı Sorular (Chips)
col1, col2, col3 = st.columns(3)
hizli_soru = None
if col1.button("💡 Ortak Ürün Fikirleri", use_container_width=True):
    hizli_soru = "Projem için yaratıcı ortak ürün fikirleri verir misin?"
if col2.button("🏆 Rubrik Kriterleri", use_container_width=True):
    hizli_soru = "Kalite Etiketi rubrikindeki 5 ana kriteri açıklar mısın?"
if col3.button("📌 Yeni Ortaklık Sınırı", use_container_width=True):
    hizli_soru = "Türkiye ortaklık sınırındaki yeni kurallar nelerdir?"

# Mesajları Ekrana Bas
for msg in st.session_state.messages:
    avatar = "twin.maskot.jpg" if msg["role"] == "assistant" and os.path.exists("twin.maskot.jpg") else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Giriş Kontrolü
prompt = st.chat_input("Projenizi anlatın veya sorunuzu yazın...")
if hizli_soru:
    prompt = hizli_soru

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="twin.maskot.jpg" if os.path.exists("twin.maskot.jpg") else None):
        with st.spinner("Twin inceliyor..."):
            cevap = gemini_cevap_uret(prompt, st.session_state.messages)
            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})