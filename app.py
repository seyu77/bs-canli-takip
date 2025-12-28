import streamlit as st
import time
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Global Haber Takip", layout="wide", initial_sidebar_state="collapsed")

# --- ÖZEL TASARIM (CSS) ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #0e1117; border: 1px solid #303030; padding: 10px; border-radius: 5px; text-align: center;}
    div[data-testid="stMetricValue"] {font-size: 2rem !important; color: #00ff41;}
    </style>
""", unsafe_allow_html=True)

# --- GÜVENLİK ---
if "giris_yapildi" not in st.session_state:
    st.session_state["giris_yapildi"] = False

if not st.session_state["giris_yapildi"]:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 Güvenli Giriş")
        sifre = st.text_input("Admin Şifresi:", type="password")
        if st.button("Giriş Yap"):
            if sifre == st.secrets["ADMIN_SIFRESI"]:
                st.session_state["giris_yapildi"] = True
                st.rerun()
            else:
                st.error("Yanlış şifre!")
    st.stop()

# --- SİTELER ---
SITELER = {
    "TR (Türkçe)": "307941301",
    "EN (İngilizce)": "358993900",
    "ES (İspanyolca)": "514697392",
    "CN (Çince)": "514704263",
    "JP (Japonya)": "514667124",
    "RU (Rusya)": "514679418",
    "KR (Korece)": "517245619"
}

@st.cache_resource
def get_client():
    key_dict = json.loads(st.secrets["GOOGLE_KEY"])
    return BetaAnalyticsDataClient.from_service_account_info(key_dict)

# --- 1. FONKSİYON: SADECE SAYIYI GETİR (GARANTİ) ---
def ana_sayiyi_getir(client, property_id):
    request = RunRealtimeReportRequest(
        property=f"properties/{property_id}",
        metrics=[{"name": "activeUsers"}]
    )
    try:
        response = client.run_realtime_report(request)
        if response.rows:
            return int(response.rows[0].metric_values[0].value)
        return 0
    except:
        return 0

# --- 2. FONKSİYON: KAYNAKLARI GETİR (DETAY) ---
def kaynaklari_getir(client, property_id):
    request = RunRealtimeReportRequest(
        property=f"properties/{property_id}",
        dimensions=[{"name": "source"}], 
        metrics=[{"name": "activeUsers"}],
        limit=5
    )
    try:
        response = client.run_realtime_report(request)
        kaynaklar = []
        sayilar = []
        
        if response.rows:
            for row in response.rows:
                source_name = row.dimension_values[0].value
                count = int(row.metric_values[0].value)
                kaynaklar.append(source_name)
                sayilar.append(count)
                
        df = pd.DataFrame({"Kaynak": kaynaklar, "Kişi": sayilar})
        if not df.empty:
             df = df.sort_values(by="Kişi", ascending=False)
        return df
    except:
        return pd.DataFrame()

# --- ARAYÜZ ---
st.title("🌍 Global Haber Trafik Merkezi")
st.caption(f"Veriler anlıktır (Son 30 dk). Otomatik yenilenir: {time.strftime('%H:%M:%S')}")

client = get_client()

cols = st.columns(4)
col_counter = 0
toplam_global_hit = 0

for ulke, pid in SITELER.items():
    with cols[col_counter % 4]:
        st.markdown(f"### {ulke}")
        
        # Verileri çek
        sayi = ana_sayiyi_getir(client, pid)
        toplam_global_hit += sayi
        df = kaynaklari_getir(client, pid)
        
        # Ekrana Bas
        st.metric(label="Aktif Okuyucu", value=sayi)
        
        if not df.empty:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Kaynak": st.column_config.TextColumn("Kaynak"),
                    "Kişi": st.column_config.ProgressColumn(
                        "Yoğunluk",
                        format="%d",
                        min_value=0,
                        max_value=int(df["Kişi"].max()),
                    ),
                },
                height=150
            )
        else:
            if sayi > 0:
                st.caption("Kaynak verisi işleniyor...")
            else:
                st.caption("Veri yok")
            
        st.divider()
        
    col_counter += 1

st.markdown("---")
st.markdown(f"<h2 style='text-align: center; color: yellow;'>TOPLAM GLOBAL ANLIK TRAFİK: {toplam_global_hit}</h2>", unsafe_allow_html=True)

time.sleep(60)
st.rerun()
