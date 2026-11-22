"""CivicPulse AI: Autonomous Infrastructure Triage & Citizen Grievance Tracker."""

from __future__ import annotations

import uuid
from pathlib import Path
import re
import json
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from ai_engine import analyze_complaint_ai, verify_proof_of_work
from database import (
    add_complaint,
    find_matching_complaint,
    get_all_complaints,
    get_complaint_by_id,
    get_or_create_user,
    increment_duplicate_report,
    init_db,
    login_user_with_password,
    login_with_google_sim,
    record_citizen_report,
    register_user_with_password,
    resolve_complaint_with_proof,
)

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "uploads"
OFFICER_SECRET_PASSCODE = "GOVT2026"
NAV_PUBLIC = "Public Dashboard"
NAV_MAP = "Live India Civic Map"
NAV_FEED = "Live Feed"
NAV_TRACK = "Track Complaint"
NAV_REPORT = "Submit a Report"
NAV_WALLET = "My Rewards & Wallet"
NAV_OFFICER = "Municipal Officer Portal"
NAV_HELPLINE = "24/7 Civic Helpline"
NAV_RECEIPT = "Download Report Receipt"
OPEN_COMPLAINT_STATUSES = {
    "Pending", "Open", "In Progress", "Assigned to Mandal/District Office",
    "Escalated to Central Municipal HQ",
}
PAGE_ICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect x='6' y='6' width='52' height='52' rx='14' fill='%23a563db'/%3E"
    "%3Cpath d='M32 11c-10 0-17 7-17 16 0 12 17 26 17 26s17-14 17-26c0-9-7-16-17-16Z' "
    "fill='none' stroke='%23ffffff' stroke-width='3'/%3E"
    "%3Ccircle cx='32' cy='27' r='4' fill='none' stroke='%23ffffff' stroke-width='3'/%3E"
    "%3Cpath d='M22 39h5l3-5 4 10 3-5h5' fill='none' stroke='%23ffffff' stroke-width='3' "
    "stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E"
)
CIVIC_ICON_SVG = (
    '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/>'
    '<circle cx="12" cy="10" r="2"/>'
    '<path d="M7.5 16h2l1.4-2.5 2 5 1.5-2.5h2.1"/>'
    '</svg>'
)
NAV_ICONS = {
    NAV_PUBLIC: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/></svg>',
    NAV_MAP: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    NAV_FEED: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l2.5-6 4 12 3-8 2 3h4.5"/></svg>',
    NAV_TRACK: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.8" cy="10.8" r="7.2"/><path d="m16.2 16.2 4.3 4.3"/></svg>',
    NAV_REPORT: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M14 3v5h5M12 12v6m-3-3h6"/></svg>',
    NAV_WALLET: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 9h18m-7 5h.01"/><circle cx="16" cy="14" r="2.5"/></svg>',
    NAV_OFFICER: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 20 6v5c0 5-3.4 8.2-8 10-4.6-1.8-8-5-8-10V6l8-3Z"/></svg>',
    NAV_HELPLINE: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 13v-2a9 9 0 0 1 18 0v2"/><rect x="3" y="12" width="4" height="7" rx="2"/><rect x="17" y="12" width="4" height="7" rx="2"/><path d="M17 19a5 5 0 0 1-5 3h-1"/></svg>',
    NAV_RECEIPT: '<svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true" stroke="currentColor" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 8h6M9 12h6"/><path d="M12 15v3m-2-2 2 2 2-2"/></svg>',
}
NAV_OPTIONS = (
    NAV_PUBLIC,
    NAV_MAP,
    NAV_FEED,
    NAV_TRACK,
    NAV_REPORT,
    NAV_WALLET,
    NAV_OFFICER,
    NAV_HELPLINE,
    NAV_RECEIPT,
)

st.set_page_config(
    page_title="CivicPulse AI",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #231436; }
    .stApp { background: linear-gradient(180deg, #f3ebfc 0%, #faf7fe 45%, #ffffff 100%); }
    [data-testid="stMainBlockContainer"] { padding-top: 3.2rem !important; }
    h1, h2, h3, h4, h5, h6,
    [data-testid="stHeading"] h1, [data-testid="stHeading"] h2,
    [data-testid="stHeading"] h3 {
      font-family: 'Manrope', sans-serif; color: #231436 !important;
      font-weight: 750; line-height: 1.25; letter-spacing: -0.02em;
      margin-top: 1.1rem; margin-bottom: .65rem;
    }
    [data-testid="stMarkdownContainer"] { color: #231436; }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] { color: #4b3b5f !important; }
    [data-testid="stMetric"] {
      background: #ffffff; border: 1px solid #c9a6eb; border-radius: 14px;
      padding: .8rem 1rem; box-shadow: 0 1px 2px #2314360A;
    }
    [data-testid="stMetricLabel"] p { color: #4b3b5f !important; font-weight: 650; }
    [data-testid="stMetricValue"] { color: #231436 !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #ffffff 0%, #f1e6fc 100%); }
    [data-testid="stSidebar"] * { color: #231436; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #4b3b5f !important; }
    [data-testid="stTextInput"] label, [data-testid="stTextArea"] label,
    [data-testid="stFileUploader"] label, [data-testid="stSelectbox"] label {
      color: #231436 !important; font-weight: 650;
    }
    div.stButton > button, div.stFormSubmitButton > button,
    [data-testid="stFormSubmitButton"] button, [data-testid="stSidebar"] button,
    button[kind="primary"], button[kind="secondary"] {
      background: #ffffff !important; background-color: #ffffff !important; color: #231436 !important;
      border: 1.5px solid #a563db !important; opacity: 1 !important;
      box-shadow: none !important; text-shadow: none !important;
    }
    div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"],
    [data-testid="stSidebar"] button[kind="primary"], button[kind="primary"] {
      background: linear-gradient(135deg, #a563db 0%, #833ec2 100%) !important;
      background-color: #833ec2 !important; color: #ffffff !important;
      border: none !important;
    }
    div.stButton > button:not([kind="primary"]):hover,
    div.stFormSubmitButton > button:not([kind="primary"]):hover,
    [data-testid="stFormSubmitButton"] button:not([kind="primary"]):hover,
    [data-testid="stSidebar"] button:not([kind="primary"]):hover,
    button[kind="secondary"]:hover {
      background: #f3ebfc !important; background-color: #f3ebfc !important; color: #231436 !important;
      border-color: #a563db !important;
    }
    button[kind="primary"]:hover, button[kind="primary"]:focus,
    button[kind="primary"]:focus-visible, button[kind="primary"]:active {
      background: linear-gradient(135deg, #a563db 0%, #833ec2 100%) !important;
      color: #ffffff !important; border-color: #833ec2 !important;
    }
    button[kind="secondary"]:focus, button[kind="secondary"]:focus-visible,
    button[kind="secondary"]:active {
      background:#f3ebfc !important;background-color:#f3ebfc !important;
      color:#231436 !important;border-color:#a563db !important;
    }
    div.stButton > button:not([kind="primary"]):focus,
    div.stFormSubmitButton > button:not([kind="primary"]):focus,
    [data-testid="stFormSubmitButton"] button:not([kind="primary"]):focus,
    [data-testid="stSidebar"] button:not([kind="primary"]):focus {
      background:#f3ebfc !important;background-color:#f3ebfc !important;
      color:#231436 !important;border-color:#a563db !important;
    }
    button:focus-visible { outline: 3px solid #c9a6eb !important; outline-offset: 2px !important; }
    button[kind="primary"] p, button[kind="primary"] span, button[kind="primary"] div,
    button[kind="primary"]:hover p, button[kind="primary"]:hover span, button[kind="primary"]:hover div,
    button[kind="primary"]:focus p, button[kind="primary"]:focus span, button[kind="primary"]:focus div {
      color: #ffffff !important; opacity: 1 !important;
    }
    [data-testid="stSidebar"] button[kind="primary"],
    [data-testid="stSidebar"] button[kind="primary"] p,
    [data-testid="stSidebar"] button[kind="primary"] span,
    [data-testid="stSidebar"] button[kind="primary"] div {
      color: #ffffff !important;
    }
    button[kind="secondary"] p, button[kind="secondary"] span, button[kind="secondary"] div,
    button[kind="secondary"]:hover p, button[kind="secondary"]:hover span, button[kind="secondary"]:hover div,
    button[kind="secondary"]:focus p, button[kind="secondary"]:focus span, button[kind="secondary"]:focus div {
      color:#231436 !important;opacity:1 !important;
    }
    div.stButton > button:not([kind="primary"]) p,
    div.stButton > button:not([kind="primary"]) span,
    div.stButton > button:not([kind="primary"]) div,
    div.stFormSubmitButton > button:not([kind="primary"]) p,
    div.stFormSubmitButton > button:not([kind="primary"]) span,
    div.stFormSubmitButton > button:not([kind="primary"]) div,
    [data-testid="stSidebar"] button:not([kind="primary"]) p,
    [data-testid="stSidebar"] button:not([kind="primary"]) span,
    [data-testid="stSidebar"] button:not([kind="primary"]) div {
      color: #231436 !important; opacity: 1 !important;
    }
    div.stButton > button:not([kind="primary"]):hover p,
    div.stButton > button:not([kind="primary"]):hover span,
    div.stButton > button:not([kind="primary"]):hover div,
    div.stFormSubmitButton > button:not([kind="primary"]):hover p,
    div.stFormSubmitButton > button:not([kind="primary"]):hover span,
    div.stFormSubmitButton > button:not([kind="primary"]):hover div {
      color: #231436 !important;
    }
    div.stButton > button:not([kind="primary"]):focus p,
    div.stButton > button:not([kind="primary"]):focus span,
    div.stButton > button:not([kind="primary"]):focus div,
    button[kind="secondary"]:focus p, button[kind="secondary"]:focus span,
    button[kind="secondary"]:focus div { color:#231436 !important; }
    input, textarea, select, [data-baseweb="input"], [data-baseweb="textarea"],
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea, [data-baseweb="select"] > div {
      background: #ffffff !important; background-color: #ffffff !important;
      color: #231436 !important; border-color: #c9a6eb !important;
      border: 1px solid #c9a6eb !important;
      -webkit-text-fill-color: #231436 !important;
    }
    input::placeholder, textarea::placeholder { color: #6b5a80 !important; opacity: 1 !important; }
    [data-baseweb="select"] * { color:#231436 !important; }
    [data-baseweb="input"] *, [data-baseweb="textarea"] * { background-color:#ffffff !important;color:#231436 !important; }
    input:focus, textarea:focus, select:focus,
    [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within,
    [data-baseweb="select"]:focus-within {
      border-color: #a563db !important; box-shadow: 0 0 0 1px #a563db !important;
    }
    [data-testid="stForm"] { background: #ffffff; border: 1px solid #c9a6eb;
      border-radius: 14px; padding: 1rem; }
    .brand-header { display:flex; align-items:center; gap:.8rem; margin:0 0 1.4rem; }
    .brand-mark { width:46px; height:46px; display:flex; align-items:center;
      justify-content:center; border-radius:14px; background:#ffffff;
      border:1.5px solid #a563db; box-shadow:0 3px 10px #a563db1A; }
    .brand-title { color:#231436; font:800 1.65rem 'Manrope',sans-serif;
      letter-spacing:-.04em; line-height:1.1; }
    .brand-subtitle { color:#4b3b5f; font-size:.9rem; margin-top:.2rem; }
    .sidebar-brand { display:flex;align-items:center;gap:.65rem;padding:.2rem 0 .35rem; }
    .sidebar-brand svg { width:32px;height:32px;stroke:#a563db;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round; }
    .sidebar-brand strong { color:#231436;font:750 1.12rem 'Manrope',sans-serif; }
    .sidebar-nav-icon { color:#833ec2;display:flex;align-items:center;justify-content:center;padding:.25rem 0; }
    .sidebar-nav-icon svg { width:23px;height:23px;color:#833ec2;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round; }
    .sidebar-profile { display:flex;align-items:center;justify-content:space-between;gap:.45rem;
      color:#231436;background:#f3ebfc;border:1px solid #a563db;border-radius:10px;padding:.55rem .65rem;margin:.5rem 0; }
    .sidebar-profile span { display:inline-flex;align-items:center;gap:.35rem;font-size:.82rem;font-weight:600; }
    .sidebar-profile svg { width:17px;height:17px;stroke:#833ec2;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round; }
    .profile-icon { display:inline-flex;width:18px;height:18px;vertical-align:middle;margin-right:.2rem; }
    .profile-icon svg { width:18px;height:18px;stroke:#c9a6eb;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round; }
    .hero { padding: 1.45rem 1.7rem; border:1px solid #833ec2;
      border-radius: 18px; color: #FFFFFF;
      background: linear-gradient(135deg, #a563db 0%, #833ec2 100%); margin-bottom: 1.35rem; }
    .hero-heading { display:flex;align-items:center;gap:.7rem; }
    .hero-icon { display:inline-flex;align-items:center;justify-content:center; }
    .hero-icon svg { width:26px;height:26px;stroke:#ffffff;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round; }
    .hero h1 { color: #FFFFFF !important; margin: 0; font-size: 2rem; }
    .hero p { margin: .45rem 0 0; color: #ffffff !important; }
    .small-muted { color: #4b3b5f; font-size: .92rem; }
    [data-testid="stAlert"] { background:#f3ebfc !important;border:1px solid #c9a6eb !important;color:#231436 !important; }
    [data-testid="stAlert"] * { color:#231436 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="brand-header">
      <div class="brand-mark" aria-hidden="true">
        <span style="display:inline-flex;width:31px;height:31px;color:#833ec2">{CIVIC_ICON_SVG}</span>
      </div>
      <div><div class="brand-title">CivicPulse AI</div>
        <div class="brand-subtitle">Autonomous Infrastructure Triage &amp; Citizen Grievance Tracker</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

init_db()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_upload(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / safe_name
    destination.write_bytes(uploaded_file.getbuffer())
    return str(destination.relative_to(APP_DIR))


def show_hero(title: str, subtitle: str) -> None:
    title_to_nav = {
        "CivicPulse Public Dashboard": NAV_PUBLIC,
        "Live India Civic Map": NAV_MAP,
        "Live Feed": NAV_FEED,
        "Your city, heard.": NAV_REPORT,
        "My Rewards & Wallet": NAV_WALLET,
        "Track Complaint": NAV_TRACK,
        "Municipal Officer Portal": NAV_OFFICER,
    }
    icon = NAV_ICONS.get(title_to_nav.get(title, ""), "")
    st.markdown(
        f'<div class="hero"><div class="hero-heading"><span class="hero-icon">{icon}</span>'
        f'<h1>{escape(title)}</h1></div><p>{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def is_valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()))


INDIA_PLACE_COORDS = {
    "srinagar": (34.0837, 74.7973), "jammu": (32.7266, 74.8570),
    "shimla": (31.1048, 77.1734), "chandigarh": (30.7333, 76.7794),
    "dehradun": (30.3165, 78.0322), "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462), "patna": (25.5941, 85.1376),
    "gangtok": (27.3389, 88.6065), "guwahati": (26.1445, 91.7362),
    "shillong": (25.5788, 91.8933), "imphal": (24.8170, 93.9368),
    "aizawl": (23.7271, 92.7176), "kohima": (25.6751, 94.1086),
    "itanagar": (27.0844, 93.6053), "agartala": (23.8315, 91.2868),
    "bhopal": (23.2599, 77.4126), "indore": (22.7196, 75.8577),
    "ahmedabad": (23.0225, 72.5714), "surat": (21.1702, 72.8311),
    "mumbai": (19.0760, 72.8777), "pune": (18.5204, 73.8567),
    "panaji": (15.4909, 73.8278), "goa": (15.2993, 74.1240),
    "hyderabad": (17.3850, 78.4867), "visakhapatnam": (17.6868, 83.2185),
    "vijayawada": (16.5062, 80.6480), "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946), "mysuru": (12.2958, 76.6394),
    "kochi": (9.9312, 76.2673), "thiruvananthapuram": (8.5241, 76.9366),
    "chennai": (13.0827, 80.2707), "coimbatore": (11.0168, 76.9558),
    "kolkata": (22.5726, 88.3639), "bhubaneswar": (20.2961, 85.8245),
    "ranchi": (23.3441, 85.3096), "raipur": (21.2514, 81.6296),
    "nagpur": (21.1458, 79.0882), "amritsar": (31.6340, 74.8723),
    "new delhi": (28.6139, 77.2090), "delhi": (28.6139, 77.2090),
    "andhra pradesh": (15.9129, 79.7400), "arunachal pradesh": (28.2180, 94.7278),
    "assam": (26.2006, 92.9376), "bihar": (25.0961, 85.3131),
    "chhattisgarh": (21.2787, 81.8661), "goa state": (15.2993, 74.1240),
    "gujarat": (22.2587, 71.1924), "haryana": (29.0588, 76.0856),
    "himachal pradesh": (31.1048, 77.1734), "jharkhand": (23.6102, 85.2799),
    "karnataka": (15.3173, 75.7139), "kerala": (10.8505, 76.2711),
    "madhya pradesh": (22.9734, 78.6569), "maharashtra": (19.7515, 75.7139),
    "manipur": (24.6637, 93.9063), "meghalaya": (25.4670, 91.3662),
    "mizoram": (23.1645, 92.9376), "nagaland": (26.1584, 94.5624),
    "odisha": (20.9517, 85.0985), "punjab": (31.1471, 75.3412),
    "rajasthan": (27.0238, 74.2179), "sikkim": (27.5330, 88.5122),
    "tamil nadu": (11.1271, 78.6569), "telangana": (18.1124, 79.0193),
    "tripura": (23.9408, 91.9882), "uttar pradesh": (26.8467, 80.9462),
    "uttarakhand": (30.0668, 79.0193), "west bengal": (22.9868, 87.8550),
}


def _coordinates_for_location(location: str) -> tuple[float, float, str]:
    normalized = (location or "").casefold()
    for place in sorted(INDIA_PLACE_COORDS, key=len, reverse=True):
        if place in normalized:
            latitude, longitude = INDIA_PLACE_COORDS[place]
            return latitude, longitude, "Approximate city/state center"
    # No report coordinates or geocoder are available; this is only a visible fallback.
    return 22.5937, 78.9629, "No city/state match; shown at India center"


def render_india_civic_map(complaints: list[dict], current_email: str = "") -> None:
    """Render a Leaflet map in an isolated HTML component, without dataframe backends."""
    map_items = []
    for item in complaints:
        latitude, longitude, coordinate_note = _coordinates_for_location(item.get("location", ""))
        map_items.append(
            {
                "id": item.get("id", ""),
                "category": item.get("category", "General Civic Issue"),
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "status": item.get("status", "Pending"),
                "severity": item.get("severity", "Low"),
                "reportCount": item.get("report_count", 1),
                "reportedByYou": bool(current_email)
                and str(item.get("citizen_email") or "").casefold()
                == current_email.casefold(),
                "lat": latitude,
                "lon": longitude,
                "coordinateNote": coordinate_note,
            }
        )
    issues_json = json.dumps(map_items, ensure_ascii=False).replace("<", "\\u003c")
    map_html = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
html,body,#map{height:100%;width:100%;margin:0;font-family:Arial,sans-serif}
#map{min-height:620px;background:#faf7fe}
.leaflet-div-icon{background:transparent;border:none}
.civic-marker{width:18px;height:18px;border:2px solid #fff;border-radius:50%;box-shadow:0 1px 7px #2229;box-sizing:border-box}
.civic-marker.open{background:#e53935}.civic-marker.resolved{background:#833ec2}
.civic-marker.minor{width:12px;height:12px;background:#f4c430}
.civic-marker.high{width:30px;height:30px;background:#f28c28;animation:pulse 1.5s infinite}
.civic-marker.high.critical{background:#8b1e2d}
.civic-marker.mine{width:25px;height:25px;border-radius:50% 50% 50% 0;background:#1976d2;transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;color:#fff;font-size:15px;font-weight:bold}
.civic-marker.mine span{transform:rotate(45deg)}
.civic-marker.mine.resolved{background:#833ec2;border-color:#1976d2;color:#1976d2}
.civic-marker.mine.high{animation:pulse 1.5s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 #f28c2870}70%{box-shadow:0 0 0 12px #f28c2800}100%{box-shadow:0 0 0 0 #f28c2800}}
.legend{background:#fff;padding:10px 12px;border-radius:8px;box-shadow:0 1px 8px #0003;line-height:1.7;color:#263238}
.legend strong{display:block;margin-bottom:3px}.swatch{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:7px;vertical-align:middle;border:1px solid #777}
.legend small{display:block;max-width:205px;color:#667085;line-height:1.35;margin-top:5px}
</style></head><body><div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const issues=__ISSUES_JSON__;
const map=L.map('map').setView([22.5937,78.9629],5);
const street=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'});
const satellite=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Tiles &copy; Esri'});
street.addTo(map);
L.control.layers({'Street View (OpenStreetMap)':street,'Satellite View (Esri)':satellite},null,{collapsed:false}).addTo(map);
function esc(value){return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
issues.forEach((issue,index)=>{
  const resolved=['verified resolved','resolved'].includes(String(issue.status).toLowerCase());
  const critical=String(issue.severity).toLowerCase()==='critical';
  const high=Number(issue.reportCount)>=2||critical;
  const mine=Boolean(issue.reportedByYou);
  const minor=String(issue.severity).toLowerCase()==='low';
  let classes='civic-marker';
  if(mine) classes+=' mine';
  if(resolved) classes+=' resolved';
  else if(high) classes+=' high'+(critical?' critical':'');
  else if(minor) classes+=' minor';
  else classes+=' open';
  const marker=L.marker([issue.lat,issue.lon],{icon:L.divIcon({className:'',html:`<div class="${classes}">${mine?'<span>★</span>':''}</div>`,iconSize:high?[30,30]:mine?[25,25]:minor?[12,12]:[18,18],iconAnchor:high?[15,15]:mine?[12,22]:minor?[6,6]:[9,9]})}).addTo(map);
  const you=mine?'Yes — Reported by You':'No';
  const approximate=`<br><em>Approximate map pin: ${esc(issue.coordinateNote)}</em>`;
  marker.bindPopup(`<strong>${esc(issue.category)} · ${esc(issue.id)}</strong><br>${esc(issue.description)}<br><b>Location:</b> ${esc(issue.location)}<br><b>Status:</b> ${esc(issue.status)}<br><b>Duplicate reports:</b> ${esc(issue.reportCount)}<br><b>Reported by you:</b> ${you}${approximate}`);
});
const legend=L.control({position:'bottomright'});
legend.onAdd=function(){const div=L.DomUtil.create('div','legend');div.innerHTML='<strong>Issue Legend</strong><div><span class="swatch" style="background:#833ec2"></span>Repaired / Resolved</div><div><span class="swatch" style="background:#e53935"></span>Open / Active</div><div><span class="swatch" style="background:#8b1e2d;width:18px;height:18px"></span>Repeated / Critical (pulsing)</div><div><span class="swatch" style="background:#f4c430;width:9px;height:9px"></span>Minor / Low</div><div><span class="swatch" style="background:#1976d2"></span>★ My Reported Issue</div><small>City/state pins are approximate. Unmatched locations appear at India center.</small>';return div;};
legend.addTo(map);
</script></body></html>"""
    map_html = map_html.replace("__ISSUES_JSON__", issues_json)
    components.html(map_html, height=660, scrolling=False)


def _complete_login(user: dict) -> None:
    st.session_state["user_email"] = user["email"]
    st.session_state["user_name"] = (
        user.get("full_name") or user["email"].split("@", 1)[0].replace(".", " ").title()
    )
    st.session_state.pop("auth_modal_action", None)
    st.rerun()


def _open_india_map() -> None:
    st.session_state["navigation_page"] = NAV_MAP


def render_auth_modal(action_label="continue"):
    """Render just-in-time authentication outside the sidebar."""
    if st.session_state.get("user_email"):
        return True

    with st.container(border=True):
        st.markdown("## Welcome to CivicPulse AI")
        st.caption(f"Sign in to {action_label} and keep your CivicCoins rewards together.")

        with st.form("auth_google_form"):
            google_email = st.text_input(
                "Google email", placeholder="you@gmail.com", key="auth_google_email"
            )
            google_submit = st.form_submit_button(
                "Continue with Google", use_container_width=True
            )
        if google_submit:
            if not is_valid_email(google_email):
                st.error("Enter a valid email address to continue.")
            else:
                user = login_with_google_sim(google_email)
                _complete_login(user)
        st.caption("Google sign-in is simulated locally with the entered email; ownership is not verified by Google OAuth.")

        st.markdown("<div style='text-align:center;color:#718096'>— OR —</div>", unsafe_allow_html=True)
        sign_in_tab, create_tab = st.tabs(["Sign In", "Create Account"])
        with sign_in_tab:
            with st.form("auth_signin_form"):
                signin_email = st.text_input("Email", key="auth_signin_email")
                signin_password = st.text_input(
                    "Password", type="password", key="auth_signin_password"
                )
                signin_submit = st.form_submit_button(
                    "Sign In", use_container_width=True
                )
            if signin_submit:
                success, result = login_user_with_password(signin_email, signin_password)
                if success:
                    _complete_login(result)
                st.error(result)

        with create_tab:
            with st.form("auth_signup_form"):
                signup_name = st.text_input("Full Name", key="auth_signup_name")
                signup_email = st.text_input("Email", key="auth_signup_email")
                signup_password = st.text_input(
                    "Password", type="password", key="auth_signup_password"
                )
                signup_submit = st.form_submit_button(
                    "Create Account", type="primary", use_container_width=True
                )
            if signup_submit:
                if not is_valid_email(signup_email):
                    st.error("Enter a valid email address.")
                else:
                    success, message = register_user_with_password(
                        signup_name, signup_email, signup_password
                    )
                    if success:
                        user = get_or_create_user(signup_email)
                        _complete_login(user)
                    st.error(message)
    return False


with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
          {CIVIC_ICON_SVG}
          <strong>CivicPulse AI</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    if st.session_state.get("user_email"):
        profile = get_or_create_user(st.session_state["user_email"])
        display_name = st.session_state.get("user_name") or profile.get("full_name") or "Citizen"
        st.markdown(
            f"""<div class="sidebar-profile">
              <span>{CIVIC_ICON_SVG}{escape(display_name)}</span>
              <span>{CIVIC_ICON_SVG}{profile['coins']} coins</span>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Logout", key="sidebar_logout", use_container_width=True):
            for key in (
                "user_email",
                "user_name",
                "auth_modal_action",
                "officer_portal_unlocked",
                "officer_secret_passcode",
            ):
                st.session_state.pop(key, None)
            st.rerun()
        st.divider()
    if st.session_state.get("navigation_page") not in NAV_OPTIONS:
        st.session_state["navigation_page"] = NAV_PUBLIC
    page = st.session_state["navigation_page"]
    for nav_label in NAV_OPTIONS:
        icon_column, button_column = st.columns([0.18, 0.82])
        with icon_column:
            st.markdown(
                f'<div class="sidebar-nav-icon">{NAV_ICONS[nav_label]}</div>',
                unsafe_allow_html=True,
            )
        with button_column:
            if st.button(
                nav_label,
                key=f"nav_{NAV_OPTIONS.index(nav_label)}",
                type="primary" if page == nav_label else "secondary",
                use_container_width=True,
            ):
                st.session_state["navigation_page"] = nav_label
                st.rerun()
    page = st.session_state["navigation_page"]
    st.divider()
    st.caption("Small reports. Better neighborhoods.")

if page != NAV_OFFICER:
    st.session_state["officer_portal_unlocked"] = False
    st.session_state.pop("officer_secret_passcode", None)

if page == NAV_PUBLIC:
    show_hero("CivicPulse Public Dashboard", "A live view of the issues citizens have reported across the city.")
    complaints = get_all_complaints()
    pending = sum(item["status"] in OPEN_COMPLAINT_STATUSES for item in complaints)
    resolved = sum(item["status"] == "Verified Resolved" for item in complaints)
    critical = sum(item["severity"] == "Critical" and item["status"] in OPEN_COMPLAINT_STATUSES for item in complaints)
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Issues", len(complaints))
    k2.metric("Open Issues", pending)
    k3.metric("Verified Resolved", resolved)
    st.caption(f"Critical escalations currently open: {critical}")
    st.button(
        NAV_MAP,
        type="primary",
        on_click=_open_india_map,
    )
    st.subheader("Recent civic activity")
    recent = sorted(complaints, key=lambda item: item.get("created_at", ""), reverse=True)[:8]
    if recent:
        table_rows = "".join(
            "<tr>"
            f"<td style='padding:12px;border-top:1px solid #c9a6eb;color:#231436'>{escape(str(item['id']))}</td>"
            f"<td style='padding:12px;border-top:1px solid #c9a6eb;color:#231436'>{escape(str(item['category']))}</td>"
            f"<td style='padding:12px;border-top:1px solid #c9a6eb;color:#231436'>{escape(str(item['location']))}</td>"
            f"<td style='padding:12px;border-top:1px solid #c9a6eb;color:#231436'>{escape(str(item['severity']))}</td>"
            f"<td style='padding:12px;border-top:1px solid #c9a6eb;color:#231436'>{escape(str(item['status']))}</td>"
            f"<td style='padding:12px;border-top:1px solid #c9a6eb;color:#231436'>{int(item.get('report_count', 1) or 1)} {'report' if int(item.get('report_count', 1) or 1) == 1 else 'reports'}</td>"
            f"<td style='padding:12px;border-top:1px solid #c9a6eb;color:#231436'>{escape(str(item.get('assigned_authority') or 'Not assigned'))}</td>"
            "</tr>"
            for item in recent
        )
        st.markdown(
            """
            <div style="overflow-x:auto;border:1px solid #c9a6eb;border-radius:12px;">
              <table style="width:100%;border-collapse:collapse;background:#ffffff;color:#231436;">
                <thead><tr style="background:#f3ebfc;text-align:left;">
                  <th style="padding:12px;color:#231436;">ID</th>
                  <th style="padding:12px;color:#231436;">Category</th>
                  <th style="padding:12px;color:#231436;">Location</th>
                  <th style="padding:12px;color:#231436;">Severity</th>
                  <th style="padding:12px;color:#231436;">Status</th>
                  <th style="padding:12px;color:#231436;">Reports</th>
                  <th style="padding:12px;color:#231436;">Assigned Authority</th>
                </tr></thead>
                <tbody>""" + table_rows + """</tbody>
              </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No civic reports have been submitted yet.")

elif page == NAV_MAP:
    show_hero("Live India Civic Map", "Explore reported civic issues across India.")
    map_complaints = get_all_complaints()
    render_india_civic_map(map_complaints, st.session_state.get("user_email", ""))

elif page == NAV_FEED:
    show_hero("Live Feed", "Recent reports and their latest public statuses.")
    complaints = get_all_complaints()
    feed = sorted(complaints, key=lambda item: item.get("created_at", ""), reverse=True)
    if not feed:
        st.info("The live feed is quiet for now.")
    for item in feed:
        with st.container(border=True):
            st.markdown(f"### {item['id']} · {item['category']}")
            st.write(f"**{item['location']}** · {item['severity']} · {item['status']}")
            st.write(item["description"])
            saved_image = item.get("image_path")
            if saved_image:
                image_file = APP_DIR / saved_image
                if image_file.is_file():
                    st.image(str(image_file), use_container_width=True)
            resolution_image = item.get("after_image_path")
            if resolution_image:
                resolution_file = APP_DIR / resolution_image
                if resolution_file.is_file():
                    st.markdown("**Resolution proof**")
                    st.image(str(resolution_file), use_container_width=True)
            st.caption(f"{item['report_count']} citizen report(s) · {item['created_at']}")

elif page == NAV_REPORT:
    show_hero("Your city, heard.", "Report an issue and help your city respond faster.")
    evidence_mode = st.radio(
        "Add visual evidence",
        ("Camera", "Gallery", "Upload"),
        horizontal=True,
        key="report_evidence_mode",
    )
    selected_image = None
    if evidence_mode == "Camera":
        selected_image = st.camera_input("Take a photo", key="report_camera_capture")
    elif evidence_mode == "Gallery":
        selected_image = st.file_uploader(
            "Choose a photo from your gallery",
            type=["jpg", "jpeg", "png", "webp"],
            key="report_gallery_image",
        )
    else:
        selected_image = st.file_uploader(
            "Upload a photo",
            type=["jpg", "jpeg", "png", "webp"],
            key="report_upload_image",
        )
    if selected_image is not None:
        st.image(selected_image, caption="Evidence preview", use_container_width=True)

    with st.form("complaint_form"):
        location = st.text_input("Location", placeholder="Street, neighborhood, or landmark", key="report_location")
        description = st.text_area(
            "What needs attention?",
            placeholder="For example: Deep pothole near the bus stop...",
            height=110,
            max_chars=500,
            key="report_description",
        )
        submitted = st.form_submit_button(
            "Submit Report", type="primary", use_container_width=True
        )
    if submitted:
        if not st.session_state.get("user_email"):
            st.session_state["auth_modal_action"] = "submit a report"
            st.rerun()
        elif not location.strip() or not description.strip():
            st.error("Add a location and a short description to continue.")
        else:
            citizen_email = st.session_state["user_email"]
            category, severity = analyze_complaint_ai(description, None)
            duplicate = find_matching_complaint(location.strip(), category, description.strip())
            if duplicate:
                image_path = save_upload(selected_image)
                count = increment_duplicate_report(
                    duplicate["id"], citizen_email=citizen_email, image_path=image_path
                )
                record_citizen_report(citizen_email, points=10)
                st.session_state["duplicate_notice"] = {"id": duplicate["id"], "count": count}
                st.session_state.pop("last_report", None)
            else:
                image_path = save_upload(selected_image)
                image_for_analysis = str(APP_DIR / image_path) if image_path else None
                category, severity = analyze_complaint_ai(description, image_for_analysis)
                tracking_id = add_complaint(
                    category=category,
                    description=description.strip(),
                    location=location.strip(),
                    severity=severity,
                    image_path=image_path,
                    citizen_email=citizen_email,
                )
                record_citizen_report(citizen_email, points=10)
                st.session_state.pop("duplicate_notice", None)
                st.session_state["last_report"] = {
                    "id": tracking_id, "category": category, "severity": severity,
                }
            st.rerun()
    if st.session_state.get("auth_modal_action") == "submit a report" and not st.session_state.get("user_email"):
        render_auth_modal(action_label="submit a report")
    notice = st.session_state.get("duplicate_notice")
    if notice:
        st.warning(
            f"Duplicate Issue Detected! Merged with existing ticket {notice['id']}. "
            f"Total reports: {notice['count']}. Priority auto-escalated to CRITICAL!"
        )
        st.info("+10 CivicCoins awarded to your wallet for reporting this issue.")
    report = st.session_state.get("last_report")
    if report:
        st.success(f"Report received — tracking ID **{report['id']}**")
        a, b, c = st.columns(3)
        a.metric("AI category", report["category"])
        b.metric("Severity", report["severity"])
        c.metric("Civic reward", "+10 CivicCoins")

elif page == NAV_WALLET:
    show_hero("My Rewards & Wallet", "Your CivicCoins and contribution history.")
    if not st.session_state.get("user_email"):
        st.session_state["auth_modal_action"] = "view My Rewards & Wallet"
        render_auth_modal(action_label="view My Rewards & Wallet")
    else:
        wallet = get_or_create_user(st.session_state["user_email"])
        st.subheader(st.session_state.get("user_name", wallet.get("full_name") or "Citizen"))
        a, b = st.columns(2)
        a.metric("CivicCoins Balance", wallet["coins"])
        b.metric("Total Reports Submitted", wallet["reports_count"])
        badge = "Civic Champion" if wallet["coins"] >= 50 else "Civic Starter"
        st.success(badge)
        st.caption("Earn 10 CivicCoins when you submit or merge a report, and 50 more when its repair is verified.")
elif page == NAV_TRACK:
    show_hero("Track Complaint", "Look up a report and see its status, priority, and photos.")
    with st.form("tracker_form"):
        tracking_id = st.text_input("Tracking ID", placeholder="CP-1001")
        search = st.form_submit_button("Find report", type="primary")
    if search:
        st.session_state["tracker_result"] = get_complaint_by_id(tracking_id)
        st.session_state["tracker_searched"] = True
    if st.session_state.get("tracker_searched"):
        complaint = st.session_state.get("tracker_result")
        if not complaint:
            st.warning("No report found. Check the ID and try again.")
        else:
            st.subheader(f"Report {complaint['id']}")
            a, b, c = st.columns(3)
            a.metric("Status", complaint["status"])
            b.metric("Severity", complaint["severity"])
            report_count = int(complaint.get("report_count", 1) or 1)
            c.metric("Reports", f"{report_count} {'report' if report_count == 1 else 'reports'}")
            st.caption(f"Assigned authority: {complaint.get('assigned_authority') or 'Not assigned'}")
            st.caption(f"Category: {complaint['category']}")
            st.write(f"**Location:** {complaint['location']}")
            st.write(f"**Description:** {complaint['description']}")
            st.caption(f"Submitted {complaint['created_at']}")
            before_path = complaint.get("image_path")
            after_path = complaint.get("after_image_path")
            before_col, after_col = st.columns(2)
            for column, label, saved_path in (
                (before_col, "Before", before_path),
                (after_col, "After", after_path),
            ):
                with column:
                    st.markdown(f"**{label} image**")
                    if saved_path:
                        photo_path = APP_DIR / saved_path
                        if photo_path.is_file():
                            st.image(str(photo_path), use_container_width=True)
                        else:
                            st.caption("The attached photo is unavailable on this device.")
                    else:
                        st.caption("No image attached.")

elif page == NAV_OFFICER:
    show_hero("Municipal Officer Portal", "Prioritize reports, verify repair evidence, and close resolved issues.")
    if not st.session_state.get("officer_portal_unlocked", False):
        st.subheader("Officer Passcode Lock")
        with st.form("officer_passcode_form"):
            entered_passcode = st.text_input(
                "Officer Secret Passcode", type="password", key="officer_secret_passcode"
            )
            unlock_clicked = st.form_submit_button(
                "Unlock Officer Portal", type="primary"
            )
        if unlock_clicked:
            if entered_passcode == OFFICER_SECRET_PASSCODE:
                st.session_state["officer_portal_unlocked"] = True
                st.rerun()
            st.session_state["officer_portal_unlocked"] = False
            st.error("Unauthorized: Only verified Municipal Officers can upload repair proofs")
        else:
            st.info("Enter the officer passcode to access complaint review and repair verification tools.")
        st.stop()

    proof_success = st.session_state.pop("proof_success", None)
    if proof_success:
        st.success(proof_success)
    complaints = get_all_complaints()
    resolved_count = sum(item["status"] == "Verified Resolved" for item in complaints)
    critical_count = sum(
        item["severity"] == "Critical"
        and item["status"] in OPEN_COMPLAINT_STATUSES
        for item in complaints
    )
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Issues", len(complaints))
    k2.metric("Critical Escalated Issues", critical_count)
    k3.metric("Verified Resolved", resolved_count)

    open_complaints = [
        item for item in complaints
        if item["status"] in OPEN_COMPLAINT_STATUSES
    ]
    st.subheader("Open complaint queue")
    if not open_complaints:
        st.success("There are no open complaints awaiting repair verification.")
    for complaint in open_complaints:
        label = "CRITICAL" if complaint["severity"] == "Critical" else complaint["severity"]
        with st.container(border=True):
            st.markdown(f"### {complaint['id']} · {label} · {complaint['status']}")
            image_col, details_col = st.columns([0.85, 1.5], gap="large")
            with image_col:
                st.markdown("**Before image**")
                before_saved = complaint.get("image_path")
                before_path = APP_DIR / before_saved if before_saved else None
                if before_path and before_path.is_file():
                    st.image(str(before_path), use_container_width=True)
                else:
                    st.caption("No before image is available for this issue.")
            with details_col:
                st.write(f"**Location:** {complaint['location']}")
                st.write(f"**Description:** {complaint['description']}")
                st.write(f"**Category:** {complaint['category']}")
                st.write(f"**Severity:** {complaint['severity']}")
                report_count = int(complaint.get("report_count", 1) or 1)
                st.write(f"**Report Count:** {report_count} {'report' if report_count == 1 else 'reports'}")
                st.write(f"**Assigned Authority:** {complaint.get('assigned_authority') or 'Not assigned'}")
                if not before_path or not before_path.is_file():
                    st.error("A Before image is required to verify repair work.")
                proof_mode = st.radio(
                    "Resolution proof photo",
                    ("Camera", "Gallery", "Upload"),
                    horizontal=True,
                    key=f"proof_mode_{complaint['id']}",
                )
                after_upload = None
                if proof_mode == "Camera":
                    after_upload = st.camera_input(
                        "Take resolution photo", key=f"proof_camera_{complaint['id']}"
                    )
                elif proof_mode == "Gallery":
                    after_upload = st.file_uploader(
                        "Choose resolution photo from gallery",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"proof_gallery_{complaint['id']}",
                    )
                else:
                    after_upload = st.file_uploader(
                        "Upload resolution photo",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"proof_upload_{complaint['id']}",
                    )
                if after_upload is not None:
                    st.image(after_upload, caption="Resolution proof preview", use_container_width=True)
                with st.form(f"proof_form_{complaint['id']}"):
                    verify_clicked = st.form_submit_button(
                        "Verify & Close Ticket", type="primary"
                    )
                if verify_clicked:
                    if after_upload is None:
                        st.error("Upload an After-Repair Photo before verification.")
                    elif not before_path or not before_path.is_file():
                        st.error("This ticket cannot be closed until a Before image is available.")
                    else:
                        after_saved = save_upload(after_upload)
                        after_path = APP_DIR / after_saved
                        verified, score, message = verify_proof_of_work(
                            before_path, after_path
                        )
                        if verified:
                            saved = resolve_complaint_with_proof(
                                complaint["id"], after_saved, score
                            )
                            if saved:
                                st.session_state["proof_success"] = (
                                    f"{message} AI confidence / change score: {score:.2f}%. "
                                    "+50 CivicCoins awarded to the citizen."
                                )
                                st.rerun()
                            st.error("This ticket is no longer open. Refresh the portal and try again.")
                        else:
                            after_path.unlink(missing_ok=True)
                            st.error(f"Fraud-prevention alert: {message} (Similarity: {score:.2f}%)")

elif page == NAV_RECEIPT:
    st.subheader("CivicPulse AI Grievance Receipt")
    st.caption("Select a reported complaint or enter its Complaint ID to prepare a receipt.")
    complaints = get_all_complaints()
    if not complaints:
        st.info("No reported complaints are available yet.")
    else:
        complaints_by_id = {str(item.get("id", "")).upper(): item for item in complaints}
        complaint_ids = list(complaints_by_id)
        selected_id = st.selectbox(
            "Choose a complaint", complaint_ids,
            format_func=lambda complaint_id: (
                f"{complaint_id} · {complaints_by_id[complaint_id].get('status', 'Submitted')} · "
                f"{complaints_by_id[complaint_id].get('location', '')}"
            ),
            key="receipt_complaint_select",
        )
        entered_id = st.text_input(
            "Or enter a Complaint ID", placeholder="CP-1001", key="receipt_complaint_id"
        ).strip().upper()
        complaint = complaints_by_id.get(entered_id) if entered_id else complaints_by_id.get(selected_id)
        if entered_id and not complaint:
            st.warning("No complaint matches that ID. Choose a listed complaint or check the ID.")
        if complaint:
            complaint_id = str(complaint.get("id", ""))
            status = str(complaint.get("status", "Submitted"))
            verification_score = complaint.get("verification_score")
            if status.casefold() in {"verified resolved", "resolved"}:
                note = "Repair evidence was verified and this complaint was marked resolved."
                if verification_score is not None:
                    note += f" Verification score: {float(verification_score):.2f}%."
            elif status.casefold() == "verified":
                note = "This complaint has been verified and is awaiting resolution."
            else:
                note = "Your complaint has been received and remains in the civic response queue."
            receipt_number = f"CPR-{complaint_id}"
            report_count = int(complaint.get("report_count", 1) or 1)
            assigned_authority = str(complaint.get("assigned_authority") or "Not assigned")
            timestamp = str(complaint.get("created_at", "Not available"))
            location = str(complaint.get("location", "Not provided"))
            description = str(complaint.get("description", "Not provided"))
            with st.container(border=True):
                st.markdown("### Official CivicPulse AI Grievance Receipt")
                st.markdown(f"**Receipt Number:** `{escape(receipt_number)}`  ")
                st.markdown(f"**Complaint ID:** `{escape(complaint_id)}`")
                st.divider()
                st.markdown(f"**Location**  \n{escape(location)}")
                st.markdown(f"**Issue Description**  \n{escape(description)}")
                st.markdown(f"**Current Status:** {escape(status)}")
                st.markdown(f"**Reports:** {report_count} {'report' if report_count == 1 else 'reports'}")
                st.markdown(f"**Assigned Authority:** {escape(assigned_authority)}")
                st.markdown(f"**Reported At:** {escape(timestamp)}")
                st.markdown(f"**Verification / Resolution Note**  \n{escape(note)}")
            receipt_text = (
                "CIVICPULSE AI\nOFFICIAL GRIEVANCE RECEIPT\n"
                "========================================\n"
                f"Receipt Number: {receipt_number}\nComplaint ID: {complaint_id}\n"
                f"Location: {location}\nIssue Description: {description}\n"
                f"Current Status: {status}\nReport Count: {report_count}\n"
                f"Assigned Authority: {assigned_authority}\nTimestamp: {timestamp}\n"
                f"Verification / Resolution Note: {note}\n"
                "========================================\n"
                "Keep this receipt for your records.\n"
            )
            st.download_button(
                "Download Receipt",
                data=receipt_text.encode("utf-8"),
                file_name=f"civicpulse_receipt_{complaint_id.lower()}.txt",
                mime="text/plain; charset=utf-8",
                type="primary",
                use_container_width=True,
            )

elif page == NAV_HELPLINE:
    st.subheader("24/7 Civic Helpline & Emergency Support")
    st.markdown(
        """
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem;">
          <div style="padding:1rem 1.1rem;background:#ffffff;border:1px solid #c9a6eb;border-radius:12px;color:#231436;">
            <strong>Municipal Civic Helpline</strong><br>
            <a href="tel:155304" style="color:#833ec2;font-weight:700;text-decoration:none;">155304</a>
            <span> / </span>
            <a href="tel:18004250000" style="color:#833ec2;font-weight:700;text-decoration:none;">1800-425-0000</a>
          </div>
          <div style="padding:1rem 1.1rem;background:#ffffff;border:1px solid #c9a6eb;border-radius:12px;color:#231436;">
            <strong>National Emergency</strong><br>
            <a href="tel:112" style="color:#833ec2;font-weight:700;text-decoration:none;">112</a>
          </div>
          <div style="padding:1rem 1.1rem;background:#ffffff;border:1px solid #c9a6eb;border-radius:12px;color:#231436;">
            <strong>Ambulance</strong><br>
            <a href="tel:108" style="color:#833ec2;font-weight:700;text-decoration:none;">108</a>
          </div>
          <div style="padding:1rem 1.1rem;background:#ffffff;border:1px solid #c9a6eb;border-radius:12px;color:#231436;">
            <strong>Fire</strong><br>
            <a href="tel:101" style="color:#833ec2;font-weight:700;text-decoration:none;">101</a>
          </div>
          <div style="padding:1rem 1.1rem;background:#ffffff;border:1px solid #c9a6eb;border-radius:12px;color:#231436;">
            <strong>Citizen Support</strong><br>
            <a href="mailto:support@civicpulse.gov.in" style="color:#833ec2;font-weight:700;text-decoration:none;">support@civicpulse.gov.in</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

