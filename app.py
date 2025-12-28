import streamlit as st
import time
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
import json
import os

# --- AYARLAR ---
st.set_page_config(page_title="Bitcoin Sistemi Canlı", layout="wide")

# --- GÜVENLİK DUVARI (BEKÇİ) ---
# Eğer giriş yapılmadıysa şifre sorar
if "giris_yapildi" not in st.session_state:
    st.session_state["giris_yapildi"] = False

if not st.session_state["giris_yapildi"]:
    st.title("🔒 Giriş Yap")
    # Şifre kutusu
    sifre = st.text_input("Şifreyi Giriniz:", type="password")
    
    if st.button("Giriş"):
        # Secrets'tan şifreyi kontrol et
        if sifre == st.secrets["ADMIN_SIFRESI"]:
            st.session_state["giris_yapildi"] = True
            st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Hatalı Şifre!")
    
    st.stop() # Şifre girilmediyse buradan aşağısını asla çalıştırma!

# ==========================================
# BURADAN AŞAĞISI VERİ ÇEKME İŞLEMLERİ
# ==========================================

# SİTE ID LİSTESİ (Senin Verdiğin ID'ler)
SITELER = {
    "TR (Türkçe)": "307941301",
    "EN (İngilizce)": "358993900",
    "ES (İspanyolca)": "514697392",
    "CN (Çince)": "514704263",
    "JP (Japonya)": "514667124",
    "RU (Rusya)": "514679418",
    "KR (Korece)": "517245619"
}

# Google Key'i Secrets'tan al
def get_client():
    key_dict = json.loads(st.secrets["GOOGLE_KEY"])
    return BetaAnalyticsDataClient.from_service_account_info(key_dict)

# API'den anlık veri çeken fonksiyon
def anlik_hit_getir(client, property_id):
    request = RunRealtimeReportRequest(
        property=f"properties/{property_id}",
        metrics=[{"name": "activeUsers"}],
    )
    try:
        response = client.run_realtime_report(request)
        if response.rows:
            return int(response.rows[0].metric_values[0].value)
        return 0
    except:
        return 0

# --- ARAYÜZ TASARIMI ---
st.title("🌐 Anlık Takip Merkezi (Son 30 Dk)")

# Manuel yenileme butonu (Gerekirse diye)
if st.button('Verileri Şimdi Yenile'):
    st.rerun()

# Verileri çekmeye başla
client = get_client()
cols = st.columns(4) # 4 sütunlu yapı

toplam = 0
# Tüm siteleri döngüye sok ve ekrana bas
for i, (ulke, pid) in enumerate(SITELER.items()):
    val = anlik_hit_getir(client, pid)
    toplam += val
    
    # Ekrana yerleştir
    col_index = i % 4
    with cols[col_index]:
        # Eğer hit 50'den fazlaysa yeşil, 200'den fazlaysa kırmızı gibi vurgular yapabilirsin
        st.metric(label=ulke, value=val)

st.divider()
# Toplam sayıyı büyük göster
st.metric(label="TOPLAM ANLIK OKUYUCU", value=toplam)

st.caption(f"Son güncelleme: {time.strftime('%H:%M:%S')}")

# --- OTOMATİK YENİLEME (60 SANİYE) ---
time.sleep(60)
st.rerun()
