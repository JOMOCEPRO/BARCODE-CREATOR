; ==============================================================================
; INSTALADOR DE PRODUCCION: BARCODE-CREATOR (CON PERFIL WHTP203E INTEGRADO)
; AUTOR: JOMOCE-SOFT | LICENCIA: GNU GPLv3
; ==============================================================================

#define MyAppName "BARCODE-CREATOR"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "JOMOCE-SOFT"
#define MyAppURL "https://github.com/JOMOCEPRO/BARCODE-CREATOR"
#define MyAppExeName "BARCODE-CREATOR.exe"

[Setup]
AppId={{8E4F2A91-6C3D-4B18-9F52-1A7D90E4B3C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppPublisher}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}\{#MyAppName}
AllowNoIcons=yes
OutputDir=C:\BARCODE-CREATOR\release
OutputBaseFilename=Setup_BARCODE-CREATOR_v{#MyAppVersion}_JOMOCE-SOFT
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce
Name: "startupicon"; Description: "Iniciar automáticamente en la bandeja del sistema (System Tray) al arrancar Windows"; GroupDescription: "Inicio con Windows:"; Flags: checkedonce
Name: "implantarwhtp"; Description: "Implantar configuración calibrada de impresora Westinghouse WHTP203e (4X6_18TICKETS, 180-Portrait, Offset 0.08 in)"; GroupDescription: "Calibración de Impresora:"; Flags: checkedonce

[Files]
Source: "C:\BARCODE-CREATOR\dist\PROD_BUNDLE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\BARCODE-CREATOR\PERFIL_CLON_WHTP203E\*"; DestDir: "{app}\PERFIL_CLON_WHTP203E"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Implantar Perfil Calibrado Westinghouse WHTP203e"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\PERFIL_CLON_WHTP203E\IMPLANTAR_CONFIG_WHTP203E.ps1"""
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BARCODE_CREATOR_JOMOCESOFT"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\PERFIL_CLON_WHTP203E\IMPLANTAR_CONFIG_WHTP203E.ps1"""; StatusMsg: "Implantando perfil calibrado Westinghouse WHTP203e..."; Flags: runhidden waituntilterminated; Tasks: implantarwhtp
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName} en la bandeja del sistema ahora"; Flags: nowait postinstall skipifsilent