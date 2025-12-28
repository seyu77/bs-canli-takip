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
        text-shadow: 0 0 15px rgba(0,255,65,0.3);
    }
    div[data-testid="stMetricLabel"] {font-size: 1.1rem !important; color: #ddd; font-weight: bold;}
    
    /* Tablo Başlıklarını Gizle/Küçült */
    thead tr th:first-child {display:none}
    tbody tr td:first-child {display:none}
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
        # ÖNCE: Toplam kesin sayıyı al
        req_total = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            metrics=[{"name": "activeUsers"}]
        )
        res_total = client.run_realtime_report(req_total)
        total_users = 0
        if res_total.rows:
            total_users = int(res_total.rows[0].metric_values[0].value)

        # SONRA: Kaynak dağılımını al (firstUserSource = Kullanıcıyla ilk ilişkilendirilen kaynak)
        req_source = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[{"name": "firstUserSource"}], 
            metrics=[{"name": "activeUsers"}],
            limit=5
        )
        res_source = client.run_realtime_report(req_source)
        
        kaynaklar = []
        sayilar = []
        tablo_toplami = 0
        
        if res_source.rows:
            for row in res_source.rows:
                src = row.dimension_values[0].value
                cnt = int(row.metric_values[0].value)
                
                if src == "(not set)": src = "Direct / Bilinmiyor"
                
                kaynaklar.append(src)
                sayilar.append(cnt)
                tablo_toplami += cnt
        
        # --- KRİTİK EŞİK KONTROLÜ ---
        # Eğer toplam kullanıcı var ama kaynak listesi boş geldiyse (Google Gizliyorsa)
        if total_users > 0 and len(kaynaklar) == 0:
            kaynaklar.append("Veri Eşiği Altında / Direct")
            sayilar.append(total_users)
        
        # Eğer toplam kullanıcı, listedekilerden fazlaysa, aradaki farkı ekle
        elif total_users > tablo_toplami:
            fark = total_users - tablo_toplami
            kaynaklar.append("Diğer / İşleniyor")
            sayilar.append(fark)

        # Tabloyu oluştur
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
        
        # Başlık ve Sayı
        st.markdown(f"#### {ulke}")
        st.metric(label="Anlık Okuyucu", value=sayi)
        
        # Tablo
        if not df.empty and sayi > 0:
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
                        max_value=int(sayi), # Max değeri toplam sayı yapalım ki bar doğru orantılı olsun
                    ),
                },
                height=150
            )
        else:
            # 0 ise
            st.markdown("<div style='text-align:center; color:#444; margin-top:10px;'>Hareketsiz</div>", unsafe_allow_html=True)
            
        st.divider()
        
    col_counter += 1

# --- ALT TOPLAM ---
st.markdown("---")
st.markdown(f"""
    <div style="background-color:#0e1117; padding:20px; border-radius:15px; text-align:center; border:1px solid #333; box-shadow: 0 0 30px rgba(0,255,65,0.1);">
        <h3 style="margin:0; color:#888; font-size:1rem;">TOPLAM GLOBAL ANLIK TRAFİK</h3>
        <h1 style="margin:0; color:#ffe600; font-size:4.5rem; font-family:sans-serif;">{toplam_global_hit}</h1>
    </div>
""", unsafe_allow_html=True)

# 60 Saniye Yenileme
time.sleep(60)
st.rerun()
