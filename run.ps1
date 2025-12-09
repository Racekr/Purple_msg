# Purple-msg Launcher - Aucune trace laissée
Write-Host "🟣 Purple-msg - Connexion sécurisée..." -ForegroundColor Magenta

# Vérifier Python
try {
    $pythonCmd = Get-Command python -ErrorAction Stop
    Write-Host "✓ Python détecté" -ForegroundColor Green
} catch {
    Write-Host "❌ Python n'est pas installé sur cet ordinateur." -ForegroundColor Red
    Write-Host "Télécharge Python sur : https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Appuie sur Entrée pour quitter"
    exit
}

# Installer aiohttp silencieusement
Write-Host "📦 Installation des dépendances..." -ForegroundColor Cyan
python -m pip install --quiet --disable-pip-version-check aiohttp 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ Problème d'installation, on continue quand même..." -ForegroundColor Yellow
}

# Télécharger le client dans un fichier temporaire
$tempFile = "$env:TEMP\purple_$([guid]::NewGuid().ToString().Substring(0,8)).py"
$clientUrl = "https://raw.githubusercontent.com/Racekr/Purple_msg/refs/heads/main/client.py"

try {
    Write-Host "🔽 Téléchargement du client..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $clientUrl -OutFile $tempFile -UseBasicParsing
    
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
    Write-Host "🟣 PURPLE-MSG CHAT" -ForegroundColor Magenta
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Magenta
    
    # Lancer le client
    python $tempFile
    
} catch {
    Write-Host "`n❌ Erreur: $_" -ForegroundColor Red
} finally {
    # Nettoyer le fichier temporaire
    if (Test-Path $tempFile) {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
    Write-Host "`n✓ Fichiers temporaires nettoyés" -ForegroundColor Green
}

Write-Host "`nAppuie sur Entrée pour fermer..." -ForegroundColor Gray
Read-Host