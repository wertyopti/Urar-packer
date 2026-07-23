# Ultra RAR Packer

Ultra RAR Packer — простая «всё в одном» утилита с GUI для упаковки и распаковки RAR-архивов. Поддерживает создание архивов с восстановлением (recovery), оптимизацию изображений, перекодирование видео/аудио через FFmpeg и сжатие текстов.

Особенности:
- Упаковка папок в `.rar` / `.urar` (по сути RAR с другим расширением).
- Три режима: fast (копирование), medium (оптимизация изображений), long (максимальная обработка: изображения, видео, аудио, текст).
- Генерация `recovery.json` с метаданными для восстановления (в режиме long).
- Простой GUI на Tkinter.
- Распаковка архивов (требует rar.exe / unrar).

Требования
- Python 3.8+
- Pillow (PIL) — `pip install Pillow`
- WinRAR / rar.exe на PATH (или поместите rar.exe рядом со скриптом)
- FFmpeg для перекодирования видео/аудио (опционально, требуется для режима long)

Файлы в репозитории
- `urar.py` — основной скрипт с GUI и логикой.
- `LICENSE` — MIT License.
- `README.md` — это руководство.

Как запустить локально
1. Склонируйте репозиторий или поместите файлы в папку.
2. Установите зависимости:
   ```bash
   pip install Pillow
   ```
3. Убедитесь, что `rar` (или `rar.exe`) и `ffmpeg` доступны в PATH или лежат рядом со скриптом.
4. Запустите:
   ```bash
   python urar.py
   ```

Как создать новый репозиторий и запушить файлы (быстро)
1. В папке с файлом выполните:
   ```bash
   git init
   git add urar.py README.md LICENSE
   git commit -m "Initial commit: Ultra RAR Packer"
   ```
2a. Если используете GitHub CLI (`gh`):
   ```bash
   gh repo create ultra-rar-packer --public --source=. --push
   ```
2b. Или создайте репозиторий через сайт GitHub, затем:
   ```bash
   git remote add origin https://github.com/USERNAME/REPO.git
   git branch -M main
   git push -u origin main
   ```

Примечания
- В Windows файл `rar.exe` нужен для создания/распаковки RAR. На Linux можно использовать `unrar`/`rar` (если доступно).
- Формат `.urar` — просто переименованный RAR. Для распаковки можно переименовать в `.rar` или открыть через WinRAR.
- Скрипт целиком в одном файле для удобства распространения.

Лицензия
- MIT (см. LICENSE).
