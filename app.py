import streamlit as st
import time
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Global Haber Takip", layout="wide", initial_sidebar_state="collapsed")

# --- CSS (Makyaj) ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    /* Metrik Stilleri */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; 
        color: #00ff41; 
        text-shadow: 0 0 10px rgba(0,255,65,0.4);
    }
    div[data-testid="stMetricLabel"] {font-size: 1.1rem !important; color: #ddd; font-weight: bold;}
    div[data-testid="stDataFrame"] {font-size: 0.8rem;}
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

# --- VERİ ÇEKME MOTORU ---
def verileri_al(client, property_id):
    try:
        # 1. Önce Kesin Sayıyı Al
        req_total = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            metrics=[{"name": "activeUsers"}]
        )
        res_total = client.run_realtime_report(req_total)
        total_users = 0
        if res_total.rows:
            total_users = int(res_total.rows[0].metric_values[0].value)

        # 2. Kaynakları Almayı Dene
        req_source = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[{"name": "source"}], # 'firstUserSource' değil 'source'
            metrics=[{"name": "activeUsers"}],
            limit=5
        )
        res_source = client.run_realtime_report(req_source)
        
        kaynaklar = []
        sayilar = []
        
        # Eğer Google Kaynak Listesi Verirse Doldur
        if res_source.rows:
            for row in res_source.rows:
                src = row.dimension_values[0].value
                cnt = int(row.metric_values[0].value)
                
                # İsim düzeltmeleri
                if src == "(direct)": src = "Doğrudan"
                if src == "t.co": src = "Twitter"
                if src == "(not set)": src = "Bilinmiyor"
                
                kaynaklar.append(src)
                sayilar.append(cnt)
        
        # --- ZORLAMA MODU (FORCE FILL) ---
        # Eğer kullanıcı var (total_users > 0) ama kaynak listesi BOŞ ise
        if total_users > 0 and not kaynaklar:
            kaynaklar = ["Genel Trafik / (Google Gizliyor)"]
            sayilar = [total_users]
        
        # Veri Çerçevesi Oluştur
        df = pd.DataFrame({"Kaynak": kaynaklar, "Kişi": sayilar})
        
        if not df.empty:
             df = df.sort_values(by="Kişi", ascending=False)
             
        return total_users, df
        
    except Exception as e:
        return 0, pd.DataFrame()

# --- ARAYÜZ ---
st.markdown(f"<h2 style='text-align: center;'>🌍 Global Haber Trafik Odası</h2>", unsafe_allow_html=True)
st.divider()

client = get_client()

cols = st.columns(4)
col_counter = 0
toplam_global_hit = 0

for ulke, pid in SITELER.items():
    with cols[col_counter % 4]:
        
        # Veri Çek
        sayi, df = verileri_al(client, pid)
        toplam_global_hit += sayi
        
        # Göster
        st.markdown(f"#### {ulke}")
        st.metric(label="Anlık Okuyucu", value=sayi)
        
        if sayi > 0:
            # Eğer bir şekilde df boş kaldıysa bile doldur
            if df.empty:
                df = pd.DataFrame({"Kaynak": ["Genel Akış"], "Kişi": [sayi]})
                
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
                        max_value=int(sayi),
                    ),
                },
                height=150
            )
        else:
            st.caption("Veri Yok")
            
        st.divider()
        
    col_counter += 1

# --- ALT TOPLAM ---
st.markdown("---")
st.markdown(f"""
    <div style="background-color:#111; padding:15px; border-radius:15px; text-align:center; border:1px solid #333;">
        <h3 style="margin:0; color:#aaa; font-size:1rem;">TOPLAM ANLIK TRAFİK</h3>
        <h1 style="margin:0; color:#ffe600; font-size:4rem;">{toplam_global_hit}</h1>
    </div>
""", unsafe_allow_html=True)

# 60 Saniye Yenileme
time.sleep(60)
st.rerun()
