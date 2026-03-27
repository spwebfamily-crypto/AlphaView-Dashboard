# Script de Setup Automático do Perfil GitHub
# Username: spwebfamily-crypto

Write-Host "🚀 Setup Automático do Perfil GitHub" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""

# Passo 1: Criar repositório no GitHub
Write-Host "📋 PASSO 1: Criar Repositório no GitHub" -ForegroundColor Cyan
Write-Host ""
Write-Host "Acesse este link e siga as instruções:" -ForegroundColor Yellow
Write-Host "https://github.com/new" -ForegroundColor White
Write-Host ""
Write-Host "Configure assim:" -ForegroundColor Yellow
Write-Host "  ✅ Repository name: spwebfamily-crypto" -ForegroundColor White
Write-Host "  ✅ Public" -ForegroundColor White
Write-Host "  ✅ Add a README file (marque esta opção)" -ForegroundColor White
Write-Host ""
Write-Host "Pressione ENTER depois de criar o repositório..." -ForegroundColor Green
Read-Host

# Passo 2: Clonar o repositório
Write-Host ""
Write-Host "📥 PASSO 2: Clonando o Repositório" -ForegroundColor Cyan
Write-Host ""

$desktopPath = [Environment]::GetFolderPath("Desktop")
$repoPath = Join-Path $desktopPath "spwebfamily-crypto"

# Remove se já existir
if (Test-Path $repoPath) {
    Write-Host "⚠️  Removendo pasta existente..." -ForegroundColor Yellow
    Remove-Item -Path $repoPath -Recurse -Force
}

Set-Location $desktopPath

Write-Host "Clonando repositório..." -ForegroundColor White
git clone https://github.com/spwebfamily-crypto/spwebfamily-crypto.git

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro ao clonar. Verifique se o repositório foi criado corretamente." -ForegroundColor Red
    Write-Host "Pressione ENTER para sair..." -ForegroundColor Yellow
    Read-Host
    exit 1
}

# Passo 3: Copiar o README
Write-Host ""
Write-Host "📄 PASSO 3: Copiando README Personalizado" -ForegroundColor Cyan
Write-Host ""

$sourcePath = "c:\Users\Rodrigo🐐\OneDrive\Desktop\AlphaView-Dashboard\README_GITHUB_PROFILE.md"
$destPath = Join-Path $repoPath "README.md"

Copy-Item -Path $sourcePath -Destination $destPath -Force
Write-Host "✅ README copiado com sucesso!" -ForegroundColor Green

# Passo 4: Commit e Push
Write-Host ""
Write-Host "📤 PASSO 4: Enviando para o GitHub" -ForegroundColor Cyan
Write-Host ""

Set-Location $repoPath

git add README.md
git commit -m "feat: add awesome profile README with animations and stats"
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🎉 SUCESSO! Seu perfil está pronto!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Acesse seu perfil em:" -ForegroundColor Cyan
    Write-Host "https://github.com/spwebfamily-crypto" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 Próximos passos (opcional):" -ForegroundColor Yellow
    Write-Host "  1. Edite o README.md para adicionar seu email e LinkedIn" -ForegroundColor White
    Write-Host "  2. Adicione mais projetos na seção 'Projetos em Destaque'" -ForegroundColor White
    Write-Host "  3. Personalize as seções conforme necessário" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Erro ao fazer push. Verifique suas credenciais do Git." -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Dica: Configure o Git com:" -ForegroundColor Yellow
    Write-Host "git config --global user.name 'Seu Nome'" -ForegroundColor White
    Write-Host "git config --global user.email 'seu-email@example.com'" -ForegroundColor White
    Write-Host ""
}

Write-Host "Pressione ENTER para finalizar..." -ForegroundColor Green
Read-Host
