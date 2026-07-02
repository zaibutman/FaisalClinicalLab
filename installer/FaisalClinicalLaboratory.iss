; ============================================================================
; Faisal Clinical Laboratory - Inno Setup installer (Task R2)
;
; Installs the complete PyInstaller onedir build produced by Task R1
; (dist\FaisalClinicalLaboratory\) into Program Files, creates shortcuts and
; an uninstaller, and PRESERVES user data across upgrades:
;   * data\settings.json  (laboratory branding + report numbering)
;   * reports\            (saved reports)
;
; This script installs files only. It does not modify application code.
; ============================================================================

#define MyAppName "Faisal Clinical Laboratory"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "Faisal Clinical Laboratory"
#define MyAppExeName "FaisalClinicalLaboratory.exe"
; Source of the onedir build, relative to this .iss (installer\ -> project root).
#define MySourceDir "..\dist\FaisalClinicalLaboratory"

[Setup]
; A stable AppId keeps upgrades recognised as the same product (never change it).
AppId={{A7E4C1F2-3B9D-4E6A-9C21-5D8F0B2E7A14}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}

; Install into "Program Files\Faisal Clinical Laboratory" (64-bit).
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Program Files requires administrator rights.
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; License page (simple, from installer\LICENSE.txt).
LicenseFile=LICENSE.txt
; Bundle the install instructions and show them after install.
InfoAfterFile=README_INSTALL.txt

; Output.
OutputDir=Output
OutputBaseFilename=FaisalClinicalLaboratory-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Add/Remove Programs: show the app's own icon and a clean display name.
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Dirs]
; Ensure the reports folder exists on a fresh install and is never removed by
; the standard uninstaller -- report removal is handled interactively in [Code].
Name: "{app}\_internal\reports"; Flags: uninsneveruninstall

[Files]
; --- The launcher executable ------------------------------------------------
Source: "{#MySourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; --- The entire _internal tree (Qt, Python runtime, reportlab, catalog data) -
;     EXCLUDING user data (settings.json), the reports folder, and runtime logs.
;     These app files are overwritten on upgrade so the program updates cleanly.
Source: "{#MySourceDir}\_internal\*"; DestDir: "{app}\_internal"; \
    Flags: ignoreversion recursesubdirs createallsubdirs; \
    Excludes: "\data\settings.json,\reports\*,\reports,\logs\*,\logs"

; --- settings.json: written ONLY on a fresh install (never overwrites an
;     existing one) and kept on uninstall, so branding + report numbering
;     survive upgrades and re-installs.
Source: "{#MySourceDir}\_internal\data\settings.json"; DestDir: "{app}\_internal\data"; \
    Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
; Start Menu program shortcut.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Start Menu uninstall shortcut.
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (via the optional task above).
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch the app after installation.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
{ During uninstall, ask whether to delete saved reports. settings.json is kept
  regardless (uninsneveruninstall) unless the user later deletes the folder. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ReportsDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    ReportsDir := ExpandConstant('{app}\_internal\reports');
    if DirExists(ReportsDir) then
    begin
      if MsgBox('Do you want to remove all saved reports?' + #13#10 + #13#10 +
                'Choose No to KEEP your reports in:' + #13#10 + ReportsDir,
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(ReportsDir, True, True, True);
      end;
    end;
  end;
end;
