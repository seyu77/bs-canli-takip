import streamlit as st
import time
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Global Haber Takip", layout="wide", initial_sidebar_state="collapsed")

# --- CSS MAKYYAJI (Daha Profesyonel Görünüm) ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    /* Kart Tasarımı */
    .css-1r6slb0 {border: 1px solid #333; padding: 15px; border-radius: 10px; background-color: #111;}
    /* Büyük Sayılar */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; 
        color: #00ff41; /* Matrix Yeşili */
        text-shadow: 0 0 10px rgba(0,255,65,0.4);
    }
    div[data-testid="stMetricLabel"] {font-size: 1.1rem !important; color: #ddd; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# --- GÜVENLİK ---
if "giris_yapildi" not in st.session_state:
    st.session_state["giris_yapildi"] = False

if not st.session_state["giris_yapildi"]:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### 🔒 Haber Merkezi Giriş")
        sifre = st.text_input("Şifre:", type="password")
        if st.button("Giriş Yap"):
            if sifre == st.secrets["ADMIN_SIFRESI"]:
                st.session_state["giris_yapildi"] = True
                st.rerun()
            else:
                st.error("Hatalı Şifre!")
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

# --- 1. FONKSİYON: NET SAYIYI ÇEK ---
def ana_sayiyi_getir(client, property_id):
    try:
        request = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            metrics=[{"name": "activeUsers"}]
        )
        response = client.run_realtime_report(request)
        if response.rows:
            return int(response.rows[0].metric_values[0].value)
        return 0
    except:
        return 0

# --- 2. FONKSİYON: KAYNAKLARI ÇEK ---
def kaynaklari_getir(client, property_id):
    try:
        request = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[{"name": "firstUserSource"}], # Kaynak (google, t.co)
            metrics=[{"name": "activeUsers"}],
            limit=5
        )
        response = client.run_realtime_report(request)
        kaynaklar = []
        sayilar = []
        
        if response.rows:
            for row in response.rows:
                source_name = row.dimension_values[0].value
                count = int(row.metric_values[0].value)
                # (not set) gelirse düzelt
                if source_name == "(not set)": source_name = "Direct / Bilinmiyor"
                kaynaklar.append(source_name)
                sayilar.append(count)
                
        df = pd.DataFrame({"Kaynak": kaynaklar, "Kişi": sayilar})
        if not df.empty:
             df = df.sort_values(by="Kişi", ascending=False)
        return df
    except:
        return pd.DataFrame()

# --- ARAYÜZ BAŞLANGICI ---
st.markdown(f"<h2 style='text-align: center;'>🌍 Global Haber Trafik Odası</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #666;'>Son Güncelleme: {time.strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
st.divider()

client = get_client()

cols = st.columns(4)
col_counter = 0
toplam_global_hit = 0

for ulke, pid in SITELER.items():
    with cols[col_counter % 4]:
        
        # --- VERİ ÇEKME ---
        sayi = ana_sayiyi_getir(client, pid)
        toplam_global_hit += sayi
        df = kaynaklari_getir(client, pid)
        
        # --- YAMA: Eğer sayı var ama tablo boşsa, yapay tablo oluştur ---
        if sayi > 0 and df.empty:
            df = pd.DataFrame({"Kaynak": ["Direct / Anlık"], "Kişi": [sayi]})
        
        # --- KART GÖRÜNÜMÜ ---
        st.markdown(f"#### {ulke}")
        st.metric(label="Aktif Okuyucu", value=sayi)
        
        # Tablo Gösterimi
        if not df.empty:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Kaynak": st.column_config.TextColumn("Kaynak"),
                    "Kişi": st.column_config.ProgressColumn(
                        "Trafik",
                        format="%d",
                        min_value=0,
                        max_value=int(df["Kişi"].max()),
                    ),
                },
                height=150
            )
        else:
            # Gerçekten 0 ise
            st.caption("Hareket yok")
            
        st.divider()
        
    col_counter += 1

# --- ALT TOPLAM ---
st.markdown("---")
st.markdown(f"""
    <div style="
        background: linear-gradient(90deg, rgba(20,20,20,1) 0%, rgba(50,50,50,1) 100%); 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center; 
        border: 1px solid #444;
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.2);">
        <h3 style="margin:0; color: #aaa; font-size: 1rem; letter-spacing: 2px;">TOPLAM GLOBAL ANLIK TRAFİK</h3>
        <h1 style="margin:0; color: #ffe600; font-size: 4rem; font-family: monospace;">{toplam_global_hit}</h1>
    </div>
""", unsafe_allow_html=True)

# 60 Saniye Yenileme
time.sleep(60)
st.rerun()
