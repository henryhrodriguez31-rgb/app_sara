import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import requests

# Configuración de página
st.set_page_config(
    page_title="App Sara",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Archivo de guardado permanente
DATA_FILE = "datos_sara.json"

# ---------------------------------------------------------
# OBTENCIÓN DE TASA DE CAMBIO EN LÍNEA
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def obtener_tasa_en_linea():
    try:
        res = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if res.status_code == 200:
            return float(res.json().get("promedio", 36.50))
    except Exception:
        pass
    return 36.50

# ---------------------------------------------------------
# FUNCIONES PARA PERSISTENCIA DE DATOS (JSON)
# ---------------------------------------------------------
def cargar_datos_locales():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                grupos = data.get("grupos", ["Entretenimiento", "Alimentación", "Servicios", "Transporte", "Salud"])
                cuentas = data.get("cuentas", {
                    "Banesco Diversión": {"saldo": 150.0, "moneda": "USD"},
                    "Provincial Ahorro": {"saldo": 500.0, "moneda": "USD"},
                    "BDV Gastos": {"saldo": 1000.0, "moneda": "VES"}
                })
                df_tx = pd.DataFrame(data.get("transacciones", []))
                df_est = pd.DataFrame(data.get("estimados", []))
                return grupos, cuentas, df_tx, df_est
        except Exception as e:
            st.error(f"Error al cargar datos guardados: {e}")
    
    return (
        ["Entretenimiento", "Alimentación", "Servicios", "Transporte", "Salud"],
        {
            "Banesco Diversión": {"saldo": 150.0, "moneda": "USD"},
            "Provincial Ahorro": {"saldo": 500.0, "moneda": "USD"},
            "BDV Gastos": {"saldo": 1000.0, "moneda": "VES"}
        },
        pd.DataFrame(columns=["Fecha", "Tipo", "Descripción", "Monto_Original", "Moneda", "Tasa", "Monto_USD", "Grupo", "Cuenta"]),
        pd.DataFrame(columns=["Grupo", "Monto_Estimado_USD"])
    )

def guardar_datos_locales():
    data = {
        "grupos": st.session_state.grupos,
        "cuentas": st.session_state.cuentas,
        "transacciones": st.session_state.transacciones.to_dict(orient="records") if not st.session_state.transacciones.empty else [],
        "estimados": st.session_state.estimados.to_dict(orient="records") if not st.session_state.estimados.empty else []
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=str)

# ---------------------------------------------------------
# INICIALIZACIÓN DE DATOS
# ---------------------------------------------------------
if 'cargado' not in st.session_state:
    st.session_state.grupos, st.session_state.cuentas, st.session_state.transacciones, st.session_state.estimados = cargar_datos_locales()
    st.session_state.cargado = True

tasa_api = obtener_tasa_en_linea()

# ---------------------------------------------------------
# BARRA LATERAL: CONFIGURACIÓN
# ---------------------------------------------------------
st.sidebar.title("⚙️ Configuración App Sara")

# 1. Cargar Presupuesto Estimado con Selector Manual de Columnas
with st.sidebar.expander("📥 Cargar Presupuesto Estimado ($ USD)"):
    archivo_subido = st.file_uploader("Subir archivo de presupuesto (XLSX o CSV)", type=["csv", "xlsx"])
    
    if archivo_subido is not None:
        try:
            if archivo_subido.name.endswith('.csv'):
                df_temp = pd.read_csv(archivo_subido)
            else:
                df_temp = pd.read_excel(archivo_subido)
            
            # Limpiar nombres de columnas
            df_temp.columns = [str(c).strip() for c in df_temp.columns]
            cols = list(df_temp.columns)
            
            st.write("**Selecciona las columnas de tu archivo:**")
            col_g = st.selectbox("Columna de Grupos / Conceptos:", cols, index=0)
            col_m = st.selectbox("Columna de Montos en $:", cols, index=min(1, len(cols)-1))
            
            if st.button("✅ Confirmar y Cargar Presupuesto"):
                df_nuevo = pd.DataFrame()
                df_nuevo["Grupo"] = df_temp[col_g].astype(str).str.strip()
                df_nuevo["Monto_Estimado_USD"] = pd.to_numeric(df_temp[col_m], errors='coerce').fillna(0.0)
                
                # Filtrar filas vacías
                df_nuevo = df_nuevo[df_nuevo["Grupo"] != "nan"]
                df_nuevo = df_nuevo[df_nuevo["Grupo"] != ""]
                
                st.session_state.estimados = df_nuevo.reset_index(drop=True)
                guardar_datos_locales()
                st.success("¡Presupuesto procesado y cargado con éxito!")
                st.rerun()
                
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

# 2. Gestión de Grupos
with st.sidebar.expander("📁 Gestionar Grupos de Gastos"):
    nuevo_grupo = st.text_input("Nuevo Grupo:")
    if st.button("Añadir Grupo") and nuevo_grupo:
        if nuevo_grupo not in st.session_state.grupos:
            st.session_state.grupos.append(nuevo_grupo)
            guardar_datos_locales()
            st.success(f"Grupo '{nuevo_grupo}' añadido.")
            st.rerun()
    
    st.write("**Grupos actuales:**")
    for g in st.session_state.grupos:
        st.caption(f"- {g}")

# 3. Gestión de Cuentas
with st.sidebar.expander("🏦 Gestionar Cuentas y Saldos"):
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Crear", "Editar", "Eliminar"])
    
    with sub_tab1:
        nueva_cuenta = st.text_input("Nombre de la Cuenta:")
        saldo_inicial = st.number_input("Saldo Inicial:", min_value=0.0, value=0.0)
        moneda_cuenta = st.selectbox("Moneda Base:", ["USD", "VES"], key="nueva_moneda")
        if st.button("Añadir Cuenta") and nueva_cuenta:
            if nueva_cuenta not in st.session_state.cuentas:
                st.session_state.cuentas[nueva_cuenta] = {"saldo": saldo_inicial, "moneda": moneda_cuenta}
                guardar_datos_locales()
                st.success(f"Cuenta '{nueva_cuenta}' creada.")
                st.rerun()

    with sub_tab2:
        if st.session_state.cuentas:
            cuenta_edit = st.selectbox("Seleccionar Cuenta:", list(st.session_state.cuentas.keys()))
            nuevo_saldo = st.number_input("Ajustar Saldo:", value=float(st.session_state.cuentas[cuenta_edit]["saldo"]), key="edit_saldo")
            nueva_moneda = st.selectbox("Moneda:", ["USD", "VES"], index=0 if st.session_state.cuentas[cuenta_edit]["moneda"] == "USD" else 1, key="edit_moneda")
            if st.button("Guardar Cambios"):
                st.session_state.cuentas[cuenta_edit] = {"saldo": nuevo_saldo, "moneda": nueva_moneda}
                guardar_datos_locales()
                st.success("Cuenta actualizada.")
                st.rerun()

    with sub_tab3:
        if st.session_state.cuentas:
            cuenta_del = st.selectbox("Seleccionar Cuenta a Eliminar:", list(st.session_state.cuentas.keys()), key="del_cuenta")
            if st.button("❌ Eliminar Cuenta", type="secondary"):
                del st.session_state.cuentas[cuenta_del]
                guardar_datos_locales()
                st.success("Cuenta eliminada.")
                st.rerun()

# ---------------------------------------------------------
# PANEL PRINCIPAL
# ---------------------------------------------------------
st.title("📱 App Sara - Control Financiero")

col_tasa1, col_tasa2 = st.columns([2, 1])
with col_tasa1:
    tasa_cambio = st.number_input(
        "💵 Tasa Referencial USDT / BCV (VES por 1 USD):",
        min_value=0.01,
        value=float(tasa_api),
        format="%.2f"
    )
with col_tasa2:
    st.caption("🟢 Tasa en línea obtenida automáticamente. Puedes modificarla si es necesario.")

st.subheader("🏦 Saldos por Cuenta")
if st.session_state.cuentas:
    cols = st.columns(min(len(st.session_state.cuentas), 4))
    for idx, (cuenta, datos) in enumerate(st.session_state.cuentas.items()):
        simbolo = "$" if datos["moneda"] == "USD" else "Bs."
        cols[idx % len(cols)].metric(
            label=f"{cuenta} ({datos['moneda']})", 
            value=f"{simbolo} {datos['saldo']:,.2f}"
        )
else:
    st.info("No hay cuentas bancarias registradas.")

st.divider()

tab1, tab2, tab3 = st.tabs(["📝 Registrar Movimiento", "📈 Ahorros e Inversiones", "🔍 Auditoría & Presupuesto"])

# ---------------------------------------------------------
# TAB 1: REGISTRO Y ELIMINACIÓN DE TRANSACCIONES
# ---------------------------------------------------------
with tab1:
    st.subheader("Registrar Movimiento")
    col1, col2 = st.columns(2)
    
    with col1:
        tipo_mov = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso", "Ahorro/Inversión"])
        descripcion = st.text_input("Descripción (ej. Cine, Mercado, Salario):")
        monto_ingresado = st.number_input("Monto:", min_value=0.01, format="%.2f")
    
    with col2:
        cuenta_origen = st.selectbox("Cuenta / Banco:", list(st.session_state.cuentas.keys()) if st.session_state.cuentas else ["Sin cuentas"])
        moneda_trans = st.session_state.cuentas[cuenta_origen]["moneda"] if st.session_state.cuentas and cuenta_origen in st.session_state.cuentas else "USD"
        
        if moneda_trans == "VES":
            monto_calculado_usd = monto_ingresado / tasa_cambio if tasa_cambio > 0 else 0.0
            st.info(f"Moneda: **VES (Bolívares)** | Equivalente: **${monto_calculado_usd:,.2f} USD** (Tasa: {tasa_cambio} Bs/$)")
        else:
            monto_calculado_usd = monto_ingresado
            st.info("Moneda: **USD (Dólares)**")
        
        grupo_sel = st.selectbox("Grupo de Gasto:", st.session_state.grupos) if tipo_mov == "Gasto" else tipo_mov
        fecha = st.date_input("Fecha:", datetime.now())

    if st.button("Guardar Registro", type="primary", use_container_width=True):
        if not st.session_state.cuentas or cuenta_origen not in st.session_state.cuentas:
            st.error("Debes registrar al menos una cuenta antes de agregar transacciones.")
        else:
            if tipo_mov in ["Gasto", "Ahorro/Inversión"]:
                st.session_state.cuentas[cuenta_origen]["saldo"] -= monto_ingresado
            elif tipo_mov == "Ingreso":
                st.session_state.cuentas[cuenta_origen]["saldo"] += monto_ingresado

            nueva_fila = pd.DataFrame([{
                "Fecha": str(fecha),
                "Tipo": tipo_mov,
                "Descripción": descripcion,
                "Monto_Original": monto_ingresado,
                "Moneda": moneda_trans,
                "Tasa": tasa_cambio if moneda_trans == "VES" else 1.0,
                "Monto_USD": monto_calculado_usd,
                "Grupo": grupo_sel,
                "Cuenta": cuenta_origen
            }])
            st.session_state.transacciones = pd.concat([st.session_state.transacciones, nueva_fila], ignore_index=True)
            guardar_datos_locales()
            st.success("¡Movimiento registrado con éxito!")
            st.rerun()

    st.divider()
    st.subheader("📋 Historial y Eliminación de Transacciones")
    
    if not st.session_state.transacciones.empty:
        df_mostrar = st.session_state.transacciones.copy()
        df_mostrar.insert(0, "Eliminar", False)
        
        df_editado = st.data_editor(
            df_mostrar,
            column_config={"Eliminar": st.column_config.CheckboxColumn("Eliminar", default=False)},
            disabled=["Fecha", "Tipo", "Descripción", "Monto_Original", "Moneda", "Tasa", "Monto_USD", "Grupo", "Cuenta"],
            use_container_width=True,
            hide_index=True,
            key="tabla_eliminar_tx"
        )
        
        if st.button("🗑️ Eliminar Registros Seleccionados", type="primary"):
            filas_a_mantener = df_editado[df_editado["Eliminar"] == False].drop(columns=["Eliminar"])
            st.session_state.transacciones = filas_a_mantener.reset_index(drop=True)
            guardar_datos_locales()
            st.success("¡Registros seleccionados eliminados correctamente!")
            st.rerun()
    else:
        st.info("No hay transacciones registradas.")

# ---------------------------------------------------------
# TAB 2: AHORROS E INVERSIONES
# ---------------------------------------------------------
with tab2:
    st.subheader("💡 Módulo de Ahorros e Inversiones")
    if not st.session_state.transacciones.empty:
        df_inv = st.session_state.transacciones[st.session_state.transacciones["Tipo"] == "Ahorro/Inversión"].copy()
        if not df_inv.empty:
            total_invertido_usd = pd.to_numeric(df_inv["Monto_USD"], errors='coerce').sum()
            st.metric(label="Total Acumulado en Ahorro/Inversión (USD Equivalente)", value=f"${total_invertido_usd:,.2f}")
            st.dataframe(df_inv[["Fecha", "Descripción", "Monto_Original", "Moneda", "Tasa", "Monto_USD", "Cuenta"]], use_container_width=True)
        else:
            st.info("No hay registros de ahorros o inversiones aún.")
    else:
        st.info("No hay transacciones registradas.")

# ---------------------------------------------------------
# TAB 3: AUDITORÍA Y COMPARATIVA ESTIMADO VS REAL
# ---------------------------------------------------------
with tab3:
    st.subheader("🔍 Auditoría: Gastos Reales ($ USD) vs. Presupuesto Estimado ($ USD)")
    
    st.write("📋 **Presupuesto Estimado Registrado ($ USD):**")
    
    # Editor interactivo para agregar/editar presupuesto manualmente
    if st.session_state.estimados.empty:
        # Plantilla inicial vacía con los grupos activos
        st.session_state.estimados = pd.DataFrame({
            "Grupo": st.session_state.grupos,
            "Monto_Estimado_USD": [0.0] * len(st.session_state.grupos)
        })

    st.session_state.estimados["Monto_Estimado_USD"] = pd.to_numeric(st.session_state.estimados["Monto_Estimado_USD"], errors='coerce').fillna(0.0)

    df_est_editado = st.data_editor(
        st.session_state.estimados,
        column_config={
            "Grupo": "Grupo / Categoría",
            "Monto_Estimado_USD": st.column_config.NumberColumn("Monto Estimado ($ USD)", format="$ %.2f", min_value=0.0)
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_presupuesto_manual"
    )
    
    if st.button("💾 Guardar Cambios en Presupuesto"):
        st.session_state.estimados = df_est_editado
        guardar_datos_locales()
        st.success("¡Presupuesto actualizado y guardado!")
        st.rerun()

    st.divider()

    # Comparativa en Dólares ($ USD)
    df_gastos = pd.DataFrame()
    if not st.session_state.transacciones.empty:
        df_gastos = st.session_state.transacciones[st.session_state.transacciones["Tipo"] == "Gasto"].copy()

    if not df_gastos.empty:
        df_gastos["Monto_USD"] = pd.to_numeric(df_gastos["Monto_USD"], errors='coerce').fillna(0.0)
        ejecutado = df_gastos.groupby("Grupo")["Monto_USD"].sum().reset_index()
        ejecutado.columns = ["Grupo", "Real_USD"]
        
        comparativa = pd.merge(st.session_state.estimados, ejecutado, on="Grupo", how="outer").fillna(0.0)
        comparativa["Monto_Estimado_USD"] = pd.to_numeric(comparativa["Monto_Estimado_USD"], errors='coerce').fillna(0.0)
        comparativa["Real_USD"] = pd.to_numeric(comparativa["Real_USD"], errors='coerce').fillna(0.0)
        comparativa["Diferencia_USD"] = comparativa["Monto_Estimado_USD"] - comparativa["Real_USD"]

        st.write("📊 **Comparativa Presupuestaria Consolidada en USD ($):**")
        st.bar_chart(data=comparativa.set_index("Grupo")[["Monto_Estimado_USD", "Real_USD"]])
        
        st.write("**Tabla Comparativa (Estimado vs Real vs Diferencia):**")
        st.dataframe(
            comparativa,
            column_config={
                "Grupo": "Grupo",
                "Monto_Estimado_USD": st.column_config.NumberColumn("Estimado ($ USD)", format="$ %.2f"),
                "Real_USD": st.column_config.NumberColumn("Real ($ USD)", format="$ %.2f"),
                "Diferencia_USD": st.column_config.NumberColumn("Diferencia ($ USD)", format="$ %.2f")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay gastos registrados aún para realizar el comparativo.")