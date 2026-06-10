import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import json
import io

# Import ReportLab modules for direct in-memory PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="CosmoTox-AI Dashboard", page_icon="🚀", layout="wide")

# =====================================================================
# DISCLAIMER FUNCTION WITH FORCED ACKNOWLEDGMENT
# =====================================================================
def add_disclaimers():
    """Add prominent disclaimers throughout the app with forced acknowledgment"""
    
    # Initialize session state for disclaimer if not exists
    if 'disclaimer_acknowledged' not in st.session_state:
        st.session_state.disclaimer_acknowledged = False
    
    # If disclaimer not acknowledged, show full-screen acknowledgment screen
    if not st.session_state.disclaimer_acknowledged:
        # Clear the main area and show only the acknowledgment screen
        st.empty()
        
        # Create a container for the acknowledgment screen
        with st.container():
            st.markdown("---")
            st.markdown("# ⚠️ IMPORTANT: READ BEFORE USING")
            st.markdown("---")
            
            # Display warning in red box
            st.error("""
            ## **THIS IS A RESEARCH PROTOTYPE – NOT FOR CLINICAL USE**
            
            ### **By using this platform, you acknowledge and agree that:**
            
            1. **All predictions are computational simulations only** – Not validated in clinical trials
            2. **No clinical decisions will be made based solely on this tool** – Requires physician oversight
            3. **This tool has not been FDA-approved or clinically validated**
            4. **The developers assume no liability** for use or misuse of predictions
            5. **You will use this tool only for research, education, or hypothesis generation**
            
            ### **This tool is NOT a substitute for:**
            - ❌ Medical judgment or clinical decision-making
            - ❌ Standard laboratory testing or diagnostic procedures
            - ❌ FDA-approved treatment protocols or guidelines
            - ❌ Professional medical advice or consultation
            
            ### **By proceeding, you confirm that:**
            - ✅ You understand this is a research prototype
            - ✅ You will not use this tool to make actual clinical decisions
            - ✅ You accept all risks associated with using simulation-based predictions
            """)
            
            st.markdown("---")
            
            # Create columns for buttons
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                st.markdown("### **Do you acknowledge and agree to the terms above?**")
                
                # Create two buttons side by side
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    if st.button("✅ Yes, I Acknowledge & Continue", use_container_width=True, type="primary"):
                        st.session_state.disclaimer_acknowledged = True
                        st.rerun()
                
                with btn_col2:
                    if st.button("❌ No, I Do Not Acknowledge", use_container_width=True):
                        st.markdown("""
                        ### You must acknowledge the disclaimer to use this application.
                        
                        Please refresh the page and click **"Yes, I Acknowledge & Continue"** if you agree to the terms.
                        """)
                        st.stop()
            
            st.markdown("---")
            st.caption("© 2024 CosmoTox-AI | Research Prototype | Not for Clinical Use")
        
        # Stop execution until acknowledgment
        st.stop()
    
    # If acknowledged, show the regular disclaimer banner at the top
    else:
        st.markdown("---")
        st.info("ℹ️ **Research Use Only** – This tool provides computational predictions. Not for clinical decision-making without physician oversight.")
        st.markdown("---")

def run_euler_simulation(params):
    """
    Bypasses Scipy completely using an explicit Euler numerical integration loop.
    Ensures 100% stability across all experimental Python server environments.
    """
    dt = 1.0
    steps = 241
    t_eval = np.linspace(0, 240, steps)
    
    Flu_C = np.zeros(steps)
    Cy_C = np.zeros(steps)
    Systemic_IL6 = np.zeros(steps)
    ICANS_CNS = np.zeros(steps)
    
    # Correct array state sequence definitions
    Flu_C[0] = 30.0 * params['bsa_m2']
    Cy_C[0] = 500.0 * params['bsa_m2']
    Systemic_IL6[0] = 15.0
    ICANS_CNS[0] = 2.0
    
    cl_flu = 9.5 * (params['crcl_ml_min'] / 100.0)
    v1_flu = params['bsa_m2'] * 20.0
    cl_cy = 11.0 * params.get('cyp_modifier', 1.0)
    v1_cy = params['bsa_m2'] * 30.0
    
    nasa_stress_impact = params['nasa_fc'] * params['nasa_splicing']
    patient_genomic_multiplier = params['patient_genomic_modifier']
    
    for i in range(steps - 1):
        dFlu = -(cl_flu / v1_flu) * Flu_C[i]
        dCy = -(cl_cy / v1_cy) * Cy_C[i]
        
        trigger_force = nasa_stress_impact * patient_genomic_multiplier
        dIL6 = (trigger_force * 50.0) - (0.18 * Systemic_IL6[i])
        
        bbb_leakage = 1.0 / (1.0 + np.exp(-0.025 * (Systemic_IL6[i] - 220.0)))
        dICANS = (Systemic_IL6[i] * bbb_leakage * 0.35) - (0.22 * ICANS_CNS[i])
        
        Flu_C[i+1] = max(0, Flu_C[i] + dFlu * dt)
        Cy_C[i+1] = max(0, Cy_C[i] + dCy * dt)
        Systemic_IL6[i+1] = max(0, Systemic_IL6[i] + dIL6 * dt)
        ICANS_CNS[i+1] = max(0, ICANS_CNS[i] + dICANS * dt)
        
    return t_eval, Systemic_IL6, ICANS_CNS

def generate_pdf_report(target, crcl, fc, splicing, genotype_summary, peak_crs, peak_icans, treatment_plan):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    disclaimer_style = ParagraphStyle('DisclaimerStyle', parent=styles['Normal'], fontSize=8, textColor=colors.red, alignment=1, spaceAfter=6)
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#0068C9'), spaceAfter=15)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#FF4B4B'), spaceBefore=12, spaceAfter=8)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
    
    # Add prominent disclaimer at the top of PDF
    story.append(Paragraph("<font color='red'><b>⚠️ RESEARCH PROTOTYPE – NOT FOR CLINICAL USE</b></font>", disclaimer_style))
    story.append(Paragraph("This report provides computational predictions for research purposes only. Not FDA-approved or clinically validated.", disclaimer_style))
    story.append(Paragraph("All clinical decisions require physician oversight and standard laboratory confirmation.", disclaimer_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("CosmoTox-AI: Precision Treatment & Safety Report", title_style))
    story.append(Paragraph("An Astropharmacogenomics & Quantitative Systems Pharmacology Analytics Output", body_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("1. Computational Input Boundaries & Patient Genotype", section_style))
    data_inputs = [
        ["Parameter Variable", "Assigned Value / Setting"],
        ["Target Construct Antigen", str(target)],
        ["Patient Baseline Organ Function (CrCl)", f"{crcl:.1f} mL/min"],
        ["NASA OSDR Tissue Stress Fold Change", f"{fc}x Overexpression"],
        ["NASA Alternative Splicing Risk Index", f"{splicing}"],
        ["Patient Genomic Risk Strata", str(genotype_summary)]
    ]
    t1 = Table(data_inputs, colWidths=[240, 240])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#0068C9')),
        ('TEXTCOLOR', (0,0), (1,0), colors.white),
        ('FONTNAME', (0,0), (1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F9F9F9'))
    ]))
    story.append(t1)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("2. Predictive Pre-Trial Analytics Outcomes", section_style))
    data_outcomes = [
        ["Simulated Pathological Vectors", "Peak Simulated Metrics Value", "Status Indication"],
        ["Max Systemic Cytokine Storm (CRS)", f"{peak_crs:.1f} pg/mL", "⚠️ HIGH CRS RISK" if peak_crs > 300 else "✅ Low Profile"],
        ["Max Neurovascular ICANS Intensity", f"{peak_icans:.1f} pts", "🚨 SEVERE NEURO-RISK" if peak_icans > 80 else "✅ Stable Profile"]
    ]
    t2 = Table(data_outcomes, colWidths=[180, 150, 150])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (2,0), colors.HexColor('#FF4B4B')),
        ('TEXTCOLOR', (0,0), (2,0), colors.white),
        ('FONTNAME', (0,0), (2,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    story.append(t2)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("3. Personalized Pharmacotherapy & Mitigation Protocol", section_style))
    for t_option in treatment_plan:
        story.append(Paragraph(f"<b>• {t_option['therapy']}:</b> {t_option['desc']}", body_style))
    
    # Add footer disclaimer
    story.append(Spacer(1, 30))
    story.append(Paragraph("<hr/>", body_style))
    story.append(Paragraph("<font size='7' color='gray'>Generated by CosmoTox-AI v1.0 (Research Edition) | Not for diagnostic or clinical decision-making | All predictions are computational simulations only</font>", body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================================================
# SIDEBAR FILTERS SETUP
# =====================================================================
st.sidebar.title("🛠️ Configuration Sandbox")

# Sidebar disclaimer
st.sidebar.info("⚠️ **Research Use Only** - Predictions are computational simulations. Not for clinical decisions without physician oversight.")

st.sidebar.markdown("### 🧬 Patient Genomic Profile Input")
genomic_source = st.sidebar.selectbox("Genomic Mode Source:", ["Standard Population Sliders", "Upload Patient Gene Profile / SNPs"])

# Initialize variables with default values
patient_genomic_modifier = 1.5
cyp_modifier = 1.0
genotype_summary_text = "Standard Population Metrics Applied"
detected_mutations = []

if genomic_source == "Upload Patient Gene Profile / SNPs":
    st.sidebar.markdown("ℹ️ *Paste or upload individual patient variants (e.g., HLA alleles, IL6 mutations, CYP SNPs).*")
    custom_gene_text = st.sidebar.text_area("Paste Patient Variant Lines:", value="IL6-rs1800795: G/G, CYP2B6*6: Heterozygous, HLA-A*02:01")
    
    if "IL6-rs1800795: G/G" in custom_gene_text or "G/G" in custom_gene_text:
        patient_genomic_modifier = 2.8
        detected_mutations.append("IL6_HYPER")
        genotype_summary_text = "IL-6 Hyper-Expression Variant Detected (G/G)"
        st.sidebar.error("🚨 Flagged: High-Expression IL-6 Polymorphism.")
    if "CYP2B6*6" in custom_gene_text or "Slow Metabolizer" in custom_gene_text.lower():
        cyp_modifier = 0.5
        detected_mutations.append("CYP_SLOW")
        genotype_summary_text += " | CYP2B6 Poor Metabolizer"
        st.sidebar.warning("⚠️ Flagged: Decreased Cyclophosphamide Clearance.")
else:
    selected_biobank = st.sidebar.selectbox("Choose Target Population Data Bank Reference:", ["UK Biobank (N=500k)", "NIH All of Us Cohort"])
    patient_genomic_modifier = st.sidebar.slider("Biobank Baseline Risk Prevalence (Host PGx)", 1.0, 3.0, value=1.5, step=0.1)

st.sidebar.write("---")
st.sidebar.markdown("### 👤 Patient Baseline Metrics")
age = st.sidebar.number_input("Patient Baseline Age:", 18, 95, 62)
weight = st.sidebar.number_input("Weight (kg):", 40, 150, 78)
serum_creatinine = st.sidebar.number_input("Serum Creatinine (mg/dL):", 0.3, 8.0, 1.3)
calculated_crcl = ((140 - age) * weight) / (72 * serum_creatinine)
st.sidebar.markdown(f"**Computed Clearance Rate (CrCl):** `{calculated_crcl:.1f} mL/min`")

# Add final sidebar disclaimer
st.sidebar.markdown("---")
st.sidebar.caption("📋 **This tool provides computational predictions only. Not a substitute for clinical judgment.**")

# =====================================================================
# MAIN USER INTERFACE DISPLAY LAYOUT
# =====================================================================

# Call the disclaimer function - THIS FORCES ACKNOWLEDGMENT BEFORE PROCEEDING
add_disclaimers()

# =====================================================================
# Only the code below runs AFTER disclaimer is acknowledged
# =====================================================================

st.title("🚀 CosmoTox-AI Clinical Simulator")
st.markdown("Predict off-target toxicities and optimize tailored treatment protocols by translating **NASA Bioscience extreme stress markers** through **personalized patient-specific genomic variant sheets**.")
st.write("---")

st.header("📥 Data Ingestion Layer")
uploaded_file = st.file_uploader("Upload Raw NASA Bioscience File (JSON Format):", type=["json"])
nasa_fc = 1.0
nasa_splicing = 1.0
target_antigen = "Unknown Target"

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

st.header("🧪 QSP Simulation Metrics Summary")
st.info(f"Active Computational Boundary Run Parameters:\n- NASA Target construct: {target_antigen}\n- Calculated Clearance: {calculated_crcl:.1f} mL/min\n- Patient Genomic Profile Weight: {patient_genomic_modifier}x")

# Run background zero-dependency Euler math execution loops
ode_params = {
    'crcl_ml_min': calculated_crcl, 'bsa_m2': 1.85, 'nasa_fc': nasa_fc, 'nasa_splicing': nasa_splicing, 
    'patient_genomic_modifier': patient_genomic_modifier, 'cyp_modifier': cyp_modifier
}
time_days, crs_trajectory, icans_trajectory = run_euler_simulation(ode_params)

peak_crs = float(np.max(crs_trajectory))
peak_icans = float(np.max(icans_trajectory))

st.write("---")

# =====================================================================
# SECTION 1: PREDICTIVE ANALYTICS OUTCOMES
# =====================================================================
st.header("🔮 Predictive Pre-Trial Analytics Outcomes")

col1, col2 = st.columns(2)

with col1:
    if peak_crs > 300:
        st.metric("Max Systemic CRS Peak", f"{peak_crs:.1f} pg/mL", delta="HIGH RISK", delta_color="inverse")
        st.error("⚠️ **CRITICAL CRS RISK DETECTED**")
        st.markdown("""
        **Clinical Intervention Required:**
        - Tocilizumab (8mg/kg) STAT
        - Consider ICU monitoring
        - Initiate cytokine panel q4h
        """)
    else:
        st.metric("Max Systemic CRS Peak", f"{peak_crs:.1f} pg/mL", delta="Low Risk", delta_color="normal")
        st.success("✅ **Low CRS Profile**")
        st.markdown("""
        **Standard Monitoring:**
        - Routine vital signs q8h
        - Continue standard protocol
        """)

with col2:
    if peak_icans > 80:
        st.metric("Max ICANS Neurotoxicity", f"{peak_icans:.1f} pts", delta="SEVERE RISK", delta_color="inverse")
        st.error("🚨 **SEVERE NEUROTOXICITY FLAGGED**")
        st.markdown("""
        **Neurological Protocol:**
        - Anakinra 100mg SC daily
        - Daily ICE assessments
        - EEG monitoring recommended
        """)
    else:
        st.metric("Max ICANS Neurotoxicity", f"{peak_icans:.1f} pts", delta="Stable", delta_color="normal")
        st.success("✅ **Stable Neurological Profile**")
        st.markdown("""
        **Standard Monitoring:**
        - Daily neurological checks
        - Standard safety protocol
        """)

st.write("---")

# =====================================================================
# SECTION 2: PLOTLY TIME-COURSE GRAPHICS CURVES
# =====================================================================
st.header("📈 Time-Course Kinetics & Trajectory Analysis")

# Create tabs for different visualization options
tab1, tab2 = st.tabs(["📊 CRS & ICANS Dynamics", "📉 Logarithmic Scale View"])

with tab1:
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add CRS trajectory trace
    fig.add_trace(go.Scatter(
        x=time_days,
        y=crs_trajectory,
        name="Systemic CRS (IL-6)",
        line=dict(color='#FF4B4B', width=3),
        fill='tozeroy',
        fillcolor='rgba(255, 75, 75, 0.2)',
        mode='lines'
    ))
    
    # Add ICANS trajectory trace
    fig.add_trace(go.Scatter(
        x=time_days,
        y=icans_trajectory,
        name="Neurotoxicity (ICANS)",
        line=dict(color='#0068C9', width=3, dash='dash'),
        mode='lines'
    ))
    
    # Add threshold lines
    fig.add_hline(y=300, line_dash="dot", line_color="red", 
                  annotation_text="CRS High Risk Threshold", annotation_position="top right")
    fig.add_hline(y=80, line_dash="dot", line_color="orange", 
                  annotation_text="ICANS Severe Threshold", annotation_position="bottom right")
    
    # Update layout
    fig.update_layout(
        title="Clinical Trajectories Over Time",
        xaxis_title="Time (Hours)",
        yaxis_title="Concentration / Index Value",
        hovermode='x unified',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(255, 255, 255, 0.8)'
        ),
        template='plotly_white',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add summary statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Peak CRS", f"{peak_crs:.0f} pg/mL", 
                  delta=f"at {time_days[np.argmax(crs_trajectory)]:.0f}h")
    with col2:
        st.metric("Peak ICANS", f"{peak_icans:.0f} pts",
                  delta=f"at {time_days[np.argmax(icans_trajectory)]:.0f}h")
    with col3:
        time_to_crs = time_days[np.where(crs_trajectory > 300)[0]]
        if len(time_to_crs) > 0:
            st.metric("Time to CRS Risk", f"{time_to_crs[0]:.0f}h", delta="⚠️")
        else:
            st.metric("Time to CRS Risk", "No Risk", delta="✅")
    with col4:
        time_to_icans = time_days[np.where(icans_trajectory > 80)[0]]
        if len(time_to_icans) > 0:
            st.metric("Time to ICANS Risk", f"{time_to_icans[0]:.0f}h", delta="🚨")
        else:
            st.metric("Time to ICANS Risk", "No Risk", delta="✅")

with tab2:
    # Logarithmic scale view for better visualization of dynamics
    fig_log = go.Figure()
    
    # Add traces with log scaling option
    fig_log.add_trace(go.Scatter(
        x=time_days,
        y=crs_trajectory + 1,  # Add 1 to avoid log(0)
        name="Systemic CRS (IL-6) - Log Scale",
        line=dict(color='#FF4B4B', width=3),
        mode='lines'
    ))
    
    fig_log.add_trace(go.Scatter(
        x=time_days,
        y=icans_trajectory + 1,
        name="Neurotoxicity (ICANS) - Log Scale",
        line=dict(color='#0068C9', width=3, dash='dash'),
        mode='lines'
    ))
    
    fig_log.update_layout(
        title="Clinical Trajectories (Logarithmic Scale)",
        xaxis_title="Time (Hours)",
        yaxis_title="Log(Value + 1)",
        yaxis_type="log",
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    st.plotly_chart(fig_log, use_container_width=True)
    
    st.info("💡 **Insight:** Logarithmic scale reveals early-phase dynamics and exponential growth patterns in cytokine response.")

st.write("---")

# =====================================================================
# SECTION 3: TAILORED PHARMACOTHERAPY & MITIGATION PLAN
# =====================================================================
st.header("💊 Tailored Pharmacotherapy & Mitigation Plan")

# Generate personalized treatment plan based on simulation results
treatment_plan = []
risk_level = "LOW"
recommendations = []

if peak_crs > 300 and peak_icans > 80:
    risk_level = "CRITICAL"
    st.error("🚨 **CRITICAL RISK PROFILE - Immediate Intervention Required**")
    
    treatment_plan = [
        {'therapy': 'Tocilizumab (Anti-IL-6R)', 
         'desc': '8mg/kg IV over 60 minutes, repeat in 8 hours if no improvement', 
         'priority': 'HIGH', 'timing': 'Immediate'},
        {'therapy': 'Anakinra (IL-1 Receptor Antagonist)', 
         'desc': '100mg SC loading dose, then 100mg daily for 7 days', 
         'priority': 'HIGH', 'timing': 'Within 2 hours'},
        {'therapy': 'High-dose Corticosteroids', 
         'desc': 'Methylprednisolone 1g IV daily for 3 days, then taper', 
         'priority': 'MEDIUM', 'timing': 'Within 4 hours'},
        {'therapy': 'Supportive Care', 
         'desc': 'ICU admission, vasopressor support if needed, continuous monitoring', 
         'priority': 'HIGH', 'timing': 'Immediate'}
    ]
    
    recommendations = [
        "Transfer to ICU for continuous monitoring",
        "Initiate hourly neurological assessments (ICE score)",
        "Obtain baseline EEG within 2 hours",
        "Daily cytokine panel (IL-6, IL-1, TNF-α)",
        "Prepare for potential mechanical ventilation"
    ]
    
elif peak_crs > 300:
    risk_level = "HIGH"
    st.warning("⚠️ **HIGH CRS RISK - Aggressive Management Recommended**")
    
    treatment_plan = [
        {'therapy': 'Tocilizumab (Anti-IL-6R)', 
         'desc': '8mg/kg IV over 60 minutes', 
         'priority': 'HIGH', 'timing': 'Within 2 hours'},
        {'therapy': 'Corticosteroids', 
         'desc': 'Methylprednisolone 2mg/kg/day divided q6h for 3-5 days', 
         'priority': 'MEDIUM', 'timing': 'Within 6 hours'},
        {'therapy': 'Supportive Care', 
         'desc': 'IV hydration, antipyretics, vital signs monitoring q2h', 
         'priority': 'MEDIUM', 'timing': 'Immediate'}
    ]
    
    recommendations = [
        "Monitor in step-down unit or ICU",
        "Check inflammatory markers q8h",
        "Neurological checks q4h",
        "Consider tocilizumab redosing if no improvement in 8 hours"
    ]
    
elif peak_icans > 80:
    risk_level = "HIGH-NEURO"
    st.warning("🧠 **SEVERE NEUROTOXICITY RISK - Neurological Protocol Required**")
    
    treatment_plan = [
        {'therapy': 'Anakinra (IL-1 Receptor Antagonist)', 
         'desc': '100mg SC daily for 7-14 days', 
         'priority': 'HIGH', 'timing': 'Within 2 hours'},
        {'therapy': 'Dexamethasone', 
         'desc': '10mg IV q6h for 48 hours, then taper', 
         'priority': 'HIGH', 'timing': 'Within 2 hours'},
        {'therapy': 'Supportive Care', 
         'desc': 'Seizure prophylaxis, EEG monitoring', 
         'priority': 'MEDIUM', 'timing': 'Within 6 hours'}
    ]
    
    recommendations = [
        "Daily ICE assessment and neurological exams",
        "Continuous EEG monitoring for 24-48 hours",
        "Avoid sedating medications if possible",
        "Consider MRI brain if neurological deficits persist"
    ]
    
else:
    risk_level = "LOW"
    st.success("✅ **LOW RISK PROFILE - Standard Prophylaxis Protocol**")
    
    treatment_plan = [
        {'therapy': 'Prophylactic Corticosteroids', 
         'desc': 'Hydrocortisone 100mg IV before CAR-T infusion', 
         'priority': 'LOW', 'timing': 'Pre-treatment'},
        {'therapy': 'Supportive Care', 
         'desc': 'Standard monitoring: vital signs q4h, neurological checks daily', 
         'priority': 'LOW', 'timing': 'Throughout treatment'},
        {'therapy': 'Patient Education', 
         'desc': 'Educate patient/family on early warning signs of CRS/ICANS', 
         'priority': 'LOW', 'timing': 'Prior to discharge'}
    ]
    
    recommendations = [
        "Outpatient monitoring with daily phone follow-up",
        "Provide emergency contact information",
        "Schedule follow-up visit in 7 days",
        "Baseline and weekly cytokine panel monitoring"
    ]

st.write("---")

# Display treatment plan in organized format
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Personalized Treatment Protocol")
    
    # Create treatment table
    treatment_df = pd.DataFrame(treatment_plan)
    st.dataframe(
        treatment_df[['therapy', 'desc', 'priority', 'timing']],
        hide_index=True,
        use_container_width=True
    )

with col2:
    st.subheader("🎯 Key Recommendations")
    for rec in recommendations:
        st.markdown(f"- {rec}")
    
    # Display risk summary
    st.markdown("---")
    st.subheader("📊 Risk Summary")
    risk_color = {
        "LOW": "🟢",
        "HIGH": "🟡",
        "HIGH-NEURO": "🟠",
        "CRITICAL": "🔴"
    }
    st.markdown(f"**Overall Risk Level:** {risk_color.get(risk_level, '⚪')} **{risk_level}**")
    
    # Additional metrics
    st.markdown(f"**CRS Peak:** {peak_crs:.1f} pg/mL")
    st.markdown(f"**ICANS Peak:** {peak_icans:.1f} pts")

st.write("---")

# =====================================================================
# PDF REPORT GENERATION & DOWNLOAD
# =====================================================================
st.subheader("📄 Generate Comprehensive Safety Report")

# Add acknowledgment checkbox for PDF generation
acknowledge_pdf = st.checkbox("I acknowledge that this is a research tool and will not use it for clinical decision-making without physician oversight")

# Prepare treatment plan for PDF (simplified version)
pdf_treatment_plan = [
    {'therapy': t['therapy'], 'desc': t['desc']} 
    for t in treatment_plan
]

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("📑 Generate & Download PDF Safety Report", use_container_width=True, type="primary", disabled=not acknowledge_pdf):
        with st.spinner("Generating comprehensive safety report..."):
            pdf_buffer = generate_pdf_report(
                target_antigen, 
                calculated_crcl, 
                nasa_fc, 
                nasa_splicing, 
                genotype_summary_text, 
                peak_crs, 
                peak_icans, 
                pdf_treatment_plan
            )
            
            st.success("✅ Report generated successfully!")
            
            st.download_button(
                label="💾 Download PDF Report",
                data=pdf_buffer,
                file_name=f"cosmotox_ai_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

st.markdown("---")
st.caption("© 2024 CosmoTox-AI | Powered by NASA Bioscience & Quantitative Systems Pharmacology")
