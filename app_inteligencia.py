import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
import json
import os
import base64
import pickle 
from io import BytesIO
from PIL import Image
from fpdf import FPDF
import plotly.express as px

# --- 1. CONFIGURACIÓN Y SEGURIDAD ---
st.set_page_config(layout="wide", page_title="Analizador Pro i2 - Operativo")

USERS_DB = "users_db.json"
CASOS_DIR = "casos_guardados"
ADMIN_USER = "admin"
ADMIN_PASS = "wick2026"

if not os.path.exists(CASOS_DIR):
    os.makedirs(CASOS_DIR)

def cargar_usuarios():
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f: return json.load(f)
    return {ADMIN_USER: {"pass": ADMIN_PASS, "status": "active", "role": "admin"}}

def guardar_usuarios(db):
    with open(USERS_DB, "w") as f: json.dump(db, f)

# Estilo de Interfaz Táctica
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #000; color: #ff4b4b; text-align: center;
        padding: 5px; font-family: monospace; border-top: 1px solid #ff4b4b; z-index: 1000;
    }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
    </style>
    <div class="footer">CLASSIFIED MATERIAL | ANALYST: JHON WICK | CONTROL DE ACCESO NIVEL 4</div>
    """, unsafe_allow_html=True)

# --- 2. CONTROL DE ACCESO ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = None
    st.session_state.role = None

if not st.session_state.auth:
    st.title("🔐 ACCESO RESTRINGIDO - UNIDAD I2")
    tab_log, tab_reg = st.tabs(["[ IDENTIFICARSE ]", "[ SOLICITAR ALTA ]"])
    db = cargar_usuarios()

    with tab_log:
        with st.form("login"):
            u = st.text_input("BADGE ID (Usuario)")
            p = st.text_input("PASSCODE", type="password")
            if st.form_submit_button("VALIDAR"):
                if u in db and db[u]["pass"] == p:
                    if db[u]["status"] == "active":
                        st.session_state.auth = True
                        st.session_state.user = u
                        st.session_state.role = db[u]["role"]
                        st.rerun()
                    else: st.warning("⚠️ ESTADO: Pendiente de autorización por Mando Central.")
                else: st.error("ERROR: Credenciales no reconocidas.")
    
    with tab_reg:
        with st.form("registro"):
            nu = st.text_input("NUEVO BADGE ID")
            np = st.text_input("DEFINIR PASSCODE", type="password")
            if st.form_submit_button("ENVIAR SOLICITUD"):
                if nu in db: st.error("El ID ya está registrado.")
                elif nu and np:
                    db[nu] = {"pass": np, "status": "pending", "role": "user"}
                    guardar_usuarios(db)
                    st.success("✅ SOLICITUD ENVIADA AL ARCHIVO CENTRAL.")
                else: st.error("Complete todos los campos de identificación.")
    st.stop()

# --- 3. PANEL DE ADMINISTRACIÓN ---
if st.session_state.role == "admin":
    with st.sidebar.expander("🛠️ GESTIÓN DE PERSONAL"):
        db = cargar_usuarios()
        pendientes = [u for u, d in db.items() if d["status"] == "pending"]
        if pendientes:
            u_act = st.selectbox("Solicitudes:", pendientes)
            if st.button("✅ AUTORIZAR ACCESO"):
                db[u_act]["status"] = "active"
                guardar_usuarios(db); st.rerun()
        
        existentes = [u for u in db.keys() if u != ADMIN_USER]
        if existentes:
            u_del = st.selectbox("Dar de baja ID:", existentes)
            if st.button("🗑️ ELIMINAR CUENTA"):
                del db[u_del]
                guardar_usuarios(db); st.success(f"ID {u_del} purgado."); st.rerun()

# --- 4. SISTEMA DE PERSISTENCIA ---
def save_project(name):
    data = {
        "df": st.session_state.get('main_df'),
        "bitacora": st.session_state.get('bitacora', {}),
        "fotos": st.session_state.get('fotos_sujetos', {}) # Ahora guarda bytes
    }
    with open(os.path.join(CASOS_DIR, f"{name}.i2"), "wb") as f:
        pickle.dump(data, f)

def load_project(name):
    with open(os.path.join(CASOS_DIR, f"{name}.i2"), "rb") as f:
        return pickle.load(f)

with st.sidebar.expander("💾 ARCHIVO DE CASOS"):
    nombre_caso = st.text_input("Nombre del Caso Actual:")
    if st.button("💾 GUARDAR TODO"):
        if 'main_df' in st.session_state and nombre_caso:
            save_project(nombre_caso)
            st.sidebar.success(f"Caso '{nombre_caso}' guardado.")
        else:
            st.sidebar.error("No hay datos para guardar.")

    st.markdown("---")
    casos_disponibles = [f.replace(".i2", "") for f in os.listdir(CASOS_DIR) if f.endswith(".i2")]
    if casos_disponibles:
        caso_selec = st.selectbox("Cargar caso previo:", casos_disponibles)
        if st.button("📂 CARGAR CASO"):
            datos = load_project(caso_selec)
            st.session_state.main_df = datos["df"]
            st.session_state.bitacora = datos["bitacora"]
            st.session_state.fotos_sujetos = datos["fotos"]
            st.rerun()

if st.sidebar.button("🔒 CERRAR SESIÓN"):
    st.session_state.auth = False
    st.rerun()

# --- 5. ANALIZADOR PRO I2 - NÚCLEO ---
st.title("🕵️‍♂️ Sistema Integral de Inteligencia Telefónica")
st.caption(f"Operador activo: {st.session_state.user} | Nivel: {st.session_state.role.upper()}")

if 'bitacora' not in st.session_state: st.session_state.bitacora = {}
if 'fotos_sujetos' not in st.session_state: st.session_state.fotos_sujetos = {}

archivo = st.sidebar.file_uploader("Cargar Sábana de Llamadas (Excel)", type=["xlsx"])

if archivo:
    df_temp = pd.read_excel(archivo)
    df_temp['Linea_A'] = df_temp['Linea_A'].astype(str).str.strip()
    df_temp['Linea_B'] = df_temp['Linea_B'].astype(str).str.strip()
    df_temp['Fecha'] = pd.to_datetime(df_temp['Fecha'], dayfirst=True, errors='coerce')
    st.session_state.main_df = df_temp.dropna(subset=['Fecha'])

if 'main_df' in st.session_state:
    df = st.session_state.main_df

    # Resumen Estadístico
    st.subheader("📊 Resumen de Actividad Total")
    col_stats1, col_stats2 = st.columns([2, 1])
    
    salientes = df['Linea_A'].value_counts().reset_index()
    salientes.columns = ['Línea', 'Salientes']
    entrantes = df['Linea_B'].value_counts().reset_index()
    entrantes.columns = ['Línea', 'Entrantes']
    stats = pd.merge(salientes, entrantes, on='Línea', how='outer').fillna(0)
    stats['Total'] = stats['Salientes'] + stats['Entrantes']
    stats = stats.sort_values(by='Total', ascending=False).reset_index(drop=True)
    
    with col_stats1:
        st.dataframe(stats, use_container_width=True)
    
    with col_stats2:
        # Mini Histograma Temporal
        df['Hora'] = df['Fecha'].dt.hour
        fig_hora = px.histogram(df, x='Hora', nbins=24, title="Picos de Actividad (24h)", color_discrete_sequence=['#ff4b4b'])
        fig_hora.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_hora, use_container_width=True)

    tab_red, tab_cruces, tab_forense, tab_fichas = st.tabs([
        "🕸️ Red de Vínculos", 
        "🔍 Análisis de Cruces", 
        "🔎 Buscador Forense",
        "📁 Fichas Policiales"
    ])

    with tab_red:
        st.subheader("Mapa Jerárquico Horizontal (L-R)")
        df_inter = df.groupby(['Linea_A', 'Linea_B']).size().reset_index(name='cantidad')
        net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
        niveles = {row['Línea']: i for i, row in stats.iterrows()}

        for index, row in stats.iterrows():
            nodo = row['Línea']
            color_nodo = "#ff4b4b" if index < 3 else "#1f77b4"
            icono = " 👤" if nodo in st.session_state.fotos_sujetos else ""
            net.add_node(nodo, label=f"{nodo}{icono}", size=int(min(row['Total'] + 20, 75)), 
                         level=niveles[nodo], color=color_nodo, shape="dot")

        for _, fila in df_inter.iterrows():
            cant = int(fila['cantidad'])
            net.add_edge(fila['Linea_A'], fila['Linea_B'], label=str(cant), 
                         width=max(1, cant/2), color="#444444")
        
        net.set_options("""{"layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed"}}, "physics": {"enabled": false}}""")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            net.save_graph(tmp.name)
            st.components.v1.html(open(tmp.name, 'r', encoding='utf-8').read(), height=700)

    with tab_cruces:
        st.subheader("Intermediarios Comunes")
        c1, c2 = st.columns(2)
        s1 = c1.selectbox("Objetivo 1:", stats['Línea'].unique(), index=0)
        s2 = c2.selectbox("Objetivo 2:", stats['Línea'].unique(), index=1 if len(stats)>1 else 0)
        cont_a = set(df[df['Linea_A'] == s1]['Linea_B']).union(set(df[df['Linea_B'] == s1]['Linea_A']))
        cont_b = set(df[df['Linea_A'] == s2]['Linea_B']).union(set(df[df['Linea_B'] == s2]['Linea_A']))
        comunes = cont_a.intersection(cont_b)
        if comunes: st.success(f"Contactos compartidos: {list(comunes)}")
        else: st.info("Sin coincidencias.")

    with tab_forense:
        st.subheader("🔎 Rastreo Detallado")
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        n_buscar = col_f1.text_input("Número a rastrear:")
        if n_buscar:
            f_ini = col_f2.date_input("Inicio:", df['Fecha'].min().date())
            f_fin = col_f3.date_input("Fin:", df['Fecha'].max().date())
            res = df[(df['Linea_A'] == n_buscar) | (df['Linea_B'] == n_buscar)]
            res = res[(res['Fecha'].dt.date >= f_ini) & (res['Fecha'].dt.date <= f_fin)]
            st.dataframe(res.sort_values('Fecha'), use_container_width=True)

    with tab_fichas:
        st.subheader("📁 Gestión de Expedientes")
        f_cols = st.columns(3)
        for i, row in stats.iterrows():
            num = row['Línea']
            with f_cols[i % 3]:
                with st.expander(f"👤 FICHA: {num}"):
                    f_up = st.file_uploader("Foto:", type=['jpg','png','jpeg'], key=f"f_{num}")
                    if f_up:
                        st.session_state.fotos_sujetos[num] = f_up.getvalue()
                    if num in st.session_state.fotos_sujetos:
                        st.image(st.session_state.fotos_sujetos[num], width=120)
                    st.session_state.bitacora[num] = st.text_area("Notas:", value=st.session_state.bitacora.get(num, ""), key=f"n_{num}")

        if st.button("📄 Generar Reporte PDF Final"):
            pdf = FPDF()
            for index, row in stats.iterrows():
                num = row['Línea']
                pdf.add_page()
                pdf.set_fill_color(30, 30, 30); pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 15, f"EXPEDIENTE: {num}", ln=True, align="C", fill=True)
                pdf.set_text_color(0, 0, 0); pdf.ln(10)
                
                if num in st.session_state.fotos_sujetos:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
                        img = Image.open(BytesIO(st.session_state.fotos_sujetos[num])).convert("RGB")
                        img.save(t.name)
                        pdf.image(t.name, x=10, y=35, w=40)
                
                pdf.set_x(55); pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 10, f"ID: {num}", ln=True)
                pdf.set_font("Helvetica", "", 11); pdf.set_x(55)
                pdf.cell(0, 7, f"Total Interacciones: {int(row['Total'])}", ln=True)
                pdf.ln(30); pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 10, "OBSERVACIONES TÁCTICAS:", ln=True, fill=True)
                pdf.multi_cell(0, 8, st.session_state.bitacora.get(num, "Sin datos registrados."), border=1)
            
            # --- CORRECCIÓN DEL TYPEERROR ---
            pdf_out = pdf.output(dest='S')
            pdf_bytes = pdf_out.encode('latin-1') if isinstance(pdf_out, str) else pdf_out
            st.download_button("📥 Descargar Reporte", data=pdf_bytes, file_name="Reporte_Intel.pdf", mime="application/pdf")
else:
    st.info("SISTEMA EN ESPERA: Cargue el vector de datos (Excel) o abra un caso guardado en la barra lateral.")
