import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import json
from scipy.integrate import solve_ivp
from openai import OpenAI

st.set_page_config(page_title="CosmoTox-AI Dashboard", page_icon="🚀", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to CosmoTox-AI! Upload your NASA spaceflight dataset to map trial risks."}
    ]

def car_t_toxicity_system(t, y, params):
    Flu_C, Cy_C, Systemic_IL6, ICANS_CNS = y
    cl_flu = 9.5 * (params['crcl_ml_min'] / 100.0)
    v1_flu = params['bsa_m2'] * 20.0
    dFlu_C = -(cl_flu / v1_flu) * Flu_C
    dCy_C = -(11.0 / (params['bsa_m2'] * 30.0)) * Cy_C
    nasa_stress_impact = params['nasa_fc'] * params['nasa_splicing']
    biobank_genomic_multiplier = params['biobank_modifier']
    dIL6 = (nasa_stress_impact * biobank_genomic_multiplier * 50.0) - (0.18 * Systemic_IL6)
    bbb_leakage_index = 1.0 / (1.0 + np.exp(-0.025 * (Systemic_IL6 - 220.0)))
    dICANS = (Systemic_IL6 * bbb_leakage_index * 0.35) - (0.22 * ICANS_CNS)
    return [dFlu_C, dCy_C, dIL6, dICANS]

st.sidebar.title("🛠️ Configuration Sandbox")
st.sidebar.markdown("### 1. Artificial Intelligence Core")
api_key_input = st.sidebar.text_input("Enter OpenAI API Key:", type="password")
api_key = api_key_input if api_key_input else ""

if not api_key:
    st.sidebar.warning("⚠️ Chat features require an OpenAI API Key.")
else:
    st.sidebar.success("🤖 OpenAI Engine Connected.")

st.sidebar.write("---")
st.sidebar.markdown("### 2. Biobank Validation Cohort")
selected_biobank = st.sidebar.selectbox("Choose Target Population Data Bank:", ["UK Biobank (N=500k)", "NIH All of Us Cohort"])
cohort_risk_skew = st.sidebar.slider("Biobank Genetic Risk Prevalence", 1.0, 3.0, value=1.5, step=0.1)

st.sidebar.write("---")
st.sidebar.markdown("### 3. Patient Baseline Metrics")
age = st.sidebar.number_input("Patient Baseline Age:", 18, 95, 62)
weight = st.sidebar.number_input("Weight (kg):", 40, 150, 78)
serum_creatinine = st.sidebar.number_input("Serum Creatinine (mg/dL):", 0.3, 8.0, 1.3)
calculated_crcl = ((140 - age) * weight) / (72 * serum_creatinine)
st.sidebar.markdown(f"**Computed Clearance Rate (CrCl):** `{calculated_crcl:.1f} mL/min`")

st.title("🚀 CosmoTox-AI Clinical Simulator")
st.markdown("Predict off-target toxicities by translating **NASA Bioscience extreme stress markers** through **terrestrial biobank population scales**.")
st.write("---")

col_left, col_right = st.columns([1.0, 1.1])
nasa_fc = 1.0
nasa_splicing = 1.0
target_antigen = "Unknown Target"

with col_left:
    st.subheader("📥 Data Processing Layer")
    uploaded_file = st.file_uploader("Upload Raw NASA Bioscience File (JSON Format):", type=["json"])
    if uploaded_file is not None:
        try:
            nasa_json = json.load(uploaded_file)
            target_antigen = nasa_json.get("target_antigen_under_stress", "Target-X")
            nasa_fc = float(nasa_json.get("antigen_overexpression_fold_change", 1.0))
            nasa_splicing = float(nasa_json.get("mRNA_alternative_splicing_risk_index", 1.0))
            st.success(f"🧬 Linked NASA Dataset targeting antigen: **{target_antigen}**")
        except Exception as e:
            st.error(f"File Parsing Error: {e}")
            
    st.write("---")
    st.subheader("🤖 AI Pre-Trial Consultant Chat")
    chat_box = st.container(height=350)
    with chat_box:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    if user_prompt := st.chat_input("Ask how to modify trial schemas to reduce risk..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with chat_box:
            with st.chat_message("user"):
                st.markdown(user_prompt)
        if not api_key:
            with chat_box:
                with st.chat_message("assistant"):
                    st.error("Please add your OpenAI API Key in the left column.")
        else:
            client = OpenAI(api_key=api_key)
            system_brief = f"You are CosmoTox-AI, an expert clinical pharmacologist. NASA Stress = {nasa_fc}x. Biobank = {selected_biobank}. CrCl = {calculated_crcl:.1f} mL/min. Give brief, direct, actionable pharmacy advice."
            with st.spinner("AI evaluating trial risk factors..."):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": system_brief}, {"role": "user", "content": user_prompt}]
                )
                ai_text = response.choices.message.content
                st.session_state.messages.append({"role": "assistant", "content": ai_text})
                with chat_box:
                    with st.chat_message("assistant"):
                        st.markdown(ai_text)
                        st.rerun()

ode_params = {'crcl_ml_min': calculated_crcl, 'bsa_m2': 1.85, 'nasa_fc': nasa_fc, 'nasa_splicing': nasa_splicing, 'biobank_modifier': cohort_risk_skew}
sol = solve_ivp(car_t_toxicity_system, (0, 240), [55.0, 925.0, 10.0, 2.0], args=(ode_params,), t_eval=np.linspace(0, 240, 200), method='RK45')
peak_crs = float(np.max(sol.y))
peak_icans = float(np.max(sol.y))

with col_right:
    st.subheader("🔮 Predictive Pre-Trial Analytics")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.metric("Max Systemic CRS", f"{peak_crs:.1f} pg/mL", delta="⚠️ HIGH CRS RISK" if peak_crs > 300 else "✅ Low Profile", delta_color="inverse" if peak_crs > 300 else "normal")
    with col_t2:
        st.metric("Max ICANS Index", f"{peak_icans:.1f} pts", delta="🚨 SEVERE NEURO-RISK" if peak_icans > 80 else "✅ Stable Profile", delta_color="inverse" if peak_icans > 80 else "normal")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sol.t / 24.0, y=sol.y, name="CRS Toxicity (IL-6)", line=dict(color='#FF4B4B', width=4)))
    fig.add_trace(go.Scatter(x=sol.t / 24.0, y=sol.y, name="ICANS Neurotoxicity Profile", line=dict(color='#0068C9', width=4, dash='dash')))
    fig.update_layout(xaxis_title="Timeline (Days Post Infusion)", yaxis_title="Pathological Load Concentrations", template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
