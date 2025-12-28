import streamlit as st
import time
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Global Haber Takip", layout="wide", initial_sidebar_state="collapsed")

# --- TASARIM (CSS) ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; 
        color: #00ff41; 
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

# --- ANALİZ FONKSİYONU ---
def verileri_al(client, property_id):
    try:
        # Tek sorguda hem toplamı hem kırılımı almaya çalışıyoruz
        request = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[{"name": "source"}], # 'firstUserSource' yerine 'source' daha günceldir
            metrics=[{"name": "activeUsers"}],
            limit=10
        )
        response = client.run_realtime_report(request)
        
        kaynaklar = []
        sayilar = []
        tablo_toplami = 0
        
        if response.rows:
            for row in response.rows:
                src = row.dimension_values[0].value
                cnt = int(row.metric_values[0].value)
                
                # GA4'te boş gelen veriyi olduğu gibi (not set) bırakıyoruz
                if src == "": src = "(not set)"
                
                kaynaklar.append(src)
                sayilar.append(cnt)
                tablo_toplami += cnt
        
        # Gerçek toplam sayıyı (activeUsers) ayrıca çekelim ki eksik kalmasın
        # (Bazen kırılımların toplamı, ana sayıdan düşük olabilir)
        request_total = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            metrics=[{"name": "activeUsers"}]
        )
        resp_total = client.run_realtime_report(request_total)
        gercek_toplam = 0
        if resp_total.rows:
            gercek_toplam = int(resp_total.rows[0].metric_values[0].value)
            
        # Eğer kırılımların toplamı ana sayıdan azsa, kalanı "GA4 İşliyor" (Processing) olarak ekle
        fark = gercek_toplam - tablo_toplami
        if fark > 0:
            kaynaklar.append("(processing...)")
            sayilar.append(fark)
            
        df = pd.DataFrame({"Kaynak": kaynaklar, "Kişi": sayilar})
        
        # Sıralama ve Temizlik
        if not df.empty:
             df = df.sort_values(by="Kişi", ascending=False).head(5)
             
        return gercek_toplam, df
        
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
        
        # Veriyi Çek
        sayi, df = verileri_al(client, pid)
        toplam_global_hit += sayi
        
        # Göster
        st.markdown(f"#### {ulke}")
        st.metric(label="Aktif Okuyucu", value=sayi)
        
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
                        max_value=int(df["Kişi"].max()) if df["Kişi"].max() > 0 else 100,
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
    <div style="background-color:#111; padding:20px; border-radius:15px; text-align:center; border:1px solid #333;">
        <h3 style="margin:0; color:#aaa;">TOPLAM GLOBAL ANLIK TRAFİK</h3>
        <h1 style="margin:0; color:#ffe600; font-size:4rem;">{toplam_global_hit}</h1>
    </div>
""", unsafe_allow_html=True)

# 60 Saniye Yenileme
time.sleep(60)
st.rerun()
