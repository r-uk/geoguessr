import json
import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_plotly_events import plotly_events
import markdown

# MUST be the first Streamlit command
st.set_page_config(layout="wide")

@st.cache_data
def load_countries(path="countries.json"):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)

    rows = []
    for iso3, r in d.items():
        lc = r.get("landcover") or {}
        ts = r.get("temp_seas") or {}
        tas_seas = ts.get("tas") or {}

        rows.append({
            "iso3": iso3,
            "country": r.get("country"),
            "hemisphere": r.get("hemisphere"),

            "lat": r.get("lat"),
            "area_wf": r.get("area_wf"),
            "coast_to_area_wri": r.get("coast_to_area_wri"),

            "lc_forest_pct": lc.get("forest_pct"),
            "lc_agri_pct": lc.get("agri_pct"),
            "lc_urban_pct_of_land": lc.get("urban_pct_of_land"),
            "lc_water_pct_of_surface": lc.get("water_pct_of_surface"),

            "tas": r.get("tas"),
            "tasmin": r.get("tasmin"),
            "tasmax": r.get("tasmax"),
            "pr": r.get("pr"),

            "hd30": r.get("hd30"),
            "hd40": r.get("hd40"),
            "id": r.get("id"),
            "txx": r.get("txx"),
            "r20mm": r.get("r20mm"),

            "pov320": r.get("pov320"),
            "popcount": r.get("popcount"),
            "popdensity": r.get("popdensity"),

            "tas_djf": tas_seas.get("dez-feb"),
            "tas_mam": tas_seas.get("mar-may"),
            "tas_jja": tas_seas.get("jun_aug"),
            "tas_son": tas_seas.get("sep-nov"),
        })

    return d, pd.DataFrame(rows)


countries, df = load_countries(
    "/Users/larspehoviak/Documents/Master/WiSe25_26/RMD/Geoguessr/countries.json"
)

left, right = st.columns([2, 1])
if "phase" not in st.session_state:
    st.session_state.phase = "guess"          # "guess" | "reveal"
    st.session_state.pending_guess = None
    st.session_state.score = 0
    st.session_state.rounds_played = 0
    st.session_state.target_iso3 = df["iso3"].sample(1).iloc[0]
    st.session_state.last_result = "–"
    st.session_state.last_guess = None
    st.session_state.last_target = None


with left:
    phase = st.session_state.phase

    # ---------- build figure ----------
    if phase == "guess":
        fig = px.choropleth(
            df,
            locations="iso3",
            hover_name="country",
            hover_data={"lat": True},
            projection="natural earth",
        )

        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False)

        if clicked:
            ev = clicked[0]
            # For choropleth, plotly usually gives the clicked ISO3 in "location"
            guess_iso3 = ev.get("location")

            # Fallback if location isn't present (less reliable)
            if not guess_iso3 and ev.get("pointNumber") is not None:
                guess_iso3 = df.iloc[int(ev["pointNumber"])]["iso3"]

            st.session_state.pending_guess = guess_iso3
            guess0 = st.session_state.pending_guess
            st.write("Selected:", countries[guess0]["country"])

        if st.button("Confirm choice", disabled=not st.session_state.pending_guess):
            guess = st.session_state.pending_guess
            target = st.session_state.target_iso3
            correct = (guess == target)

            st.session_state.last_guess = guess
            st.session_state.last_target = target
            st.session_state.last_result = "Correct!" if correct else "False!"
            st.session_state.rounds_played += 1
            if correct:
                st.session_state.score += 1

            st.session_state.phase = "reveal"
            st.rerun()

    else:  # ---------- reveal ----------
        guess = st.session_state.last_guess
        target = st.session_state.last_target

        dfx = df[["iso3", "country"]].copy()
        dfx["status"] = "neutral"

        if guess == target:
            dfx.loc[dfx["iso3"] == target, "status"] = "target"
        else:
            dfx.loc[dfx["iso3"] == guess, "status"] = "guess_wrong"
            dfx.loc[dfx["iso3"] == target, "status"] = "target"

        fig = px.choropleth(
            dfx,
            locations="iso3",
            color="status",
            hover_name="country",
            projection="natural earth",
            category_orders={"status": ["neutral", "guess_wrong", "target"]},
            color_discrete_map={
                "neutral": "#cfcfcf",
                "guess_wrong": "#d62728",
                "target": "#2ca02c",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

        if st.button("Next round"):
            st.session_state.target_iso3 = df["iso3"].sample(1).iloc[0]
            st.session_state.pending_guess = None
            st.session_state.phase = "guess"
            st.rerun()
        
        with st.container(border=True):
            t1, t2 = st.columns(2)
            t1.markdown(f"### Your guess: **{countries[guess]["country"]}**")
            t2.markdown(f"### Correct guess: **{countries[target]["country"]}**")

    # ---------- scoreboard ----------
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"### Score: **{st.session_state.score}**")
        c2.markdown(f"### Rounds: **{st.session_state.rounds_played}**")
        c3.markdown(f"### Last round was: **{st.session_state.get('last_result','–')}**")



with right:
    tiso = st.session_state.target_iso3
    t = df.loc[df["iso3"] == tiso].iloc[0]  # one row, flattened columns

    def fmt(x, nd=1):
        return "—" if pd.isna(x) else round(float(x), nd)

    #st.write("ISO:", t["iso3"])
    st.write("Hemisphere:", t["hemisphere"])
    st.write("Mean temp (°C):", fmt(t["tas"], 1))
    st.write("Annual precip (mm):", fmt(t["pr"], 0))

    # geo
    st.write("Lat:", fmt(t["lat"], 1))
    st.write("Area (km^2):", fmt(t["area_wf"], 0))
    st.write("Coast/Area (km/km^2):", fmt(t["coast_to_area_wri"], 3))

    # landcover
    st.write("Forest Lancover (%):", fmt(t["lc_forest_pct"], 1))
    st.write("Agri Lancover (%):", fmt(t["lc_agri_pct"], 1))
    st.write("Urban Lancover (%):", fmt(t["lc_urban_pct_of_land"], 2))
    st.write("Waterbodies Lancover (%):", fmt(t["lc_water_pct_of_surface"], 2))

    # extremes / socio (optional)
    st.write("Hot days >30:", fmt(t["hd30"], 0))
    st.write("Frost days <0:", fmt(t["id"], 0))
    st.write("Pop density (pop/km^2):", fmt(t["popdensity"], 1))
    st.write("Pop annual wage <3,20$ (%)", fmt(t["id"], 0))

    # seasonal (optional)
    st.write("Temp Dez-Feb:", fmt(t["tas_djf"], 1))
    st.write("Temp Mar-May:", fmt(t["tas_mam"], 1))
    st.write("Temp Jun-Aug:", fmt(t["tas_jja"], 1))
    st.write("Temp Sep-Nov:", fmt(t["tas_son"], 1))