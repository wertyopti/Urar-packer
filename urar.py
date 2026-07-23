#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ultra RAR Packer - Полная версия с GUI
Поддерживает: упаковку и распаковку .urar/.rar архивов
Запускается двойным кликом, всё в одном файле.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import json
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from pathlib import Path
from PIL import Image
import zlib
import hashlib
import platform

# ============================ ЛОГИКА УПАКОВКИ ============================

def get_tool_path(tool_name):
    """Ищет утилиту в папке с программой, а потом в PATH."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    local_path = os.path.join(base_path, tool_name)
    if os.path.exists(local_path):
        return local_path
    
    # В Windows пробуем с .exe
    if platform.system() == "Windows" and not local_path.endswith('.exe'):
        local_path_exe = local_path + '.exe'
        if os.path.exists(local_path_exe):
            return local_path_exe
    
    return tool_name

RAR_CMD = get_tool_path("rar")
FFMPEG_CMD = get_tool_path("ffmpeg")
RECOVERY_PERCENT = 10

def check_tool(cmd):
    return shutil.which(cmd) is not None

def classify_file(filename):
    ext = filename.suffix.lower()
    image = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico'}
    video = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}
    audio = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'}
    text = {'.txt', '.log', '.json', '.xml', '.html', '.htm', '.css', '.js', '.py', '.java', '.c', '.cpp', '.h', '.csv', '.md', '.ini', '.cfg', '.yaml', '.yml'}
    if ext in image: return "image"
    elif ext in video: return "video"
    elif ext in audio: return "audio"
    elif ext in text: return "text"
    else: return "other"

def process_image(input_path, output_path, quality=85):
    try:
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
        return True
    except Exception:
        return False

def process_video(input_path, output_path, bitrate='800k', audio_bitrate='128k'):
    if not check_tool(FFMPEG_CMD):
        return False
    try:
        cmd = [FFMPEG_CMD, "-i", str(input_path),
               "-c:v", "libx264", "-b:v", bitrate,
               "-c:a", "libmp3lame", "-b:a", audio_bitrate,
               "-y", str(output_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def process_audio(input_path, output_path, bitrate='128k'):
    if not check_tool(FFMPEG_CMD):
        return False
    try:
        cmd = [FFMPEG_CMD, "-i", str(input_path),
               "-c:a", "libmp3lame", "-b:a", bitrate,
               "-y", str(output_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def process_text(input_path, output_path):
    try:
        with open(input_path, 'rb') as f_in:
            data = f_in.read()
        compressed = zlib.compress(data, level=9)
        with open(output_path, 'wb') as f_out:
            f_out.write(compressed)
        return True
    except Exception:
        return False

def create_recovery_metadata(file_list, archive_path, log_callback=None):
    meta = {"created": time.ctime(), "total_files": 0, "files": []}
    total_size = 0
    for item in file_list:
        if not item.is_file():
            continue
        try:
            rel_path = str(item.relative_to(archive_path))
            size = item.stat().st_size
            total_size += size
            try:
                md5_hash = hashlib.md5(item.read_bytes()).hexdigest()
            except:
                md5_hash = "недоступно"
            meta["files"].append({"path": rel_path, "size": size, "md5": md5_hash})
            meta["total_files"] += 1
        except Exception as e:
            if log_callback:
                log_callback(f"⚠️ Пропущен {item.name}: {e}")
            continue
    meta["total_size"] = total_size
    with open(archive_path / "recovery.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

def create_rar_archive(source_dir, output_rar, recovery_percent=10, log_callback=None):
    if not check_tool(RAR_CMD):
        if log_callback:
            log_callback("❌ RAR не найден. Установите WinRAR или положите rar.exe рядом.")
        return False
    cmd = [RAR_CMD, "a", f"-rr{recovery_percent}", "-ep1", "-r", "-m5",
           output_rar, str(source_dir) + os.sep + "*"]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError as e:
        if log_callback:
            log_callback(f"❌ Ошибка создания архива: {e}")
        return False

# ============================ РАСПАКОВКА ============================

def extract_rar_archive(archive_path, output_dir, log_callback=None):
    """Распаковывает .rar/.urar архив в указанную папку."""
    if not check_tool(RAR_CMD):
        if log_callback:
            log_callback("❌ RAR не найден. Установите WinRAR или положите rar.exe рядом.")
        return False
    
    # Проверяем существование архива
    if not os.path.exists(archive_path):
        if log_callback:
            log_callback(f"❌ Архив не найден: {archive_path}")
        return False
    
    # Создаём папку назначения
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [RAR_CMD, "x", "-y", archive_path, str(output_dir)]
    
    try:
        if log_callback:
            log_callback(f"📦 Распаковка: {archive_path} → {output_dir}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if log_callback:
                log_callback("✅ Распаковка успешно завершена!")
            return True
        else:
            if log_callback:
                log_callback(f"❌ Ошибка распаковки (код {result.returncode})")
                if result.stderr:
                    log_callback(result.stderr)
            return False
    except Exception as e:
        if log_callback:
            log_callback(f"❌ Ошибка: {e}")
        return False

def run_packer(input_dir, mode, recovery, video_bitrate, audio_bitrate, log_callback, progress_callback=None):
    input_dir = Path(input_dir).resolve()
    if not input_dir.is_dir():
        log_callback("❌ Папка не существует.")
        return False

    if mode == "long" and not check_tool(FFMPEG_CMD):
        log_callback("⚠️ FFmpeg не найден. Видео и аудио будут скопированы.")

    if not check_tool(RAR_CMD):
        log_callback("❌ RAR не найден. Установите WinRAR.")
        return False

    base_name = input_dir.name
    # Пробуем .urar, потом .ur, потом .rar
    for ext in [".urar", ".ur", ".rar"]:
        test_path = base_name + ext
        try:
            with open(test_path, 'w') as f:
                pass
            os.remove(test_path)
            output_rar = test_path
            log_callback(f"📦 Используем расширение: {ext}")
            break
        except:
            continue
    else:
        output_rar = base_name + ".rar"
        log_callback("⚠️ Не удалось создать .urar/.ur, используем .rar")

    with tempfile.TemporaryDirectory(prefix="ultra_rar_") as tmp_dir:
        work_dir = Path(tmp_dir) / "files"
        work_dir.mkdir(parents=True, exist_ok=True)

        all_files = list(input_dir.rglob("*"))
        total = len([f for f in all_files if f.is_file()])
        processed = 0
        log_callback(f"📁 Найдено файлов: {total}")

        for file_path in all_files:
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(input_dir)
            dest_path = work_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            category = classify_file(file_path)
            success = True

            try:
                if mode == "fast":
                    shutil.copy2(file_path, dest_path)
                elif mode == "medium":
                    if category == "image":
                        success = process_image(file_path, dest_path.with_suffix(".jpg"), quality=85)
                        if not success:
                            shutil.copy2(file_path, dest_path)
                    else:
                        shutil.copy2(file_path, dest_path)
                elif mode == "long":
                    if category == "image":
                        success = process_image(file_path, dest_path.with_suffix(".jpg"), quality=70)
                        if not success:
                            shutil.copy2(file_path, dest_path)
                    elif category == "video" and check_tool(FFMPEG_CMD):
                        success = process_video(file_path, dest_path.with_suffix(".mp4"),
                                                bitrate=video_bitrate, audio_bitrate=audio_bitrate)
                        if not success:
                            shutil.copy2(file_path, dest_path)
                    elif category == "audio" and check_tool(FFMPEG_CMD):
                        success = process_audio(file_path, dest_path.with_suffix(".mp3"), bitrate=audio_bitrate)
                        if not success:
                            shutil.copy2(file_path, dest_path)
                    elif category == "text":
                        success = process_text(file_path, dest_path.with_suffix(".gz"))
                        if not success:
                            shutil.copy2(file_path, dest_path)
                    else:
                        shutil.copy2(file_path, dest_path)
                else:
                    shutil.copy2(file_path, dest_path)
            except Exception as e:
                log_callback(f"⚠️ Ошибка с {file_path.name}: {e}")
                shutil.copy2(file_path, dest_path)

            processed += 1
            if processed % 20 == 0 or processed == total:
                log_callback(f"  Обработано {processed}/{total} файлов")
            if progress_callback:
                progress_callback(processed / total * 100)

        # Восстановление
        if mode == "long":
            all_items = list(work_dir.rglob("*"))
            only_files = [item for item in all_items if item.is_file()]
            create_recovery_metadata(only_files, work_dir, log_callback)
            log_callback("🛡️ Файл recovery.json добавлен")

        log_callback(f"📦 Упаковка в {output_rar} с восстановлением {recovery}% ...")
        if create_rar_archive(work_dir, output_rar, recovery, log_callback):
            log_callback(f"✅ Архив успешно создан: {output_rar}")
            if output_rar.endswith(('.urar', '.ur')):
                log_callback("💡 Файл .urar — это RAR-архив с другим расширением.")
                log_callback("   Распакуйте его в WinRAR или переименуйте в .rar")
            return True
        else:
            log_callback("❌ Ошибка при создании архива")
            return False

# ============================ GUI ============================

class UltraRAR_GUI:
    def __init__(self, root):
        self.root = root
        root.title("Ultra RAR Packer")
        root.geometry("720x620")
        root.configure(bg='#1a1a2e')
        root.minsize(700, 550)

        # Заголовок
        tk.Label(root, text="⚡ Ultra RAR Packer", font=("Segoe UI", 24, "bold"),
                 bg='#1a1a2e', fg='#e94560').pack(pady=15)

        # Вкладки
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=5, padx=15, fill='both', expand=True)

        # --- Вкладка 1: Упаковка ---
        self.pack_frame = tk.Frame(self.notebook, bg='#1a1a2e')
        self.notebook.add(self.pack_frame, text="📦 Упаковка")

        self._create_pack_tab()

        # --- Вкладка 2: Распаковка ---
        self.unpack_frame = tk.Frame(self.notebook, bg='#1a1a2e')
        self.notebook.add(self.unpack_frame, text="📂 Распаковка")

        self._create_unpack_tab()

        # Лог (общий для обеих вкладок)
        log_frame = tk.Frame(root, bg='#1a1a2e')
        log_frame.pack(pady=5, padx=15, fill='both', expand=True)

        tk.Label(log_frame, text="📋 Лог операций:", bg='#1a1a2e', fg='#aaa',
                 font=("Segoe UI", 10)).pack(anchor='w')

        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, bg='#0f3460', 
                                                   fg='#a6e3e9', font=("Consolas", 9), 
                                                   wrap='word', state='disabled')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.tag_config('error', foreground='#e94560')
        self.log_text.tag_config('success', foreground='#4caf50')
        self.log_text.tag_config('info', foreground='#a6e3e9')

        self.running = False

    def _create_pack_tab(self):
        parent = self.pack_frame

        # Выбор папки
        frame1 = tk.Frame(parent, bg='#1a1a2e')
        frame1.pack(pady=10, padx=20, fill='x')
        
        self.folder_var = tk.StringVar()
        self.folder_label = tk.Label(frame1, text="📁 Папка не выбрана",
                                     bg='#16213e', fg='white', font=("Segoe UI", 11),
                                     relief='sunken', anchor='w', padx=10)
        self.folder_label.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Button(frame1, text="Выбрать папку", command=self.browse_folder,
                  bg='#e94560', fg='white', font=("Segoe UI", 10, "bold"),
                  padx=20, pady=5).pack(side='right')

        # Режимы
        frame2 = tk.Frame(parent, bg='#1a1a2e')
        frame2.pack(pady=12, padx=20, fill='x')
        
        tk.Label(frame2, text="Режим сжатия:", bg='#1a1a2e', fg='#aaa',
                 font=("Segoe UI", 12)).pack(anchor='w')
        
        self.mode_var = tk.StringVar(value="medium")
        modes_frame = tk.Frame(frame2, bg='#1a1a2e')
        modes_frame.pack(fill='x', pady=5)
        
        for mode, desc, color in [("fast", "⚡ Быстрый", "#4caf50"),
                                  ("medium", "⚖️ Средний", "#ffc107"),
                                  ("long", "🌟 Долгий", "#e94560")]:
            rb = tk.Radiobutton(modes_frame, text=desc, variable=self.mode_var, value=mode,
                                bg='#1a1a2e', fg='white', font=("Segoe UI", 10),
                                selectcolor='#16213e', activebackground='#1a1a2e')
            rb.pack(side='left', padx=15)

        # Параметры
        frame3 = tk.Frame(parent, bg='#1a1a2e')
        frame3.pack(pady=8, padx=20, fill='x')

        tk.Label(frame3, text="Восстановление (%):", bg='#1a1a2e', fg='#aaa',
                 font=("Segoe UI", 11)).pack(side='left')
        
        self.recovery_var = tk.StringVar(value="10")
        spin = tk.Spinbox(frame3, from_=0, to=100, textvariable=self.recovery_var,
                          width=5, font=("Segoe UI", 11), bg='#16213e', fg='white')
        spin.pack(side='left', padx=10)

        # Битрейты
        frame4 = tk.Frame(parent, bg='#1a1a2e')
        frame4.pack(pady=5, padx=20, fill='x')

        tk.Label(frame4, text="Битрейт видео (k):", bg='#1a1a2e', fg='#aaa',
                 font=("Segoe UI", 10)).pack(side='left')
        self.video_bitrate = tk.Entry(frame4, width=8, bg='#16213e', fg='white')
        self.video_bitrate.insert(0, "800")
        self.video_bitrate.pack(side='left', padx=5)

        tk.Label(frame4, text="Битрейт аудио (k):", bg='#1a1a2e', fg='#aaa',
                 font=("Segoe UI", 10)).pack(side='left', padx=(20,0))
        self.audio_bitrate = tk.Entry(frame4, width=8, bg='#16213e', fg='white')
        self.audio_bitrate.insert(0, "128")
        self.audio_bitrate.pack(side='left', padx=5)

        # Кнопка запуска
        self.pack_btn = tk.Button(parent, text="🚀 ЗАПАКОВАТЬ", command=self.start_packing,
                                  bg='#e94560', fg='white', font=("Segoe UI", 14, "bold"),
                                  padx=50, pady=10, width=20)
        self.pack_btn.pack(pady=15)

        # Прогресс
        self.progress = ttk.Progressbar(parent, length=500, mode='determinate')
        self.progress.pack(pady=5)

    def _create_unpack_tab(self):
        parent = self.unpack_frame

        # Выбор архива
        frame1 = tk.Frame(parent, bg='#1a1a2e')
        frame1.pack(pady=10, padx=20, fill='x')
        
        self.archive_var = tk.StringVar()
        self.archive_label = tk.Label(frame1, text="📦 Архив не выбран",
                                      bg='#16213e', fg='white', font=("Segoe UI", 11),
                                      relief='sunken', anchor='w', padx=10)
        self.archive_label.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Button(frame1, text="Выбрать архив", command=self.browse_archive,
                  bg='#e94560', fg='white', font=("Segoe UI", 10, "bold"),
                  padx=20, pady=5).pack(side='right')

        # Выбор папки для распаковки
        frame2 = tk.Frame(parent, bg='#1a1a2e')
        frame2.pack(pady=10, padx=20, fill='x')
        
        self.unpack_folder_var = tk.StringVar()
        self.unpack_folder_label = tk.Label(frame2, text="📁 Папка назначения",
                                            bg='#16213e', fg='white', font=("Segoe UI", 11),
                                            relief='sunken', anchor='w', padx=10)
        self.unpack_folder_label.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Button(frame2, text="Выбрать папку", command=self.browse_unpack_folder,
                  bg='#4caf50', fg='white', font=("Segoe UI", 10, "bold"),
                  padx=20, pady=5).pack(side='right')

        # Кнопка распаковки
        self.unpack_btn = tk.Button(parent, text="📂 РАСПАКОВАТЬ", command=self.start_unpacking,
                                    bg='#4caf50', fg='white', font=("Segoe UI", 14, "bold"),
                                    padx=50, pady=10, width=20)
        self.unpack_btn.pack(pady=20)

        # Информация об архиве
        self.archive_info = tk.Label(parent, text="", bg='#1a1a2e', fg='#aaa',
                                     font=("Segoe UI", 10), wraplength=600)
        self.archive_info.pack(pady=5)

        # Прогресс распаковки
        self.unpack_progress = ttk.Progressbar(parent, length=500, mode='indeterminate')
        self.unpack_progress.pack(pady=5)

    # ==================== ОБЩИЕ МЕТОДЫ ====================

    def log(self, message, tag='info'):
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n', tag)
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update()

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')

    # ==================== УПАКОВКА ====================

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            self.folder_label.config(text=f"📁 {folder}")

    def start_packing(self):
        if self.running:
            return
        folder = self.folder_var.get()
        if not folder:
            messagebox.showerror("Ошибка", "Выберите папку для упаковки!")
            return

        mode = self.mode_var.get()
        recovery = self.recovery_var.get()
        v_bit = self.video_bitrate.get().strip() or "800"
        a_bit = self.audio_bitrate.get().strip() or "128"
        if v_bit.isdigit(): v_bit += "k"
        if a_bit.isdigit(): a_bit += "k"

        self.clear_log()
        self.pack_btn.config(state='disabled')
        self.progress['value'] = 0
        self.running = True

        thread = threading.Thread(target=self.run_packer_thread, 
                                  args=(folder, mode, recovery, v_bit, a_bit))
        thread.daemon = True
        thread.start()

    def run_packer_thread(self, folder, mode, recovery, v_bit, a_bit):
        try:
            success = run_packer(folder, mode, int(recovery), v_bit, a_bit, self.log, self.update_progress)
            if success:
                self.log("✅ Готово!", 'success')
            else:
                self.log("❌ Завершено с ошибками.", 'error')
        except Exception as e:
            self.log(f"❌ Критическая ошибка: {e}", 'error')
        finally:
            self.running = False
            self.pack_btn.config(state='normal')

    def update_progress(self, value):
        self.progress['value'] = value
        self.root.update()

    # ==================== РАСПАКОВКА ====================

    def browse_archive(self):
        filetypes = [
            ("Архивы Ultra RAR", "*.urar"),
            ("Архивы RAR", "*.rar"),
            ("Все файлы", "*.*")
        ]
        archive = filedialog.askopenfilename(filetypes=filetypes)
        if archive:
            self.archive_var.set(archive)
            self.archive_label.config(text=f"📦 {os.path.basename(archive)}")
            
            # Показываем информацию
            size = os.path.getsize(archive)
            size_str = f"{size / (1024*1024):.2f} МБ" if size > 1024*1024 else f"{size / 1024:.2f} КБ"
            self.archive_info.config(text=f"Размер: {size_str}")

    def browse_unpack_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.unpack_folder_var.set(folder)
            self.unpack_folder_label.config(text=f"📁 {folder}")

    def start_unpacking(self):
        if self.running:
            return
        archive = self.archive_var.get()
        if not archive:
            messagebox.showerror("Ошибка", "Выберите архив для распаковки!")
            return

        output_dir = self.unpack_folder_var.get()
        if not output_dir:
            messagebox.showerror("Ошибка", "Выберите папку для распаковки!")
            return

        self.clear_log()
        self.unpack_btn.config(state='disabled')
        self.unpack_progress.start()
        self.running = True

        thread = threading.Thread(target=self.run_unpacker_thread, 
                                  args=(archive, output_dir))
        thread.daemon = True
        thread.start()

    def run_unpacker_thread(self, archive, output_dir):
        try:
            success = extract_rar_archive(archive, output_dir, self.log)
            if success:
                self.log("✅ Распаковка успешно завершена!", 'success')
                messagebox.showinfo("Готово", f"Архив распакован в:\n{output_dir}")
            else:
                self.log("❌ Распаковка завершена с ошибками.", 'error')
        except Exception as e:
            self.log(f"❌ Критическая ошибка: {e}", 'error')
        finally:
            self.running = False
            self.unpack_btn.config(state='normal')
            self.unpack_progress.stop()

# ============================ ЗАПУСК ============================

if __name__ == "__main__":
    # Проверка библиотек
    try:
        import PIL
    except ImportError:
        print("⚠️ Pillow не установлена. Установите: pip install Pillow")
    
    root = tk.Tk()
    app = UltraRAR_GUI(root)
    root.mainloop()
