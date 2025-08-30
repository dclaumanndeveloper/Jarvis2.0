# Script PowerShell para build automático do .exe
# Fecha o main.exe se estiver rodando, limpa build antigo e gera novo .exe

# Fecha o main.exe se estiver aberto
Get-Process main -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }

# Remove build antigo
Remove-Item -Recurse -Force .\build, .\dist, .\main.spec -ErrorAction SilentlyContinue

# Instala dependências (opcional, descomente se quiser garantir)
# & "C:/Users/diego/OneDrive - New Music Brasil/Documentos/GitHub/PESSOAL/Jarvis2.0/.venv/Scripts/python.exe" -m pip install -r requirements.txt

 # Gera o novo .exe incluindo o jarvis.gif
& "C:/Users/diego/OneDrive - New Music Brasil/Documentos/GitHub/PESSOAL/Jarvis2.0/.venv/Scripts/python.exe" -m PyInstaller --onefile --windowed main.py --hidden-import=PyQt6 --hidden-import=PyQt6.QtWidgets --hidden-import=PyQt6.QtGui --hidden-import=PyQt6.QtCore --add-data "jarvis.gif;."
Write-Host "Build finalizado! O executável está em .\dist\main.exe" -ForegroundColor Green
