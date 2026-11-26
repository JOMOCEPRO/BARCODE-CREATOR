# ==============================================================================
# PROYECTO: BARCODE-CREATOR | FIRMA: JOMOCE-SOFT
# LICENCIA: GNU GENERAL PUBLIC LICENSE V3 (GNU GPLv3)
# COPYRIGHT (C) 2026 JOMOCE-SOFT - TODOS LOS DERECHOS CONCEDIDOS BAJO GNU GPLv3
# ==============================================================================

import base64
import streamlit as st
import pandas as pd
import win32print
from rutas import obtener_dir_recursos
from motor_etiquetas import (
    cargar_archivo_tabular,
    formatear_moneda_excel,
    construir_pdf_4x6,
    enviar_a_impresora_windows,
)
from base_datos import (
    inicializar_db,
    guardar_catalogo,
    cargar_catalogo,
    limpiar_catalogo,
    obtener_estado_catalogo,
    guardar_plantilla,
    listar_plantillas,
    eliminar_plantilla,
)

st.set_page_config(
    page_title="BARCODE-CREATOR - WHTP203E",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inicializar_db()

with open(obtener_dir_recursos() / "styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("BARCODE-CREATOR")
st.caption("DESARROLLADO POR JOMOCE-SOFT | LICENCIA GNU GPLv3 | SISTEMA DE ETIQUETAS WHTP203E (4 X 6 PULGADAS)")

# ==============================================================================
# SECCION 1: GESTION DE BASE DE DATOS DE PRODUCTOS (TABLA DINAMICA A MEDIDA)
# ==============================================================================
st.subheader("1. BASE DE DATOS DE PRODUCTOS (TABLA A MEDIDA DEL ARCHIVO)")

estado_db = obtener_estado_catalogo()
df_datos = cargar_catalogo()

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

with st.expander("IMPORTAR ARCHIVO EXCEL / CSV O LIMPIAR TODO", expanded=df_datos.empty):
    c_imp1, c_imp2 = st.columns([2, 1])
    with c_imp1:
        archivo = st.file_uploader(
            "SELECCIONA ARCHIVO EXCEL O CSV (.XLSX, .XLS, .CSV)",
            type=["xlsx", "xls", "csv"],
            key=f"uploader_catalogo_{st.session_state['uploader_key']}",
        )
    with c_imp2:
        modo_importacion = st.radio(
            "MODO DE GUARDADO EN BASE DE DATOS",
            ["REEMPLAZAR CATALOGO COMPLETO (RECREAR TABLA)", "AGREGAR A LO EXISTENTE"],
            index=0,
        )

    b_imp1, b_imp2, b_imp3 = st.columns([2, 1, 1])
    with b_imp1:
        if st.button("GUARDAR ARCHIVO EN BASE DE DATOS", type="primary", use_container_width=True, disabled=(archivo is None)):
            try:
                df_nuevo = cargar_archivo_tabular(archivo)
                if df_nuevo.empty:
                    st.warning("EL ARCHIVO NO CONTIENE REGISTROS.")
                else:
                    modo_clave = "REEMPLAZAR" if modo_importacion.startswith("REEMPLAZAR") else "AGREGAR"
                    guardar_catalogo(df_nuevo, modo=modo_clave)
                    nueva_ukey = st.session_state.get("uploader_key", 0) + 1
                    tpl_resguardada = st.session_state.get("tpl_activa", None)
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    for k in list(st.session_state.keys()):
                        del st.session_state[k]
                    st.session_state["uploader_key"] = nueva_ukey
                    if tpl_resguardada is not None:
                        st.session_state["tpl_activa"] = tpl_resguardada
                    st.rerun()
            except Exception as err:
                st.error(f"ERROR AL IMPORTAR ARCHIVO: {err}")

    with b_imp2:
        confirmar_limpieza = st.checkbox("CONFIRMAR LIMPIEZA TOTAL")
    with b_imp3:
        if st.button("LIMPIAR TODO (DB Y SESION)", use_container_width=True, disabled=(not confirmar_limpieza)):
            limpiar_catalogo()
            st.cache_data.clear()
            st.cache_resource.clear()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

if df_datos.empty:
    st.info(f"BASE DE DATOS LIMPIA ({estado_db['ruta_db']}). IMPORTA UN ARCHIVO EXCEL O CSV PARA CREAR LA TABLA.")
    st.stop()

columnas_disponibles = list(df_datos.columns)
st.success(
    f"TABLA ACTIVA: {len(df_datos)} REGISTROS | {len(columnas_disponibles)} COLUMNAS ({', '.join(columnas_disponibles)}) | "
    f"ACTUALIZADO: {estado_db['actualizado']}"
)

st.divider()

# ==============================================================================
# SECCION 2: PLANTILLAS GUARDADAS (CARGAR / GUARDAR / ELIMINAR)
# ==============================================================================
st.subheader("2. PLANTILLAS DE DISEÑO Y DATOS DE IMPRESION")

plantillas_guardadas = listar_plantillas()
nombres_plantillas = ["NINGUNA (CONFIGURACION MANUAL)"] + list(plantillas_guardadas.keys())

cp1, cp2, cp3 = st.columns([2, 1, 1])
with cp1:
    plantilla_sel = st.selectbox("CARGAR PLANTILLA GUARDADA", nombres_plantillas)
with cp2:
    st.write("")
    st.write("")
    btn_cargar_tpl = st.button("APLICAR PLANTILLA", use_container_width=True, disabled=(plantilla_sel == "NINGUNA (CONFIGURACION MANUAL)"))
with cp3:
    st.write("")
    st.write("")
    btn_borrar_tpl = st.button("ELIMINAR PLANTILLA", use_container_width=True, disabled=(plantilla_sel == "NINGUNA (CONFIGURACION MANUAL)"))

if btn_cargar_tpl and plantilla_sel in plantillas_guardadas:
    st.session_state["tpl_activa"] = plantillas_guardadas[plantilla_sel]
    st.success(f"PLANTILLA '{plantilla_sel}' APLICADA.")

if btn_borrar_tpl and plantilla_sel in plantillas_guardadas:
    eliminar_plantilla(plantilla_sel)
    st.session_state.pop("tpl_activa", None)
    st.warning(f"PLANTILLA '{plantilla_sel}' ELIMINADA.")
    st.rerun()

tpl = st.session_state.get("tpl_activa", {})
# ==============================================================================
# SECCION 3: TAMANO DE ETIQUETA Y DISTRIBUCION EN HOJA DE 4 X 6 PULGADAS
# ==============================================================================
st.subheader("3. TAMANO DE ETIQUETA Y DISTRIBUCION EN HOJA DE 4 X 6 PULGADAS")

PRESETS_4X6 = {
    "3.2 X 2.5 CM (3 COLS X 6 FILAS = 18 TICKETS/HOJA) - ESTANDAR RETAIL 3 COLUMNAS": {
        "ancho": 32.0, "alto": 25.0, "cols": 3, "filas": 6, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 1.0
    },
    "3.2 X 2.5 CM (3 COLS X 5 FILAS = 15 TICKETS/HOJA) - RETAIL 5 FILAS": {
        "ancho": 32.0, "alto": 25.0, "cols": 3, "filas": 5, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 0.0
    },
    "3.2 X 2.9 CM (3 COLS X 4 FILAS = 12 TICKETS/HOJA) - RECOMENDADO CON PRECIO": {
        "ancho": 32.0, "alto": 29.0, "cols": 3, "filas": 4, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 0.0
    },
    "1.8 X 2.0 CM (5 COLS X 6 FILAS = 30 TICKETS/HOJA) - ARTICULOS PEQUENOS": {
        "ancho": 18.0, "alto": 20.0, "cols": 5, "filas": 6, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 0.0
    },
    "4.8 X 2.5 CM (2 COLS X 5 FILAS = 10 TICKETS/HOJA) - COMERCIAL 50X25 MM": {
        "ancho": 48.0, "alto": 25.0, "cols": 2, "filas": 5, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 0.0
    },
    "4.0 X 2.0 CM (2 COLS X 6 FILAS = 12 TICKETS/HOJA) - FARMACIA / RETAIL": {
        "ancho": 40.0, "alto": 20.0, "cols": 2, "filas": 6, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 0.0
    },
    "3.0 X 1.5 CM (3 COLS X 8 FILAS = 24 TICKETS/HOJA) - COMPACTA CODIGO + PRECIO": {
        "ancho": 30.0, "alto": 15.0, "cols": 3, "filas": 8, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 0.0
    },
    "2.5 X 1.5 CM (3 COLS X 8 FILAS = 24 TICKETS/HOJA) - PIEZAS PEQUENAS": {
        "ancho": 25.0, "alto": 15.0, "cols": 3, "filas": 8, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 0.0
    },
    "PERSONALIZADO (DEFINIR MEDIDAS Y CUADRICULA EN HOJA 4 X 6 PULGADAS)": {
        "ancho": 32.0, "alto": 25.0, "cols": 3, "filas": 6, "gap_h": 2.0, "gap_v": 2.0, "margen_sup": 1.0
    },
}

lista_presets = list(PRESETS_4X6.keys())
idx_preset_default = lista_presets.index(tpl["preset"]) if tpl.get("preset") in lista_presets else 0

col_p1, col_p2 = st.columns([2, 1])
with col_p1:
    preset_elegido = st.selectbox("PLANTILLA DE DISTRIBUCION EN HOJA 4 X 6\"", lista_presets, index=idx_preset_default)
with col_p2:
    impresoras = [
        p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
    ]
    idx_whtp = next((i for i, n in enumerate(impresoras) if "WHTP" in n.upper() or "203" in n.upper()), 0)
    impresora_destino = st.selectbox("IMPRESORA TERMICA DESTINO", impresoras, index=idx_whtp)

vals = PRESETS_4X6[preset_elegido]
es_personalizado = preset_elegido.startswith("PERSONALIZADO")

def_ancho = float(tpl.get("ancho_mm", vals["ancho"])) if es_personalizado else vals["ancho"]
def_alto = float(tpl.get("alto_mm", vals["alto"])) if es_personalizado else vals["alto"]
def_cols = int(tpl.get("columnas", vals["cols"])) if es_personalizado else vals["cols"]
def_filas = int(tpl.get("filas", vals["filas"])) if es_personalizado else vals["filas"]
def_gap_h = float(tpl.get("gap_h_mm", vals["gap_h"]))
def_gap_v = float(tpl.get("gap_v_mm", vals["gap_v"]))
def_margen_sup = float(tpl.get("margen_sup_mm", vals.get("margen_sup", 1.0)))

c_dim1, c_dim2, c_dim3, c_dim4, c_dim5, c_dim6, c_dim7 = st.columns(7)
with c_dim1:
    ancho_mm = st.number_input("ANCHO TICKET (MM)", min_value=12.0, max_value=98.0, value=def_ancho, step=0.5, disabled=not es_personalizado)
with c_dim2:
    alto_mm = st.number_input("ALTO TICKET (MM)", min_value=10.0, max_value=148.0, value=def_alto, step=0.5, disabled=not es_personalizado)
with c_dim3:
    cols = st.number_input("COLUMNAS / HOJA", min_value=1, max_value=8, value=def_cols, step=1, disabled=not es_personalizado)
with c_dim4:
    filas = st.number_input("FILAS / HOJA", min_value=1, max_value=14, value=def_filas, step=1, disabled=not es_personalizado)
with c_dim5:
    gap_h_mm = st.number_input("SEPARACION HORIZ. (MM)", min_value=0.0, max_value=15.0, value=def_gap_h, step=0.2)
with c_dim6:
    gap_v_mm = st.number_input("SEPARACION VERT. (MM)", min_value=0.0, max_value=15.0, value=def_gap_v, step=0.2)
with c_dim7:
    margen_sup_mm = st.number_input("MARGEN SUP. CORTE (MM)", min_value=0.0, max_value=20.0, value=def_margen_sup, step=0.1)

ancho_ocupado = (cols * ancho_mm) + ((cols - 1) * gap_h_mm)
alto_ocupado = round(margen_sup_mm + (filas * alto_mm) + ((filas - 1) * gap_v_mm), 4)

if ancho_ocupado > 100.0 or alto_ocupado > 180.0:
    st.error(
        f"LA DISTRIBUCION EXCEDE EL LIMITE PERMITIDO DE IMPRESION: "
        f"OCUPA {ancho_ocupado:.1f} MM DE ANCHO X {alto_ocupado:.1f} MM DE ALTO."
    )
    st.stop()

st.divider()

# ==============================================================================
# SECCION 4: DEFINIR CODIGO DE BARRAS, PRECIO (MONEDA), DATOS Y GUARDAR PLANTILLA
# ==============================================================================
st.subheader("4. CONFIGURACION DE DATOS DEL STICKER (MAYUSCULAS Y MONEDA)")

if tpl.get("col_codigo") in columnas_disponibles:
    idx_ref = columnas_disponibles.index(tpl["col_codigo"])
else:
    idx_ref = next((i for i, c in enumerate(columnas_disponibles) if "REFERENCIA" in c or "CODIGO" in c or "SKU" in c), 0)

def_sup_tpl = [c for c in tpl.get("cols_superiores", []) if c in columnas_disponibles]
if not def_sup_tpl and not tpl:
    def_sup_tpl = [c for c in columnas_disponibles if "NOMBRE" in c or "DESCRIP" in c][:1]

opciones_precio = ["NINGUNA (NO IMPRIMIR PRECIO)"] + columnas_disponibles
if tpl.get("col_precio") in opciones_precio:
    idx_precio = opciones_precio.index(tpl["col_precio"])
else:
    idx_precio = next((i for i, c in enumerate(opciones_precio) if "PRECIO" in c or "VALOR" in c or "PVP" in c), 0)

def_decimales = int(tpl.get("decimales_precio", 0))
def_inf_tpl = [c for c in tpl.get("cols_inferiores", []) if c in columnas_disponibles]

c_map1, c_map2 = st.columns(2)
with c_map1:
    col_codigo = st.selectbox("COLUMNA A TRANSFORMAR EN CODIGO DE BARRAS (CODE 128)", columnas_disponibles, index=idx_ref)
with c_map2:
    cols_superiores = st.multiselect("DATOS ENCIMA DEL CODIGO (EJ. NOMBRE EN MAYUSCULAS)", columnas_disponibles, default=def_sup_tpl, max_selections=2)

c_pre1, c_pre2, c_pre3 = st.columns([2, 1, 2])
with c_pre1:
    col_precio = st.selectbox("COLUMNA DESTINADA PARA PRECIOS (FORMATO MONEDA)", opciones_precio, index=idx_precio)
with c_pre2:
    decimales_precio = st.number_input(
        "DIGITOS DECIMALES",
        min_value=0,
        max_value=4,
        value=def_decimales,
        step=1,
        disabled=(col_precio == "NINGUNA (NO IMPRIMIR PRECIO)"),
    )
with c_pre3:
    cols_inferiores = st.multiselect("OTROS DATOS DEBAJO DEL CODIGO (OPCIONAL)", columnas_disponibles, default=def_inf_tpl, max_selections=2)

c_opt1, c_opt2 = st.columns(2)
with c_opt1:
    mostrar_texto_codigo = st.checkbox("IMPRIMIR EL TEXTO DE LA REFERENCIA DEBAJO DE LAS BARRAS", value=bool(tpl.get("mostrar_texto_codigo", True)))
with c_opt2:
    guia_corte = st.checkbox("IMPRIMIR LIMITES Y GUIAS DE CORTE PARA TROQUELADO MANUAL", value=bool(tpl.get("guia_corte", True)))

cg1, cg2 = st.columns([3, 1])
with cg1:
    nombre_nueva_tpl = st.text_input("NOMBRE PARA GUARDAR ESTA CONFIGURACION COMO PLANTILLA (EJ. ETIQUETA RETAIL 3.2X2.9)")
with cg2:
    st.write("")
    st.write("")
    if st.button("GUARDAR PLANTILLA", use_container_width=True):
        if not nombre_nueva_tpl.strip():
            st.error("ESCRIBE UN NOMBRE PARA LA PLANTILLA ANTES DE GUARDAR.")
        else:
            config_a_guardar = {
                "preset": preset_elegido,
                "ancho_mm": float(ancho_mm),
                "alto_mm": float(alto_mm),
                "columnas": int(cols),
                "filas": int(filas),
                "gap_h_mm": float(gap_h_mm),
                "gap_v_mm": float(gap_v_mm),
                "margen_sup_mm": float(margen_sup_mm),
                "col_codigo": col_codigo,
                "cols_superiores": cols_superiores,
                "col_precio": col_precio,
                "decimales_precio": int(decimales_precio),
                "cols_inferiores": cols_inferiores,
                "mostrar_texto_codigo": mostrar_texto_codigo,
                "guia_corte": guia_corte,
            }
            guardar_plantilla(nombre_nueva_tpl, config_a_guardar)
            st.session_state["tpl_activa"] = config_a_guardar
            st.success(f"PLANTILLA '{nombre_nueva_tpl.strip().upper()}' GUARDADA EN BASE DE DATOS.")
            st.rerun()

st.divider()

# ==============================================================================
# SECCION 5: SELECCIONAR PRODUCTOS Y CANTIDAD DE TICKETS A IMPRIMIR
# ==============================================================================
st.subheader("5. SELECCIONAR PRODUCTOS Y CANTIDAD DE TICKETS A IMPRIMIR")

clave_lote_estado = f"lote_persistente_{estado_db['version']}"
if clave_lote_estado not in st.session_state:
    st.session_state[clave_lote_estado] = {}

lote_guardado = st.session_state[clave_lote_estado]

df_tabla = df_datos.copy()
df_tabla.insert(0, "__ROW_ID__", df_tabla.index.astype(int))
df_tabla.insert(
    1,
    "CANTIDAD_TICKETS",
    df_tabla["__ROW_ID__"].map(lambda rid: int(lote_guardado.get(int(rid), 0))),
)
df_tabla.insert(
    2,
    "SELECCIONAR",
    df_tabla["CANTIDAD_TICKETS"] > 0,
)

c_busq1, c_busq2, c_busq3 = st.columns([2, 1, 1])
with c_busq1:
    filtro_texto = st.text_input("BUSCAR REGISTRO POR CUALQUIER COLUMNA")
with c_busq2:
    cant_lote = st.number_input("CANTIDAD RAPIDA PARA FILTRADOS", min_value=1, max_value=500, value=1, step=1)
with c_busq3:
    st.write("")
    st.write("")
    aplicar_lote = st.button("ASIGNAR A VISIBLES", use_container_width=True)

c_filt1, c_filt2 = st.columns([2, 1])
with c_filt1:
    solo_seleccionados = st.checkbox(
        f"VER SOLO SELECCIONADOS EN EL LOTE ACTUAL ({len(lote_guardado)} PRODUCTOS)",
        value=False,
    )
with c_filt2:
    if st.button("LIMPIAR SELECCION DE LOTE", use_container_width=True):
        st.session_state[clave_lote_estado] = {}
        st.rerun()

df_vista = df_tabla.copy()

if solo_seleccionados:
    df_vista = df_vista[df_vista["SELECCIONAR"]].copy()

if filtro_texto.strip():
    termino = filtro_texto.strip().upper()
    mascara = df_vista[columnas_disponibles].apply(
        lambda fila: fila.str.contains(termino, regex=False).any(), axis=1
    )
    df_vista = df_vista[mascara].copy()

if aplicar_lote and not df_vista.empty:
    for rid in df_vista["__ROW_ID__"].tolist():
        st.session_state[clave_lote_estado][int(rid)] = int(cant_lote)
    st.rerun()

clave_tabla = f"editor_{estado_db['version']}_{filtro_texto.strip().upper()}_{solo_seleccionados}"
df_editado = st.data_editor(
    df_vista,
    key=clave_tabla,
    use_container_width=True,
    hide_index=True,
    disabled=["__ROW_ID__"] + columnas_disponibles,
    column_order=["SELECCIONAR", "CANTIDAD_TICKETS"] + columnas_disponibles,
    column_config={
        "SELECCIONAR": st.column_config.CheckboxColumn("SELECCIONAR", default=False),
        "CANTIDAD_TICKETS": st.column_config.NumberColumn("CANTIDAD TICKETS", min_value=0, max_value=1000, step=1),
    },
)

hubo_cambios = False
for _, fila_ed in df_editado.iterrows():
    rid = int(fila_ed["__ROW_ID__"])
    marcado = bool(fila_ed["SELECCIONAR"])
    cant_actual = int(fila_ed["CANTIDAD_TICKETS"])
    cant_previa = int(st.session_state[clave_lote_estado].get(rid, 0))

    if marcado and cant_previa == 0 and cant_actual == 0:
        st.session_state[clave_lote_estado][rid] = 1
        hubo_cambios = True
    elif not marcado and cant_previa > 0:
        st.session_state[clave_lote_estado].pop(rid, None)
        hubo_cambios = True
    elif marcado and cant_actual > 0 and cant_actual != cant_previa:
        st.session_state[clave_lote_estado][rid] = cant_actual
        hubo_cambios = True
    elif not marcado and cant_actual > 0:
        st.session_state[clave_lote_estado][rid] = cant_actual
        hubo_cambios = True

if hubo_cambios:
    st.rerun()

lote_final = st.session_state[clave_lote_estado]
df_tabla["CANTIDAD_TICKETS"] = df_tabla["__ROW_ID__"].map(lambda rid: int(lote_final.get(int(rid), 0)))
seleccionados = df_tabla[df_tabla["CANTIDAD_TICKETS"] > 0].copy()

total_tickets = int(seleccionados["CANTIDAD_TICKETS"].sum())
tickets_por_hoja = int(cols * filas)
total_hojas = (total_tickets + tickets_por_hoja - 1) // tickets_por_hoja if total_tickets > 0 else 0

m1, m2, m3 = st.columns(3)
m1.metric("TICKETS TOTALES A IMPRIMIR", f"{total_tickets}")
m2.metric("CAPACIDAD POR HOJA (4 X 6\")", f"{tickets_por_hoja} TICKETS ({int(cols)}X{int(filas)})")
m3.metric("HOJAS TROQUELADAS REQUERIDAS", f"{total_hojas}")

if total_tickets == 0:
    st.info("MARCA LA CASILLA 'SELECCIONAR' O ASIGNA UNA CANTIDAD MAYOR A 0 PARA GENERAR E IMPRIMIR.")
    st.stop()

cola_impresion = []
registros_sin_codigo = 0

for _, reg in seleccionados.iterrows():
    valor_cb = str(reg[col_codigo]).strip().upper()
    if not valor_cb:
        registros_sin_codigo += 1
        continue

    sup_vals = [str(reg[c]).strip().upper() for c in cols_superiores]
    inf_vals = [str(reg[c]).strip().upper() for c in cols_inferiores]

    precio_fmt = ""
    if col_precio != "NINGUNA (NO IMPRIMIR PRECIO)":
        precio_fmt = formatear_moneda_excel(reg[col_precio], int(decimales_precio))

    for _ in range(int(reg["CANTIDAD_TICKETS"])):
        cola_impresion.append({
            "codigo_barras": valor_cb,
            "superiores": sup_vals,
            "inferiores": inf_vals,
            "precio_formateado": precio_fmt,
        })

if registros_sin_codigo > 0:
    st.warning(f"SE OMITIERON {registros_sin_codigo} REGISTROS PORQUE LA COLUMNA '{col_codigo}' ESTA VACIA.")

if not cola_impresion:
    st.error(f"NINGUNO DE LOS REGISTROS SELECCIONADOS TIENE DATOS EN LA COLUMNA '{col_codigo}'.")
    st.stop()

config_diseno = {
    "ancho_mm": float(ancho_mm),
    "alto_mm": float(alto_mm),
    "columnas": int(cols),
    "filas": int(filas),
    "gap_h_mm": float(gap_h_mm),
    "gap_v_mm": float(gap_v_mm),
    "margen_sup_mm": float(margen_sup_mm),
    "mostrar_texto_codigo": mostrar_texto_codigo,
    "guia_corte": guia_corte,
}

pdf_bytes = construir_pdf_4x6(cola_impresion, config_diseno)
st.divider()

col_act1, col_act2 = st.columns(2)
with col_act1:
    if st.button("IMPRIMIR DIRECTO EN WHTP203E", type="primary", use_container_width=True):
        try:
            enviar_a_impresora_windows(pdf_bytes, impresora_destino)
            st.success(f"ORDEN ENVIADA A '{impresora_destino}' ({len(cola_impresion)} TICKETS EN {total_hojas} HOJAS).")
        except Exception as e:
            st.error(f"ERROR AL ENVIAR A LA IMPRESORA: {e}")

with col_act2:
    st.download_button(
        label="DESCARGAR PDF LISTO PARA IMPRIMIR (4 X 6\")",
        data=pdf_bytes,
        file_name=f"barcode_creator_4x6_{int(ancho_mm)}x{int(alto_mm)}mm.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

with st.expander("VISTA PREVIA DEL DOCUMENTO PDF GENERADO (ESCALA 1:1)", expanded=True):
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    iframe_pdf = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="580" type="application/pdf"></iframe>'
    st.markdown(iframe_pdf, unsafe_allow_html=True)



st.divider()
st.markdown(
    """
    <div style="text-align: center; padding: 12px 0; font-size: 13px; opacity: 0.85;">
        <strong>JOMOCE-SOFT</strong> &copy; 2026 &mdash; SOFTWARE LIBRE DISTRIBUIDO BAJO LICENCIA <strong>GNU GPLv3</strong> | BARCODE-CREATOR
    </div>
    """,
    unsafe_allow_html=True,
)