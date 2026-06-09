import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import json
from scipy.integrate import solve_ivp
from openai import OpenAI
import io

# Import ReportLab modules for direct in-memory PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="CosmoTox-AI Dashboard", page_icon="🚀", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to CosmoTox-AI! Upload your NASA spaceflight dataset or paste a patient's genetic/variant profile to calculate custom trial risks."}
    ]

def car_t_toxicity_system(t, y, params):
    Flu_C, Cy_C, Systemic_IL6, ICANS_CNS = y
    
    # Scale fludarabine clearance by renal function
    cl_flu = 9.5 * (params['crcl_ml_min'] / 100.0)
    v1_flu = params['bsa_m2'] * 20.0
    
    # Incorporate Patient Genotype Modifier on Cyclophosphamide Metabolism (e.g., CYP2B6/CYP2C19 variants)
    cyp_modifier = params.get('cyp_modifier', 1.0)
    cl_cy = 11.0 * cyp_modifier
    v1_cy = params['bsa_m2'] * 30.0
    
    dFlu_C = -(cl_flu / v1_flu) * Flu_C
    dCy_C = -(cl_cy / v1_cy) * Cy_C
    
    # Dynamic Cytokine Release Syndrome Equation (CRS Model)
    # Scaled by NASA's cellular stress metric multiplied by the patient's exact genomic variant weight
    nasa_stress_impact = params['nasa_fc'] * params['nasa_splicing']
    patient_genomic_multiplier = params['patient_genomic_modifier']
    
    dIL6 = (nasa_stress_impact * patient_genomic_multiplier * 50.0) - (0.18 * Systemic_IL6)
    
    # Mathematical Modeling of ICANS Neurotoxicity via Sigmoidal BBB Leaking
    bbb_leakage_index = 1.0 / (1.0 + np.exp(-0.025 * (Systemic_IL6 - 220.0)))
    dICANS = (Systemic_IL6 * bbb_leakage_index * 0.35) - (0.22 * ICANS_CNS)
    
    return [dFlu_C, dCy_C, dIL6, dICANS]

def generate_pdf_report(target, crcl, fc, splicing, genotype_summary, peak_crs, peak_icans):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#0068C9'), spaceAfter=15)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#FF4B4B'), spaceBefore=12, spaceAfter=8)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
    
    story.append(Paragraph("CosmoTox-AI: Patient-Specific Pre-Clinical Risk Report", title_style))
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
    t1 = Table(data_inputs, colWidths=[200, 320])
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
        ["Max Systemic Cytokine Storm (CRS)", f"{peak_crs:.1f} pg/mL", "⚠️ HIGH CRS RISK" if peak_crs > 300 else "✅ Low Exposure Profile"],
        ["Max Neurovascular ICANS Intensity", f"{peak_icans:.1f} pts", "🚨 SEVERE NEURO-RISK" if peak_icans > 80 else "✅ Stable Profile"]
    ]
    t2 = Table(data_outcomes, colWidths=[200, 160, 160])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (2,0), colors.HexColor('#FF4B4B')),
        ('TEXTCOLOR', (0,0), (2,0), colors.white),
        ('FONTNAME', (0,0), (2,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    story.append(t2)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("3. Automated Clinical Trial Mitigation Blueprint", section_style))
    if peak_crs > 300 or peak_icans > 80:
        verdict = f"CRITICAL ACTION REQUIRED: High risk profile flagged for antigen target '{target}'. Based on the patient's individual genomic variant risk profile, mandate prophylactic IL-6 receptor antagonists within the first 12 hours of cellular infusion, and establish a strict exclusion filter for patients with a baseline CrCl below 50 mL/min."
    else:
        verdict = "ACCEPTABLE TOXICITY SCHEMAS: Acceptable clinical toxicology profile model. Standard inpatient observation monitoring is appropriate for this design framework."
    story.append(Paragraph(verdict, body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================================================
# SIDEBAR CONFIGURATION FILTERS
# =====================================================================
st.sidebar.title("🛠️ Configuration Sandbox")

st.sidebar.markdown("### 1. Artificial Intelligence Core")
api_key_input = st.sidebar.text_input("Enter OpenAI API Key:", type="password")
api_key = st.secrets.get("OPENAI_API_KEY", "") if not api_key_input else api_key_input

if not api_key:
    st.sidebar.warning("⚠️ Chat features require an OpenAI API Key.")
else:
    st.sidebar.success("🤖 OpenAI Engine Connected.")

st.sidebar.write("---")

# NEW BLOCK: Patient-Specific Personal Gene Profile Filters
st.sidebar.markdown("### 🧬 2. Patient Genomic Profile Input")
genomic_source = st.sidebar.selectbox("Genomic Mode Source:", ["Standard Population Sliders", "Upload Patient Gene Profile / SNPs"])

patient_genomic_modifier = 1.5
cyp_modifier = 1.0
genotype_summary_text = "Standard Population Metrics Applied"

if genomic_source == "Upload Patient Gene Profile / SNPs":
    st.sidebar.markdown("ℹ️ *Paste or upload individual patient variants (e.g., HLA alleles, IL6 mutations, CYP SNPs).*")
    custom_gene_text = st.sidebar.text_area("Paste Patient Variant Lines (e.g., 'IL6-rs1800795: G/G, CYP2B6*6: True'):", value="IL6-rs1800795: G/G, CYP2B6*6: Heterozygous, HLA-A*02:01")
    
    # High-utility parsing logic translating genetic raw texts into active ODE math multipliers
    if "IL6-rs1800795: G/G" in custom_gene_text or "G/G" in custom_gene_text:
        patient_genomic_modifier = 2.8
        genotype_summary_text = "IL-6 Hyper-Expression Variant Detected (G/G)"
        st.sidebar.error("🚨 Flagged: High-Expression IL-6 Polymorphism.")
    if "CYP2B6*6" in custom_gene_text or "Slow Metabolizer" in custom_gene_text.lower():
        cyp_modifier = 0.5
        genotype_summary_text += " | CYP2B6 Poor Metabolizer (Altered Chemo Clearance)"
        st.sidebar.warning("⚠️ Flagged: Decreased Cyclophosphamide Clearance.")
else:
    selected_biobank = st.sidebar.selectbox("Choose Target Population Data Bank Reference:", ["UK Biobank (N=500k)", "NIH All of Us Cohort"])
    patient_genomic_modifier = st.sidebar.slider("Biobank Baseline Risk Prevalence (Host PGx)", 1.0, 3.0, value=1.5, step=0.1)

st.sidebar.write("---")
st.sidebar.markdown("### 👤 3. Patient Baseline Metrics")
age = st.sidebar.number_input("Patient Baseline Age:", 18, 95, 62)
weight = st.sidebar.number_input("Weight (kg):", 40, 150, 78)
serum_creatinine = st.sidebar.number_input("Serum Creatinine (mg/dL):", 0.3, 8.0, 1.3)
calculated_crcl = ((140 - age) * weight) / (72 * serum_creatinine)
st.sidebar.markdown(f"**Computed Clearance Rate (CrCl):** `{calculated_crcl:.1f} mL/min`")

# =====================================================================
# MAIN USER INTERFACE DISPLAY LAYOUT
# =====================================================================
st.title("🚀 CosmoTox-AI Clinical Simulator")
st.markdown("Predict off-target toxicities by translating **NASA Bioscience extreme stress markers** through **personalized patient-specific genomic variant sheets**.")
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
                
