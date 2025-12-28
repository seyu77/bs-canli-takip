import streamlit as st
import time
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunRealtimeReportRequest
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Haber Takip", layout="wide", initial_sidebar_state="collapsed")

# --- CSS ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem;}
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; 
        color: #00ff41; 
        text-shadow: 0 0 10px rgba(0,255,65,0.4);
    }
    div[data-testid="stMetricLabel"] {font-size: 1.1rem !important; color: #ddd;}
    </style>
""", unsafe_allow_html=True)

# --- GÜVENLİK ---
if "giris_yapildi" not in st.session_state:
    st.session_state["giris_yapildi"] = False

if not st.session_state["giris_yapildi"]:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### 🔒 Giriş")
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

# --- AYRIŞTIRILMIŞ VERİ MOTORU ---
def verileri_al(client, property_id):
    # 1. ADIM: SADECE SAYIYI AL (Burada hata olursa direkt hata mesajı dönecek)
    toplam_sayi = 0
    hata_mesaji = None
    
    try:
        req_total = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            metrics=[{"name": "activeUsers"}]
        )
        res_total = client.run_realtime_report(req_total)
        if res_total.rows:
            toplam_sayi = int(res_total.rows[0].metric_values[0].value)
    except Exception as e:
        hata_mesaji = str(e) # Hatayı yakala ama akışı bozma
        return 0, pd.DataFrame(), hata_mesaji

    # 2. ADIM: TABLOYU AL (Hata olsa bile toplam sayıyı etkilemesin)
    df = pd.DataFrame()
    try:
        req_source = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[{"name": "source"}], # 'firstUserSource' yerine 'source'
            metrics=[{"name": "activeUsers"}],
            limit=5
        )
        res_source = client.run_realtime_report(req_source)
        
        kaynaklar = []
        sayilar = []
        
        if res_source.rows:
            for row in res_source.rows:
                src = row.dimension_values[0].value
                cnt = int(row.metric_values[0].value)
                
                if src == "(not set)": src = "Doğrudan"
                if src == "(direct)": src = "Doğrudan"
                
                kaynaklar.append(src)
                sayilar.append(cnt)
        
        # ZORLAMA DOLGU: Sayı var ama liste boşsa
        if toplam_sayi > 0 and not kaynaklar:
            kaynaklar = ["Genel Trafik"]
            sayilar = [toplam_sayi]
            
        df = pd.DataFrame({"Kaynak": kaynaklar, "Kişi": sayilar})
        if not df.empty:
             df = df.sort_values(by="Kişi", ascending=False)
             
    except:
        # Tablo hatası önemli değil, boş dönsün ama sayı kalsın
        pass
        
    return toplam_sayi, df, None

# --- ARAYÜZ ---
st.markdown(f"<h2 style='text-align: center;'>🌍 Global Haber Trafik Odası</h2>", unsafe_allow_html=True)
st.divider()

client = get_client()

cols = st.columns(4)
col_counter = 0
toplam_global_hit = 0

for ulke, pid in SITELER.items():
    with cols[col_counter % 4]:
        
        # Fonksiyonu çağır
        sayi, df, hata = verileri_al(client, pid)
        toplam_global_hit += sayi
        
        st.markdown(f"#### {ulke}")
        
        if hata:
            # HATA VARSA KIRMIZI YAZ
            st.error(f"Hata: {hata}")
        else:
            # HATA YOKSA SAYIYI BAS
            st.metric(label="Anlık", value=sayi)
            
            # Tablo varsa bas
            if sayi > 0:
                if df.empty:
                    # Tablo boşsa yapay oluştur
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
    <div style="text-align:center;">
        <h3 style="margin:0; color:#aaa;">TOPLAM</h3>
        <h1 style="margin:0; color:#ffe600; font-size:4rem;">{toplam_global_hit}</h1>
    </div>
""", unsafe_allow_html=True)

time.sleep(60)
st.rerun()
