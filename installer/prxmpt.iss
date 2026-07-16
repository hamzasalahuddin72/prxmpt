#define MyAppName "prxmpt"
#define MyAppVersion "1.0.9"
#define MyAppPublisher "Hamza Salahuddin"
#define MyAppExeName "prxmpt.exe"

[Setup]
AppId={{B638BBAF-6C2B-4B53-94B2-AD2F7F4C7311}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=prxmptUpdate_1.0.9
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
VersionInfoVersion=1.0.9.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\prxmpt\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README_INSTALLATION.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\sample_context_template.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PATCH_NOTES_1.0.9.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Installation guide"; Filename: "{app}\README_INSTALLATION.md"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[InstallDelete]
; The AppId is intentionally unchanged, so this is an in-place rename update.
Type: files; Name: "{app}\ClearCue.exe"
Type: files; Name: "{userdesktop}\ClearCue.lnk"
Type: filesandordirs; Name: "{userprograms}\ClearCue"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyAppExeName}"; Flags: nowait skipifdoesntexist; Check: RelaunchRequested

[Code]
function RelaunchRequested(): Boolean;
begin
  Result := CompareText(ExpandConstant('{param:RELAUNCH|0}'), '1') = 0;
end;
