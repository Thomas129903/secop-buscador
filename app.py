import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# ─── Configuración de la página ────────────────────────────────────────────
st.set_page_config(
    page_title="BuscaContrato — SECOP II",
    page_icon="🔍",
    layout="wide"
)

# ─── Estilos personalizados ─────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: white; border-radius: 10px; padding: 10px; }
    .contrato-card {
        background: white;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        border-left: 4px solid #1a6fb5;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    .tag {
        display: inline-block;
        background: #e8f0fe;
        color: #1a6fb5;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 12px;
        margin-right: 6px;
    }
    .valor { color: #1e7e34; font-weight: 600; font-size: 15px; }
    .entidad { color: #555; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ─── Header ────────────────────────────────────────────────────────────────
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    st.markdown("## 🔍")
with col_titulo:
    st.markdown("# BuscaContrato")
    st.markdown("*Buscador inteligente de oportunidades en SECOP II*")

st.divider()

# ─── Función de búsqueda en API de datos abiertos ──────────────────────────
@st.cache_data(ttl=300)  # Cache 5 minutos
def buscar_contratos(palabras_clave, departamento, estado, tipo_proceso,
                     fecha_desde, fecha_hasta, limite=50):
    """
    Consulta la API de datos abiertos de Colombia (SODA)
    Dataset: SECOP II - Procesos de Contratación (p6dx-8zbt)
    """
    BASE_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"

    # Construir filtro WHERE
    filtros = []

    if departamento and departamento != "Todos":
        filtros.append(f"upper(departamento_entidad) = upper('{departamento}')")

    if estado and estado != "Todos":
        filtros.append(f"upper(estado_del_proceso) = upper('{estado}')")

    if tipo_proceso and tipo_proceso != "Todos":
        filtros.append(f"upper(modalidad_de_contratacion) = upper('{tipo_proceso}')")

    if fecha_desde:
        filtros.append(f"fecha_de_publicacion >= '{fecha_desde}T00:00:00'")

    if fecha_hasta:
        filtros.append(f"fecha_de_publicacion <= '{fecha_hasta}T23:59:59'")

    # Búsqueda por palabras clave en descripción o nombre entidad
    if palabras_clave:
        termino = palabras_clave.replace("'", "''")
        filtros.append(
            f"(upper(descripcion_del_proceso) like upper('%{termino}%') "
            f"OR upper(nombre_entidad) like upper('%{termino}%'))"
        )

    params = {
        "$limit": limite,
        "$order": "fecha_de_publicacion DESC",
    }
    if filtros:
        params["$where"] = " AND ".join(filtros)

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, "❌ No se pudo conectar. Verifica tu conexión a internet."
    except requests.exceptions.Timeout:
        return None, "⏱️ La consulta tardó demasiado. Intenta de nuevo."
    except Exception as e:
        return None, f"Error inesperado: {str(e)}"


def formatear_valor(valor_str):
    """Formatea el valor del contrato a pesos colombianos legibles."""
    try:
        valor = float(valor_str)
        if valor >= 1_000_000_000:
            return f"$ {valor/1_000_000_000:.1f} Mil millones"
        elif valor >= 1_000_000:
            return f"$ {valor/1_000_000:.0f}M"
        elif valor >= 1_000:
            return f"$ {valor/1_000:.0f}K"
        else:
            return f"$ {valor:,.0f}"
    except:
        return "No especificado"


def get_color_estado(estado):
    colores = {
        "publicado": "#1a6fb5",
        "adjudicado": "#1e7e34",
        "desierto": "#c0392b",
        "terminado": "#7f8c8d",
        "celebrado": "#8e44ad",
    }
    estado_lower = (estado or "").lower()
    for key, color in colores.items():
        if key in estado_lower:
            return color
    return "#555"


# ─── Panel de filtros ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Filtros de búsqueda")

    palabras = st.text_input(
        "🔎 Palabras clave",
        placeholder="Ej: mantenimiento, consultoria, suministro...",
        help="Busca en el título y descripción del proceso"
    )

    departamento = st.selectbox("📍 Departamento", [
        "Todos", "VALLE DEL CAUCA", "ANTIOQUIA", "BOGOTÁ D.C.",
        "CUNDINAMARCA", "ATLÁNTICO", "SANTANDER", "BOLÍVAR",
        "NARIÑO", "CÓRDOBA", "TOLIMA", "RISARALDA", "CALDAS",
        "CAUCA", "HUILA", "META", "BOYACÁ", "MAGDALENA"
    ], index=1)  # Valle del Cauca por defecto

    estado = st.selectbox("📋 Estado del proceso", [
        "Todos", "Publicado", "Adjudicado", "Celebrado",
        "Desierto", "Terminado", "Suspendido"
    ], index=1)  # Publicado por defecto

    tipo_proceso = st.selectbox("📝 Tipo de proceso", [
        "Todos", "Mínima cuantía", "Contratación directa",
        "Selección abreviada", "Licitación pública",
        "Concurso de méritos"
    ])

    st.markdown("**📅 Rango de fechas**")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_desde = st.date_input(
            "Desde",
            value=datetime.now() - timedelta(days=7)
        )
    with col_f2:
        fecha_hasta = st.date_input(
            "Hasta",
            value=datetime.now()
        )

    limite = st.slider("Máximo de resultados", 10, 200, 50, 10)

    buscar = st.button("🔍 Buscar contratos", type="primary", use_container_width=True)

    st.divider()
    st.markdown("**💡 Consejos:**")
    st.markdown("- Usa palabras del objeto del contrato")
    st.markdown("- Ejemplo: *construcción*, *software*, *aseo*")
    st.markdown("- Combina con tipo de proceso para afinar")


# ─── Resultados ─────────────────────────────────────────────────────────────
if buscar or "resultados" in st.session_state:

    if buscar:
        with st.spinner("🔄 Buscando en SECOP II..."):
            datos, error = buscar_contratos(
                palabras_clave=palabras,
                departamento=departamento,
                estado=estado,
                tipo_proceso=tipo_proceso,
                fecha_desde=str(fecha_desde),
                fecha_hasta=str(fecha_hasta),
                limite=limite
            )
            st.session_state["resultados"] = datos
            st.session_state["error"] = error

    datos = st.session_state.get("resultados")
    error = st.session_state.get("error")

    if error:
        st.error(error)

    elif datos is not None:
        if len(datos) == 0:
            st.warning("⚠️ No se encontraron contratos con esos criterios. Intenta ampliar el rango de fechas o cambiar las palabras clave.")
        else:
            # Métricas resumen
            df = pd.DataFrame(datos)
            total = len(df)

            # Calcular valor total aproximado
            try:
                valor_total = df["valor_total_estimado"].dropna().astype(float).sum()
            except:
                valor_total = 0

            entidades_unicas = df["nombre_entidad"].nunique() if "nombre_entidad" in df.columns else 0

            st.markdown(f"### ✅ {total} contratos encontrados")
            col1, col2, col3 = st.columns(3)
            col1.metric("📋 Procesos", total)
            col2.metric("🏛️ Entidades", entidades_unicas)
            col3.metric("💰 Valor estimado total", formatear_valor(valor_total))

            st.divider()

            # Tabs: tarjetas y tabla
            tab1, tab2 = st.tabs(["📋 Vista por contratos", "📊 Vista tabla"])

            with tab1:
                for _, row in df.iterrows():
                    nombre = row.get("descripcion_del_proceso") or row.get("nombre_proceso") or "Sin descripción"
                    entidad = row.get("nombre_entidad", "Entidad no especificada")
                    valor = formatear_valor(row.get("valor_total_estimado", "0"))
                    estado_proc = row.get("estado_del_proceso", "")
                    modalidad = row.get("modalidad_de_contratacion", "")
                    fecha_pub = str(row.get("fecha_de_publicacion", ""))[:10]
                    ciudad = row.get("ciudad_entidad", "")
                    url_proceso = row.get("urlproceso", {})
                    if isinstance(url_proceso, dict):
                        url = url_proceso.get("url", "")
                    else:
                        url = ""

                    color = get_color_estado(estado_proc)

                    st.markdown(f"""
                    <div class="contrato-card" style="border-left-color: {color}">
                        <div style="font-weight:600; font-size:15px; margin-bottom:6px">{nombre[:200]}</div>
                        <div class="entidad">🏛️ {entidad} &nbsp;|&nbsp; 📍 {ciudad}</div>
                        <div style="margin-top:8px">
                            <span class="tag">{estado_proc}</span>
                            <span class="tag">{modalidad}</span>
                            <span class="tag">📅 {fecha_pub}</span>
                            <span class="valor" style="float:right">{valor}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if url:
                        st.markdown(f"[🔗 Ver proceso en SECOP II]({url})", unsafe_allow_html=False)

            with tab2:
                cols_mostrar = [c for c in [
                    "descripcion_del_proceso", "nombre_entidad", "ciudad_entidad",
                    "valor_total_estimado", "estado_del_proceso",
                    "modalidad_de_contratacion", "fecha_de_publicacion"
                ] if c in df.columns]

                df_show = df[cols_mostrar].copy()
                df_show.columns = [c.replace("_", " ").title() for c in cols_mostrar]
                st.dataframe(df_show, use_container_width=True, height=500)

                # Botón de descarga
                csv = df_show.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Descargar resultados en Excel/CSV",
                    data=csv,
                    file_name=f"contratos_secop_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

else:
    # Pantalla de bienvenida
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px">
        <div style="font-size:64px">🔍</div>
        <h2>Bienvenido a BuscaContrato</h2>
        <p style="color:#666; font-size:16px; max-width:500px; margin:0 auto">
            Configura tus filtros en el panel izquierdo y haz clic en
            <strong>Buscar contratos</strong> para encontrar oportunidades
            de negocio en SECOP II automáticamente.
        </p>
        <br>
        <p style="color:#999; font-size:13px">
            Datos actualizados diariamente por Colombia Compra Eficiente
        </p>
    </div>
    """, unsafe_allow_html=True)
