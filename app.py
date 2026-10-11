import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import requests
from datetime import date, datetime

st.set_page_config(page_title="App Sara", page_icon="📊", layout="wide")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Diccionario de Tasas Históricas (Octubre 2026)
TASAS_HISTORICAS_OCT_2026 = {
    "2026-10-01": 860.18,
    "2026-10-02": 866.56,
    "2026-10-03": 871.37,
    "2026-10-04": 871.37,
    "2026-10-05": 871.37,
    "2026-10-06": 871.37,
}

# Extraer ID numérico seguro
def extraer_id_seguro(texto_opcion):
    if not texto_opcion:
        return None
    try:
        primera_parte = str(texto_opcion).split(" - ")[0].strip()
        return int(float(primera_parte))
    except (ValueError, TypeError, IndexError):
        return None

# Estandarizar Movimientos
def estandarizar_df_movimientos(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["ID", "Fecha", "Tipo", "Categoria", "Grupo", "Cuenta", "Monto_VES", "Tasa_Usada", "Monto_USD", "Detalle"])
    
    df_clean = df.dropna(how="all").copy()
    
    if "Categoria" in df_clean.columns:
        df_clean = df_clean[df_clean["Categoria"].astype(str).str.strip().str.lower().isin(["nan", "none", ""]) == False]
    elif "Monto_VES" in df_clean.columns:
        df_clean = df_clean[df_clean["Monto_VES"].astype(str).str.strip().str.lower().isin(["nan", "none", ""]) == False]

    if df_clean.empty:
        return pd.DataFrame(columns=["ID", "Fecha", "Tipo", "Categoria", "Grupo", "Cuenta", "Monto_VES", "Tasa_Usada", "Monto_USD", "Detalle"])

    req_cols = ["ID", "Fecha", "Tipo", "Categoria", "Grupo", "Cuenta", "Monto_VES", "Tasa_Usada", "Monto_USD", "Detalle"]
    for c in req_cols:
        if c not in df_clean.columns:
            df_clean[c] = ""
            
    df_clean["ID"] = range(1, len(df_clean) + 1)
    return df_clean[req_cols].reset_index(drop=True)

# Estandarizar Estimaciones
def estandarizar_df_estimaciones(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["ID", "Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"])
    
    df_clean = df.dropna(how="all").copy()
    
    column_mapping = {}
    for col in df_clean.columns:
        clow = str(col).strip().lower()
        if clow == "id":
            column_mapping[col] = "ID"
        elif "tipo" in clow:
            column_mapping[col] = "Tipo"
        elif "cat" in clow:
            column_mapping[col] = "Categoria"
        elif "grup" in clow:
            column_mapping[col] = "Grupo"
        elif "monto" in clow or "estimado" in clow or "usd" in clow:
            column_mapping[col] = "Monto_Estimado_USD"
            
    df_clean = df_clean.rename(columns=column_mapping)
    
    if "Categoria" in df_clean.columns:
        df_clean = df_clean[df_clean["Categoria"].astype(str).str.strip().str.lower().isin(["nan", "none", ""]) == False]

    if df_clean.empty:
        return pd.DataFrame(columns=["ID", "Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"])

    for required_col in ["Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"]:
        if required_col not in df_clean.columns:
            df_clean[required_col] = ""
            
    df_clean["ID"] = range(1, len(df_clean) + 1)
    return df_clean[["ID", "Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"]].reset_index(drop=True)

# Cargar datos e inicializar estado
def inicializar_estado():
    if "df_movimientos" not in st.session_state:
        try:
            df_mov = conn.read(worksheet="Movimientos", ttl=0)
            st.session_state.df_movimientos = estandarizar_df_movimientos(df_mov)
        except Exception:
            st.session_state.df_movimientos = pd.DataFrame(
                columns=["ID", "Fecha", "Tipo", "Categoria", "Grupo", "Cuenta", "Monto_VES", "Tasa_Usada", "Monto_USD", "Detalle"]
            )

    if "df_estimaciones" not in st.session_state:
        try:
            df_est = conn.read(worksheet="Estimaciones", ttl=0)
            st.session_state.df_estimaciones = estandarizar_df_estimaciones(df_est)
        except Exception:
            st.session_state.df_estimaciones = pd.DataFrame(
                columns=["ID", "Tipo", "Categoria", "Grupo", "Monto_Estimado_USD"]
            )

    if "df_inversiones" not in st.session_state:
        try:
            df_inv = conn.read(worksheet="Inversiones", ttl=0)
            st.session_state.df_inversiones = df_inv.dropna(how="all")
        except Exception:
            st.session_state.df_inversiones = pd.DataFrame(
                columns=["Fecha", "Plataforma", "Activo", "Tipo_Operacion", "Monto_Invertido_USD", "Valor_Actual_USD", "Detalle"]
            )

    if "df_saldos_iniciales" not in st.session_state:
        try:
            df_si = conn.read(worksheet="Saldos_Iniciales", ttl=0)
            st.session_state.df_saldos_iniciales = df_si.dropna(how="all")
        except Exception:
            st.session_state.df_saldos_iniciales = pd.DataFrame(
                columns=["Cuenta", "Saldo_Inicial_VES", "Saldo_Inicial_USD"]
            )

    if "lista_grupos" not in st.session_state:
        try:
            df_grup = conn.read(worksheet="Grupos", ttl=0)
            grupos = df_grup["Nombre_Grupo"].dropna().astype(str).str.strip().tolist()
            st.session_state.lista_grupos = [g for g in grupos if g and g.lower() not in ["nan", "none"]]
            if not st.session_state.lista_grupos:
                st.session_state.lista_grupos = ["Gastos fijos", "Fondo ahorro", "Entretenimiento", "Personal", "Hogar", "Trabajo"]
        except Exception:
            st.session_state.lista_grupos = ["Gastos fijos", "Fondo ahorro", "Entretenimiento", "Personal", "Hogar", "Trabajo"]

    if "lista_cuentas" not in st.session_state:
        try:
            df_cta = conn.read(worksheet="Cuentas", ttl=0)
            cuentas = df_cta["Nombre_Cuenta"].dropna().astype(str).str.strip().tolist()
            st.session_state.lista_cuentas = [c for c in cuentas if c and c.lower() not in ["nan", "none"]]
            if not st.session_state.lista_cuentas:
                st.session_state.lista_cuentas = ["Banesco (VES)", "BDV (VES)", "Mercantil (VES)", "Efectivo (USD)", "Binance (USDT)", "Quantfury (USDT)", "Cashea"]
        except Exception:
            st.session_state.lista_cuentas = ["Banesco (VES)", "BDV (VES)", "Mercantil (VES)", "Efectivo (USD)", "Binance (USDT)", "Quantfury (USDT)", "Cashea"]

inicializar_estado()

# Guardar en Google Sheets
def guardar_en_sheets(worksheet_name, df_data, min_rows=100):
    try:
        df_padded = df_data.copy()
        for col in df_padded.columns:
            df_padded[col] = df_padded[col].fillna("").astype(str)

        if len(df_padded) < min_rows:
            rows_to_add = min_rows - len(df_padded)
            empty_rows = pd.DataFrame({col: [""] * rows_to_add for col in df_padded.columns})
            df_padded = pd.concat([df_padded, empty_rows], ignore_index=True)
            
        conn.update(worksheet=worksheet_name, data=df_padded)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar en la pestaña '{worksheet_name}' de Google Sheets: {e}")
        return False

# Suma estimada
def calcular_total_estimado(df_est, tipo_buscado):
    if df_est is None or df_est.empty or "Tipo" not in df_est.columns or "Monto_Estimado_USD" not in df_est.columns:
        return 0.0

    mask = df_est["Tipo"].astype(str).str.strip().str.lower() == tipo_buscado.lower()
    df_filtrado = df_est[mask]

    if df_filtrado.empty:
        return 0.0

    def limpiar_num(v):
        if pd.isna(v):
            return 0.0
        s = str(v).replace("$", "").replace("USD", "").replace("usd", "").strip()
        if "," in s and "." in s:
            s = s.replace(",", "")
        elif "," in s and "." not in s:
            s = s.replace(",", ".")
        return pd.to_numeric(s, errors="coerce") or 0.0

    return df_filtrado["Monto_Estimado_USD"].apply(limpiar_num).sum()

# Obtener tasas del día con respaldo (Fallback Multifuente)
@st.cache_data(ttl=300)
def obtener_tasas():
    tasa_bcv = 871.37
    tasa_paralelo = 974.38
    
    # Fuente 1: ve.dolarapi.com
    try:
        res = requests.get("https://ve.dolarapi.com/v1/dolares", timeout=5)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                fuente = str(item.get("fuente", "")).lower()
                if "oficial" in fuente or "bcv" in fuente:
                    tasa_bcv = float(item.get("promedio", tasa_bcv))
                elif "paralelo" in fuente:
                    tasa_paralelo = float(item.get("promedio", tasa_paralelo))
            return tasa_bcv, tasa_paralelo
    except Exception:
        pass

    # Fuente 2: rates.dolarvzla.com (Respaldo BCV)
    try:
        res = requests.get("https://rates.dolarvzla.com/bcv/current.json", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "current" in data and "usd" in data["current"]:
                tasa_bcv = float(data["current"]["usd"])
    except Exception:
        pass

    # Fuente 3: pydolarvenezuela
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

tasa_bcv_hoy, tasa_paralelo_hoy = obtener_tasas()

def obtener_tasa_por_fecha(fecha_obj, modo_tasa):
    fecha_str = str(fecha_obj)
    if fecha_str in TASAS_HISTORICAS_OCT_2026:
        return TASAS_HISTORICAS_OCT_2026[fecha_str]
    elif modo_tasa == "BCV Oficial":
        return tasa_bcv_hoy
    elif modo_tasa == "Paralelo":
        return tasa_paralelo_hoy
    else:
        return tasa_bcv_hoy

# BARRA LATERAL
st.sidebar.title("📌 App Sara Menu")

tipo_tasa = st.sidebar.radio("Tasa activa de referencia:", ["BCV Oficial", "Paralelo", "Manual"])

if tipo_tasa == "BCV Oficial":
    tasa_activa = tasa_bcv_hoy
elif tipo_tasa == "Paralelo":
    tasa_activa = tasa_paralelo_hoy
else:
    tasa_activa = st.sidebar.number_input("Tasa personalizada (VES/USD)", min_value=1.0, value=tasa_bcv_hoy, step=0.1)

st.sidebar.caption(f"💵 Tasa BCV Hoy: **{tasa_bcv_hoy:.2f} VES**")
st.sidebar.caption(f"📈 Tasa Paralela Hoy: **{tasa_paralelo_hoy:.2f} VES**")
st.sidebar.caption(f"⚡ Tasa Activa Seleccionada: **{tasa_activa:.2f} VES**")

if st.sidebar.button("🔄 Actualizar Tasas"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

OPC_SALDOS = "🏛️ Saldos & Cuentas"
OPC_REGISTRAR = "📝 Registrar / Editar Movimiento"
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
    st.subheader("🏛️ Saldos Disponibles y Fondos por Banco / Startup")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.metric("💵 Tasa BCV Hoy", f"{tasa_bcv_hoy:.2f} VES/USD")
    with col_t2:
        st.metric("📈 Tasa Paralela Hoy", f"{tasa_paralelo_hoy:.2f} VES/USD")
    with col_t3:
        st.metric("⚡ Tasa Activa Actual", f"{tasa_activa:.2f} VES/USD")
    st.divider()

    tab_saldos1, tab_saldos2 = st.tabs(["📊 Saldos Consolidados", "⚙️ Configurar Saldos Iniciales"])

    df_mov = st.session_state.df_movimientos
    df_si = st.session_state.df_saldos_iniciales

    with tab_saldos1:
        saldos = []
        for cta in st.session_state.lista_cuentas:
            s_init_ves = 0.0
            s_init_usd = 0.0
            if not df_si.empty and "Cuenta" in df_si.columns:
                match = df_si[df_si["Cuenta"] == cta]
                if not match.empty:
                    s_init_ves = pd.to_numeric(match["Saldo_Inicial_VES"].iloc[0], errors="coerce") or 0.0
                    s_init_usd = pd.to_numeric(match["Saldo_Inicial_USD"].iloc[0], errors="coerce") or 0.0

            ing_ves = pd.to_numeric(df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Ingreso")]["Monto_VES"], errors="coerce").sum() if not df_mov.empty else 0.0
            gast_ves = pd.to_numeric(df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Gasto")]["Monto_VES"], errors="coerce").sum() if not df_mov.empty else 0.0
            
            ing_usd = pd.to_numeric(df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Ingreso")]["Monto_USD"], errors="coerce").sum() if not df_mov.empty else 0.0
            gast_usd = pd.to_numeric(df_mov[(df_mov["Cuenta"] == cta) & (df_mov["Tipo"] == "Gasto")]["Monto_USD"], errors="coerce").sum() if not df_mov.empty else 0.0

            saldo_total_ves = s_init_ves + ing_ves - gast_ves
            saldo_total_usd = s_init_usd + ing_usd - gast_usd

            saldos.append({
                "Cuenta / Banco / Startup": cta, 
                "Saldo Inicial (VES)": s_init_ves,
                "Saldo Inicial ($ USD)": s_init_usd,
                "Movimientos (VES)": ing_ves - gast_ves,
                "Movimientos ($ USD)": ing_usd - gast_usd,
                "Saldo Total Disponible (VES)": saldo_total_ves, 
                "Saldo Total Disponible ($ USD)": saldo_total_usd
            })
        
        df_saldos = pd.DataFrame(saldos)
        st.dataframe(df_saldos, use_container_width=True)
        
        total_ves = df_saldos["Saldo Total Disponible (VES)"].sum()
        total_usd = df_saldos["Saldo Total Disponible ($ USD)"].sum()
        st.subheader(f"💰 Saldo Total Consolidado en Fondos: **{total_ves:,.2f} VES** / **${total_usd:,.2f} USD**")

    with tab_saldos2:
        st.markdown("### ⚙️ Establecer Saldo Base Inicial por Cuenta")
        st.caption("Ingresa los fondos de arranque (al 01/10/2026) con los que cuenta cada entidad financiera o startup.")
        
        col_si1, col_si2 = st.columns(2)
        with col_si1:
            cta_sel_si = st.selectbox("Seleccionar Cuenta / Banco / Startup", st.session_state.lista_cuentas, key="sel_si_cta")
            init_ves = st.number_input("Saldo Inicial en Bolívares (VES)", min_value=0.0, step=100.0, key="txt_si_ves")
        with col_si2:
            init_usd = st.number_input("Saldo Inicial en Dólares ($ USD)", min_value=0.0, step=10.0, key="txt_si_usd")

        if st.button("Guardar Saldo Inicial", type="primary"):
            if not df_si.empty and "Cuenta" in df_si.columns and cta_sel_si in df_si["Cuenta"].values:
                idx = df_si.index[df_si["Cuenta"] == cta_sel_si][0]
                st.session_state.df_saldos_iniciales.at[idx, "Saldo_Inicial_VES"] = init_ves
                st.session_state.df_saldos_iniciales.at[idx, "Saldo_Inicial_USD"] = init_usd
            else:
                nuevo_si = pd.DataFrame([{
                    "Cuenta": cta_sel_si,
                    "Saldo_Inicial_VES": init_ves,
                    "Saldo_Inicial_USD": init_usd
                }])
                st.session_state.df_saldos_iniciales = pd.concat([st.session_state.df_saldos_iniciales, nuevo_si], ignore_index=True)

            if guardar_en_sheets("Saldos_Iniciales", st.session_state.df_saldos_iniciales):
                st.success(f"¡Saldo inicial guardado para '{cta_sel_si}'!")
                st.rerun()

# 2. REGISTRAR / EDITAR / ELIMINAR MOVIMIENTOS
elif opcion_menu == OPC_REGISTRAR:
    tab1, tab2 = st.tabs(["➕ Nuevo Registro", "✏️ Modificar o Eliminar Registro"])
    
    with tab1:
        st.subheader("Nuevo Registro Diario en Bolívares (VES)")
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha del Movimiento", value=date.today())
            tasa_calculo = obtener_tasa_por_fecha(fecha, tipo_tasa) if tipo_tasa != "Manual" else tasa_activa
            st.caption(f"Tasa aplicada para la fecha {fecha}: **{tasa_calculo:.2f} VES/USD**")

            tipo = st.selectbox("Tipo de Movimiento", ["Gasto", "Ingreso"])
            categoria = st.text_input("Categoría", value="Alimentación" if tipo == "Gasto" else "Sueldo")
            cuenta = st.selectbox("Cuenta / Banco", st.session_state.lista_cuentas)
        with col2:
            grupo = st.selectbox("Grupo", st.session_state.lista_grupos)
            monto_ves = st.number_input("Monto en Bolívares (VES)", min_value=0.0, step=10.0)
            monto_usd = monto_ves / tasa_calculo if tasa_calculo > 0 else 0.0
            st.success(f"Equivalente a Dólares con Tasa Histórica ({tasa_calculo:.2f} VES): **${monto_usd:,.2f} USD**")
            detalle = st.text_input("Detalle / Observación")

        if st.button("Guardar Movimiento", type="primary"):
            st.session_state.df_movimientos = estandarizar_df_movimientos(st.session_state.df_movimientos)
            next_id = len(st.session_state.df_movimientos) + 1

            nuevo = pd.DataFrame([{
                "ID": next_id,
                "Fecha": str(fecha),
                "Tipo": tipo,
                "Categoria": categoria,
                "Grupo": grupo,
                "Cuenta": cuenta,
                "Monto_VES": monto_ves,
                "Tasa_Usada": tasa_calculo,
                "Monto_USD": round(monto_usd, 2),
                "Detalle": detalle
            }])
            
            st.session_state.df_movimientos = pd.concat([st.session_state.df_movimientos, nuevo], ignore_index=True)
            st.session_state.df_movimientos = estandarizar_df_movimientos(st.session_state.df_movimientos)
            if guardar_en_sheets("Movimientos", st.session_state.df_movimientos):
                st.success(f"¡Movimiento registrado con éxito! Guardado en USD: ${monto_usd:,.2f} USD.")
                st.rerun()

    with tab2:
        st.subheader("Gestión y Modificación de Movimientos")
        df_mov = estandarizar_df_movimientos(st.session_state.df_movimientos)
        st.session_state.df_movimientos = df_mov
        
        if not df_mov.empty:
            opciones_ids = df_mov["ID"].astype(str) + " - " + df_mov["Fecha"].astype(str) + " - " + df_mov["Categoria"].astype(str) + " (" + df_mov["Monto_VES"].astype(str) + " VES)"
            mov_seleccionado = st.selectbox("Selecciona un movimiento para editar o eliminar:", opciones_ids, key="sel_mov_editar")
            
            id_sel = extraer_id_seguro(mov_seleccionado)
            
            # Buscar el registro por ID numérico
            ids_numericos = pd.to_numeric(df_mov["ID"], errors="coerce")
            idx_registro = df_mov.index[ids_numericos == id_sel].tolist() if id_sel is not None else []
            
            if idx_registro:
                idx = idx_registro[0]
                row = df_mov.loc[idx]

                try:
                    fecha_val = datetime.strptime(str(row["Fecha"]), "%Y-%m-%d").date()
                except Exception:
                    fecha_val = date.today()

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e_fecha = st.date_input("Modificar Fecha", value=fecha_val, key=f"edit_fecha_{id_sel}")
                    e_tipo = st.selectbox("Modificar Tipo", ["Gasto", "Ingreso"], index=0 if str(row["Tipo"]) == "Gasto" else 1, key=f"edit_tipo_{id_sel}")
                    e_categoria = st.text_input("Modificar Categoría", value=str(row["Categoria"]), key=f"edit_cat_{id_sel}")
                    
                    idx_cta = st.session_state.lista_cuentas.index(row["Cuenta"]) if row["Cuenta"] in st.session_state.lista_cuentas else 0
                    e_cuenta = st.selectbox("Modificar Cuenta", st.session_state.lista_cuentas, index=idx_cta, key=f"edit_cta_{id_sel}")

                with col_e2:
                    idx_grp = st.session_state.lista_grupos.index(row["Grupo"]) if row["Grupo"] in st.session_state.lista_grupos else 0
                    e_grupo = st.selectbox("Modificar Grupo", st.session_state.lista_grupos, index=idx_grp, key=f"edit_grp_{id_sel}")
                    
                    try:
                        m_ves_val = float(row["Monto_VES"])
                    except Exception:
                        m_ves_val = 0.0

                    e_monto_ves = st.number_input("Modificar Monto (VES)", value=m_ves_val, step=10.0, key=f"edit_mves_{id_sel}")
                    tasa_edit = obtener_tasa_por_fecha(e_fecha, tipo_tasa) if tipo_tasa != "Manual" else tasa_activa
                    e_monto_usd = e_monto_ves / tasa_edit if tasa_edit > 0 else 0.0
                    
                    st.info(f"Nuevo valor en USD recalculado ({tasa_edit:.2f} VES): **${e_monto_usd:,.2f} USD**")
                    e_detalle = st.text_input("Modificar Detalle", value=str(row["Detalle"]), key=f"edit_det_{id_sel}")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("💾 Guardar Cambios", type="primary", key=f"btn_save_{id_sel}"):
                        st.session_state.df_movimientos.at[idx, "Fecha"] = str(e_fecha)
                        st.session_state.df_movimientos.at[idx, "Tipo"] = e_tipo
                        st.session_state.df_movimientos.at[idx, "Categoria"] = e_categoria
                        st.session_state.df_movimientos.at[idx, "Cuenta"] = e_cuenta
                        st.session_state.df_movimientos.at[idx, "Grupo"] = e_grupo
                        st.session_state.df_movimientos.at[idx, "Monto_VES"] = e_monto_ves
                        st.session_state.df_movimientos.at[idx, "Tasa_Usada"] = tasa_edit
                        st.session_state.df_movimientos.at[idx, "Monto_USD"] = round(e_monto_usd, 2)
                        st.session_state.df_movimientos.at[idx, "Detalle"] = e_detalle

                        st.session_state.df_movimientos = estandarizar_df_movimientos(st.session_state.df_movimientos)
                        if guardar_en_sheets("Movimientos", st.session_state.df_movimientos):
                            st.success("¡Registro actualizado exitosamente!")
                            st.rerun()

                with col_btn2:
                    if st.button("🗑️️ Eliminar Movimiento", type="secondary", key=f"btn_del_{id_sel}"):
                        st.session_state.df_movimientos = st.session_state.df_movimientos.drop(idx).reset_index(drop=True)
                        st.session_state.df_movimientos = estandarizar_df_movimientos(st.session_state.df_movimientos)
                        if guardar_en_sheets("Movimientos", st.session_state.df_movimientos):
                            st.success("¡Registro eliminado correctamente!")
                            st.rerun()
        else:
            st.info("No hay movimientos para editar o eliminar.")

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
            if guardar_en_sheets("Inversiones", st.session_state.df_inversiones):
                st.success("¡Posición de inversión registrada!")
                st.rerun()

    st.divider()
    st.subheader("Resumen de Portafolio de Inversiones")
    
    df_inv = st.session_state.df_inversiones
    if not df_inv.empty:
        df_inv["Rendimiento ($)"] = pd.to_numeric(df_inv["Valor_Actual_USD"], errors="coerce") - pd.to_numeric(df_inv["Monto_Invertido_USD"], errors="coerce")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        total_inv = pd.to_numeric(df_inv["Monto_Invertido_USD"], errors="coerce").sum()
        total_val = pd.to_numeric(df_inv["Valor_Actual_USD"], errors="coerce").sum()
        total_pnl = total_val - total_inv
        
        col_m1.metric("Capital Invertido", f"${total_inv:,.2f}")
        col_m2.metric("Valor Actual del Portafolio", f"${total_val:,.2f}")
        col_m3.metric("Ganancia / Pérdida Total", f"${total_pnl:,.2f}", delta=f"${total_pnl:,.2f}")
        
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("Aún no tienes posiciones de inversión registradas.")

# 4. PRESUPUESTO VS REAL
elif opcion_menu == OPC_PRESUPUESTO:
    st.subheader("🎯 Comparativo de Desempeño Financiero")
    
    tab_comp1, tab_comp2, tab_comp3 = st.tabs([
        "📊 Comparativo (Métricas)", 
        "➕ Registrar Estimado Manual", 
        "📋 Ver / Eliminar Estimados"
    ])
    
    df_est = st.session_state.df_estimaciones
    df_mov = st.session_state.df_movimientos

    # TAB 1: COMPARATIVO Y TABLAS DE ESTIMADO VS REAL
    with tab_comp1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 📥 Ingresos")
            ing_est = calcular_total_estimado(df_est, "Ingreso")
            ing_real = pd.to_numeric(df_mov[df_mov["Tipo"].astype(str).str.strip().str.lower() == "ingreso"]["Monto_USD"], errors="coerce").sum() if not df_mov.empty else 0.0
            st.metric("Ingresos Estimados", f"${ing_est:,.2f}")
            st.metric("Ingresos Reales Ejecutados", f"${ing_real:,.2f}", delta=f"${ing_real - ing_est:,.2f}")

        with col_b:
            st.markdown("### 📤 Gastos")
            gast_est = calcular_total_estimado(df_est, "Gasto")
            gast_real = pd.to_numeric(df_mov[df_mov["Tipo"].astype(str).str.strip().str.lower() == "gasto"]["Monto_USD"], errors="coerce").sum() if not df_mov.empty else 0.0
            st.metric("Gastos Estimados", f"${gast_est:,.2f}")
            st.metric("Gastos Reales Ejecutados", f"${gast_real:,.2f}", delta=f"${gast_est - gast_real:,.2f}")

    # TAB 2: AGREGAR UN INGRESO O GASTO ESTIMADO MANUALMENTE
    with tab_comp2:
        st.markdown("### ➕ Registrar Nuevo Ingreso o Gasto Estimado")
        col_est1, col_est2 = st.columns(2)
        
        with col_est1:
            est_tipo = st.selectbox("Tipo de Estimación", ["Gasto", "Ingreso"], key="add_est_tipo")
            est_categoria = st.text_input("Categoría Estimada", value="Alimentación" if est_tipo == "Gasto" else "Sueldo", key="add_est_cat")
        
        with col_est2:
            est_grupo = st.selectbox("Grupo", st.session_state.lista_grupos, key="add_est_grp")
            est_monto = st.number_input("Monto Estimado ($ USD)", min_value=0.0, step=10.0, key="add_est_monto")

        if st.button("Guardar Estimación Presupuestaria", type="primary"):
            next_est_id = len(st.session_state.df_estimaciones) + 1

            nueva_est = pd.DataFrame([{
                "ID": next_est_id,
                "Tipo": est_tipo,
                "Categoria": est_categoria,
                "Grupo": est_grupo,
                "Monto_Estimado_USD": est_monto
            }])
            
            st.session_state.df_estimaciones = pd.concat([st.session_state.df_estimaciones, nueva_est], ignore_index=True)
            st.session_state.df_estimaciones = estandarizar_df_estimaciones(st.session_state.df_estimaciones)
            if guardar_en_sheets("Estimaciones", st.session_state.df_estimaciones):
                st.success(f"¡Estimación de {est_tipo} por ${est_monto:,.2f} USD agregada exitosamente!")
                st.rerun()

    # TAB 3: VER TODAS LAS ESTIMACIONES Y ELIMINAR O EDITAR
    with tab_comp3:
        st.markdown("### 📋 Presupuestos Estimados Registrados")
        if not df_est.empty:
            st.dataframe(df_est, use_container_width=True)
            
            opciones_est = df_est["ID"].astype(str) + " - " + df_est["Tipo"].astype(str) + " - " + df_est["Categoria"].astype(str)
            est_sel = st.selectbox("Selecciona una estimación para borrar:", opciones_est)
            
            id_est_del = extraer_id_seguro(est_sel)
            if st.button("🗑️ Eliminar Estimación Seleccionada") and id_est_del is not None:
                st.session_state.df_estimaciones = df_est[df_est["ID"] != id_est_del].reset_index(drop=True)
                st.session_state.df_estimaciones = estandarizar_df_estimaciones(st.session_state.df_estimaciones)
                if guardar_en_sheets("Estimaciones", st.session_state.df_estimaciones):
                    st.success("¡Estimación eliminada con éxito!")
                    st.rerun()
        else:
            st.info("No hay presupuestos estimados registrados aún.")

# 5. CARGAR PRESUPUESTO DESDE ARCHIVO
elif opcion_menu == OPC_CARGAR:
    st.subheader("Importar Presupuesto Estimado por Archivo (Excel / CSV)")
    archivo = st.file_uploader("Sube tu archivo de presupuesto (Excel o CSV)", type=["xlsx", "xls", "csv"])
    
    st.caption("El archivo debe contener las columnas: **Tipo**, **Categoria**, **Grupo**, **Monto_Estimado_USD**")
    
    if archivo is not None:
        try:
            if archivo.name.endswith(".csv"):
                df_cargado = pd.read_csv(archivo)
            else:
                df_cargado = pd.read_excel(archivo)
            
            df_cargado = estandarizar_df_estimaciones(df_cargado)
            
            st.write(f"📋 **Vista previa de todas las filas cargadas ({len(df_cargado)} filas encontradas):**")
            st.dataframe(df_cargado, use_container_width=True)
            
            if st.button("Guardar Presupuesto Completo en Google Sheets", type="primary"):
                st.session_state.df_estimaciones = df_cargado
                if guardar_en_sheets("Estimaciones", df_cargado, min_rows=max(100, len(df_cargado))):
                    st.success(f"¡Se han importado y guardado las {len(df_cargado)} filas de tu presupuesto exitosamente!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

# 6. RESUMEN Y GRÁFICOS
elif opcion_menu == OPC_RESUMEN:
    st.subheader("Evolución y Distribución de Gastos (en USD)")
    df_mov = st.session_state.df_movimientos
    if not df_mov.empty:
        df_gastos = df_mov[df_mov["Tipo"].astype(str).str.strip().str.lower() == "gasto"].copy()
        df_gastos["Monto_USD"] = pd.to_numeric(df_gastos["Monto_USD"], errors="coerce")
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
                if guardar_en_sheets("Grupos", pd.DataFrame({"Nombre_Grupo": st.session_state.lista_grupos})):
                    st.success(f"Grupo '{nuevo_grupo}' agregado con éxito.")
                    st.rerun()

        st.divider()
        if st.session_state.lista_grupos:
            grupo_eliminar = st.selectbox("Seleccionar grupo a eliminar", st.session_state.lista_grupos, key="sel_del_grupo")
            if st.button("🗑️ Eliminar Grupo", key="btn_del_grupo"):
                if grupo_eliminar in st.session_state.lista_grupos:
                    st.session_state.lista_grupos.remove(grupo_eliminar)
                    if guardar_en_sheets("Grupos", pd.DataFrame({"Nombre_Grupo": st.session_state.lista_grupos})):
                        st.success(f"Grupo '{grupo_eliminar}' eliminado.")
                        st.rerun()

    with col_g2:
        st.markdown("### 🏦 Gestión de Cuentas / Bancos")
        nueva_cuenta = st.text_input("Nombre del nuevo banco/cuenta", key="txt_nueva_cuenta")
        if st.button("➕ Agregar Cuenta", key="btn_add_cuenta"):
            if nueva_cuenta and nueva_cuenta not in st.session_state.lista_cuentas:
                st.session_state.lista_cuentas.append(nueva_cuenta)
                if guardar_en_sheets("Cuentas", pd.DataFrame({"Nombre_Cuenta": st.session_state.lista_cuentas})):
                    st.success(f"Cuenta '{nueva_cuenta}' agregada con éxito.")
                    st.rerun()

        st.divider()
        if st.session_state.lista_cuentas:
            cuenta_eliminar = st.selectbox("Seleccionar cuenta a eliminar", st.session_state.lista_cuentas, key="sel_del_cuenta")
            if st.button("🗑️ Eliminar Cuenta", key="btn_del_cuenta"):
                if cuenta_eliminar in st.session_state.lista_cuentas:
                    st.session_state.lista_cuentas.remove(cuenta_eliminar)
                    if guardar_en_sheets("Cuentas", pd.DataFrame({"Nombre_Cuenta": st.session_state.lista_cuentas})):
                        st.success(f"Cuenta '{cuenta_eliminar}' eliminada.")
                        st.rerun()