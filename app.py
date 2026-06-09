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
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#0068C9'), spaceAfter=15)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#FF4B4B'), spaceBefore=12, spaceAfter=8)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
    
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
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================================================
# SIDEBAR FILTERS SETUP
# =====================================================================
st.sidebar.title("🛠️ Configuration Sandbox")
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

# =====================================================================
# MAIN USER INTERFACE DISPLAY LAYOUT
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

# Flattened tracking metrics list view to prevent line spaces indentation errors
st.header("🔮 Predictive Pre-Trial Analytics")
if peak_crs > 300:
    st.error(f"💥 **Max Systemic CRS Peak:** {peak_crs:.1f} pg/mL ➔ ⚠️ HIGH CRS RISK DETECTED")
else:
    st.success(f"💥 **Max Systemic CRS Peak:** {peak_crs:.1f} pg/mL ➔ ✅ Low Profile")

if peak_icans > 80:
    st.error(f"🧠 **Max ICANS Neurotoxicity Index:** {peak_icans:.1f} pts ➔ 🚨 SEVERE NEURO-RISK FLAGGED")
else:
    st.success(f"🧠 **Max ICANS Neurotoxicity Index:** {peak_icans:.1f} pts ➔ ✅ Stable Profile")

# Add PDF download button (this was missing and would cause issues if called without treatment_plan)
if st.button("📄 Generate PDF Report"):
    # Define treatment plan based on simulation results
    treatment_plan = []
    
    if peak_crs > 300:
        treatment_plan.append({
            'therapy': 'Tocilizumab (Anti-IL6R)',
            'desc': 'Administer 8mg/kg IV over 60 minutes for severe CRS management'
        })
        treatment_plan.append({
            'therapy': 'Corticosteroids',
            'desc': 'Methylprednisolone 2mg/kg/day divided q6h for 3 days'
        })
    else:
        treatment_plan.append({
            'therapy': 'Supportive Care',
            'desc': 'Monitor vitals, hydration, and antipyretics as needed'
        })
    
    if peak_icans > 80:
        treatment_plan.append({
            'therapy': 'Anakinra (IL-1Ra)',
            'desc': '100mg SC daily for 7 days for neurotoxicity management'
        })
        treatment_plan.append({
            'therapy': 'Neurological Monitoring',
            'desc': 'Daily ICE assessment and EEG monitoring'
        })
    
    pdf_buffer = generate_pdf_report(
        target_antigen, calculated_crcl, nasa_fc, nasa_splicing, 
        genotype_summary_text, peak_crs, peak_icans, treatment_plan
    )
    
    st.download_button(
        label="💾 Download Safety Report (PDF)",
        data=pdf_buffer,
        file_name="cosmotox_ai_safety_report.pdf",
        mime="application/pdf"
    )
