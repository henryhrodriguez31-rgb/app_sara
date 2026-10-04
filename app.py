import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import requests

st.set_page_config(page_title="App Sara", page_icon="📊", layout="wide")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Cargar datos e inicializar en st.session_state
def inicializar_estado():
    if "df_movimientos" not in st.session_state:
        try:
            df_mov = conn.read(worksheet="Movimientos", ttl=0)
            st.session_state.df_movimientos = df_mov.dropna(how="all")
        except Exception:
            st.session_state.df_movimientos = pd.DataFrame(
                columns=["Fecha", "Tipo", "Categoria", "Grupo", "Cuenta", "Monto_VES", "Tasa_Usada", "Monto_USD", "Detalle"]
            )

    if "df_estimaciones" not in st.session_state:
        try:
            df_est = conn.read(worksheet="Estimaciones", ttl=0)
            st.session_state.df_estimaciones = df_est.dropna(how="all")
        except Exception:
            st.session_state.df_estimaciones = pd.DataFrame(
                columns=["Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"]
            )

    if "df_inversiones" not in st.session_state:
        try:
            df_inv = conn.read(worksheet="Inversiones", ttl=0)
            st.session_state.df_inversiones = df_inv.dropna(how="all")
        except Exception:
            st.session_state.df_inversiones = pd.DataFrame(
                columns=["Fecha", "Plataforma", "Activo", "Tipo_Operacion", "Monto_Invertido_USD", "Valor_Actual_USD", "Detalle"]
            )

    if "lista_grupos" not in st.session_state:
        try:
            df_grup = conn.read(worksheet="Grupos", ttl=0)
            grupos = df_grup["Nombre_Grupo"].dropna().astype(str).str.strip().tolist()
            st.session_state.lista_grupos = [g for g in grupos if g and g != "nan"]
            if not st.session_state.lista_grupos:
                st.session_state.lista_grupos = ["Personal", "Hogar", "Inversión", "Trabajo"]
        except Exception:
            st.session_state.lista_grupos = ["Personal", "Hogar", "Inversión", "Trabajo"]

    if "lista_cuentas" not in st.session_state:
        try:
            df_cta = conn.read(worksheet="Cuentas", ttl=0)
            cuentas = df_cta["Nombre_Cuenta"].dropna().astype(str).str.strip().tolist()
            st.session_state.lista_cuentas = [c for c in cuentas if c and c != "nan"]
            if not st.session_state.lista_cuentas:
                st.session_state.lista_cuentas = ["Banesco (VES)", "Mercantil (VES)", "Efectivo (USD)", "Binance (USDT)", "Quantfury (USDT)"]
        except Exception:
            st.session_state.lista_cuentas = ["Banesco (VES)", "Mercantil (VES)", "Efectivo (USD)", "Binance (USDT)", "Quantfury (USDT)"]

inicializar_estado()

# Guardado en Google Sheets asegurando guardar todas las filas
def guardar_en_sheets(worksheet_name, df_data, min_rows=100):
    try:
        df_padded = df_data.copy()
        if len(df_padded) < min_rows:
            rows_to_add = min_rows - len(df_padded)
            empty_rows = pd.DataFrame({col: [""] * rows_to_add for col in df_padded.columns})
            df_padded = pd.concat([df_padded, empty_rows], ignore_index=True)
            
        conn.update(worksheet=worksheet_name, data=df_padded)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error guardando en Google Sheets: {e}")

# Obtener tasas de cambio
@st.cache_data(ttl=300)
def obtener_tasas():
    tasa_bcv = 866.56
    tasa_paralelo = 974.38
    
    try:
        res = requests.get("https://pydolarvenezuela-api.vercel.app/api/v1/dollar", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "monedas" in data and "dollar" in data["monedas"]:
                tasa_bcv = float(data["monedas"]["dollar"]["price"])
            elif "bcv" in data:
                tasa_bcv = float(data["bcv"]["price"])
            if "enparalelovzla" in data:
                tasa_paralelo = float(data["enparalelovzla"]["price"])
            return tasa_bcv, tasa_paralelo
    except Exception:
        pass

    return tasa_bcv, tasa_paralelo

tasa_bcv, tasa_paralelo = obtener_tasas()

# BARRA LATERAL (MENU IZQUIERDO)
st.sidebar.title("📌 App Sara Menu")

tipo_tasa = st.sidebar.radio("Tasa activa para nuevos registros:", ["BCV Oficial", "Paralelo", "Manual"])

if tipo_tasa == "BCV Oficial":
    tasa_activa = tasa_bcv
elif tipo_tasa == "Paralelo":
    tasa_activa = tasa_paralelo
else:
    tasa_activa = st.sidebar.number_input("Tasa personalizada (VES/USD)", min_value=1.0, value=tasa_bcv, step=0.1)

st.sidebar.caption(f"💵 Tasa BCV: **{tasa_bcv:.2f} VES**")
st.sidebar.caption(f"📈 Tasa Paralela: **{tasa_paralelo:.2f} VES**")
st.sidebar.caption(f"⚡ Tasa Activa Seleccionada: **{tasa_activa:.2f} VES**")

if st.sidebar.button("🔄 Actualizar Tasas"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

OPC_SALDOS = "🏛️ Saldos & Cuentas"
OPC_REGISTRAR = "📝 Registrar Movimiento"
OPC_INVERSIONES = "📈 Portafolio de Inversiones"
OPC_PRESUPUESTO = "🎯 Presupuesto vs Real"
OPC_CARGAR = "📥 Cargar Presupuesto (Excel/CSV)"
OPC_RESUMEN = "📊 Resumen y Gráficos"
OPC_CONFIGURACION = "⚙️ Gestión de Grupos y Cuentas"

opcion_menu = st.sidebar.radio(
    "Selecciona una opción:",
    [
        OPC_SALDOS,
        OPC_REGISTRAR,
        OPC_INVERSIONES,
        OPC_PRESUPUESTO,
        OPC_CARGAR,
        OPC_RESUMEN,
        OPC_CONFIGURACION
    ]
)

st.title("📊 App Sara - Gestión Financiera Integrada")

# 1. SALDOS & CUENTAS
if opcion_menu == OPC_SALDOS:
    st.subheader("Saldos Disponibles por Cuenta / Banco")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.metric("💵 Tasa BCV Oficial", f"{tasa_bcv:.2f} VES/USD")
    with col_t2:
        st.metric("📈 Tasa Paralela", f"{tasa_paralelo:.2f} VES/USD")
    with col_t3:
        st.metric("⚡ Tasa Activa Actual", f"{tasa_activa:.2f} VES/USD")
    st.divider()

    df_mov = st.session_state.df_movimientos
    if not df_mov.empty and "Cuenta" in df_mov.columns:
        saldos = []
        for cta in st.session_state.lista_cuentas:
            ing_ves = df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Ingreso")]["Monto_VES"].sum()
            gast_ves = df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Gasto")]["Monto_VES"].sum()
            
            ing_usd = df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Ingreso")]["Monto_USD"].sum()
            gast_usd = df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Gasto")]["Monto_USD"].sum()

            saldo_ves = ing_ves - gast_ves
            saldo_usd = ing_usd - gast_usd

            saldos.append({
                "Cuenta": cta, 
                "Saldo (VES)": saldo_ves, 
                "Saldo Registrado ($ USD)": saldo_usd
            })
        
        df_saldos = pd.DataFrame(saldos)
        st.dataframe(df_saldos, use_container_width=True)
        
        total_ves = df_saldos["Saldo (VES)"].sum()
        total_usd = df_saldos["Saldo Registrado ($ USD)"].sum()
        st.subheader(f"💰 Saldo Total Consolidado: **{total_ves:,.2f} VES** / **${total_usd:,.2f} USD**")
    else:
        st.info("Registra tu primer movimiento asociando una cuenta para calcular los saldos automáticos.")

# 2. REGISTRAR MOVIMIENTO
elif opcion_menu == OPC_REGISTRAR:
    st.subheader("Nuevo Registro Diario en Bolívares (VES)")
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha")
        tipo = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso"])
        categoria = st.text_input("Categoría", value="Alimentación" if tipo == "Gasto" else "Sueldo")
        cuenta = st.selectbox("Cuenta / Banco", st.session_state.lista_cuentas)
    with col2:
        grupo = st.selectbox("Grupo", st.session_state.lista_grupos)
        monto_ves = st.number_input("Monto en Bolívares (VES)", min_value=0.0, step=10.0)
        
        monto_usd = monto_ves / tasa_activa if tasa_activa > 0 else 0.0
        
        st.success(f"Equivalente a Dólares con Tasa del Día ({tasa_activa:.2f} VES): **${monto_usd:,.2f} USD**")
        detalle = st.text_input("Detalle / Observación")

    if st.button("Guardar Movimiento", type="primary"):
        nuevo = pd.DataFrame([{
            "Fecha": str(fecha),
            "Tipo": tipo,
            "Categoria": categoria,
            "Grupo": grupo,
            "Cuenta": cuenta,
            "Monto_VES": monto_ves,
            "Tasa_Usada": tasa_activa,
            "Monto_USD": round(monto_usd, 2),
            "Detalle": detalle
        }])
        
        st.session_state.df_movimientos = pd.concat([st.session_state.df_movimientos, nuevo], ignore_index=True)
        guardar_en_sheets("Movimientos", st.session_state.df_movimientos)
        st.success(f"¡Movimiento registrado con éxito! Guardado en USD: ${monto_usd:,.2f} USD a una tasa de {tasa_activa:.2f} VES.")
        st.rerun()

    st.divider()
    st.subheader("Historial Completo de Movimientos")
    st.dataframe(st.session_state.df_movimientos, use_container_width=True)

# 3. PORTAFOLIO DE INVERSIONES
elif opcion_menu == OPC_INVERSIONES:
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
            st.session_state.df_inversiones = pd.concat([st.session_state.df_inversiones, nueva_inv], ignore_index=True)
            guardar_en_sheets("Inversiones", st.session_state.df_inversiones)
            st.success("¡Posición de inversión registrada!")
            st.rerun()

    st.divider()
    st.subheader("Resumen de Portafolio de Inversiones")
    
    df_inv = st.session_state.df_inversiones
    if not df_inv.empty:
        df_inv["Rendimiento ($)"] = df_inv["Valor_Actual_USD"] - df_inv["Monto_Invertido_USD"]
        
        col_m1, col_m2, col_m3 = st.columns(3)
        total_inv = df_inv["Monto_Invertido_USD"].sum()
        total_val = df_inv["Valor_Actual_USD"].sum()
        total_pnl = total_val - total_inv
        
        col_m1.metric("Capital Invertido", f"${total_inv:,.2f}")
        col_m2.metric("Valor Actual del Portafolio", f"${total_val:,.2f}")
        col_m3.metric("Ganancia / Pérdida Total", f"${total_pnl:,.2f}", delta=f"${total_pnl:,.2f}")
        
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("Aún no tienes posiciones de inversión registradas.")

# 4. PRESUPUESTO VS REAL
elif opcion_menu == OPC_PRESUPUESTO:
    st.subheader("Comparativo de Desempeño Financiero (en $ USD)")
    
    df_est = st.session_state.df_estimaciones
    df_mov = st.session_state.df_movimientos

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 📥 Ingresos")
        ing_est = df_est[df_est["Tipo"] == "Ingreso"]["Monto_Estimado_USD"].sum() if not df_est.empty else 0.0
        ing_real = df_mov[df_mov["Tipo"] == "Ingreso"]["Monto_USD"].sum() if not df_mov.empty else 0.0
        st.metric("Ingresos Estimados", f"${ing_est:,.2f}")
        st.metric("Ingresos Reales (A Tasa Histórica)", f"${ing_real:,.2f}", delta=f"${ing_real - ing_est:,.2f}")

    with col_b:
        st.markdown("### 📤 Gastos")
        gast_est = df_est[df_est["Tipo"] == "Gasto"]["Monto_Estimado_USD"].sum() if not df_est.empty else 0.0
        gast_real = df_mov[df_mov["Tipo"] == "Gasto"]["Monto_USD"].sum() if not df_mov.empty else 0.0
        st.metric("Gastos Estimados", f"${gast_est:,.2f}")
        st.metric("Gastos Reales (A Tasa Histórica)", f"${gast_real:,.2f}", delta=f"${gast_est - gast_real:,.2f}")

# 5. CARGAR PRESUPUESTO
elif opcion_menu == OPC_CARGAR:
    st.subheader("Importar Presupuesto Estimado por Archivo")
    archivo = st.file_uploader("Sube tu archivo de presupuesto (Excel o CSV)", type=["xlsx", "xls", "csv"])
    
    st.caption("El archivo debe contener las columnas: **Tipo**, **Categoria**, **Grupo**, **Monto_Estimado_USD**")
    
    if archivo is not None:
        try:
            if archivo.name.endswith(".csv"):
                df_cargado = pd.read_csv(archivo)
            else:
                df_cargado = pd.read_excel(archivo)
            
            # Limpiar filas completamente vacías pero conservar toda la información
            df_cargado = df_cargado.dropna(how="all")
            
            st.write(f"📋 **Vista previa de todas las filas cargadas ({len(df_cargado)} filas encontradas):**")
            st.dataframe(df_cargado, use_container_width=True)
            
            if st.button("Guardar Presupuesto Completo en Google Sheets", type="primary"):
                st.session_state.df_estimaciones = df_cargado
                guardar_en_sheets("Estimaciones", df_cargado, min_rows=max(100, len(df_cargado)))
                st.success(f"¡Se han importado y guardado las {len(df_cargado)} filas de tu presupuesto exitosamente!")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

# 6. RESUMEN Y GRÁFICOS
elif opcion_menu == OPC_RESUMEN:
    st.subheader("Evolución y Distribución de Gastos (en USD)")
    df_mov = st.session_state.df_movimientos
    if not df_mov.empty:
        df_gastos = df_mov[df_mov["Tipo"] == "Gasto"]
        if not df_gastos.empty:
            df_grp = df_gastos.groupby("Grupo")["Monto_USD"].sum().reset_index()
            st.bar_chart(df_grp.set_index("Grupo"))
        else:
            st.info("No hay gastos registrados para graficar.")
    else:
        st.info("Aún no existen registros para mostrar métricas.")

# 7. GESTIÓN DE GRUPOS Y CUENTAS
elif opcion_menu == OPC_CONFIGURACION:
    st.subheader("Configuración de Grupos y Cuentas Bancarias")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("### 📁 Gestión de Grupos")
        nuevo_grupo = st.text_input("Nombre del nuevo grupo", key="txt_nuevo_grupo")
        if st.button("➕ Agregar Grupo", key="btn_add_grupo"):
            if nuevo_grupo and nuevo_grupo not in st.session_state.lista_grupos:
                st.session_state.lista_grupos.append(nuevo_grupo)
                guardar_en_sheets("Grupos", pd.DataFrame({"Nombre_Grupo": st.session_state.lista_grupos}))
                st.success(f"Grupo '{nuevo_grupo}' agregado con éxito.")
                st.rerun()

        st.divider()
        if st.session_state.lista_grupos:
            grupo_eliminar = st.selectbox("Seleccionar grupo a eliminar", st.session_state.lista_grupos, key="sel_del_grupo")
            if st.button("🗑️ Eliminar Grupo", key="btn_del_grupo"):
                if grupo_eliminar in st.session_state.lista_grupos:
                    st.session_state.lista_grupos.remove(grupo_eliminar)
                    guardar_en_sheets("Grupos", pd.DataFrame({"Nombre_Grupo": st.session_state.lista_grupos}))
                    st.success(f"Grupo '{grupo_eliminar}' eliminado.")
                    st.rerun()

    with col_g2:
        st.markdown("### 🏦 Gestión de Cuentas / Bancos")
        nueva_cuenta = st.text_input("Nombre del nuevo banco/cuenta", key="txt_nueva_cuenta")
        if st.button("➕ Agregar Cuenta", key="btn_add_cuenta"):
            if nueva_cuenta and nueva_cuenta not in st.session_state.lista_cuentas:
                st.session_state.lista_cuentas.append(nueva_cuenta)
                guardar_en_sheets("Cuentas", pd.DataFrame({"Nombre_Cuenta": st.session_state.lista_cuentas}))
                st.success(f"Cuenta '{nueva_cuenta}' agregada con éxito.")
                st.rerun()

        st.divider()
        if st.session_state.lista_cuentas:
            cuenta_eliminar = st.selectbox("Seleccionar cuenta a eliminar", st.session_state.lista_cuentas, key="sel_del_cuenta")
            if st.button("🗑️ Eliminar Cuenta", key="btn_del_cuenta"):
                if cuenta_eliminar in st.session_state.lista_cuentas:
                    st.session_state.lista_cuentas.remove(cuenta_eliminar)
                    guardar_en_sheets("Cuentas", pd.DataFrame({"Nombre_Cuenta": st.session_state.lista_cuentas}))
                    st.success(f"Cuenta '{cuenta_eliminar}' eliminada.")
                    st.rerun()