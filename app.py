import streamlit as st
import time
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
import json
import os

# --- AYARLAR ---
st.set_page_config(page_title="Bitcoin Sistemi Canlı", layout="wide")

# SİTE ID LİSTESİ
SITELER = {
    "TR (Türkçe)": "307941301",     # TR ID'sini buraya
    "EN (İngilizce)": "358993900",  # EN ID'sini buraya
    "ES (İspanyolca)": "514697392",  # <--- BURAYA İSPANYOLCA ID GELECEK
    "CN (Çince)": "514704263",      # CN ID'sini buraya
    "JP (Japonya)": "514667124",    # JP ID'sini buraya
    "RU (Rusya)": "514679418",      # RU ID'sini buraya
    "KR (Korece)": "517245619"      # KR ID'sini buraya
}

# Google Key'i Streamlit Secrets'tan alacağız (Güvenlik için)
def get_client():
    key_dict = json.loads(st.secrets["GOOGLE_KEY"])
    return BetaAnalyticsDataClient.from_service_account_info(key_dict)

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

# --- ARAYÜZ ---
st.title("🌐 Anlık Takip Merkezi (Son 30 Dk)")

# Yenileme butonu
if st.button('Verileri Yenile'):
    st.rerun()

client = get_client()
cols = st.columns(4) # 4'lü satır yapısı

toplam = 0
for i, (ulke, pid) in enumerate(SITELER.items()):
    val = anlik_hit_getir(client, pid)
    toplam += val
    
    # Renklendirme mantığı (Delta ile artış azalış gibi gösterelim)
    col_index = i % 4
    with cols[col_index]:
        st.metric(label=ulke, value=val)

st.divider()
st.metric(label="TOPLAM ANLIK OKUYUCU", value=toplam)

# Otomatik yenileme için basit bir bilgi
st.caption(f"Son güncelleme: {time.strftime('%H:%M:%S')}. Sayfayı yenileyerek güncelleyebilirsin.")