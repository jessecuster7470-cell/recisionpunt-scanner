import streamlit as st
import requests
import datetime
import time
import pandas as pd

# --- KONFIGURATION ---
st.set_page_config(page_title="PrecisionPunt DeepDive Pro", page_icon="⚽", layout="wide")

try:
    API_KEY = st.secrets["MY_API_KEY"]
except:
    st.error("Fehler: MY_API_KEY nicht in den Secrets gefunden!")
    st.stop()

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}

LEAGUE_IDS = [78, 79, 207, 208, 88, 89, 90, 80, 144, 119, 120, 121, 179, 318, 40, 41, 42, 43, 46, 47, 48, 103, 104, 105, 113, 114, 115, 244, 245, 307, 308, 383, 384, 301, 276, 355, 188, 189, 204, 205, 295, 296, 110, 285, 231, 252]

def get_points(goals):
    if goals is None: return 0
    return 3 if goals >= 3 else (2 if goals == 2 else (1 if goals == 1 else 0))

def get_detailed_stats(team_id, side):
    url = f"{BASE_URL}/fixtures?team={team_id}&last=10&status=FT"
    try:
        res = requests.get(url, headers=HEADERS).json()
        time.sleep(0.4)
        stats = {"pts": 0, "over05_1h": 0, "over15": 0, "over25": 0, "goal_2h": 0, "count": 0}
        for f in res.get("response", []):
            if f["teams"][side]["id"] == team_id:
                # Tore 1. HZ & Gesamt
                h1 = (f["score"]["halftime"]["home"] or 0) + (f["score"]["halftime"]["away"] or 0)
                total = (f["goals"]["home"] or 0) + (f["goals"]["away"] or 0)
                h2 = total - h1
                
                # Punkte berechnen (altes System)
                stats["pts"] += get_points(total)
                
                # Prozente tracken
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

col1, col2 = st.columns(2)
with col1:
    target_date = st.date_input("Datum wählen", datetime.date.today())
with col2:
    min_score = st.slider("Filter: Mindest-Punkte (Form)", 15, 30, 24)

if st.button("🚀 Analyse starten"):
    results = []
    progress_bar = st.progress(0)
    date_str = target_date.strftime('%Y-%m-%d')
    
    for i, l_id in enumerate(LEAGUE_IDS):
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
                total_pts = h_stats["pts"] + a_stats["pts"]
                
                if total_pts >= min_score:
                    # Wahrscheinlichkeiten berechnen
                    p_05_1h = (h_stats["over05_1h"] + a_stats["over05_1h"]) * 10
                    p_15 = (h_stats["over15"] + a_stats["over15"]) * 10
                    p_25 = (h_stats["over25"] + a_stats["over25"]) * 10
                    p_g2h = (h_stats["goal_2h"] + a_stats["goal_2h"]) * 10
                    
                    is_star = "⭐" if total_pts >= 27 and p_15 >= 90 else ""
                    
                    results.append({
                        "Pkt": total_pts,
                        "H": f"{h_stats['pts']} Pkt",
                        "A": f"{a_stats['pts']} Pkt",
                        "Spiel": f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
                        "FHG %": f"{p_05_1h}%",
                        "Ü1.5 %": f"{p_15}%",
                        "Ü2.5 %": f"{p_25}%",
                        "SHG %": f"{p_g2h}%",
                        "Star": is_star,
                        "Liga": m["league"]["name"]
                    })
        progress_bar.progress((i + 1) / len(LEAGUE_IDS))

    if results:
        df = pd.DataFrame(results).sort_values(by="Pkt", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # CSV Downloads
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Ergebnisse speichern (CSV)", data=csv, file_name=f"precision_{date_str}.csv", mime='text/csv')
    else:
        st.warning("Keine Treffer mit dieser Punktzahl gefunden.")
