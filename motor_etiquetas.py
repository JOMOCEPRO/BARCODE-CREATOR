# ==============================================================================
# PROYECTO: BARCODE-CREATOR | FIRMA: JOMOCE-SOFT
# LICENCIA: GNU GENERAL PUBLIC LICENSE V3 (GNU GPLv3)
# COPYRIGHT (C) 2026 JOMOCE-SOFT - TODOS LOS DERECHOS CONCEDIDOS BAJO GNU GPLv3
# ==============================================================================
import io
import tempfile
import openpyxl
import pandas as pd
import barcode
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, inch
from reportlab.lib.utils import ImageReader

ANCHO_HOJA_4X6 = 4.0 * inch
ALTO_HOJA_4X6 = 6.0 * inch


def _detectar_fila_cabecera_matriz(filas_matriz: list) -> int:
    palabras_clave = {"REFERENCIA", "CODIGO", "SKU", "DESCRIPCION", "NOMBRE", "PRECIO", "PROVEEDOR", "CANTIDAD", "CATEGORIA"}
    limite = min(15, len(filas_matriz))

    for idx in range(limite):
        valores = [str(v).strip().upper() for v in filas_matriz[idx] if v is not None and str(v).strip() != ""]
        if any(v in palabras_clave for v in valores) and len(valores) >= 2:
            return idx

    mejor_idx = 0
    max_celdas = -1
    for idx in range(limite):
        valores = [str(v).strip() for v in filas_matriz[idx] if v is not None and str(v).strip() != ""]
        if len(valores) > max_celdas and len(valores) >= 2:
            max_celdas = len(valores)
            mejor_idx = idx
    return mejor_idx


def cargar_archivo_tabular(archivo_subido) -> pd.DataFrame:
    nombre = archivo_subido.name.lower()
    if nombre.endswith((".xlsx", ".xls")):
        wb = openpyxl.load_workbook(io.BytesIO(archivo_subido.getvalue()), data_only=True)
        ws = wb["INVENTARIO"] if "INVENTARIO" in wb.sheetnames else wb.active
        filas_matriz = [list(fila) for fila in ws.iter_rows(values_only=True)]
    elif nombre.endswith(".csv"):
        contenido = archivo_subido.getvalue()
        texto = None
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                texto = contenido.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if texto is None:
            raise ValueError("NO SE PUDO DECODIFICAR EL ARCHIVO CSV.")
        df_csv = pd.read_csv(io.StringIO(texto), sep=None, engine="python", header=None, dtype=str)
        filas_matriz = df_csv.where(pd.notnull(df_csv), None).values.tolist()
    else:
        raise ValueError("FORMATO NO SOPORTADO. USE .XLSX, .XLS O .CSV.")

    if not filas_matriz:
        return pd.DataFrame()

    fila_header = _detectar_fila_cabecera_matriz(filas_matriz)
    raw_headers = filas_matriz[fila_header]

    # CONSERVAR UNICAMENTE COLUMNAS QUE TENGAN CABECERA REAL O DATOS VALIDOS
    indices_validos = []
    cabeceras_limpias = []
    vistas = {}

    for i, celda in enumerate(raw_headers):
        txt = "" if celda is None else str(celda).strip().upper()
        tiene_datos_abajo = any(
            (i < len(r) and r[i] is not None and str(r[i]).strip() != "")
            for r in filas_matriz[fila_header + 1:]
        )
        if not txt and not tiene_datos_abajo:
            continue

        nombre_col = txt if txt else f"SIN_NOMBRE_{i + 1}"
        if nombre_col in vistas:
            vistas[nombre_col] += 1
            nombre_col = f"{nombre_col}_{vistas[nombre_col]}"
        else:
            vistas[nombre_col] = 1

        indices_validos.append(i)
        cabeceras_limpias.append(nombre_col)

    registros = []
    for fila in filas_matriz[fila_header + 1:]:
        reg = []
        vacia = True
        for idx_col in indices_validos:
            val = "" if (idx_col >= len(fila) or fila[idx_col] is None) else str(fila[idx_col]).strip().upper()
            if val != "":
                vacia = False
            reg.append(val)
        if not vacia:
            registros.append(reg)

    return pd.DataFrame(registros, columns=cabeceras_limpias)


def _generar_imagen_code128(valor_codigo: str, ancho_etiqueta_mm: float) -> ImageReader:
    clase_cb = barcode.get_barcode_class("code128")
    writer = ImageWriter()
    if ancho_etiqueta_mm <= 22:
        mod_width, quiet = 0.20, 1.0
    elif ancho_etiqueta_mm <= 35:
        mod_width, quiet = 0.25, 1.5
    else:
        mod_width, quiet = 0.30, 2.0

    opciones = {
        "module_width": mod_width,
        "module_height": 9.0,
        "quiet_zone": quiet,
        "write_text": False,
        "dpi": 203,
    }
    buffer = io.BytesIO()
    cb = clase_cb(str(valor_codigo).strip().upper(), writer=writer)
    cb.write(buffer, options=opciones)
    buffer.seek(0)
    return ImageReader(buffer)


def _parsear_numero_flexible(valor_str: str) -> float:
    limpio = str(valor_str).strip().replace("$", "").replace(" ", "")
    if not limpio:
        raise ValueError("VACIO")
    if "," in limpio and "." in limpio:
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        partes = limpio.split(",")
        if len(partes) == 2 and len(partes[1]) != 3:
            limpio = limpio.replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    return float(limpio)


def formatear_moneda_excel(valor: str, decimales: int = 0) -> str:
    val = str(valor).strip().upper()
    if not val:
        return ""
    try:
        numero = _parsear_numero_flexible(val)
        formateado_us = f"{numero:,.{int(decimales)}f}"
        formateado_co = formateado_us.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"$ {formateado_co}"
    except ValueError:
        return val


def _dibujar_guias_corte_pagina(c: canvas.Canvas, margen_izq: float, margen_sup: float, ancho_etq: float, alto_etq: float, cols: int, filas: int, gap_h: float, gap_v: float):
    c.saveState()
    c.setStrokeColorRGB(0.15, 0.15, 0.15)
    c.setLineWidth(0.6)
    ext = 3.0 * mm

    y_top_grid = ALTO_HOJA_4X6 - margen_sup
    y_bot_grid = y_top_grid - (filas * alto_etq) - ((filas - 1) * gap_v)

    for col_i in range(cols):
        x_izq = margen_izq + col_i * (ancho_etq + gap_h)
        x_der = x_izq + ancho_etq
        for x_pos in (x_izq, x_der):
            c.line(x_pos, y_top_grid + 0.5 * mm, x_pos, min(ALTO_HOJA_4X6 - 0.5 * mm, y_top_grid + ext))
            c.line(x_pos, max(0.5 * mm, y_bot_grid - ext), x_pos, y_bot_grid - 0.5 * mm)

    x_right_grid = margen_izq + (cols * ancho_etq) + ((cols - 1) * gap_h)

    for fila_i in range(filas):
        y_sup = y_top_grid - fila_i * (alto_etq + gap_v)
        y_inf = y_sup - alto_etq
        for y_pos in (y_sup, y_inf):
            c.line(max(0.5 * mm, margen_izq - ext), y_pos, margen_izq - 0.5 * mm, y_pos)
            c.line(x_right_grid + 0.5 * mm, y_pos, min(ANCHO_HOJA_4X6 - 0.5 * mm, x_right_grid + ext), y_pos)

    c.restoreState()


def construir_pdf_4x6(cola_tickets: list, config_diseno: dict) -> bytes:
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(ANCHO_HOJA_4X6, ALTO_HOJA_4X6))
    c.setAuthor("JOMOCE-SOFT")
    c.setCreator("BARCODE-CREATOR | JOMOCE-SOFT (GNU GPLv3)")
    c.setSubject("ETIQUETAS CODE 128 - LICENCIA GNU GPLv3")

    ancho_etq = config_diseno["ancho_mm"] * mm
    alto_etq = config_diseno["alto_mm"] * mm
    cols = config_diseno["columnas"]
    filas = config_diseno["filas"]
    gap_h = config_diseno["gap_h_mm"] * mm
    gap_v = config_diseno["gap_v_mm"] * mm

    ancho_total_grid = (cols * ancho_etq) + ((cols - 1) * gap_h)
    alto_total_grid = (filas * alto_etq) + ((filas - 1) * gap_v)

    margen_izq = max(2.5 * mm, (ANCHO_HOJA_4X6 - ancho_total_grid) / 2.0)
    margen_sup = max(2.5 * mm, (ALTO_HOJA_4X6 - alto_total_grid) / 2.0)

    tickets_por_hoja = cols * filas
    cache_barcodes = {}

    if config_diseno["guia_corte"] and len(cola_tickets) > 0:
        _dibujar_guias_corte_pagina(c, margen_izq, margen_sup, ancho_etq, alto_etq, cols, filas, gap_h, gap_v)

    for idx, ticket in enumerate(cola_tickets):
        pos_hoja = idx % tickets_por_hoja
        if idx > 0 and pos_hoja == 0:
            c.showPage()
            if config_diseno["guia_corte"]:
                _dibujar_guias_corte_pagina(c, margen_izq, margen_sup, ancho_etq, alto_etq, cols, filas, gap_h, gap_v)

        col_idx = pos_hoja % cols
        fila_idx = pos_hoja // cols

        x = margen_izq + col_idx * (ancho_etq + gap_h)
        y = ALTO_HOJA_4X6 - margen_sup - ((fila_idx + 1) * alto_etq) - (fila_idx * gap_v)

        if config_diseno["guia_corte"]:
            c.saveState()
            c.setStrokeColorRGB(0.20, 0.20, 0.20)
            c.setLineWidth(0.75)
            c.rect(x, y, ancho_etq, alto_etq, stroke=1, fill=0)
            c.restoreState()

        codigo_raw = str(ticket["codigo_barras"]).strip().upper()
        if not codigo_raw:
            continue

        sup_list = [str(s).strip().upper() for s in ticket.get("superiores", []) if str(s).strip()]
        inf_list = [str(i).strip().upper() for i in ticket.get("inferiores", []) if str(i).strip()]
        precio_txt = str(ticket.get("precio_formateado", "")).strip().upper()
        mostrar_txt_cod = config_diseno["mostrar_texto_codigo"]

        pad_x = 1.4 * mm
        pad_y = 1.4 * mm
        ancho_util = max(8 * mm, ancho_etq - (2 * pad_x))

        if config_diseno["alto_mm"] <= 22:
            font_sup, font_inf, font_cod, font_pre = 4.5, 4.8, 4.8, 5.5
        elif config_diseno["alto_mm"] <= 32:
            font_sup, font_inf, font_cod, font_pre = 5.5, 5.8, 5.8, 7.5
        else:
            font_sup, font_inf, font_cod, font_pre = 7.0, 7.2, 7.0, 9.0

        cursor_y = y + alto_etq - pad_y - (font_sup * 0.35 * mm)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", font_sup)

        max_chars = max(10, int(config_diseno["ancho_mm"] * 0.70))
        lineas_sup_render = []
        for txt in sup_list:
            lineas_sup_render.append(txt[:max_chars])
            if len(txt) > max_chars and len(sup_list) == 1 and config_diseno["alto_mm"] >= 26:
                lineas_sup_render.append(txt[max_chars:max_chars * 2])

        for linea in lineas_sup_render[:2]:
            c.drawCentredString(x + ancho_etq / 2.0, cursor_y, linea)
            cursor_y -= (font_sup * 0.42 * mm)

        cursor_y_inf = y + pad_y + 0.5 * mm

        if precio_txt:
            c.setFont("Helvetica-Bold", font_pre)
            c.drawCentredString(x + ancho_etq / 2.0, cursor_y_inf, precio_txt)
            cursor_y_inf += (font_pre * 0.44 * mm)

        for linea in reversed(inf_list[:2]):
            c.setFont("Helvetica", font_inf)
            c.drawCentredString(x + ancho_etq / 2.0, cursor_y_inf, linea[:max_chars])
            cursor_y_inf += (font_inf * 0.42 * mm)

        if mostrar_txt_cod:
            c.setFont("Helvetica", font_cod)
            c.drawCentredString(x + ancho_etq / 2.0, cursor_y_inf, codigo_raw[:max_chars + 4])
            cursor_y_inf += (font_cod * 0.42 * mm)

        y_barra_inf = cursor_y_inf + 0.4 * mm
        y_barra_sup = cursor_y + 0.8 * mm
        alto_barras = max(5.2 * mm, y_barra_sup - y_barra_inf)

        if codigo_raw not in cache_barcodes:
            cache_barcodes[codigo_raw] = _generar_imagen_code128(codigo_raw, config_diseno["ancho_mm"])

        c.drawImage(
            cache_barcodes[codigo_raw],
            x + pad_x,
            y_barra_inf,
            width=ancho_util,
            height=alto_barras,
            preserveAspectRatio=False,
        )

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def enviar_a_impresora_windows(pdf_bytes: bytes, nombre_impresora: str):
    import win32api
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        ruta_pdf = tmp.name
    win32api.ShellExecute(0, "printto", ruta_pdf, f'"{nombre_impresora}"', ".", 0)


