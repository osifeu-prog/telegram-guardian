# 1. לוודא we're in the right folder
Set-Location -Path "C:\Users\Giga Store\Downloads\telegram-guardian-master"

# 2. הפעלת סביבה וירטואלית (אם לא קיימת, יוצרת)
if (-Not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    py -m venv .venv
}

# 3. הפעלה של הסביבה
Write-Host "Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

# 4. עדכון pip
Write-Host "Updating pip..."
py -m pip install --upgrade pip

# 5. התקנת חבילות קריטיות
Write-Host "Installing required packages..."
py -m pip install --upgrade python-telegram-bot==20.3 flask sqlalchemy alembic requests python-dotenv

# 6. הפעלת פאטצ'ים
Write-Host "Applying patches..."
py tools\patch_tg_guardian.py

# 7. הרצת הבוט הראשי
Write-Host "Starting Telegram Guardian Bot..."
py -m app.tg_bot
