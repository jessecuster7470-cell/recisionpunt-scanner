import streamlit as st
import requests
import datetime
import time

# --- KONFIGURATION ---
st.set_page_config(page_title="PrecisionPunt Scanner", page_icon="⚽")

# Lädt den Key unsichtbar aus den Streamlit Secrets
API_KEY = st.secrets["MY_API_KEY"]
BASE_URL = "https://v3.football.api-sports.io"

LEAGUE_IDS = [
    78, 79, 207, 208, 88, 89, 90, 80, 144, 119, 120, 121, 179, 318, 
    40, 41, 42, 43, 46, 47, 48, 103, 104, 105, 113, 114, 115, 244, 245, 
    307, 308, 383, 384, 301, 276, 355, 188, 189, 204, 205, 295, 296, 110, 285, 231, 252
]

def get_points(goals):
    if goals is None: return 0
    if goals >= 3: return 3
    if goals == 2: return 2
    if goals == 1: return 1
    return 0

def get_form(team_id, headers):
    url = f"{BASE_URL}/fixtures?team={team_id}&last=5&status=FT"
    try:
        res = requests.get(url, headers=headers).json()
        time.sleep(1.0) # Schutz vor Rate-Limit
        pts = 0
        for f in res.get("response", []):
            g = (f["goals"]["home"] or 0) + (f["goals"]["away"] or 0)
            pts += get_points(g)
        return pts
    except: return 0

# --- UI ---
st.title("⚽ PrecisionPunt Scanner")
st.markdown("Filtert Spiele basierend auf der Tor-Form (24-Punkte-Regel).")

col1, col2 = st.columns(2)
with col1:
    target_date = st.date_input("Spieltag wählen", datetime.date.today())
with col2:
    min_score = st.number_input("Mindestpunktzahl", value=24)

if st.button("🚀 Scan starten"):
    if not API_KEY:
        st.error("Bitte gib deinen API-Key in der Seitenleiste ein!")
    else:
        headers = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}
        date_str = target_date.strftime('%Y-%m-%d')
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, l_id in enumerate(LEAGUE_IDS):
            status_text.text(f"Scanne Liga {l_id}...")
            url = f"{BASE_URL}/fixtures?league={l_id}&date={date_str}&season=2025"
            res = requests.get(url, headers=headers).json()
            
            for m in res.get("response", []):
                h_id, h_name = m["teams"]["home"]["id"], m["teams"]["home"]["name"]
                a_id, a_name = m["teams"]["away"]["id"], m["teams"]["away"]["name"]
                
                h_p = get_form(h_id, headers)
                a_p = get_form(a_id, headers)
                total = h_p + a_p
                
                if total >= min_score:
                    results.append({
                        "Punkte": total,
                        "Spiel": f"{h_name} vs {a_name}",
                        "Liga": m["league"]["name"]
                    })
            
            progress_bar.progress((i + 1) / len(LEAGUE_IDS))
        
        status_text.text("Scan abgeschlossen!")
        
        if results:
            st.success(f"{len(results)} Treffer gefunden!")
            st.table(results)
        else:

            st.warning("Keine Treffer gefunden.")
