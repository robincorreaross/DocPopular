# Gera o DocPopular.iss para o Inno Setup (ASCII, sem BOM)
# Usa os arquivos .isl locais patcheados para evitar erro de BOM no ISCC
iss = """; DocPopular.iss - Script do instalador (Inno Setup 6)

[Setup]
AppId={{B4C9E2F1-7A3D-4E8B-92F0-1D5A6C8E3B7F}
AppName=DocPopular
AppVersion=1.0.0
AppVerName=DocPopular v1.0.0
AppPublisher=Ross Sistemas
AppPublisherURL=https://github.com/robincorreaross/DocPopular
DefaultDirName={autopf}\\DocPopular
DefaultGroupName=DocPopular
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=DocPopular_Setup_v1.0.0
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
AllowNoIcons=yes
UninstallDisplayName=DocPopular
UninstallDisplayIcon={app}\\DocPopular.exe

[Languages]
; Usamos os arquivos .isl locais da pasta installer_meta que foram patcheados (sem BOM)
Name: "english"; MessagesFile: "installer_meta\\Default.isl"
Name: "brazilianportuguese"; MessagesFile: "installer_meta\\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon";   Description: "Criar atalho na Area de Trabalho"; GroupDescription: "Atalhos:"
Name: "startmenuicon"; Description: "Criar atalho no Menu Iniciar";     GroupDescription: "Atalhos:"

[Files]
Source: "dist\\DocPopular\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\\DocPopular";       Filename: "{app}\\DocPopular.exe"; Tasks: desktopicon
Name: "{group}\\DocPopular";             Filename: "{app}\\DocPopular.exe"; Tasks: startmenuicon
Name: "{group}\\Desinstalar DocPopular"; Filename: "{uninstallexe}";         Tasks: startmenuicon

[Run]
Filename: "{app}\\DocPopular.exe"; Description: "Abrir DocPopular agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
"""

outfile = "DocPopular.iss"
with open(outfile, "w", encoding="ascii") as f:
    f.write(iss)

print(f"Gerado: {outfile} (Com linguagens locais)")
