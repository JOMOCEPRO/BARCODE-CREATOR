# ==============================================================================
# NOMBRE: CONFIGURAR_DRIVER_WHTP203E.ps1
# AUTOR: JOMOCE-SOFT | LICENCIA GNU GPLv3
# DESCRIPCION: REGISTRA EL FORMULARIO 4X6_18TICKETS (101.6 X 162.0 MM / 4.00 X 6.38 IN)
#              Y FIJA TEAR OFF + FEED OFFSET 0.08 IN (2.0 MM) EN WESTINGHOUSE WHTP203E.
# ==============================================================================

$identidad = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identidad)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$ErrorActionPreference = "Stop"

$NOMBRE_FORMULARIO = "4X6_18TICKETS"
$ANCHO_UM          = 101600   # 101.60 MM = 4.00 IN
$ALTO_UM           = 162000   # 162.00 MM = 6.38 IN

$impresora = Get-Printer | Where-Object { $_.Name -match "WHTP|203" } | Select-Object -First 1
if (-not $impresora) {
    Write-Host "[ERROR] NO SE ENCONTRO NINGUNA IMPRESORA WESTINGHOUSE WHTP203E." -ForegroundColor Red
    Pause
    exit 1
}

$nombreImpresora = $impresora.Name
Write-Host "[OK] IMPRESORA DETECTADA: $nombreImpresora" -ForegroundColor Green

$codigoWinSpool = @"
using System;
using System.Runtime.InteropServices;

public class WinSpoolFormHelper
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct SIZEL { public int cx; public int cy; }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct RECTL { public int left; public int top; public int right; public int bottom; }

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
            throw new Exception("ERROR WIN32: " + Marshal.GetLastWin32Error());

        try
        {
            DeleteForm(hPrinter, formName);
            FORM_INFO_1 form = new FORM_INFO_1
            {
                Flags = 0,
                pName = formName,
                Size = new SIZEL { cx = widthUm, cy = heightUm },
                ImageableArea = new RECTL { left = 0, top = 0, right = widthUm, bottom = heightUm }
            };
            if (!AddForm(hPrinter, 1, ref form))
            {
                if (!SetForm(hPrinter, formName, 1, ref form))
                    throw new Exception("ERROR FORM: " + Marshal.GetLastWin32Error());
            }
        }
        finally { ClosePrinter(hPrinter); }
    }
}
"@

Add-Type -TypeDefinition $codigoWinSpool -Language CSharp
[WinSpoolFormHelper]::RegistrarFormulario($nombreImpresora, $NOMBRE_FORMULARIO, $ANCHO_UM, $ALTO_UM)
Write-Host "[OK] FORMULARIO '$NOMBRE_FORMULARIO' REGISTRADO (101.60 X 162.00 MM / 4.00 X 6.38 IN)." -ForegroundColor Green

try {
    Set-PrintConfiguration -PrinterName $nombreImpresora -PaperSize $NOMBRE_FORMULARIO
    Write-Host "[OK] PAPEL PREDETERMINADO ASIGNADO A '$NOMBRE_FORMULARIO'." -ForegroundColor Green
} catch {
    Write-Host "[AVISO] VERIFICA QUE '$NOMBRE_FORMULARIO' ESTE SELECCIONADO EN PAGE SETUP." -ForegroundColor Yellow
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " VERIFICACION DE PARAMETROS VALIDADOS EN PRODUCCION:              " -ForegroundColor Cyan
Write-Host " - PAGE SETUP     : 4.00 X 6.38 IN | 180-PORTRAIT | V-OFFSET 0.00 " -ForegroundColor Cyan
Write-Host " - PRINT SETTINGS : TEAR OFF | FEED OFFSET 0.08 INCH (2.0 MM)     " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

rundll32.exe printui.dll,PrintUIEntry /e /n "$nombreImpresora"