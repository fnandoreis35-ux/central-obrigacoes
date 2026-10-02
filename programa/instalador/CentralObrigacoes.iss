; Instalador da Central de Obrigações (Inno Setup 6). Gerado automaticamente pelo GitHub Actions.
#ifndef Versao
  #define Versao "1.0.0"
#endif

[Setup]
AppId={{6E2B8A41-6C1D-4F7B-9B38-5B7C2E0C9A11}
AppName=Central de Obrigações
AppVersion={#Versao}
AppPublisher=Fernando Reis
DefaultDirName={localappdata}\Programs\CentralObrigacoes
DefaultGroupName=Central de Obrigações
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\saida
OutputBaseFilename=CentralObrigacoes-Instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Central de Obrigações

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\CentralObrigacoes\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Central de Obrigações"; Filename: "{app}\CentralObrigacoes.exe"
Name: "{userdesktop}\Central de Obrigações"; Filename: "{app}\CentralObrigacoes.exe"; Tasks: atalho

[Run]
Filename: "{app}\CentralObrigacoes.exe"; Description: "Abrir a Central de Obrigações"; Flags: nowait postinstall skipifsilent
