$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identidad)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ErrorActionPreference = "Stop"
$NOMBRE_FORMULARIO = "4X6_18TICKETS"
$ANCHO_UM          = 101600
$ALTO_UM           = 162000
$ORIENTACION_180   = $true

$impresora = Get-Printer | Where-Object { $_.Name -match "WHTP|203" } | Select-Object -First 1
if (-not $impresora) {
    Write-Host "[ERROR] NO SE ENCONTRO IMPRESORA WESTINGHOUSE WHTP203E." -ForegroundColor Red
    Pause
    exit 1
}

$nombreImpresora = $impresora.Name

$codigoWinSpool = @"
using System;
using System.Runtime.InteropServices;
public class WinSpoolFormHelper {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct SIZEL { public int cx; public int cy; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct RECTL { public int left; public int top; public int right; public int bottom; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct FORM_INFO_1 { public uint Flags; [MarshalAs(UnmanagedType.LPWStr)] public string pName; public SIZEL Size; public RECTL ImageableArea; }
    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);
    [DllImport("winspool.drv", SetLastError = true)] public static extern bool ClosePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool AddForm(IntPtr hPrinter, int Level, ref FORM_INFO_1 pForm);
    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool SetForm(IntPtr hPrinter, string pFormName, int Level, ref FORM_INFO_1 pForm);
    [DllImport("winspool.drv", SetLastError = true, CharSet = CharSet.Unicode)] public static extern bool DeleteForm(IntPtr hPrinter, string pFormName);
    public static void RegistrarFormulario(string printerName, string formName, int widthUm, int heightUm) {
        IntPtr hPrinter;
        if (!OpenPrinter(printerName, out hPrinter, IntPtr.Zero)) throw new Exception("ERROR WIN32: " + Marshal.GetLastWin32Error());
        try {
            DeleteForm(hPrinter, formName);
            FORM_INFO_1 form = new FORM_INFO_1 { Flags = 0, pName = formName, Size = new SIZEL { cx = widthUm, cy = heightUm }, ImageableArea = new RECTL { left = 0, top = 0, right = widthUm, bottom = heightUm } };
            if (!AddForm(hPrinter, 1, ref form)) { if (!SetForm(hPrinter, formName, 1, ref form)) throw new Exception("ERROR FORM: " + Marshal.GetLastWin32Error()); }
        } finally { ClosePrinter(hPrinter); }
    }
}
"@

Add-Type -TypeDefinition $codigoWinSpool -Language CSharp
[WinSpoolFormHelper]::RegistrarFormulario($nombreImpresora, $NOMBRE_FORMULARIO, $ANCHO_UM, $ALTO_UM)

$rutaRegBase = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Printers\$nombreImpresora"
try { Set-PrintConfiguration -PrinterName $nombreImpresora -PaperSize $NOMBRE_FORMULARIO } catch {}

$regImpresora = Get-ItemProperty -Path $rutaRegBase
if ($regImpresora.'Default DevMode') {
    [byte[]]$devMode = $regImpresora.'Default DevMode'
    if ($devMode.Length -ge 134) {
        $bytesNombre = [System.Text.Encoding]::Unicode.GetBytes($NOMBRE_FORMULARIO.PadRight(32, "`0"))
        [Array]::Copy($bytesNombre, 0, $devMode, 70, 64)
        [Array]::Copy([BitConverter]::GetBytes([Int16]1), 0, $devMode, 44, 2)
        [Array]::Copy([BitConverter]::GetBytes([Int16]1620), 0, $devMode, 48, 2)
        [Array]::Copy([BitConverter]::GetBytes([Int16]1016), 0, $devMode, 50, 2)
        [Array]::Copy([BitConverter]::GetBytes([Int16]100), 0, $devMode, 52, 2)
        [Array]::Copy([BitConverter]::GetBytes([Int16]203), 0, $devMode, 58, 2)
        Set-ItemProperty -Path $rutaRegBase -Name "Default DevMode" -Value $devMode
    }
}

$rutaDriverData = Join-Path $rutaRegBase "PrinterDriverData"
if (Test-Path $rutaDriverData) {
    $props = Get-ItemProperty -Path $rutaDriverData
    if ($null -ne $props.Rotate180) { Set-ItemProperty -Path $rutaDriverData -Name "Rotate180" -Value ([int]$ORIENTACION_180) }
    if ($null -ne $props.Orientation) { Set-ItemProperty -Path $rutaDriverData -Name "Orientation" -Value $(if ($ORIENTACION_180) { 2 } else { 0 }) }
    if ($null -ne $props.PageWidth) { Set-ItemProperty -Path $rutaDriverData -Name "PageWidth" -Value 1016 }
    if ($null -ne $props.PageHeight) { Set-ItemProperty -Path $rutaDriverData -Name "PageHeight" -Value 1620 }
    if ($null -ne $props.MediaType) { Set-ItemProperty -Path $rutaDriverData -Name "MediaType" -Value 0 }
}

Restart-Service -Name Spooler -Force
Start-Sleep -Seconds 2
Write-Host "[OK] CONFIGURACION COMPLETADA PARA $nombreImpresora ($NOMBRE_FORMULARIO)" -ForegroundColor Green
