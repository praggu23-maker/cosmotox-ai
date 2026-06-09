import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import json
from scipy.integrate import solve_ivp
from openai import OpenAI

st.set_page_config(page_title="CosmoTox-AI Core Engine", page_icon="🚀", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to CosmoTox-AI! Upload your NASA spaceflight dataset or adjust parameters. I will simulate tumor killing velocity, CAR-T survival tracking, and clinical toxicity cascades simultaneously."}
    ]

# =====================================================================
# SYSTEM QSP MATHEMATICAL SOLVER CORE (Predator-Prey Kinetics)
# =====================================================================
def qsp_cart_tumor_system(t, y, params):
    """
    y = [Tumor_Cells, CART_Cells, Systemic_IL6, ICANS_CNS]
    """
    T, E, IL6, ICANS = y
    
    # 1. Extract Scaled Clinical Variables
    rho = 0.015                     # Tumor growth rate constant (per hour)
    T_max = 500.0                   # Max tumor structural carrying capacity
    kappa = params['killing_velocity'] # Scaled Tumor Killing Velocity Index
    theta = 0.008                   # Antigen-driven CAR-T proliferation multiplier
    alpha = params['survival_decay'] # CAR-T attrition/survival decay factor
    
    # 2. Cellular Systems Diff Equations
    # Tumor progression / regression equation
    dT = rho * T * (1.0 - T / T_max) - kappa * T * E
    
    # Effector CAR-T survival, expansion, and contraction equation
    dE = theta * T * E - alpha * E
    
    # 3. Toxicity Cascades Linked Directly to Real-time Cytotoxicity Lysing
    nasa_stress_impact = params['nasa_fc'] * params['nasa_splicing']
    biobank_genomic_multiplier = params['biobank_modifier']
    
    # IL-6 release scales dynamically based on the rate of cell lysis (kappa * T * E)
    dIL6 = (kappa * T * E * nasa_stress_impact * biobank_genomic_multiplier * 4.0) - (0.15 * IL6)
    
    # ICANS Neurovascular leakage sigmoidal tracking model
    bbb_leakage_index = 1.0 / (1.0 + np.exp(-0.025 * (IL6 - 220.0)))
    dICANS = (IL6 * bbb_leakage_index * 0.35) - (0.22 * ICANS)
    
    return [dT, dE, dIL6, dICANS]

# =====================================================================
# FRONT-END SIDEBAR PARAMETER FILTER SANDBOX
# =====================================================================
st.sidebar.title("🛠️ Configuration Sandbox")

st.sidebar.markdown("### 1. Artificial Intelligence Core")
api_key_input = st.sidebar.text_input("Enter OpenAI API Key:", type="password")
api_key = api_key_input if api_key_input else st.secrets.get("OPENAI_API_KEY", "")

if not api_key:
    st.sidebar.warning("⚠️ Chat features require an OpenAI API Key.")
else:
    st.sidebar.success("🤖 OpenAI Engine Connected.")

st.sidebar.write("---")

st.sidebar.markdown("### 2. Biobank Validation Cohort")
selected_biobank = st.sidebar.selectbox("Choose Target Population Data Bank:", ["UK Biobank (N=500k)", "NIH All of Us Cohort"])
cohort_risk_skew = st.sidebar.slider("Biobank Genetic Risk Prevalence", 1.0, 3.0, value=1.5, step=0.1)

st.sidebar.write("---")

# NEW INTERACTIVE PHARMACY MODEL SCALERS
st.sidebar.markdown("### 3. Cellular Kinetic Assays")
killing_vel = st.sidebar.slider("Tumor Cell Killing Velocity (κ)", 0.005, 0.080, value=0.025, step=0.005)
survival_dec = st.sidebar.slider("CAR-T Survival Attrition Rate (α)", 0.005, 0.050, value=0.015, step=0.005)

st.sidebar.write("---")
st.sidebar.markdown("### 4. Patient Baseline Metrics")
age = st.sidebar.number_input("Patient Baseline Age:", 18, 95, 62)
weight = st.sidebar.number_input("Weight (kg):", 40, 150, 78)
serum_creatinine = st.sidebar.number_input("Serum Creatinine (mg/dL):", 0.3, 8.0, 1.3)
calculated_crcl = ((140 - age) * weight) / (72 * serum_creatinine)
st.sidebar.markdown(f"**Computed Clearance Rate (CrCl):** `{calculated_crcl:.1f} mL/min`")

# =====================================================================
# MASTER APPLICATION VIEW DISPLAY LAYOUT
# =====================================================================
st.title("🚀 CosmoTox-AI Clinical Simulator")
st.markdown("Predict off-target toxicities, tumor cell killing velocity, and therapeutic persistence by translating **NASA Bioscience extreme stress markers** through **population scales**.")
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
                
    if user_prompt := st.chat_input("Ask about structural killing velocity or survival tracking kinetics..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with chat_box:
            with st.chat_message("user"):
                st.markdown(user_prompt)
        if not api_key:
            with chat_box:
                with st.chat_message("assistant"):
                    st.error("Please add your OpenAI API Key in the left column configuration sandbox.")
        else:
            client = OpenAI(api_key=api_key)
            system_brief = f"You are CosmoTox-AI, an expert clinical pharmacologist. Target Construct = {target_antigen}. Killing Velocity κ = {killing_vel}. CAR-T Survival Attrition α = {survival_dec}. Give brief, quantitative systems pharmacology insights on tumor eradication and systemic toxicity mitigation."
            with st.spinner("AI analyzing clinical therapeutic indexes..."):
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

# Run the Multi-Variable ODE System Simulation Solver Engine
ode_params = {
    'crcl_ml_min': calculated_crcl, 'nasa_fc': nasa_fc, 'nasa_splicing': nasa_splicing, 
    'biobank_modifier': cohort_risk_skew, 'killing_velocity': killing_vel, 'survival_decay': survival_dec
}
# Initial States Vector: [Tumor Burden Volume (x10^6), Initial CAR-T Dose, Base IL-6, Base ICANS]
y0 = [350.0, 15.0, 10.0, 2.0]
time_array = np.linspace(0, 360, 300) # Extended 15-day longitudinal telemetry window

sol = solve_ivp(qsp_cart_tumor_system, (0, 360), y0, args=(ode_params,), t_eval=time_array, method='RK45')

# Isolate critical peak metrics for calculation tiles
peak_tumor_clearance = ((y0[0] - np.min(sol.y[0])) / y0[0]) * 100.0
peak_crs = float(np.max(sol.y[2]))
peak_icans = float(np.max(sol.y[3]))

with col_right:
    st.subheader("🔮 Predictive Integrated Pre-Trial Analytics")
    
    # 4-Tile High Density Dashboard Layout view
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.metric("Tumor Cleared Volume", f"{peak_tumor_clearance:.1f}%", delta="🟢 Optimal Lysis Rate" if peak_tumor_clearance > 75 else "🔴 Insufficient Dose Efficiency", delta_color="normal")
    with col_t2:
        st.metric("Max Systemic CRS", f"{peak_crs:.1f} pg/mL", delta="⚠️ CRITICAL BIOMARKER" if peak_crs > 300 else "✅ Stable Level", delta_color="inverse" if peak_crs > 300 else "normal")
    with col_t3:
        st.metric("Max ICANS Index", f"{peak_icans:.1f} pts", delta="🚨 SEVERE NEURO-HAZARD" if peak_icans > 80 else "✅ Normal Profile", delta_color="inverse" if peak_icans > 80 else "normal")

    # Render Parallel Visualization Framework Layout panes
    st.markdown("### 📊 Longitudinal Cellular Persistence Dynamics (Therapeutic Efficacy)")
    fig_efficacy = go.Figure()
    fig_efficacy.add_trace(go.Scatter(x=sol.t / 24.0, y=sol.y[0], name="Tumor Cell Burden (Prey)", line=dict(color='#29B573', width=4)))
    fig_efficacy.add_trace(go.Scatter(x=sol.t / 24.0, y=sol.y[1], name="CAR-T Proliferation & Survival Tracker (Predator)", line=dict(color='#7209B7', width=4, dash='dot')))
    fig_efficacy.update_layout(xaxis_title="Days Post Infusion", yaxis_title="Cellular Density Populations", template="plotly_white", margin=dict(l=40, r=20, t=20, b=40), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_efficacy, use_container_width=True)
    
    st.markdown("### 📈 Coupled Systemic Inflammatory Cascades (Toxicological Hazard)")
    fig_toxicity = go.Figure()
    fig_toxicity.add_trace(go.Scatter(x=sol.t / 24.0, y=sol.y[2], name="CRS Toxicity Velocity (IL-6)", line=dict(color='#FF4B4B', width=4)))
    fig_toxicity.add_trace(go.Scatter(x=sol.t / 24.0, y=sol.y[3], name="ICANS Neurovascular Index Tracker", line=dict(color='#0068C9', width=4, dash='dash')))

