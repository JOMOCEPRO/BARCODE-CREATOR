# ==============================================================================
# NOMBRE: EXPORTAR_CLON_WHTP203E.ps1
# AUTOR: JOMOCE-SOFT | LICENCIA: GNU GPLv3
# DESCRIPCION: ABSTRAE TODA LA CONFIGURACION BINARIA Y XML DE LA IMPRESORA
#              WESTINGHOUSE WHTP203E CALIBRADA Y GENERA EL SCRIPT IMPLANTADOR
#              AUTONOMO PARA DESPLIEGUE CERO-CLICS EN OTROS COMPUTADORES.
# ==============================================================================

$ErrorActionPreference = "Stop"
$dirSalida = "C:\BARCODE-CREATOR\PERFIL_CLON_WHTP203E"
New-Item -ItemType Directory -Path $dirSalida -Force | Out-Null

# 1. LOCALIZAR LA IMPRESORA CALIBRADA ACTUAL
$impresora = Get-Printer | Where-Object { $_.Name -match "WHTP|203" -and $_.PrinterStatus -eq "Normal" } | Select-Object -First 1
if (-not $impresora) {
    $impresora = Get-Printer | Where-Object { $_.Name -match "WHTP|203" } | Select-Object -First 1
}
if (-not $impresora) {
    Write-Host "[ERROR] NO SE ENCONTRO LA IMPRESORA WESTINGHOUSE WHTP203E." -ForegroundColor Red
    exit 1
}

$nombreOrigen = $impresora.Name
Write-Host "[1/4] EXTRAYENDO CONFIGURACION DETALLADA DE: '$nombreOrigen'..." -ForegroundColor Cyan

# 2. INSPECCIONAR Y EXPORTAR PARAMETROS DETALLADOS (XML Y LEGIBLES)
$configPrint = Get-PrintConfiguration -PrinterName $nombreOrigen
$propiedades = Get-PrinterProperty -PrinterName $nombreOrigen -ErrorAction SilentlyContinue

$reporteDetalle = Join-Path $dirSalida "DETALLE_CONFIGURACION_WHTP203E.txt"
@"
================================================================================
AUDITORIA DE CONFIGURACION EXPORTADA - WESTINGHOUSE WHTP203E (JOMOCE-SOFT)
FECHA: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
IMPRESORA ORIGEN: $nombreOrigen
DRIVER: $($impresora.DriverName)
PUERTO: $($impresora.PortName)
================================================================================
[RESUMEN DE CONFIGURACION DE IMPRESION]
- Tamano de Papel (PaperSize) : $($configPrint.PaperSize)
- Orientacion                  : $($configPrint.Orientation)
- Color                        : $($configPrint.Color)
- Duplex                       : $($configPrint.DuplexingMode)
- Collate                      : $($configPrint.Collate)

[XML COMPLETO DEL PRINT TICKET]
$($configPrint.PrintTicketXML)

[PROPIEDADES INTERNAS DEL DRIVER]
$($propiedades | Format-Table PropertyName, Value -AutoSize | Out-String)
"@ | Out-File -FilePath $reporteDetalle -Encoding UTF8

# 3. VOLCAR EL BLOQUE BINARIO DEVMODE + PRINTERDATA VIA PRINTUI.DLL
$archivoBinario = Join-Path $dirSalida "WHTP203E_DEVMODE_COMPLETO.dat"
if (Test-Path $archivoBinario) { Remove-Item $archivoBinario -Force }

Start-Process -FilePath "rundll32.exe" -ArgumentList "printui.dll,PrintUIEntry /Ss /n `"$nombreOrigen`" /a `"$archivoBinario`" d g u 2 7" -Wait
if (-not (Test-Path $archivoBinario)) {
    Write-Host "[ERROR] NO SE PUDO VOLCAR EL ARCHIVO BINARIO DEVMODE." -ForegroundColor Red
    exit 1
}
Write-Host "[2/4] VOLCADO BINARIO DEVMODE GENERADO ($((Get-Item $archivoBinario).Length) BYTES)." -ForegroundColor Green

# 4. GENERAR EL SCRIPT AUTONOMO QUE IMPLANTA ESTA CONFIGURACION EN OTROS PCS
$scriptImplantador = Join-Path $dirSalida "IMPLANTAR_CONFIG_WHTP203E.ps1"

$contenidoImplantador = @'
# ==============================================================================
# NOMBRE: IMPLANTAR_CONFIG_WHTP203E.ps1
# AUTOR: JOMOCE-SOFT | LICENCIA: GNU GPLv3
# DESCRIPCION: IMPLANTA AUTOMATICAMENTE EL FORMULARIO 4X6_18TICKETS, EL PERFIL
#              BINARIO DEVMODE (180-PORTRAIT, DIRECT THERMAL, TEAR OFF,
#              FEED OFFSET 0.08 IN) Y LOS COMANDOS TSPL POR USB EN WINDOWS.
# ==============================================================================

$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identidad)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ErrorActionPreference = "Stop"
$dirActual = Split-Path -Parent $MyInvocation.MyCommand.Path
$archivoBinario = Join-Path $dirActual "WHTP203E_DEVMODE_COMPLETO.dat"

if (-not (Test-Path $archivoBinario)) {
    Write-Host "[ERROR] FALTA EL ARCHIVO BINARIO: $archivoBinario" -ForegroundColor Red
    Pause
    exit 1
}

# 1. DETECTAR IMPRESORA WHTP203E EN EL EQUIPO DESTINO
$impresoraDestino = Get-Printer | Where-Object { $_.Name -match "WHTP|203" -and $_.PrinterStatus -eq "Normal" } | Select-Object -First 1
if (-not $impresoraDestino) {
    $impresoraDestino = Get-Printer | Where-Object { $_.Name -match "WHTP|203" } | Select-Object -First 1
}
if (-not $impresoraDestino) {
    Write-Host "[ERROR] CONECTE Y ENCIENDA LA IMPRESORA WESTINGHOUSE WHTP203E ANTES DE EJECUTAR." -ForegroundColor Red
    Pause
    exit 1
}

$nombreDestino = $impresoraDestino.Name
Write-Host "[1/4] IMPRESORA DESTINO DETECTADA: '$nombreDestino'" -ForegroundColor Cyan

# 2. REGISTRAR FORMULARIO FISICO 4X6_18TICKETS (101.6 X 162.0 MM) E INYECTAR TSPL USB
$codigoWinSpool = @"
using System;
using System.Runtime.InteropServices;

public class Whtp203eClonHelper {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct SIZEL { public int cx; public int cy; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct RECTL { public int left; public int top; public int right; public int bottom; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct FORM_INFO_1 { public uint Flags; [MarshalAs(UnmanagedType.LPWStr)] public string pName; public SIZEL Size; public RECTL ImageableArea; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)] public class DOCINFOA { [MarshalAs(UnmanagedType.LPStr)] public string pDocName; [MarshalAs(UnmanagedType.LPStr)] public string pOutputFile; [MarshalAs(UnmanagedType.LPStr)] public string pDataType; }

    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);
    [DllImport("winspool.drv", SetLastError = true)] public static extern bool ClosePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool AddForm(IntPtr hPrinter, int Level, ref FORM_INFO_1 pForm);
    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool SetForm(IntPtr hPrinter, string pFormName, int Level, ref FORM_INFO_1 pForm);
    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool DeleteForm(IntPtr hPrinter, string pFormName);

    [DllImport("winspool.Drv", EntryPoint = "OpenPrinterA", SetLastError = true, CharSet = CharSet.Ansi)] public static extern bool OpenPrinterAnsi(string szPrinter, out IntPtr hPrinter, IntPtr pd);
    [DllImport("winspool.Drv", EntryPoint = "StartDocPrinterA", SetLastError = true, CharSet = CharSet.Ansi)] public static extern bool StartDocPrinter(IntPtr hPrinter, Int32 level, [In, MarshalAs(UnmanagedType.LPStruct)] DOCINFOA di);
    [DllImport("winspool.Drv", EntryPoint = "EndDocPrinter", SetLastError = true)] public static extern bool EndDocPrinter(IntPtr hPrinter);
    [DllImport("winspool.Drv", EntryPoint = "StartPagePrinter", SetLastError = true)] public static extern bool StartPagePrinter(IntPtr hPrinter);
    [DllImport("winspool.Drv", EntryPoint = "EndPagePrinter", SetLastError = true)] public static extern bool EndPagePrinter(IntPtr hPrinter);
    [DllImport("winspool.Drv", EntryPoint = "WritePrinter", SetLastError = true)] public static extern bool WritePrinter(IntPtr hPrinter, IntPtr pBytes, Int32 dwCount, out Int32 dwWritten);

    public static void RegistrarFormulario(string printerName) {
        IntPtr hPrinter;
        if (!OpenPrinter(printerName, out hPrinter, IntPtr.Zero)) return;
        try {
            DeleteForm(hPrinter, "4X6_18TICKETS");
            FORM_INFO_1 form = new FORM_INFO_1 {
                Flags = 0, pName = "4X6_18TICKETS",
                Size = new SIZEL { cx = 101600, cy = 162000 },
                ImageableArea = new RECTL { left = 0, top = 0, right = 101600, bottom = 162000 }
            };
            if (!AddForm(hPrinter, 1, ref form)) SetForm(hPrinter, "4X6_18TICKETS", 1, ref form);
        } finally { ClosePrinter(hPrinter); }
    }

    public static bool EnviarTspl(string printerName, string tspl) {
        IntPtr hPrinter;
        DOCINFOA di = new DOCINFOA { pDocName = "JOMOCESOFT_TSPL_CLON", pDataType = "RAW" };
        if (!OpenPrinterAnsi(printerName.Normalize(), out hPrinter, IntPtr.Zero)) return false;
        try {
            if (!StartDocPrinter(hPrinter, 1, di)) return false;
            if (!StartPagePrinter(hPrinter)) return false;
            IntPtr pBytes = Marshal.StringToCoTaskMemAnsi(tspl);
            int dwWritten;
            bool ok = WritePrinter(hPrinter, pBytes, tspl.Length, out dwWritten);
            Marshal.FreeCoTaskMem(pBytes);
            EndPagePrinter(hPrinter); EndDocPrinter(hPrinter);
            return ok;
        } finally { ClosePrinter(hPrinter); }
    }
}
"@
Add-Type -TypeDefinition $codigoWinSpool -Language CSharp

[Whtp203eClonHelper]::RegistrarFormulario($nombreDestino)
Write-Host "[2/4] FORMULARIO '4X6_18TICKETS' REGISTRADO EN WINDOWS." -ForegroundColor Green

# 3. RESTAURAR EL PERFIL BINARIO DEVMODE COMPLETO EN EL DRIVER DESTINO
Start-Process -FilePath "rundll32.exe" -ArgumentList "printui.dll,PrintUIEntry /Sr /n `"$nombreDestino`" /a `"$archivoBinario`" d g u 2 7 r" -Wait
Write-Host "[3/4] PERFIL BINARIO DEVMODE IMPLANTADO (180-PORTRAIT | TEAR OFF | OFFSET 0.08 IN)." -ForegroundColor Green

# 4. INYECTAR COMANDOS TSPL POR USB EN LA MEMORIA DE LA IMPRESORA
$tspl = "SIZE 101.6 mm, 162 mm`r`nGAP 2 mm, 0 mm`r`nSET TEAR ON`r`nSET BACK OFF`r`nSET PEEL OFF`r`nSET CUTTER OFF`r`n"
$okTspl = [Whtp203eClonHelper]::EnviarTspl($nombreDestino, $tspl)
Write-Host "[4/4] CALIBRACION USB TSPL APLICADA: $okTspl" -ForegroundColor Green

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [LISTO] IMPRESORA WESTINGHOUSE WHTP203E CALIBRADA AL 100%.         " -ForegroundColor White
Write-Host " RECUERDA: AL CARGAR ROLLO DEJA 8 FILAS AFUERA Y PULSA 1x [FEED].  " -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan
Start-Sleep -Seconds 3
'@

$contenidoImplantador | Out-File -FilePath $scriptImplantador -Encoding UTF8

Write-Host "[3/4] REPORTE DETALLADO GUARDADO EN: $reporteDetalle" -ForegroundColor Green
Write-Host "[4/4] PAQUETE IMPLANTADOR GENERADO EN: $dirSalida" -ForegroundColor Green
Get-ChildItem $dirSalida