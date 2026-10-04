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
        df_mov = pd.DataFrame(columns=["Fecha", "Tipo", "Categoria", "Grupo", "Cuenta", "Monto_USD", "Monto_VES", "Detalle"])

    try:
        df_est = conn.read(worksheet="Estimaciones", ttl=0)
    except Exception:
        df_est = pd.DataFrame(columns=["Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"])

    try:
        df_inv = conn.read(worksheet="Inversiones", ttl=0)
    except Exception:
        df_inv = pd.DataFrame(columns=["Fecha", "Plataforma", "Activo", "Tipo_Operacion", "Monto_Invertido_USD", "Valor_Actual_USD", "Detalle"])

    try:
        df_grup = conn.read(worksheet="Grupos", ttl=0)
        grupos = df_grup["Nombre_Grupo"].dropna().tolist()
    except Exception:
        grupos = ["Personal", "Hogar", "Inversión", "Trabajo"]

    try:
        df_cta = conn.read(worksheet="Cuentas", ttl=0)
        cuentas = df_cta["Nombre_Cuenta"].dropna().tolist()
    except Exception:
        cuentas = ["Banesco (VES)", "Mercantil (VES)", "Efectivo (USD)", "Binance (USDT)", "Quantfury (USDT)"]

    return df_mov, df_est, df_inv, grupos, cuentas

df_movimientos, df_estimaciones, df_inversiones, lista_grupos, lista_cuentas = cargar_datos()

# Función para obtener tasas en tiempo real mediante API
@st.cache_data(ttl=300)
def obtener_tasas():
    tasa_bcv = 36.5
    tasa_paralelo = 36.5
    
    # Consulta Tasa BCV y Paralelo desde API
    try:
        res_bcv = requests.get("https://dolarapi.com/v1/dolares/oficial", timeout=5)
        if res_bcv.status_code == 200:
            tasa_bcv = float(res_bcv.json()["promedio"])
    except Exception:
        pass

    try:
        res_par = requests.get("https://dolarapi.com/v1/dolares/paralelo", timeout=5)
        if res_par.status_code == 200:
            tasa_paralelo = float(res_par.json()["promedio"])
    except Exception:
        tasa_paralelo = tasa_bcv

    return tasa_bcv, tasa_paralelo

tasa_bcv, tasa_paralelo = obtener_tasas()

# BARRA LATERAL (MENU IZQUIERDO)
st.sidebar.title("📌 App Sara Menu")

# Selector dinámico de tasa
tipo_tasa = st.sidebar.radio("Tasa activa para cálculo:", ["BCV Oficial", "Paralelo", "Manual"])

if tipo_tasa == "BCV Oficial":
    tasa_activa = tasa_bcv
elif tipo_tasa == "Paralelo":
    tasa_activa = tasa_paralelo
else:
    tasa_activa = st.sidebar.number_input("Tasa personalizada (VES/USD)", min_value=1.0, value=tasa_bcv, step=0.1)

st.sidebar.caption(f"💵 Tasa BCV: **{tasa_bcv:.2f} VES**")
st.sidebar.caption(f"📈 Tasa Paralela: **{tasa_paralelo:.2f} VES**")
st.sidebar.caption(f"⚡ Tasa Activa: **{tasa_activa:.2f} VES**")

if st.sidebar.button("🔄 Actualizar Tasas"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

opcion_menu = st.sidebar.radio(
    "Selecciona una opción:",
    [
        "🏛️ Saldos & Cuentas",
        "📝 Registrar Movimiento",
        "📈 Portafolio de Inversiones",
        "🎯 Presupuesto vs Real",
        "📥 Cargar Presupuesto (Excel/CSV)",
        "📊 Resumen y Gráficos",
        "⚙️ Gestión de Grupos y Cuentas"
    ]
)

st.title("📊 App Sara - Gestión Financiera Integrada")

# 1. SALDOS & CUENTAS
if opcion_menu == "🏛️ Saldos & Cuentas":
    st.subheader("Saldos Disponibles por Cuenta / Banco")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.metric("💵 Tasa BCV Oficial", f"{tasa_bcv:.2f} VES/USD")
    with col_t2:
        st.metric("📈 Tasa Paralela", f"{tasa_paralelo:.2f} VES/USD")
    with col_t3:
        st.metric("⚡ Tasa Activa Aplicada", f"{tasa_activa:.2f} VES/USD")
    st.divider()

    if not df_movimientos.empty and "Cuenta" in df_movimientos.columns:
        saldos = []
        for cta in lista_cuentas:
            ing = df_movimientos[(df_movimientos["Cuenta"] == cta) & (df_movimientos["Tipo"] == "Ingreso")]["Monto_USD"].sum()
            gast = df_movimientos[(df_movimientos["Cuenta"] == cta) & (df_movimientos["Tipo"] == "Gasto")]["Monto_USD"].sum()
            saldo_usd = ing - gast
            saldo_ves = saldo_usd * tasa_activa
            saldos.append({"Cuenta": cta, "Saldo ($ USD)": saldo_usd, "Saldo (VES)": saldo_ves})
        
        df_saldos = pd.DataFrame(saldos)
        st.dataframe(df_saldos, use_container_width=True)
        
        total_usd = df_saldos["Saldo ($ USD)"].sum()
        st.subheader(f"💰 Saldo Total Consolidado: **${total_usd:,.2f} USD** / **{total_usd * tasa_activa:,.2f} VES**")
    else:
        st.info("Registra tu primer movimiento asociando una cuenta para calcular los saldos automáticos.")

# 2. REGISTRAR MOVIMIENTO
elif opcion_menu == "📝 Registrar Movimiento":
    st.subheader("Nuevo Registro Diario")
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha")
        tipo = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso"])
        categoria = st.text_input("Categoría", value="Alimentación" if tipo == "Gasto" else "Sueldo")
        cuenta = st.selectbox("Cuenta / Banco", lista_cuentas)
    with col2:
        grupo = st.selectbox("Grupo", lista_grupos)
        monto_usd = st.number_input("Monto ($ USD)", min_value=0.0, step=1.0)
        monto_ves = monto_usd * tasa_activa
        st.info(f"Equivalente a Tasa Activa ({tasa_activa:.2f}): **{monto_ves:,.2f} VES**")
        detalle = st.text_input("Detalle / Observación")

    if st.button("Guardar Movimiento", type="primary"):
        nuevo = pd.DataFrame([{
            "Fecha": str(fecha),
            "Tipo": tipo,
            "Categoria": categoria,
            "Grupo": grupo,
            "Cuenta": cuenta,
            "Monto_USD": monto_usd,
            "Monto_VES": monto_ves,
            "Detalle": detalle
        }])
        df_actualizado = pd.concat([df_movimientos, nuevo], ignore_index=True)
        conn.update(worksheet="Movimientos", data=df_actualizado)
        st.success("¡Movimiento registrado correctamente!")
        st.rerun()

    st.divider()
    st.subheader("Historial Completo de Movimientos")
    st.dataframe(df_movimientos, use_container_width=True)

# 3. PORTAFOLIO DE INVERSIONES
elif opcion_menu == "📈 Portafolio de Inversiones":
    st.subheader("Seguimiento de Inversiones (Quantfury & Binance)")
    
    with st.expander("➕ Registrar Nueva Inversión / Posición"):
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            fecha_inv = st.date_input("Fecha de Operación")
            plataforma = st.selectbox("Plataforma", ["Quantfury", "Binance Futuros", "Binance Spot", "Otro"])
            activo = st.text_input("Activo / Ticker", value="SPY (S&P 500)")
            tipo_op = st.selectbox("Tipo de Operación", ["Compra (Long)", "Venta (Short)", "Hold / Staking"])
        with col_i2:
            monto_inv = st.number_input("Monto Invertido ($ USD)", min_value=0.0, step=10.0)
            valor_act = st.number_input("Valor Actual / Valor de Cierre ($ USD)", min_value=0.0, value=monto_inv, step=10.0)
            det_inv = st.text_input("Estrategia / Notas")

        if st.button("Guardar Inversión", type="primary"):
            nueva_inv = pd.DataFrame([{
                "Fecha": str(fecha_inv),
                "Plataforma": plataforma,
                "Activo": activo,
                "Tipo_Operacion": tipo_op,
                "Monto_Invertido_USD": monto_inv,
                "Valor_Actual_USD": valor_act,
                "Detalle": det_inv
            }])
            df_inv_actualizado = pd.concat([df_inversiones, nueva_inv], ignore_index=True)
            conn.update(worksheet="Inversiones", data=df_inv_actualizado)
            st.success("¡Posición de inversión registrada!")
            st.rerun()

    st.divider()
    st.subheader("Resumen de Portafolio de Inversiones")
    
    if not df_inversiones.empty:
        df_inversiones["Rendimiento ($)"] = df_inversiones["Valor_Actual_USD"] - df_inversiones["Monto_Invertido_USD"]
        
        col_m1, col_m2, col_m3 = st.columns(3)
        total_inv = df_inversiones["Monto_Invertido_USD"].sum()
        total_val = df_inversiones["Valor_Actual_USD"].sum()
        total_pnl = total_val - total_inv
        
        col_m1.metric("Capital Invertido", f"${total_inv:,.2f}")
        col_m2.metric("Valor Actual del Portafolio", f"${total_val:,.2f}")
        col_m3.metric("Ganancia / Pérdida Total", f"${total_pnl:,.2f}", delta=f"${total_pnl:,.2f}")
        
        st.dataframe(df_inversiones, use_container_width=True)
    else:
        st.info("Aún no tienes posiciones de inversión registradas.")

# 4. PRESUPUESTO VS REAL
elif opcion_menu == "🎯 Presupuesto vs Real":
    st.subheader("Comparativo de Desempeño Financiero")
    
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

# 5. CARGAR PRESUPUESTO
elif opcion_menu == "📥 Cargar Presupuesto (Excel/CSV)":
    st.subheader("Importar Presupuesto Estimado por Archivo")
    archivo = st.file_uploader("Sube tu archivo de presupuesto (Excel o CSV)", type=["xlsx", "xls", "csv"])
    
    st.caption("El archivo debe contener las columnas: **Tipo**, **Categoria**, **Grupo**, **Monto_Estimado_USD**")
    
    if archivo is not None:
        try:
            if archivo.name.endswith(".csv"):
                df_cargado = pd.read_csv(archivo)
            else:
                df_cargado = pd.read_excel(archivo)
                
            st.write("Vista previa del archivo cargado:")
            st.dataframe(df_cargado.head())
            
            if st.button("Guardar Presupuesto en Google Sheets", type="primary"):
                conn.update(worksheet="Estimaciones", data=df_cargado)
                st.success("¡Presupuesto importado y guardado exitosamente!")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

# 6. RESUMEN Y GRÁFICOS
elif opcion_menu == "📊 Resumen y Gráficos":
    st.subheader("Evolución y Distribución de Gastos")
    if not df_movimientos.empty:
        df_gastos = df_movimientos[df_movimientos["Tipo"] == "Gasto"]
        if not df_gastos.empty:
            df_grp = df_gastos.groupby("Grupo")["Monto_USD"].sum().reset_index()
            st.bar_chart(df_grp.set_index("Grupo"))
        else:
            st.info("No hay gastos registrados para graficar.")
    else:
        st.info("Aún no existen registros para mostrar métricas.")

# 7. GESTIÓN DE GRUPOS Y CUENTAS
elif opcion_menu == "⚙️ Gestión de Grupos y Cuentas":
    st.subheader("Configuración de Parámetros")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### 📁 Gestión de Grupos")
        nuevo_grupo = st.text_input("Agregar Nuevo Grupo")
        if st.button("Agregar Grupo"):
            if nuevo_grupo and nuevo_grupo not in lista_grupos:
                lista_grupos.append(nuevo_grupo)
                conn.update(worksheet="Grupos", data=pd.DataFrame({"Nombre_Grupo": lista_grupos}))
                st.success(f"Grupo '{nuevo_grupo}' agregado.")
                st.rerun()

        grupo_eliminar = st.selectbox("Eliminar Grupo Existente", lista_grupos)
        if st.button("Eliminar Grupo"):
            if grupo_eliminar in lista_grupos:
                lista_grupos.remove(grupo_eliminar)
                conn.update(worksheet="Grupos", data=pd.DataFrame({"Nombre_Grupo": lista_grupos}))
                st.success(f"Grupo '{grupo_eliminar}' eliminado.")
                st.rerun()

    with col_g2:
        st.markdown("#### 🏦 Gestión de Cuentas")
        nueva_cuenta = st.text_input("Agregar Nueva Cuenta / Banco")
        if st.button("Agregar Cuenta"):
            if nueva_cuenta and nueva_cuenta not in lista_cuentas:
                lista_cuentas.append(nueva_cuenta)
                conn.update(worksheet="Cuentas", data=pd.DataFrame({"Nombre_Cuenta": lista_cuentas}))
                st.success(f"Cuenta '{nueva_cuenta}' agregada.")
                st.rerun()

        cuenta_eliminar = st.selectbox("Eliminar Cuenta Existente", lista_cuentas)
        if st.button("Eliminar Cuenta"):
            if cuenta_eliminar in lista_cuentas:
                lista_cuentas.remove(cuenta_eliminar)
                conn.update(worksheet="Cuentas", data=pd.DataFrame({"Nombre_Cuenta": lista_cuentas}))
                st.success(f"Cuenta '{cuenta_eliminar}' eliminada.")
                st.rerun()