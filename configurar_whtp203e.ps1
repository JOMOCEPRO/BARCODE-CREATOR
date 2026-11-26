# ==============================================================================
# SCRIPT: configurar_whtp203e.ps1
# AUTOR: JOMOCE-SOFT (LICENCIA GNU)
# PROPOSITO: REGISTRAR Y ASIGNAR FORMULARIO PERSONALIZADO 3COL_32X25MM
#            (102 X 25 MM) VIA DEVMODE NATIVO EN WESTINGHOUSE WHTP203E
# ==============================================================================

# ==============================================================================
# NOMBRE: CONFIGURAR_DRIVER_WHTP203E.ps1
# AUTOR: JOMOCE-SOFT | LICENCIA GNU GPLv3
# DESCRIPCION: CONFIGURA AUTOMATICAMENTE EL FORMULARIO DE PAPEL (101.6 X 162.0 MM /
#              4.00 X 6.38 IN), ORIENTACION Y PARAMETROS DEL DRIVER WESTINGHOUSE
#              WHTP203E EN WINDOWS 11 PRO PARA IMPRESION DE 18 TICKETS (3 X 6).
# ==============================================================================

# 1. AUTO-ELEVACION A ADMINISTRADOR SI NO SE EJECUTA CON PRIVILEGIOS
$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identidad)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[INFO] SOLICITANDO PERMISOS DE ADMINISTRADOR..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ErrorActionPreference = "Stop"

# PARAMETROS EXACTOS VALIDADOS EN PRODUCCION
$NOMBRE_FORMULARIO = "4X6_18TICKETS"
$ANCHO_UM          = 101600   # 101.60 MM = 4.00 PULGADAS (EN MILESIMAS DE MILIMETRO)
$ALTO_UM           = 162000   # 162.00 MM = 6.38 PULGADAS (EVITA RECORTE EN FILA 6)
$ORIENTACION_180   = $true    # CAMBIAR A $false SI EL ROLLO SALE DE ARRIBA HACIA ABAJO SIN INVERTIR

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " CONFIGURADOR AUTOMATICO DE CONTROLADOR - WESTINGHOUSE WHTP203E   " -ForegroundColor Cyan
Write-Host " DESARROLLADO POR JOMOCE-SOFT | LICENCIA GNU GPLv3                " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 2. DETECTAR IMPRESORA WHTP203E INSTALADA
$impresora = Get-Printer | Where-Object { $_.Name -match "WHTP|203" } | Select-Object -First 1
if (-not $impresora) {
    Write-Host "[ERROR] NO SE ENCONTRO NINGUNA IMPRESORA WESTINGHOUSE WHTP203E INSTALADA." -ForegroundColor Red
    Pause
    exit 1
}

$nombreImpresora = $impresora.Name
Write-Host "[OK] IMPRESORA DETECTADA: $nombreImpresora" -ForegroundColor Green

# 3. DEFINIR INTEROP CON WINSPOOL.DRV PARA REGISTRAR FORMULARIO DE PAPEL EN WINDOWS
$codigoWinSpool = @"
using System;
using System.Runtime.InteropServices;

public class WinSpoolFormHelper
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct SIZEL
    {
        public int cx;
        public int cy;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct RECTL
    {
        public int left;
        public int top;
        public int right;
        public int bottom;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct FORM_INFO_1
    {
        public uint Flags;
        [MarshalAs(UnmanagedType.LPWStr)]
        public string pName;
        public SIZEL Size;
        public RECTL ImageableArea;
    }

    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);

    [DllImport("winspool.drv", SetLastError = true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);

    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool AddForm(IntPtr hPrinter, int Level, ref FORM_INFO_1 pForm);

    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool SetForm(IntPtr hPrinter, string pFormName, int Level, ref FORM_INFO_1 pForm);

    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool DeleteForm(IntPtr hPrinter, string pFormName);

    public static void RegistrarFormulario(string printerName, string formName, int widthUm, int heightUm)
    {
        IntPtr hPrinter;
        if (!OpenPrinter(printerName, out hPrinter, IntPtr.Zero))
            throw new Exception("NO SE PUDO ABRIR LA IMPRESORA. CODIGO WIN32: " + Marshal.GetLastWin32Error());

        try
        {
            DeleteForm(hPrinter, formName);

            FORM_INFO_1 form = new FORM_INFO_1();
            form.Flags = 0; // FORM_USER
            form.pName = formName;
            form.Size = new SIZEL { cx = widthUm, cy = heightUm };
            form.ImageableArea = new RECTL { left = 0, top = 0, right = widthUm, bottom = heightUm };

            if (!AddForm(hPrinter, 1, ref form))
            {
                if (!SetForm(hPrinter, formName, 1, ref form))
                    throw new Exception("NO SE PUDO REGISTRAR EL FORMULARIO. CODIGO WIN32: " + Marshal.GetLastWin32Error());
            }
        }
        finally
        {
            ClosePrinter(hPrinter);
        }
    }
}
"@

Add-Type -TypeDefinition $codigoWinSpool -Language CSharp

# 4. REGISTRAR FORMULARIO PERSONALIZADO 4X6_18TICKETS (101.6 MM X 162.0 MM)
[WinSpoolFormHelper]::RegistrarFormulario($nombreImpresora, $NOMBRE_FORMULARIO, $ANCHO_UM, $ALTO_UM)
Write-Host "[OK] FORMULARIO '$NOMBRE_FORMULARIO' REGISTRADO (101.60 MM X 162.00 MM / 4.00 X 6.38 IN)." -ForegroundColor Green

# 5. RESPALDAR CONFIGURACION ACTUAL DEL REGISTRO DE LA IMPRESORA
$rutaRegBase = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Printers\$nombreImpresora"
$carpetaBackup = Join-Path $PSScriptRoot "BACKUP_DRIVER_WHTP203E"
if (-not (Test-Path $carpetaBackup)) {
    New-Item -ItemType Directory -Path $carpetaBackup | Out-Null
}
$archivoRegBackup = Join-Path $carpetaBackup ("RESPALDO_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".reg")
reg export "HKLM\SYSTEM\CurrentControlSet\Control\Print\Printers\$nombreImpresora" "$archivoRegBackup" /y | Out-Null
Write-Host "[OK] RESPALDO DE REGISTRO GUARDADO EN: $archivoRegBackup" -ForegroundColor Green

# 6. APLICAR FORMULARIO PREDETERMINADO EN EL SUBSISTEMA DE IMPRESION DE WINDOWS
try {
    Set-PrintConfiguration -PrinterName $nombreImpresora -PaperSize $NOMBRE_FORMULARIO
    Write-Host "[OK] TAMANO DE PAPEL PREDETERMINADO ASIGNADO A '$NOMBRE_FORMULARIO'." -ForegroundColor Green
} catch {
    Write-Host "[AVISO] SET-PRINTCONFIGURATION REQUIRIO AJUSTE DIRECTO EN DEVMODE: $_" -ForegroundColor Yellow
}

# 7. ACTUALIZAR BINARIO DEFAULT DEVMODE (ANCHO = 1016, ALTO = 1620 EN DECIMAS DE MM, PORTRAIT)
$regImpresora = Get-ItemProperty -Path $rutaRegBase
if ($regImpresora.'Default DevMode') {
    [byte[]]$devMode = $regImpresora.'Default DevMode'
    if ($devMode.Length -ge 72) {
        # dmFormName (32 WCHARs = 64 BYTES EN OFFSET 70 EN DEVMODEW)
        $bytesNombre = [System.Text.Encoding]::Unicode.GetBytes($NOMBRE_FORMULARIO.PadRight(32, "`0"))
        if ($devMode.Length -ge 134) {
            [Array]::Copy($bytesNombre, 0, $devMode, 70, 64)
        }

        # dmOrientation (OFFSET 44, INT16): 1 = PORTRAIT
        [Array]::Copy([BitConverter]::GetBytes([Int16]1), 0, $devMode, 44, 2)

        # dmPaperLength (OFFSET 48, INT16 EN DECIMAS DE MM): 1620 = 162.0 MM
        [Array]::Copy([BitConverter]::GetBytes([Int16]1620), 0, $devMode, 48, 2)

        # dmPaperWidth (OFFSET 50, INT16 EN DECIMAS DE MM): 1016 = 101.6 MM
        [Array]::Copy([BitConverter]::GetBytes([Int16]1016), 0, $devMode, 50, 2)

        # dmScale (OFFSET 52, INT16): 100%
        [Array]::Copy([BitConverter]::GetBytes([Int16]100), 0, $devMode, 52, 2)

        # dmPrintQuality (OFFSET 58, INT16): 203 DPI
        [Array]::Copy([BitConverter]::GetBytes([Int16]203), 0, $devMode, 58, 2)

        Set-ItemProperty -Path $rutaRegBase -Name "Default DevMode" -Value $devMode
        Write-Host "[OK] DEFAULT DEVMODE ACTUALIZADO (101.6 X 162.0 MM | 203 DPI | ESCALA 100%)." -ForegroundColor Green
    }
}

# 8. AJUSTAR PARAMETROS INTERNOS DEL DRIVER TERMICO (PrinterDriverData) SI EXISTEN
$rutaDriverData = Join-Path $rutaRegBase "PrinterDriverData"
if (Test-Path $rutaDriverData) {
    $props = Get-ItemProperty -Path $rutaDriverData

    # SINCRONIZAR PROPIEDADES COMUNES DE DRIVERS TERMICOS TSPL / WESTINGHOUSE
    if ($null -ne $props.Rotate180) {
        Set-ItemProperty -Path $rutaDriverData -Name "Rotate180" -Value ([int]$ORIENTACION_180)
    }
    if ($null -ne $props.Orientation) {
        Set-ItemProperty -Path $rutaDriverData -Name "Orientation" -Value $(if ($ORIENTACION_180) { 2 } else { 0 })
    }
    if ($null -ne $props.PageWidth) {
        Set-ItemProperty -Path $rutaDriverData -Name "PageWidth" -Value 1016
    }
    if ($null -ne $props.PageHeight) {
        Set-ItemProperty -Path $rutaDriverData -Name "PageHeight" -Value 1620
    }
    if ($null -ne $props.MediaType) {
        # 0 = LABEL WITH GAPS (ETIQUETA TROQUELADA CON SEPARACION)
        Set-ItemProperty -Path $rutaDriverData -Name "MediaType" -Value 0
    }
    Write-Host "[OK] PARAMETROS DE PRINTERDRIVERDATA SINCRONIZADOS (MEDIA CON GAPS + ORIENTACION)." -ForegroundColor Green
}

# 9. REINICIAR COLA DE IMPRESION (SPOOLER) PARA APLICAR CAMBIOS EN CALIENTE
Write-Host "[INFO] REINICIANDO SERVICIO DE COLA DE IMPRESION (SPOOLER)..." -ForegroundColor Cyan
Restart-Service -Name Spooler -Force
Start-Sleep -Seconds 2

# 10. EXPORTAR INSTANTANEA FINAL DE CONFIGURACION PARA REPLICACION EN OTROS PC
$archivoSnapshot = Join-Path $carpetaBackup "CONFIGURACION_FINAL_WHTP203E.reg"
reg export "HKLM\SYSTEM\CurrentControlSet\Control\Print\Printers\$nombreImpresora" "$archivoSnapshot" /y | Out-Null

Write-Host "==================================================================" -ForegroundColor Green
Write-Host " CONFIGURACION COMPLETADA EXITOSAMENTE                            " -ForegroundColor Green
Write-Host " - IMPRESORA : $nombreImpresora                                   " -ForegroundColor Green
Write-Host " - PAPEL     : $NOMBRE_FORMULARIO (101.60 MM X 162.00 MM)         " -ForegroundColor Green
Write-Host " - SNAPSHOT  : $archivoSnapshot" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green

# ABRIR PREFERENCIAS DE IMPRESION PARA VERIFICACION VISUAL OPCIONAL
rundll32.exe printui.dll,PrintUIEntry /e /n "$nombreImpresora"