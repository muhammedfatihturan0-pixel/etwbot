# ==============================================================================
# İL DIŞI ERİŞİM KONTROLÜ
# ==============================================================================
if not erisim_izni:
    location_label = html.escape(str(tespit_edilen_yer))
    st.markdown(
        f"""
<div class="access-card">
  <h3>🚫 Erişim doğrulanamadı</h3>
  <p>Bu asistan kurumsal kullanım için yapılandırılmıştır.</p>
  <p class="muted">IP tabanlı yaklaşık bölge: {location_label}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    if IGDIR_ACCESS_CODE:
        st.info("VPN, mobil operatör veya hatalı IP konumu nedeniyle yanlış engellendiyseniz kurumsal erişim kodunu kullanabilirsiniz.")
        access_code = st.text_input("Kurumsal erişim kodu", type="password")
        if st.button("Erişimi doğrula"):
            if safe_equals(access_code, IGDIR_ACCESS_CODE):
                st.session_state.location_override = True
                st.rerun()
            else:
                st.error("Erişim kodu geçersiz.")
    st.stop()

# ==============================================================================
# HIZLI İŞLEMLER — KATEGORİLER
# ==============================================================================
hizli_soru = None

st.markdown("### Kısayollar")
st.caption("Bir kategoriye tıklayın; ilgili seçenekler açılır.")

quick_categories = {
    "Proje Tasarımı": [
        (
            "Proje fikrimi değerlendir",
            "Sana birazdan proje fikrimi yazacağım. Fikrimi müfredat uyumu, öğrenci merkezlilik, uluslararası işbirliği, karma takımlar, ortak ürün, e-Güvenlik ve TwinSpace kanıt planı başlıklarıyla değerlendir.",
        ),
        (
            "Ortaklık sınırlarını açıkla",
            "Türkiye ortaklık sınırındaki kuralları bu uygulamanın bilgi bankasına göre açıkla ve proje kurarken nelere dikkat etmem gerektiğini belirt.",
        ),
    ],
    "İşbirliği": [
        (
            "Ortak ürün / işbirlikçi ürün farkı",
            "eTwinning'de Ortak Ürün ile İşbirlikçi Ürün arasındaki fark nedir? Somut örneklerle ve Kalite Etiketi açısından açıklar mısın?",
        ),
        (
            "Çapraz karma takım kur",
            "10 öğretmen ve 30 öğrenci ile çapraz mentörlü karma takım yapısını kur; görev dağılımını ve tek bir ortak ürüne dönüşen zinciri örnekle.",
        ),
    ],
    "Kalite": [
        (
            "Kritik hataları kontrol et",
            "Kalite Etiketi değerlendirmesinde projeyi riske atan kritik hataları; neden, sonuç ve düzeltme önerisi formatında açıkla.",
        ),
    ],
    "TwinSpace": [
        (
            "Kanıt planı oluştur",
            "Bir eTwinning projesi için TwinSpace'te hangi sayfaları açmam gerektiğini ve her sayfada hangi kanıtları tutmam gerektiğini uygulanabilir bir yapı halinde öner.",
        ),
    ],
}

category_cols = st.columns(len(quick_categories))
for col, (category, actions) in zip(category_cols, quick_categories.items()):
    with col:
        with st.popover(category, use_container_width=True):
            for idx, (label, question) in enumerate(actions):
                if st.button(
                    label,
                    use_container_width=True,
                    key=f"quick_{category}_{idx}",
                ):
                    hizli_soru = question

# ==============================================================================
# SOHBET GEÇMİŞİ
# ==============================================================================
st.markdown("### Sohbet")
last_index = len(st.session_state.messages) - 1
for idx, msg in enumerate(st.session_state.messages):
    avatar = MASKOT_PATH if msg["role"] == "assistant" and os.path.exists(MASKOT_PATH) else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and idx == last_index and len(st.session_state.messages) > 1:
            try:
                feedback = st.feedback("thumbs", key=f"feedback_{idx}_{len(st.session_state.messages)}")
                if feedback is not None:
                    st.caption("Geri bildiriminiz bu oturum için alındı.")
            except Exception:
                pass

# ==============================================================================
# SOHBET GİRİŞİ
# ==============================================================================
typed_prompt = st.chat_input("Projenizi anlatın veya eTwinning sorunuzu yazın...")
prompt = hizli_soru or typed_prompt

if prompt:
    prompt = str(prompt).strip()
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=MASKOT_PATH if os.path.exists(MASKOT_PATH) else None):
            with st.status("Twin proje çerçevesini inceliyor...", expanded=False) as status:
                cevap = gemini_cevap_uret(prompt)
                status.update(label="Değerlendirme tamamlandı", state="complete", expanded=False)
            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})

