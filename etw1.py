import os
import base64
import requests
import streamlit as st
import streamlit.components.v1 as components

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

# CSS: Sarı-Mavi Tema ve Maskot
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #002B54 0%, #001A33 100%);
        color: #F8FAFC;
    }
    header, .stDeployButton { display: none !important; }
    
    .main-title {
        color: #FFCC00;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 2px;
    }
    .sub-title {
        color: #CBD5E1;
        font-size: 13px;
        margin-bottom: 15px;
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
    
    # Günlük kota aşım kontrolü (Kullanıcıya gösterilmez, sadece aşılırsa durdurur)
    if st.session_state.get("toplam_token", 0) >= GUNLUK_TOKEN_LIMITI:
        return "Bugünkü danışmanlık kotası dolmuştur. Lütfen yarın tekrar deneyiniz."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{AKTIF_MODEL}:generateContent?key={API_KEY}"
    gecmis_metni = "".join([f"{m['role']}: {m['content']}\n" for m in gecmis[-3:]])

    system_instruction = (
        "Sen Millî Eğitim Bakanlığı eTwinning ve ESEP resmi akıllı koç yapay zekâ asistanısın. Adın 'Twin'. "
        "Karşındaki öğretmenlere 'Hocam' veya 'Değerli Öğretmenim' diyerek saygılı, net ve ilham verici rehberlik et.\n"
        "Cevapların sesli okunacağını unutma; akıcı ve anlaşılır Türkçe kullan.\n"
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
        "content": "Merhaba Değerli Öğretmenim! 👋 Ben **Twin**, eTwinning koçunuz. Proje fikrinizi bana anlatın; Kalite Etiketi kriterlerine göre birlikte inceleyelim!"
    }]
if "toplam_token" not in st.session_state:
    st.session_state.toplam_token = 0

maskot_b64 = ""
if os.path.exists("twin.maskot.jpg"):
    with open("twin.maskot.jpg", "rb") as img_f:
        maskot_b64 = base64.b64encode(img_f.read()).decode()

# ==============================================================================
# YAN PANEL (SADECE ÇİFT YÖNLÜ ÇEVİRİ - TOKEN SAYAÇLARI KALDIRILDI)
# ==============================================================================
with st.sidebar:
    st.markdown("### 🌍 Akıllı Çift Yönlü Çevirmen")
    st.caption("Türkçe yazın İngilizce olsun, İngilizce yazın Türkçe olsun!")
    cevir_metni = st.text_area("Çevrilecek metni yazın:", height=120)
    
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
# ANA PANEL - BAŞLIK VE MASKOT
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

# Hızlı Butonlar
c1, c2, c3 = st.columns(3)
hizli_soru = None
if c1.button("💡 Ortak Ürün Fikirleri", use_container_width=True):
    hizli_soru = "Projem için yaratıcı ortak ürün fikirleri verir misin?"
if c2.button("🏆 Rubrik Kriterleri", use_container_width=True):
    hizli_soru = "Kalite Etiketi rubrikindeki 5 ana kriteri açıklar mısın?"
if c3.button("📌 Yeni Ortaklık Sınırı", use_container_width=True):
    hizli_soru = "Türkiye ortaklık sınırındaki yeni kurallar nelerdir?"

# Mesaj Geçmişi
for msg in st.session_state.messages:
    avatar = "twin.maskot.jpg" if msg["role"] == "assistant" and os.path.exists("twin.maskot.jpg") else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ==============================================================================
# SES MOTORU BİLEŞENİ (SESLİ KONUŞMA BUTONU)
# ==============================================================================
components.html(r"""
<div style="display:flex; gap:10px; align-items:center; margin-top:5px;">
    <button id="micBtn" style="background:#0EA5E9; color:#fff; border:none; padding:10px 18px; border-radius:10px; font-weight:700; cursor:pointer; font-size:14px; font-family:'Plus Jakarta Sans',sans-serif;">
        🎤 Mikrofonla Konuş
    </button>
    <button id="stopBtn" style="background:#EF4444; color:#fff; border:none; padding:10px 18px; border-radius:10px; font-weight:700; cursor:pointer; font-size:14px; display:none; font-family:'Plus Jakarta Sans',sans-serif;">
        🛑 Sesi Durdur
    </button>
    <span id="durumText" style="color:#CBD5E1; font-size:13px; font-family:'Plus Jakarta Sans',sans-serif;"></span>
</div>

<script>
    const micBtn = document.getElementById("micBtn");
    const stopBtn = document.getElementById("stopBtn");
    const durumText = document.getElementById("durumText");
    let recognition = null;
    let synth = window.speechSynthesis;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRec();
        recognition.lang = 'tr-TR';
        recognition.continuous = false;

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            durumText.innerText = "Algılandı: " + transcript;
            
            // Streamlit altındaki chat input'a metni aktar
            const parentDoc = window.parent.document;
            const chatInput = parentDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput) {
                chatInput.value = transcript;
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Gönder butonuna tıkla
                setTimeout(() => {
                    const sendBtn = parentDoc.querySelector('button[data-testid="stChatInputSubmitButton"]');
                    if (sendBtn) sendBtn.click();
                }, 300);
            }
        };

        recognition.onerror = () => {
            micBtn.innerText = "🎤 Mikrofonla Konuş";
            micBtn.style.background = "#0EA5E9";
            durumText.innerText = "";
        };

        recognition.onend = () => {
            micBtn.innerText = "🎤 Mikrofonla Konuş";
            micBtn.style.background = "#0EA5E9";
        };

        micBtn.onclick = () => {
            if (synth) synth.cancel();
            micBtn.innerText = "🔴 Dinliyor...";
            micBtn.style.background = "#EF4444";
            durumText.innerText = "Dinleniyor, konuşabilirsiniz...";
            recognition.start();
        };
    } else {
        micBtn.style.display = "none";
    }

    stopBtn.onclick = () => {
        if (synth) synth.cancel();
        stopBtn.style.display = "none";
    };
</script>
""", height=65)

# ==============================================================================
# SOHBET GİRİŞ ALANI VE SESLİ OKUMA
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

            # Botun verdiği yanıtı otomatik seslendiren bileşen
            temiz_cevap = cevap.replace('"', '\\"').replace('\n', ' ')
            components.html(f"""
            <script>
                const synth = window.speechSynthesis;
                if (synth) {{
                    synth.cancel();
                    const utter = new SpeechSynthesisUtterance("{temiz_cevap}");
                    utter.lang = 'tr-TR';
                    utter.rate = 1.05;
                    const voices = synth.getVoices();
                    const trVoice = voices.find(v => v.lang.includes('tr'));
                    if (trVoice) utter.voice = trVoice;
                    synth.speak(utter);
                }}
            </script>
            """, height=0)
