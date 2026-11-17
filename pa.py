import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Dashboard de Denuncias", layout="wide")

st.title("📊 Panel de Análisis y Visualización de Denuncias")
st.markdown(
    "Sube tu archivo **CSV** o **Excel** con la estructura de denuncias para"
    " generar el análisis."
)

# 1. Barra lateral: Carga de archivo y filtros
with st.sidebar:
    st.header("1. Carga de Datos")
    archivo = st.file_uploader(
        "Sube tu archivo aquí", type=["csv", "xlsx", "xls"]
    )


@st.cache_data
def cargar_y_limpiar_datos(file):
    if file is not None:
        if file.name.endswith(".csv"):
            # 1. Leer primeras líneas para encontrar dónde empiezan los encabezados reales
            file.seek(0)
            primeras_lineas = [
                file.readline().decode("utf-8", errors="ignore")
                for _ in range(15)
            ]
            fila_inicio = 0
            for i, linea in enumerate(primeras_lineas):
                if "denunciaid" in linea.lower() or "comuna" in linea.lower():
                    fila_inicio = i
                    break

            # 2. Volver al inicio y leer con autodetección de separador (sep=None)
            file.seek(0)
            try:
                df = pd.read_csv(
                    file,
                    sep=None,
                    engine="python",
                    skiprows=fila_inicio,
                    on_bad_lines="skip",
                )
            except UnicodeDecodeError:
                # Si falla por tildes o eñes, intentar con codificación latin-1
                file.seek(0)
                df = pd.read_csv(
                    file,
                    sep=None,
                    engine="python",
                    skiprows=fila_inicio,
                    encoding="latin-1",
                    on_bad_lines="skip",
                )
        else:
            df = pd.read_excel(file)

        # Limpiar espacios en blanco en los nombres de las columnas
        df.columns = df.columns.str.strip()

        # Eliminar columnas vacías sin nombre
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        # Detectar automáticamente la columna de fecha y convertirla
        col_fecha = [c for c in df.columns if "fecha" in c.lower()]
        if col_fecha:
            df[col_fecha[0]] = pd.to_datetime(
                df[col_fecha[0]], errors="coerce"
            )

        return df
    return None


df = cargar_y_limpiar_datos(archivo)

if df is not None:
    # Identificar nombres exactos de tus columnas dinámicamente
    col_id = next(
        (c for c in df.columns if "id" in c.lower()), df.columns[0]
    )
    col_fecha = next((c for c in df.columns if "fecha" in c.lower()), None)
    col_comuna = next((c for c in df.columns if "comuna" in c.lower()), None)
    col_motivo = next((c for c in df.columns if "motivo" in c.lower()), None)
    col_rubro = next((c for c in df.columns if "rubro" in c.lower()), None)

    # 2. Filtros dinámicos en la barra lateral
    st.sidebar.header("2. Filtros")
    df_filtrado = df.copy()

    if col_comuna:
        comunas = st.sidebar.multiselect(
            "Filtrar por Comuna",
            options=df[col_comuna].dropna().unique(),
            default=df[col_comuna].dropna().unique(),
        )
        df_filtrado = df_filtrado[df_filtrado[col_comuna].isin(comunas)]

    if col_rubro:
        rubros = st.sidebar.multiselect(
            "Filtrar por Rubro",
            options=df[col_rubro].dropna().unique(),
            default=df[col_rubro].dropna().unique(),
        )
        df_filtrado = df_filtrado[df_filtrado[col_rubro].isin(rubros)]

    # 3. Tarjetas de Métricas Principales (KPIs)
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de Denuncias", len(df_filtrado))
    if col_comuna:
        kpi2.metric("Comunas Afectadas", df_filtrado[col_comuna].nunique())
    if col_rubro:
        kpi3.metric("Rubros Distintos", df_filtrado[col_rubro].nunique())

    st.divider()

    # 4. Gráficos especializados para estos atributos
    col_izq, col_der = st.columns(2)

    with col_izq:
        if col_comuna:
            st.subheader("📍 Denuncias por Comuna")
            conteo_comuna = (
                df_filtrado[col_comuna].value_counts().reset_index()
            )
            conteo_comuna.columns = ["Comuna", "Cantidad"]
            fig_comuna = px.bar(
                conteo_comuna,
                x="Comuna",
                y="Cantidad",
                text_auto=True,
                color="Cantidad",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_comuna, use_container_width=True)

    with col_der:
        if col_rubro:
            st.subheader("🏷️ Distribución por Rubro")
            conteo_rubro = df_filtrado[col_rubro].value_counts().reset_index()
            conteo_rubro.columns = ["Rubro", "Cantidad"]
            fig_rubro = px.pie(
                conteo_rubro,
                names="Rubro",
                values="Cantidad",
                hole=0.4,
            )
            st.plotly_chart(fig_rubro, use_container_width=True)

    col_inf_izq, col_inf_der = st.columns(2)

    with col_inf_izq:
        if col_motivo:
            st.subheader("📋 Top Motivos de Denuncia")
            conteo_motivo = (
                df_filtrado[col_motivo].value_counts().head(10).reset_index()
            )
            conteo_motivo.columns = ["Motivo", "Cantidad"]
            fig_motivo = px.bar(
                conteo_motivo,
                x="Cantidad",
                y="Motivo",
                orientation="h",
                text_auto=True,
            )
            fig_motivo.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )
            st.plotly_chart(fig_motivo, use_container_width=True)

    with col_inf_der:
        if col_fecha:
            st.subheader("📅 Evolución Temporal de Denuncias")
            tendencia = (
                df_filtrado.groupby(df_filtrado[col_fecha].dt.date)
                .size()
                .reset_index(name="Cantidad")
            )
            tendencia.columns = ["Fecha", "Cantidad"]
            fig_tiempo = px.line(
                tendencia, x="Fecha", y="Cantidad", markers=True
            )
            st.plotly_chart(fig_tiempo, use_container_width=True)

    # 5. Tabla de datos filtrados
    with st.expander("🔍 Ver tabla de registros filtrados"):
        st.dataframe(df_filtrado, use_container_width=True)

else:
    st.info(
        "👈 Sube tu archivo en el panel izquierdo para visualizar los datos de"
        " tus denuncias."
    )