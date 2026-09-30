import os
import base64
import requests
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

API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
AKTIF_MODEL = "gemini-3.1-flash-lite"
GUNLUK_TOKEN_LIMITI = 150000

# CSS: Sade ve Şık eTwinning Teması
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #002B54 0%, #001A33 100%);
        color: #F8FAFC;
    }
    header, .stDeployButton { display: none !important; }
    
    .mascot-container {
        display: flex;
        align-items: center;
        gap: 16px;
        background: rgba(0, 51, 102, 0.6);
        border: 2px solid #FFCC00;
        border-radius: 16px;
        padding: 14px 20px;
        margin-bottom: 20px;
    }
    .mascot-img {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        border: 2px solid #FFCC00;
        object-fit: cover;
    }
    .main-title {
        color: #FFCC00;
        font-size: 26px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }
    .engelli-kutu {
        background: rgba(239, 68, 68, 0.15);
        border: 2px solid #EF4444;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: #FCA5A5;
        font-size: 16px;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# IĞDIR İL KONTROLÜ (IP & GEOLOCATION)
# ==============================================================================
def kullanici_konum_kontrol():
    try:
        headers = st.context.headers
        forwarded = headers.get("X-Forwarded-For", "")
        ip = forwarded.split(",")[0].strip() if forwarded else ""
        
        if not ip or ip in ["127.0.0.1", "localhost"]:
            return True, "Yerel Ağ / Geliştirici (Iğdır)"

        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,city,regionName,country", timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                sehir = data.get("city", "") or data.get("regionName", "")
                ulke = data.get("country", "")
                if "igdir" in sehir.lower() or "iğdır" in sehir.lower():
                    return True, f"{sehir}, {ulke}"
                return False, f"{sehir}, {ulke}"
        return True, "Konum Doğrulanamadı (Geçişe İzin Verildi)"
    except Exception:
        return True, "Bilinmiyor"

# ==============================================================================
# BİLGİ BANKASI VE MODEL YAPILANDIRMASI
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
    
    if st.session_state.get("toplam_token", 0) >= GUNLUK_TOKEN_LIMITI:
        return "Bugünkü danışmanlık kotası dolmuştur. Lütfen yarın tekrar deneyiniz."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{AKTIF_MODEL}:generateContent?key={API_KEY}"
    gecmis_metni = "".join([f"{m['role']}: {m['content']}\n" for m in gecmis[-3:]])

    system_instruction = (
        "Sen eTwinning ve ESEP akıllı koç asistanısın. Adın 'Twin'.\n"
        "KESİN KURALLAR:\n"
        "1. GÖREV ALANI: SADECE eTwinning, ESEP, Erasmus+, okul projeleri, pedagoji, eğitim teknolojileri ve ders entegrasyonu konularında rehberlik edersin.\n"
        "2. KIRMIZI ÇİZGİLER: Siyaset, parti politikaları, ideoloji, genel gündem, geyik, dedikodu, özel hayat, kişisel muhabbet veya müstehcen (+18) içeriklere ASLA girme, yorum yapma.\n"
        "3. RET CEVABI: Konu dışına çıkıldığında doğrudan şu kalıpla cevap ver:\n"
        "'Değerli Hocam, ben yalnızca eTwinning projeleri süreçlerinde rehberlik etmek üzere geliştirilmiş bir asistanım. Size projeniz, Kalite Etiketi kriterleri veya ortak ürün süreçleri hakkında nasıl yardımcı olabilirim?'\n"
        "4. ÜSLUP: Saygılı, net, kurumsal ve yapıcı bir ton kullan.\n"
        f"KAYNAK DOKÜMAN:\n{ETWINNING_KORPUSU}\n"
    )

    prompt = f"{system_instruction}\n{gecmis_metni}\nKullanıcı: {soru}\nTwin:"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_LOW_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_LOW_AND_ABOVE"}
        ]
    }

    try:
        r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
        if r.status_code == 200:
            veri = r.json()
            candidates = veri.get("candidates", [])
            if not candidates or "content" not in candidates[0]:
                return "Değerli Hocam, mesajınız güvenlik ve kurumsal kullanım ilkeleri doğrultusunda yanıtlanamadı. Lütfen eTwinning projenizle ilgili bir soru yöneltiniz."
            
            cevap = candidates[0]["content"]["parts"][0]["text"].strip()
            harcanan = veri.get("usageMetadata", {}).get("totalTokenCount", 300)
            st.session_state["toplam_token"] = st.session_state.get("toplam_token", 0) + harcanan
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
        "content": "Merhaba Değerli Öğretmenim! 👋 Ben **Twin**, eTwinning koçunuz. Proje fikrinizi bana anlatın; Kalite Etiketi kriterlerine ve ortak ürün süreçlerine göre birlikte planlayalım!"
    }]
if "toplam_token" not in st.session_state:
    st.session_state.toplam_token = 0

maskot_b64 = ""
if os.path.exists("twin.maskot.jpg"):
    with open("twin.maskot.jpg", "rb") as img_f:
        maskot_b64 = base64.b64encode(img_f.read()).decode()

erisim_izni, tespit_edilen_yer = kullanici_konum_kontrol()

# ==============================================================================
# YAN PANEL (GİZLİ ADMIN MODU + ÇİFT YÖNLÜ ÇEVİRİ)
# ==============================================================================
with st.sidebar:
    if st.query_params.get("admin") == "1":
        st.markdown("### 👑 Yönetici Paneli")
        st.metric(
            label="Harcanan Token",
            value=f"{st.session_state.get('toplam_token', 0):,}",
            delta=f"Limit: {GUNLUK_TOKEN_LIMITI:,}"
        )
        st.caption(f"📍 Tespit Edilen Konum: **{tespit_edilen_yer}**")
        st.markdown("---")

    st.markdown("### 🌍 Akıllı Çift Yönlü Çevirmen")
    st.caption("Türkçe yazın İngilizce olsun, İngilizce yazın Türkçe olsun!")
    cevir_metni = st.text_area("Çevrilecek metni yazın:", height=130)
    
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
# ANA PANEL - SADELEŞTİRİLMİŞ BAŞLIK VE MASKOT
# ==============================================================================
maskot_html = f'<img src="data:image/jpeg;base64,{maskot_b64}" class="mascot-img">' if maskot_b64 else '🤖'

st.markdown(f"""
<div class="mascot-container">
    {maskot_html}
    <div class="main-title">eTwinning Sohbet Botu</div>
</div>
""", unsafe_allow_html=True)

# İl dışı engeli
if not erisim_izni:
    st.markdown(f"""
    <div class="engelli-kutu">
        <h3>🚫 Erişim Kısıtlaması</h3>
        <p>Bu asistan yalnızca <b>Iğdır İl Millî Eğitim Müdürlüğü</b> bünyesinde görev yapan öğretmenlerimizin kullanımına tahsis edilmiştir.</p>
        <p style="font-size:12px; color:#94A3B8; margin-top:10px;">Tespit Edilen Bölge: {tespit_edilen_yer}</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# HIZLI BUTONLAR
# ==============================================================================
c1, c2, c3 = st.columns(3)
hizli_soru = None
if c1.button("💡 Ortak Ürün Fikirleri", use_container_width=True):
    hizli_soru = "Projem için yaratıcı ortak ürün fikirleri verir misin?"
if c2.button("🏆 Rubrik Kriterleri", use_container_width=True):
    hizli_soru = "Kalite Etiketi rubrikindeki 5 ana kriteri açıklar mısın?"
if c3.button("📌 Yeni Ortaklık Sınırı", use_container_width=True):
    hizli_soru = "Türkiye ortaklık sınırındaki yeni kurallar nelerdir?"

# Mesaj Geçmişini Listele
for msg in st.session_state.messages:
    avatar = "twin.maskot.jpg" if msg["role"] == "assistant" and os.path.exists("twin.maskot.jpg") else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ==============================================================================
# SOHBET GİRİŞ KONTROLÜ
# ==============================================================================
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
            st.rerun()
