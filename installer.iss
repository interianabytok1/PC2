[Setup]
AppName=Polozky pre OBERON
AppVersion=0.1.0
DefaultDirName={autopf}\PolozkyPreOberon
DefaultGroupName=Polozky pre OBERON
OutputDir=release
OutputBaseFilename=PolozkyPreOberon-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayName=Polozky pre OBERON

[Files]
Source: "release\PolozkyPreOberon\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\Polozky pre OBERON"; Filename: "{app}\PolozkyPreOberon.exe"; WorkingDir: "{app}"
Name: "{group}\Polozky pre OBERON"; Filename: "{app}\PolozkyPreOberon.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\PolozkyPreOberon.exe"; Description: "Spustiť aplikáciu"; Flags: nowait postinstall skipifsilent
