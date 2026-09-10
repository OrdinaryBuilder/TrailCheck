import streamlit as st
import requests
import time
from datetime import date, timedelta

# --- 1. PAGE SETUP & TACTICAL CSS ---
st.set_page_config(page_title="TrailCheck", page_icon="🧭", layout="wide")

custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    .stApp {
        background-color: #050505;
        background-image: linear-gradient(rgba(5, 5, 5, 0.85), rgba(5, 5, 5, 0.95)), url("https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=2000&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'JetBrains Mono', monospace;
        color: #d1d1d1;
    }
    .block-container {
        padding-top: 4rem;
        padding-bottom: 4rem;
        max-width: 95%; 
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input {
        background-color: rgba(18, 18, 18, 0.9) !important;
        border: 1px solid #333 !important;
        color: #f39c12 !important;
        border-radius: 0px !important; 
    }
    .stButton>button {
        background-color: transparent !important;
        border: 1px solid #f39c12 !important;
        color: #f39c12 !important;
        border-radius: 0px !important;
        text-transform: uppercase;
        font-weight: bold;
        letter-spacing: 1px;
        transition: 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #f39c12 !important;
        color: #050505 !important;
    }
    
    /* Extra spacing and separation for daily matrix blocks */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
        background-color: rgba(15, 15, 18, 0.6);
        border: 1px solid #222;
        padding: 24px;
        margin-bottom: 30px;
    }

    text-shadow: 0px 0px 4px rgba(243, 156, 18, 0.4);
    #MainMenu, footer, header {visibility: hidden;}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. SESSION STATE & VARIABLES ---
if "search_active" not in st.session_state:
    st.session_state.search_active = False

today = date.today()
max_allowed_date = today + timedelta(days=14)

# --- 3. DASHBOARD HEADER & INPUTS ---
# --- 3. DASHBOARD HEADER & INPUTS ---
st.markdown("<h1 style='color: #f39c12; text-transform: uppercase; letter-spacing: 2px;'>TRAILCHECK</h1>", unsafe_allow_html=True)

# Wrap inputs and button inside a form so pressing ENTER works instantly
with st.form(key="search_form"):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        city_input = st.text_input("ENTER TRAILHEAD", placeholder="e.g., Kathmandu")
    with col2:
        start_date = st.date_input("START DATE", min_value=today, max_value=max_allowed_date)
    with col3:
        end_date = st.date_input("END DATE", min_value=start_date, max_value=max_allowed_date)

    submit_button = st.form_submit_button("INITIATE UPLINK", use_container_width=True)

if submit_button and city_input:
    st.session_state.search_active = True
# --- 4. MAIN LOGIC ENGINE ---
if st.session_state.search_active and city_input:
    
    # Terminal Boot Sequence
    status_text = st.empty()
    status_text.code("SYS: ESTABLISHING SATELLITE UPLINK...")
    time.sleep(0.3)
    status_text.code("SYS: DECRYPTING ATMOSPHERIC DATA...")
    time.sleep(0.3)
    status_text.empty()

    # Geocoding API
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_input}&count=10&language=en&format=json"
    response = requests.get(geo_url).json()
    locations = response.get("results", [])
    
    if len(locations) == 0:
        st.error(f"COULD NOT LOCATE COORDINATES FOR '{city_input}'. VERIFY SPELLING.")
        st.stop()
        
    elif len(locations) > 1:
        st.warning(f"AMBIGUITY DETECTED: {len(locations)} MATCHES. SPECIFY TARGET:")
        loc_options = {
            f"{loc.get('name')}, {loc.get('admin1', '')}, {loc.get('country', '')}": loc 
            for loc in locations
        }
        selected_loc_name = st.selectbox(
            "MATCH LIST:", 
            list(loc_options.keys()),
            index=None,
            placeholder="Awaiting manual override..."
        )
        if selected_loc_name is None:
            st.stop()
        target_location = loc_options[selected_loc_name]
        
    else:
        target_location = locations[0]
        
    lat = target_location["latitude"]
    lon = target_location["longitude"]
    
    # Weather API
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,uv_index_max,wind_speed_10m_max&timezone=auto&start_date={start_date}&end_date={end_date}"
    weather_res = requests.get(weather_url).json()
    daily = weather_res.get("daily", {})
    
    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precip_probs = daily.get("precipitation_probability_max", [])
    precip_sums = daily.get("precipitation_sum", [])
    wind_speeds = daily.get("wind_speed_10m_max", [])
    
    # Decision Matrix Loop
    parsed_days = []
    packing_list = set()
    
    for i in range(len(dates)):
        t_max = max_temps[i]
        t_min = min_temps[i]
        p_prob = precip_probs[i]
        p_sum = precip_sums[i]
        wind = wind_speeds[i]
        
        # Calculate Threat Score
        rain_factor = (p_prob / 100) * 6.0
        wind_factor = (min(wind / 100, 1.0)) * 4.0
        threat_score = round(rain_factor + wind_factor, 1)

        # Apply Thresholds
        if p_prob > 30 or p_sum > 2:
            verdict = "CRITICAL: Mandatory rain covers and waterproof boots."
            packing_list.add("Waterproof pack cover")
            packing_list.add("Lightweight rain jacket / poncho")
            packing_list.add("Waterproof gaiters or extra synthetic socks")
        elif wind > 25:
            verdict = "WARNING: Breezy ridgeline conditions; windproof shell required."
            packing_list.add("Windproof shell jacket")
            packing_list.add("Neck gaiter / buff")
        elif t_min <= 10:
            verdict = "WARNING: Cold conditions; thermal layers required."
            packing_list.add("Thermal base layers (merino wool or synthetic)")
            packing_list.add("Fleece mid-layer / packable down jacket")
            packing_list.add("Insulated beanie & gloves")
        elif t_max > 35:
            verdict = "CRITICAL: Extreme heat; early morning start strongly advised."
            packing_list.add("Wide-brim sun hat & UV sunglasses")
            packing_list.add("Electrolyte powder packets")
            packing_list.add("High SPF sunblock (50+)")
        else:
            verdict = "CLEAR: Prime trail conditions. Standard gear sufficient."

        parsed_days.append({
            "date": dates[i],
            "verdict": verdict,
            "t_max": t_max,
            "t_min": t_min,
            "wind": wind,
            "rain_prob": p_prob,
            "threat_score": threat_score
        })

    # --- 5. UI RENDERING ---
    st.markdown("---")
    st.caption(f"UPLINK ESTABLISHED | COORDS: {lat:.4f}° N, {lon:.4f}° E")
    st.markdown(f"## {target_location['name'].upper()} REGION")
    
    if any("rain covers" in day["verdict"] for day in parsed_days):
        st.error("WET CONDITIONS DETECTED. WATERPROOF GEAR MANDATORY.")
    elif any("Extreme heat" in day["verdict"] for day in parsed_days):
        st.warning("HIGH HEAT DETECTED. PLAN FOR EARLY STARTS.")
    else:
        st.success("TRAIL CONDITIONS OPTIMAL.")

    # Modular Loadout with Spacing
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### EXPEDITION LOADOUT")
    colA, colB = st.columns(2)
    with colA:
        st.markdown("**STANDARD ISSUE**")
        st.markdown("- Sturdy trail shoes\n- Moisture-wicking base layers\n- Hydration bladder\n- First aid kit")
    with colB:
        st.markdown("**ENVIRONMENTAL ADDITIONS**")
        if len(packing_list) > 0:
            for item in sorted(list(packing_list)):
                st.markdown(f"- {item}")
        else:
            st.caption("No specialized gear required for this operational window.")

    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### DAILY TRAIL MATRIX")
    st.markdown("<br>", unsafe_allow_html=True)

    # Flat Grid Loop with Enhanced Box Spacing
    for day in parsed_days:
        with st.container():
            st.markdown(f"### {day['date']} | THREAT RATING: {day['threat_score']}/10.0")
            st.info(f"{day['verdict']}")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.metric("Max Temp", f"{day['t_max']}°C")
            with col2:
                st.metric("Min Temp", f"{day['t_min']}°C")
            with col3:
                st.caption(f"Precipitation: {day['rain_prob']}%")
                st.progress(day['rain_prob'] / 100)
                st.caption(f"Wind Velocity: {day['wind']} km/h")
                st.progress(min(day['wind'] / 100, 1.0))
        
        # Generous vertical spacing between cards
        st.markdown("<br>", unsafe_allow_html=True)