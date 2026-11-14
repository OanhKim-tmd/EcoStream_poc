; Script Inno Setup tao bo cai dat chuyen nghiep EcoStream cho Windows
; Hoan toan mien phi, giup han che toi da loi bao dong gia virus (false-positive)
; Tai Inno Setup mien phi tai: https://jrsoftware.org/isdl.php

#define MyAppName "EcoStream AI Carbon Accounting"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "EcoStream Technologies"
#define MyAppURL "https://ecostream.vn"
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
OutputBaseFilename=EcoStream_Windows_Setup_v1.0
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

