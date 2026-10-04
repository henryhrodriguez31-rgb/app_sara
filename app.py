import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import requests

st.set_page_config(page_title="App Sara", page_icon="📊", layout="wide")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_mov = conn.read(worksheet="Movimientos", ttl=0)
    except Exception:
        df_mov = pd.DataFrame(columns=["Fecha", "Tipo", "Categoria", "Grupo", "Monto_USD", "Monto_VES", "Detalle"])

    try:
        df_est = conn.read(worksheet="Estimaciones", ttl=0)
    except Exception:
        df_est = pd.DataFrame(columns=["Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"])

    try:
        df_grup = conn.read(worksheet="Grupos", ttl=0)
        grupos = df_grup["Nombre_Grupo"].dropna().tolist()
    except Exception:
        grupos = ["Personal", "Hogar", "Inversión", "Trabajo"]

    return df_mov, df_est, grupos

df_movimientos, df_estimaciones, lista_grupos = cargar_datos()

# Tasa de cambio desde dolarapi.com
@st.cache_data(ttl=300)
def obtener_tasa_bcv():
    try:
        res = requests.get("https://dolarapi.com/v1/dolares/oficial")
        if res.status_code == 200:
            return float(res.json()["promedio"])
    except Exception:
        pass
    return 36.5  # Valor por defecto en caso de error de red

tasa_bcv = obtener_tasa_bcv()

st.title("📊 App Sara - Gestión Financiera")
st.caption(f"Tasa BCV Oficial: **{tasa_bcv:.2f} VES/USD**")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Registrar Movimiento", "🎯 Presupuesto vs Real", "📊 Resumen y Gráficos", "⚙️ Gestión de Grupos"])

# TAB 1: REGISTRAR MOVIMIENTO
with tab1:
    st.subheader("Nuevo Registro")
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha")
        tipo = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso"])
        categoria = st.text_input("Categoría", value="Alimentación" if tipo == "Gasto" else "Sueldo")
    with col2:
        grupo = st.selectbox("Grupo", lista_grupos)
        monto_usd = st.number_input("Monto ($ USD)", min_value=0.0, step=1.0)
        monto_ves = monto_usd * tasa_bcv
        st.info(f"Equivalente: **{monto_ves:,.2f} VES**")
        detalle = st.text_input("Detalle / Observación")

    if st.button("Guardar Movimiento", type="primary"):
        nuevo = pd.DataFrame([{
            "Fecha": str(fecha),
            "Tipo": tipo,
            "Categoria": categoria,
            "Grupo": grupo,
            "Monto_USD": monto_usd,
            "Monto_VES": monto_ves,
            "Detalle": detalle
        }])
        df_actualizado = pd.concat([df_movimientos, nuevo], ignore_index=True)
        conn.update(worksheet="Movimientos", data=df_actualizado)
        st.success("¡Movimiento registrado con éxito en Google Sheets!")
        st.rerun()

    st.divider()
    st.subheader("Historial de Movimientos")
    st.dataframe(df_movimientos, use_container_width=True)

# TAB 2: PRESUPUESTO VS REAL (Ingresos y Gastos)
with tab2:
    st.subheader("Comparativo Estimado vs Real")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 📥 Ingresos")
        ing_est = df_estimaciones[df_estimaciones["Tipo"] == "Ingreso"]["Monto_Estimado_USD"].sum() if not df_estimaciones.empty else 0.0
        ing_real = df_movimientos[df_movimientos["Tipo"] == "Ingreso"]["Monto_USD"].sum() if not df_movimientos.empty else 0.0
        st.metric("Ingresos Estimados", f"${ing_est:,.2f}")
        st.metric("Ingresos Reales", f"${ing_real:,.2f}", delta=f"${ing_real - ing_est:,.2f}")

    with col_b:
        st.markdown("### 📤 Gastos")
        gast_est = df_estimaciones[df_estimaciones["Tipo"] == "Gasto"]["Monto_Estimado_USD"].sum() if not df_estimaciones.empty else 0.0
        gast_real = df_movimientos[df_movimientos["Tipo"] == "Gasto"]["Monto_USD"].sum() if not df_movimientos.empty else 0.0
        st.metric("Gastos Estimados", f"${gast_est:,.2f}")
        st.metric("Gastos Reales", f"${gast_real:,.2f}", delta=f"${gast_est - gast_real:,.2f}")

# TAB 3: RESUMEN Y GRÁFICOS
with tab3:
    st.subheader("Análisis Visual")
    if not df_movimientos.empty:
        df_gastos = df_movimientos[df_movimientos["Tipo"] == "Gasto"]
        if not df_gastos.empty:
            df_grp = df_gastos.groupby("Grupo")["Monto_USD"].sum().reset_index()
            st.bar_chart(df_grp.set_index("Grupo"))
        else:
            st.info("No hay gastos registrados para graficar.")
    else:
        st.info("Aún no existen registros.")

# TAB 4: GESTIÓN DE GRUPOS
with tab4:
    st.subheader("Configuración de Grupos")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### ➕ Agregar Grupo")
        nuevo_grupo = st.text_input("Nombre del nuevo grupo")
        if st.button("Agregar Grupo"):
            if nuevo_grupo and nuevo_grupo not in lista_grupos:
                lista_grupos.append(nuevo_grupo)
                df_g = pd.DataFrame({"Nombre_Grupo": lista_grupos})
                conn.update(worksheet="Grupos", data=df_g)
                st.success(f"Grupo '{nuevo_grupo}' agregado con éxito.")
                st.rerun()

    with col_g2:
        st.markdown("#### 🗑️ Eliminar Grupo")
        grupo_eliminar = st.selectbox("Seleccionar grupo a eliminar", lista_grupos)
        if st.button("Eliminar Grupo", type="secondary"):
            if grupo_eliminar in lista_grupos:
                lista_grupos.remove(grupo_eliminar)
                df_g = pd.DataFrame({"Nombre_Grupo": lista_grupos})
                conn.update(worksheet="Grupos", data=df_g)
                st.success(f"Grupo '{grupo_eliminar}' eliminado.")
                st.rerun()