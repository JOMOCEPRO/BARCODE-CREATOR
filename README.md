# BARCODE-CREATOR | JOMOCE-SOFT

Sistema de escritorio portable (*local-first*) en Python, Streamlit y SQLite con esquema dinamico a medida para la generacion e impresion por lotes de etiquetas **Code 128** sobre hojas termicas de **4 x 6 pulgadas** (203 DPI - Westinghouse WHTP203e).

## Caracteristicas
- Esquema SQLite dinamico (DROP/CREATE/ALTER) adaptado automaticamente a las columnas del archivo Excel/CSV importado.
- Generacion vectorial de PDF a escala 1:1 con ReportLab, cuadriculas predefinidas o personalizadas y guias de corte.
- Ejecucion en segundo plano desde System Tray (pystray) e impresion directa en Windows (win32print).

## Licencia
Desarrollado por **JOMOCE-SOFT** (Jose Luis Molina Ceballos) bajo licencia **GNU GPLv3**.
