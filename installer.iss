; installer.iss — Script de Inno Setup para SISFE Monitor
; Descarga Inno Setup en: https://jrsoftware.org/isinfo.php
; Compilar: abrí este .iss en Inno Setup y presioná F9

#define MyAppName      "SISFE Monitor"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "BE LEGAL"
#define MyAppExeName   "SISFEMonitor.exe"
#define MyAppURL       "https://github.com/estanijd/sisfe-monitor-releases"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=SISFE_Monitor_Setup_v{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
; Mostrar bienvenida con logo
WizardImageFile=assets\wizard_banner.bmp
WizardSmallImageFile=assets\icon_small.bmp

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
; Textos personalizados en español
WelcomeLabel1=Bienvenido al instalador de {#MyAppName}
WelcomeLabel2=Este asistente instalará {#MyAppName} en tu computadora.%n%nAl finalizar, se abrirá automáticamente para que lo configures.%n%nTiempo estimado: 2-3 minutos.
FinishedLabel=La instalación de {#MyAppName} fue completada exitosamente.%n%nHacé clic en Finalizar para abrir la configuración inicial.

[Tasks]
Name: "desktopicon";  Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: checked
Name: "startupicon";  Description: "Iniciar SISFE Monitor con Windows (recomendado)"; GroupDescription: "Inicio automático:"; Flags: checked

[Files]
; Todos los archivos compilados por PyInstaller
Source: "dist\SISFEMonitor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Configuración";             Filename: "{app}\{#MyAppExeName}"; Parameters: "--config"
Name: "{group}\Enviar email de prueba";    Filename: "{app}\{#MyAppExeName}"; Parameters: "--test-email"
Name: "{group}\Desinstalar {#MyAppName}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Iniciar con Windows
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run";
  ValueType: string; ValueName: "SISFEMonitor";
  ValueData: """{app}\{#MyAppExeName}""";
  Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Paso 1: Instalar Playwright Chromium (con barra de progreso)
Filename: "{app}\{#MyAppExeName}";
  Parameters: "--install-browser";
  StatusMsg: "Instalando navegador (puede tardar 1-2 minutos, por favor esperá)...";
  Flags: runhidden waituntilterminated;
  Check: not IsUpgrade

; Paso 2: Abrir wizard de configuracion al terminar
Filename: "{app}\{#MyAppExeName}";
  Parameters: "--config";
  Description: "Abrir configuración inicial de {#MyAppName}";
  Flags: postinstall nowait skipifsilent

[UninstallRun]
; Eliminar todas las tareas del Programador de tareas al desinstalar
Filename: "schtasks.exe"; Parameters: "/delete /tn ""SISFE_Check_01*"" /f"; Flags: runhidden; RunOnceId: "DelTask01"
Filename: "schtasks.exe"; Parameters: "/delete /tn ""SISFE_Check_02*"" /f"; Flags: runhidden; RunOnceId: "DelTask02"
Filename: "schtasks.exe"; Parameters: "/delete /tn ""SISFE_Check_03*"" /f"; Flags: runhidden; RunOnceId: "DelTask03"
Filename: "schtasks.exe"; Parameters: "/delete /tn ""SISFE_Check_04*"" /f"; Flags: runhidden; RunOnceId: "DelTask04"
Filename: "schtasks.exe"; Parameters: "/delete /tn ""SISFE_Check_05*"" /f"; Flags: runhidden; RunOnceId: "DelTask05"
Filename: "schtasks.exe"; Parameters: "/delete /tn ""SISFE_Resumen_Semanal"" /f"; Flags: runhidden; RunOnceId: "DelTaskSem"

[UninstallDelete]
; Borrar el archivo de configuracion del usuario al desinstalar
Type: files; Name: "{userappdata}\SISFEMonitor\config.json"
Type: dirifempty; Name: "{userappdata}\SISFEMonitor"

[Code]
function IsUpgrade(): Boolean;
begin
  Result := RegKeyExists(HKLM,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1');
end;

// Mostrar mensaje personalizado si la instalacion anterior se detecta
function InitializeSetup(): Boolean;
begin
  Result := True;
  if IsUpgrade() then begin
    MsgBox(
      'Se detectó una versión anterior de SISFE Monitor.' + #13#10 +
      'La actualización mantendrá tu configuración existente.',
      mbInformation, MB_OK
    );
  end;
end;
