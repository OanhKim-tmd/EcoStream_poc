; Inno Setup script: builds dist\EcoStream-Windows-Setup.exe from dist\EcoStream\ (PyInstaller output).
; Run after scripts/build_desktop_app.py. Inno Setup: https://jrsoftware.org/isdl.php

#define MyAppName "EcoStream"
#define MyAppVersion "0.3.0"
#define MyAppPublisher "EcoStream (USTH Inno 2026)"
#define MyAppURL "https://github.com/OanhKim-tmd/EcoStream_poc"
#define MyAppExeName "EcoStream.exe"

[Setup]
AppId={{E10D2C7B-8A55-449D-9CE2-D46D19E528BC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=EcoStream-Windows-Setup
SetupIconFile=..\scripts\ecostream.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Sao chep toan bo thu muc build dist\EcoStream vao thu muc cai dat
Source: "..\dist\EcoStream\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

