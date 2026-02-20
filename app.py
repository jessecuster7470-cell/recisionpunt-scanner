import streamlit as st
import requests
import datetime
import time

# --- KONFIGURATION ---
st.set_page_config(page_title="PrecisionPunt DeepDive", page_icon="⚽", layout="wide")

# Lädt den Key unsichtbar aus den Streamlit Secrets
try:
    API_KEY = st.secrets["MY_API_KEY"]
except:
    st.error("Fehler: MY_API_KEY wurde nicht in den Streamlit Secrets gefunden!")
    st.stop()

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}

LEAGUE_IDS = [
    78, 79, 207, 208, 88, 89, 90, 80, 144, 119, 120, 121, 179, 318, 
    40, 41, 42, 43, 46, 47, 48, 103, 104, 105, 113, 114, 115, 244, 245, 
    307, 308, 383, 384, 301, 276, 355, 188, 189, 204, 205, 295, 296, 110, 285, 231, 252
]

def get_points(goals):
    if goals is None: return 0
    return 3 if goals >= 3 else (2 if goals == 2 else (1 if goals == 1 else 0))

def get_specialized_form(team_id, side):
    """Holt die Form basierend auf Heim- ODER Auswärtsspielen"""
    url = f"{BASE_URL}/fixtures?team={team_id}&last=10&status=FT"
    try:
        res = requests.get(url, headers=HEADERS).json()
        time.sleep(0.4)
        pts = 0
        count = 0
        for f in res.get("response", []):
            if f["teams"][side]["id"] == team_id:
                g = (f["goals"]["home"] or 0) + (f["goals"]["away"] or 0)
                pts += get_points(g)
                count += 1
                if count == 5: break # Die letzten 5 relevanten Spiele
        return pts
    except: return 0

def get_h2h_info(team1, team2):
    """Prüft die letzten direkten Duelle"""
    url = f"{BASE_URL}/fixtures/headtohead?h2h={team1}-{team2}&last=5"
    try:
        res = requests.get(url, headers=HEADERS).json()
        time.sleep(0.4)
        total_goals = 0
        matches = res.get("response", [])
        if not matches: return "Keine Daten"
        for m in matches:
            total_goals += (m["goals"]["home"] or 0) + (m["goals"]["away"] or 0)
        avg = total_goals / len(matches)
        return "✅" if avg >= 2.5 else "❌"
    except: return "?"

# --- UI ---
st.title("⚽ PrecisionPunt DeepDive Scanner")
st.markdown("Analyse-Fokus: Heimform (Heimteam) vs. Auswärtsform (Gastteam) + H2H Check.")

col1, col2 = st.columns(2)
with col1:
    target_date = st.date_input("Datum wählen", datetime.date.today())
with col2:
    min_score = st.slider("Mindest-Gesamt-Score", 15, 30, 22)

if st.button("🚀 DeepDive Analyse starten"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    date_str = target_date.strftime('%Y-%m-%d')
    
    for i, l_id in enumerate(LEAGUE_IDS):
        status_text.text(f"Scanne Liga {l_id}...")
        url = f"{BASE_URL}/fixtures?league={l_id}&date={date_str}&season=2025"
        res = requests.get(url, headers=HEADERS).json()
        matches = res.get("response", [])
        
        if not matches:
            url = f"{BASE_URL}/fixtures?league={l_id}&date={date_str}&season=2026"
            res = requests.get(url, headers=HEADERS).json()
            matches = res.get("response", [])

        for m in matches:
            h_id, a_id = m["teams"]["home"]["id"], m["teams"]["away"]["id"]
            h_name, a_name = m["teams"]["home"]["name"], m["teams"]["away"]["name"]
            
            # Spezialisierte Form abrufen
            h_p = get_specialized_form(h_id, "home")
            a_p = get_specialized_form(a_id, "away")
            total = h_p + a_p
            
            if total >= min_score:
                h2h = get_h2h_info(h_id, a_id)
                results.append({
                    "Punkte": total,
                    "Heim (H)": f"{h_p} Pkt",
                    "Gast (A)": f"{a_p} Pkt",
                    "Spiel": f"{h_name} vs {a_name}",
                    "H2H > 2.5": h2h,
                    "Liga": m["league"]["name"]
                })
        
        progress_bar.progress((i + 1) / len(LEAGUE_IDS))

    status_text.success("DeepDive abgeschlossen!")
    
    if results:
        # Sortieren nach höchster Punktzahl
        results = sorted(results, key=lambda x: x['Punkte'], reverse=True)
        st.table(results)
        
        copy_text = "⚽ PRECISIONPUNT PICKS ⚽\n"
        for r in results:
            copy_text += f"\n🔥 {r['Punkte']} Pkt | {r['Spiel']} | H2H: {r['H2H > 2.5']}"
        st.text_area("Ergebnisse zum Kopieren:", copy_text, height=200)
    else:
        st.warning("Keine Treffer mit diesen Kriterien gefunden.")

