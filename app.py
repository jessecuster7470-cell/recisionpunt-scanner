import streamlit as st
import requests
import datetime
import time
import pandas as pd

# --- KONFIGURATION ---
st.set_page_config(page_title="PrecisionPunt Predictor Pro", page_icon="⚽", layout="wide")

try:
    API_KEY = st.secrets["MY_API_KEY"]
except:
    st.error("Fehler: MY_API_KEY nicht in den Streamlit Secrets gefunden!")
    st.stop()

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}

LEAGUE_IDS = [
    78, 79, 207, 208, 88, 89, 90, 80, 144, 119, 120, 121, 179, 318, 
    40, 41, 42, 43, 46, 47, 48, 103, 104, 105, 113, 114, 115, 244, 245, 
    307, 308, 383, 384, 301, 276, 355, 188, 189, 204, 205, 295, 296, 110, 285, 231, 252
]

def get_detailed_stats(team_id, side):
    url = f"{BASE_URL}/fixtures?team={team_id}&last=10&status=FT"
    try:
        res = requests.get(url, headers=HEADERS).json()
        time.sleep(0.4)
        stats = {"over05_1h": 0, "over15": 0, "over25": 0, "goal_2h": 0, "count": 0}
        
        for f in res.get("response", []):
            if f["teams"][side]["id"] == team_id:
                h1 = (f["score"]["halftime"]["home"] or 0) + (f["score"]["halftime"]["away"] or 0)
                total = (f["goals"]["home"] or 0) + (f["goals"]["away"] or 0)
                h2 = total - h1
                
                if h1 > 0: stats["over05_1h"] += 1
                if total > 1.5: stats["over15"] += 1
                if total > 2.5: stats["over25"] += 1
                if h2 > 0: stats["goal_2h"] += 1
                
                stats["count"] += 1
                if stats["count"] == 5: break
        return stats
    except: return None

# --- UI ---
st.title("⚽ PrecisionPunt Predictor & Tracker")
st.markdown("Analysiere Spiele, finde **⭐ STAR PICKS** und exportiere sie für dein Tracking.")

col1, col2 = st.columns(2)
with col1:
    target_date = st.date_input("Datum wählen", datetime.date.today())
with col2:
    min_prob = st.slider("Filter: Min. Ü1.5 Wahrscheinlichkeit (%)", 50, 100, 75)

if st.button("🚀 Analyse starten & Export vorbereiten"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    date_str = target_date.strftime('%Y-%m-%d')
    
    for i, l_id in enumerate(LEAGUE_IDS):
        status_text.text(f"Scanne Liga {l_id}...")
        url = f"{BASE_URL}/fixtures?league={l_id}&date={date_str}&season=2025"
        res = requests.get(url, headers=HEADERS).json()
        matches = res.get("response", []) or []
        
        if not matches:
            url = f"{BASE_URL}/fixtures?league={l_id}&date={date_str}&season=2026"
            res = requests.get(url, headers=HEADERS).json()
            matches = res.get("response", []) or []

        for m in matches:
            h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
            h_stats = get_detailed_stats(h_id, "home")
            a_stats = get_detailed_stats(a_id, "away")
            
            if h_stats and a_stats and h_stats["count"] > 0:
                p_05_1h = (h_stats["over05_1h"] + a_stats["over05_1h"]) * 10
                p_15 = (h_stats["over15"] + a_stats["over15"]) * 10
                p_25 = (h_stats["over25"] + a_stats["over25"]) * 10
                p_g2h = (h_stats["goal_2h"] + a_stats["goal_2h"]) * 10
                
                if p_15 >= min_prob:
                    is_star = "⭐ STAR PICK" if p_15 >= 90 and p_05_1h >= 80 else ""
                    
                    results.append({
                        "Status": is_star,
                        "Match": f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
                        "Ü1.5 %": p_15,
                        "Ü0.5 1.HZ %": p_05_1h,
                        "Ü2.5 %": p_25,
                        "Tor 2.HZ %": p_g2h,
                        "Liga": m["league"]["name"],
                        "Datum": date_str
                    })
        
        progress_bar.progress((i + 1) / len(LEAGUE_IDS))

    status_text.empty()
    if results:
        # In DataFrame umwandeln für bessere Handhabung
        df = pd.DataFrame(results)
        
        # Sortieren: Erst Star Picks, dann nach Ü1.5 %
        df = df.sort_values(by=["Status", "Ü1.5 %"], ascending=[False, False])
        
        # Tabelle anzeigen
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # DOWNLOAD BEREICH
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Ergebnisse als CSV herunterladen",
                data=csv,
                file_name=f"precisionpunt_{date_str}.csv",
                mime='text/csv',
            )
            
        with col_dl2:
            star_picks_only = df[df["Status"] == "⭐ STAR PICK"]
            if not star_picks_only.empty:
                csv_stars = star_picks_only.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="🌟 Nur STAR PICKS herunterladen",
                    data=csv_stars,
                    file_name=f"stars_{date_str}.csv",
                    mime='text/csv',
                )

        # WhatsApp Block
        st.subheader("📋 Kurzbericht")
        copy_text = f"⚽ PRECISIONPUNT ANALYSIS {date_str} ⚽\n"
        for _, r in df.head(15).iterrows():
            prefix = "⭐ " if r['Status'] else "🔹 "
            copy_text += f"\n{prefix}{r['Ü1.5 %']}% | {r['Match']}"
        st.text_area("", copy_text, height=200)
    else:
        st.warning("Keine Spiele gefunden.")
