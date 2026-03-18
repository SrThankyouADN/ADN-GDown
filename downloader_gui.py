import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
from bs4 import BeautifulSoup
import re
import subprocess
import threading
import os
import json
import platform
from pathlib import Path
import queue
from google_auth import GoogleAuthManager
from login_window import LoginWindow

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class GoogleDriveDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("ADN GDown")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        
        # Tema (True = escuro, False = claro)
        self.dark_mode = True
        
        # Caminho para arquivo de configuração
        self.config_file = os.path.join(os.path.dirname(__file__), '.downloader_config.json')
        self.config = self.load_config()
        
        self.setup_styles()
        self.setup_icon()
        
        self.download_queue = queue.Queue()
        self.download_thread = None
        self.selected_files = {}
        self.downloads_paused = False
        
        # Gerenciador de autenticação Google
        self.auth_manager = GoogleAuthManager()
        self.login_window = LoginWindow()
        self.requires_auth = False
        
        self.create_widgets()
        self.process_queue()
    
    def load_config(self):
        """Carregar configurações salvas"""
        default_config = {
            'selected_folder': None,
            'last_urls': []
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    return {**default_config, **loaded}
            except:
                pass
        
        return default_config
    
    def save_config(self):
        """Salvar configurações"""
        try:
            self.config['selected_folder'] = self.selected_folder
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass  # Silenciosamente falhar se não conseguir salvar
    
    def setup_styles(self):
        """Configurar tema moderno com suporte a claro/escuro"""
        self.apply_theme()
    
    def apply_theme(self):
        """Aplicar tema (escuro ou claro) a todos os componentes"""
        style = ttk.Style()
        style.theme_use('alt')
        
        if self.dark_mode:
            # Paleta escura
            bg_color = "#1a1a1a"
            fg_color = "#e0e0e0"
            frame_bg = "#252525"
            accent_color = "#0f88ff"
            accent_light = "#1a9fff"
            accent_hover = "#0d6fbf"
            button_bg = "#404040"
            button_hover = "#505050"
            text_bg = "#2a2a2a"
            text_fg = "#e0e0e0"
            desc_fg = "#a0a0a0"
        else:
            # Paleta clara
            bg_color = "#f5f5f5"
            fg_color = "#1e1e1e"
            frame_bg = "#ececec"
            accent_color = "#0066cc"
            accent_light = "#0d7fd9"
            accent_hover = "#0052a3"
            button_bg = "#e0e0e0"
            button_hover = "#d0d0d0"
            text_bg = "#ffffff"
            text_fg = "#1e1e1e"
            desc_fg = "#666666"
        
        self.root.configure(bg=bg_color)
        
        # Frame styles - usar fieldbackground para aplicar cores
        style.configure('TFrame', background=bg_color, foreground=fg_color, borderwidth=0)
        style.configure('Main.TFrame', background=bg_color, foreground=fg_color, borderwidth=0)
        
        # LabelFrame styles - muito importante aplicar fieldbackground
        style.configure('TLabelFrame', background=frame_bg, foreground=fg_color, borderwidth=1, relief='flat', lightcolor=frame_bg, darkcolor=frame_bg)
        style.configure('TLabelFrame.Label', background=frame_bg, foreground=accent_color, font=('Segoe UI', 9, 'bold'))
        
        # Label styles
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 9))
        style.configure('Title.TLabel', background=bg_color, foreground=accent_color, font=('Segoe UI', 16, 'bold'))
        style.configure('Desc.TLabel', background=frame_bg, foreground=desc_fg, font=('Segoe UI', 8))
        
        # Button styles
        style.configure('TButton', font=('Segoe UI', 8), background=button_bg, foreground=fg_color, borderwidth=1, relief='solid', padding=4)
        style.map('TButton', background=[('active', button_hover), ('pressed', accent_hover)])
        
        style.configure('Accent.TButton', font=('Segoe UI', 8, 'bold'), background=accent_color, foreground='#ffffff' if self.dark_mode else '#1a1a1a', borderwidth=0, relief='flat', padding=5)
        style.map('Accent.TButton', background=[('active', accent_light), ('pressed', accent_hover)])
        
        style.configure('Secondary.TButton', font=('Segoe UI', 8), background=button_bg, foreground=fg_color, borderwidth=1, relief='solid', padding=4)
        style.map('Secondary.TButton', background=[('active', button_hover), ('pressed', '#303030' if self.dark_mode else '#c0c0c0')])
        
        style.configure('TScrollbar', background=frame_bg, troughcolor=bg_color, borderwidth=0)
        
        # Armazenar cores para usar em Text widgets
        self.colors = {
            'bg': bg_color,
            'fg': fg_color,
            'frame_bg': frame_bg,
            'text_bg': text_bg,
            'text_fg': text_fg,
            'accent': accent_color
        }
    
    def setup_icon(self):
        """Configurar ícone da aplicação a partir do PNG"""
        script_dir = os.path.dirname(__file__)
        png_path = os.path.join(script_dir, 'icon.png')
        svg_path = os.path.join(script_dir, 'icon.svg')
        
        # Método 1: Tentar carregar o PNG (prioritário)
        if os.path.exists(png_path):
            try:
                photo = tk.PhotoImage(file=png_path)
                self.root.iconphoto(False, photo)
                return  # Sucesso, sair
            except Exception as e:
                pass  # PNG não funcionou, tentar SVG
        
        # Método 2: Fallback - Tentar carregar SVG se PNG não existir
        if os.path.exists(svg_path):
            try:
                photo = tk.PhotoImage(file=svg_path)
                self.root.iconphoto(False, photo)
                return  # Sucesso, sair
            except Exception as e:
                pass  # SVG não funcionou
        
        # Método 3: Fallback - Criar ícone padrão com PIL
        if PIL_AVAILABLE:
            try:
                from PIL import Image, ImageDraw
                
                # Criar um ícone simples se nenhum arquivo existir
                size = 256
                img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Desenhar um círculo azul com borda branca
                draw.ellipse(
                    [(20, 20), (size - 20, size - 20)],
                    fill=(0, 102, 204, 255),
                    outline=(255, 255, 255, 255),
                    width=3
                )
                
                # Salvar temporário e carregar
                temp_path = os.path.join(script_dir, '.temp_icon.png')
                img.save(temp_path)
                
                photo = tk.PhotoImage(file=temp_path)
                self.root.iconphoto(False, photo)
                
                # Limpar arquivo temporário
                try:
                    os.remove(temp_path)
                except:
                    pass
            except Exception as e:
                pass  # Se tudo falhar, continuar sem ícone
    
    def create_widgets(self):
        """Criar interface minimalista e compacta"""
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Header com título e botão de tema
        self.header = tk.Frame(self.main_frame, bg=self.colors['bg'])
        self.header.pack(fill=tk.X, pady=(0, 12))
        self.header.grid_columnconfigure(1, weight=1)
        
        title_frame = tk.Frame(self.header, bg=self.colors['bg'])
        title_frame.pack(side=tk.LEFT)
        tk.Label(title_frame, text="📥 ADN GDown", bg=self.colors['bg'], fg=self.colors['accent'], font=('Segoe UI', 16, 'bold')).pack(anchor=tk.W)
        tk.Label(title_frame, text="Faça scrape e baixe arquivos do GDrive de forma facilitada", bg=self.colors['bg'], fg=self.colors['fg'], font=('Segoe UI', 8)).pack(anchor=tk.W, pady=(2, 0))
        
        # Botão de alternar tema no canto superior direito
        theme_btn = ttk.Button(self.header, text="☀️" if self.dark_mode else "🌙", command=self.toggle_theme, width=3)
        theme_btn.pack(side=tk.RIGHT)
        self.theme_btn = theme_btn
        
        # Entrada
        self.input_frame = tk.LabelFrame(self.main_frame, text="🔗 Cole a URL ou código HTML", bg=self.colors['frame_bg'], fg=self.colors['accent'], font=('Segoe UI', 9, 'bold'), borderwidth=1, relief='flat', padx=8, pady=8)
        self.input_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.desc_input_label = tk.Label(self.input_frame, text="Insira um link do Google Drive ou página com links", bg=self.colors['frame_bg'], fg=self.colors['fg'], font=('Segoe UI', 8))
        self.desc_input_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.url_frame = tk.Frame(self.input_frame, bg=self.colors['frame_bg'])
        self.url_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        
        scrollbar_url = ttk.Scrollbar(self.url_frame)
        scrollbar_url.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        self.url_input = tk.Text(self.url_frame, height=3, wrap=tk.WORD, yscrollcommand=scrollbar_url.set,
                                 bg=self.colors['text_bg'], fg=self.colors['text_fg'], font=('Segoe UI', 9), 
                                 insertbackground=self.colors['accent'], relief=tk.SOLID, borderwidth=1)
        self.url_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_url.config(command=self.url_input.yview)
        
        self.button_frame_input = tk.Frame(self.input_frame, bg=self.colors['frame_bg'])
        self.button_frame_input.pack(fill=tk.X)
        
        ttk.Button(self.button_frame_input, text="🔍 Checar", command=self.check_url, style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(self.button_frame_input, text="🕷️ Scrape", command=self.site_scrape, style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(self.button_frame_input, text="🗑️ Limpar", command=lambda: self.url_input.delete('1.0', tk.END), style='Secondary.TButton').pack(side=tk.LEFT)
        
        # Resultados
        self.results_frame = tk.LabelFrame(self.main_frame, text="📄 Links Encontrados", bg=self.colors['frame_bg'], fg=self.colors['accent'], font=('Segoe UI', 9, 'bold'), borderwidth=1, relief='flat', padx=8, pady=8)
        self.results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        scrollbar_files = ttk.Scrollbar(self.results_frame)
        scrollbar_files.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        self.files_listbox = tk.Listbox(self.results_frame, yscrollcommand=scrollbar_files.set, selectmode=tk.MULTIPLE,
                                       height=8, bg=self.colors['text_bg'], fg=self.colors['text_fg'], font=('Segoe UI', 9), 
                                       selectbackground=self.colors['accent'], relief=tk.SOLID, borderwidth=1, activestyle='none')
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_files.config(command=self.files_listbox.yview)
        
        # Ações
        self.action_frame = tk.LabelFrame(self.main_frame, text="⚙️  Ações", bg=self.colors['frame_bg'], fg=self.colors['accent'], font=('Segoe UI', 9, 'bold'), borderwidth=1, relief='flat', padx=8, pady=8)
        self.action_frame.pack(fill=tk.X, pady=(0, 8))
        
        button_line1 = tk.Frame(self.action_frame, bg=self.colors['frame_bg'])
        button_line1.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(button_line1, text="📁 Pasta", command=self.select_folder, style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(button_line1, text="📂 Abrir", command=self.open_folder, style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(button_line1, text="🔐 Auth", command=self.show_login, style='Secondary.TButton').pack(side=tk.LEFT)
        
        self.status_line = tk.Frame(self.action_frame, bg=self.colors['frame_bg'])
        self.status_line.pack(fill=tk.X, pady=(0, 6))
        tk.Label(self.status_line, text="Status:", bg=self.colors['frame_bg'], fg=self.colors['fg'], font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 8))
        self.auth_status = tk.Label(self.status_line, text="⚫ Não autenticado", bg=self.colors['frame_bg'], fg="#ff9500", font=('Segoe UI', 9))
        self.auth_status.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(self.status_line, text="Pasta:", bg=self.colors['frame_bg'], fg=self.colors['fg'], font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 8))
        self.folder_label = tk.Label(self.status_line, text="Não selecionada", bg=self.colors['frame_bg'], fg="#ff9500", font=('Segoe UI', 9))
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Atualizar status de autenticação
        self.update_auth_status()
        
        # Restaurar pasta selecionada anterior
        if self.config['selected_folder'] and os.path.exists(self.config['selected_folder']):
            self.selected_folder = self.config['selected_folder']
            display_path = ("..." + self.selected_folder[-47:]) if len(self.selected_folder) > 50 else self.selected_folder
            self.folder_label.config(text=f"✓ {display_path}", foreground="#00cc00")
        
        # Restaurar URLs anteriores
        if self.config['last_urls']:
            urls_text = '\n'.join(self.config['last_urls'][:5])  # Mostrar últimas 5 URLs
            self.url_input.insert('1.0', urls_text)
        
        # Download e Progress
        self.download_frame = tk.LabelFrame(self.main_frame, text="⬇️  Download", bg=self.colors['frame_bg'], fg=self.colors['accent'], font=('Segoe UI', 9, 'bold'), borderwidth=1, relief='flat', padx=8, pady=8)
        self.download_frame.pack(fill=tk.X, pady=(0, 8))
        
        button_line = tk.Frame(self.download_frame, bg=self.colors['frame_bg'])
        button_line.pack(fill=tk.X, pady=(0, 6))
        self.download_btn = ttk.Button(button_line, text="⬇️ Baixar", command=self.start_download, style='Accent.TButton')
        self.download_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        self.stop_btn = ttk.Button(button_line, text="⏹️ Parar", command=self.stop_download, state=tk.DISABLED, style='Secondary.TButton')
        self.stop_btn.pack(side=tk.LEFT)
        
        # Progresso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.download_frame, variable=self.progress_var, maximum=100, mode='determinate', length=300)
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))
        
        self.progress_label = tk.Label(self.download_frame, text="Pronto", bg=self.colors['frame_bg'], fg=self.colors['fg'], font=('Segoe UI', 8))
        self.progress_label.pack(anchor=tk.W)
        
        # Terminal
        self.terminal_frame = tk.LabelFrame(self.main_frame, text="📋 Log", bg=self.colors['frame_bg'], fg=self.colors['accent'], font=('Segoe UI', 9, 'bold'), borderwidth=1, relief='flat', padx=8, pady=8)
        self.terminal_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_terminal = ttk.Scrollbar(self.terminal_frame)
        scrollbar_terminal.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        self.terminal_text = tk.Text(self.terminal_frame, height=7, wrap=tk.WORD, yscrollcommand=scrollbar_terminal.set,
                                    bg=self.colors['bg'], fg="#00cc00", font=('Consolas', 8), 
                                    relief=tk.SOLID, borderwidth=1)
        self.terminal_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.terminal_text.config(state=tk.DISABLED)
        scrollbar_terminal.config(command=self.terminal_text.yview)
        
        self.selected_folder = None
    
    def toggle_theme(self):
        """Alternar entre tema escuro e claro"""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.theme_btn.config(text="☀️" if self.dark_mode else "🌙")
        self.refresh_ui()
    
    def refresh_ui(self):
        """Atualizar cores de todos os widgets após mudar tema"""
        # Atualizar root window
        self.root.configure(bg=self.colors['bg'])
        
        # Atualizar frames principais
        self.main_frame.configure(bg=self.colors['bg'])
        self.header.configure(bg=self.colors['bg'])
        self.input_frame.configure(bg=self.colors['frame_bg'], fg=self.colors['accent'])
        self.url_frame.configure(bg=self.colors['frame_bg'])
        self.button_frame_input.configure(bg=self.colors['frame_bg'])
        self.desc_input_label.configure(bg=self.colors['frame_bg'], fg=self.colors['fg'])
        
        self.results_frame.configure(bg=self.colors['frame_bg'], fg=self.colors['accent'])
        
        self.action_frame.configure(bg=self.colors['frame_bg'], fg=self.colors['accent'])
        self.status_line.configure(bg=self.colors['frame_bg'])
        
        self.download_frame.configure(bg=self.colors['frame_bg'], fg=self.colors['accent'])
        self.progress_label.configure(bg=self.colors['frame_bg'], fg=self.colors['fg'])
        
        self.terminal_frame.configure(bg=self.colors['frame_bg'], fg=self.colors['accent'])
        
        # Atualizar Text widgets
        self.url_input.config(bg=self.colors['text_bg'], fg=self.colors['text_fg'], insertbackground=self.colors['accent'])
        self.files_listbox.config(bg=self.colors['text_bg'], fg=self.colors['text_fg'], selectbackground=self.colors['accent'])
        self.terminal_text.config(bg=self.colors['bg'], fg="#00cc00" if self.dark_mode else "#008c00")
        
        # Atualizar labels de status
        self.auth_status.configure(bg=self.colors['frame_bg'])
        self.folder_label.configure(bg=self.colors['frame_bg'])
        
        # Atualizar labels dentro dos frames
        for widget in self.status_line.winfo_children():
            if isinstance(widget, tk.Label) and widget != self.auth_status and widget != self.folder_label:
                widget.configure(bg=self.colors['frame_bg'], fg=self.colors['fg'])
        
        # Forçar redraw
        self.root.update_idletasks()
        self.root.update()
    
    def log_terminal(self, message):
        """Log no terminal"""
        self.terminal_text.config(state=tk.NORMAL)
        self.terminal_text.insert(tk.END, f"{message}\n")
        self.terminal_text.see(tk.END)
        self.terminal_text.config(state=tk.DISABLED)
        self.root.update_idletasks()  # Atualizar visual em tempo real
    
    def extract_drive_links(self, text):
        """Extrair IDs e resourcekey do Google Drive"""
        file_data = {}  # {file_id: resourcekey}
        
        # Padrão 1: URLs novas (drive.google.com/file/d/)
        pattern1 = r'https://drive\.google\.com/file/d/[a-zA-Z0-9-_]+[^\s)]*'
        urls1 = re.findall(pattern1, text)
        
        for url in urls1:
            # Extrair ID
            id_match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', url)
            if not id_match:
                continue
            
            file_id = id_match.group(1)
            
            # Extrair resourcekey se existir
            resourcekey_match = re.search(r'resourcekey=([^&\s]+)', url)
            resourcekey = resourcekey_match.group(1) if resourcekey_match else None
            
            file_data[file_id] = resourcekey
        
        # Padrão 2: URLs antigas (drive.usercontent.google.com/open?id=)
        pattern2 = r'https://drive\.usercontent\.google\.com/open\?id=([a-zA-Z0-9-_]+)[^\s)]*'
        urls2 = re.findall(pattern2, text)
        
        for match in urls2:
            file_id = match
            if file_id not in file_data:
                file_data[file_id] = None  # URLs antigas não precisam de resourcekey
        
        return file_data
    
    def check_url(self):
        """Verificar URL e extrair links"""
        url_text = self.url_input.get('1.0', tk.END).strip()
        
        if not url_text:
            messagebox.showwarning("Aviso", "Cole uma URL ou HTML")
            return
        
        # Salvar URL nas últimas usadas
        if url_text.startswith(('http://', 'https://')):
            if url_text not in self.config['last_urls']:
                self.config['last_urls'].insert(0, url_text)
                if len(self.config['last_urls']) > 10:  # Manter apenas últimas 10
                    self.config['last_urls'] = self.config['last_urls'][:10]
                self.save_config()
        
        self.files_listbox.delete(0, tk.END)
        self.selected_files = {}
        
        if url_text.startswith(('http://', 'https://')):
            try:
                self.log_terminal("Baixando conteúdo da URL...")
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url_text, headers=headers, timeout=10)
                content = response.text
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao acessar URL: {str(e)}")
                self.log_terminal(f"Erro: {str(e)}")
                return
        else:
            content = url_text
        
        file_data = self.extract_drive_links(content)
        
        if not file_data:
            messagebox.showinfo("Resultado", "Nenhum link do Google Drive encontrado")
            self.log_terminal("Nenhum link encontrado")
            return
        
        for i, (file_id, resourcekey) in enumerate(file_data.items(), 1):
            display_id = file_id[:20] + "..." if len(file_id) > 20 else file_id
            rk_flag = " [+resourcekey]" if resourcekey else ""
            self.files_listbox.insert(tk.END, f"[{i}] {display_id}{rk_flag}")
            self.selected_files[i-1] = (file_id, resourcekey)
        
        self.log_terminal(f"✓ {len(file_ids)} link(s) encontrado(s)")
    
    def site_scrape(self):
        """Site scrape"""
        url = self.url_input.get('1.0', tk.END).strip()
        
        if not url:
            messagebox.showwarning("Aviso", "Cole a URL de um site")
            return
        
        if not url.startswith(('http://', 'https://')):
            messagebox.showwarning("Aviso", "URL deve começar com http:// ou https://")
            return
        
        self.log_terminal("\nIniciando scrape...")
        
        scrape_thread = threading.Thread(target=self._do_scrape, args=(url,), daemon=True)
        scrape_thread.start()
    
    def _do_scrape(self, url):
        """Fazer scrape"""
        try:
            self.log_terminal(f"Acessando: {url}")
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            
            self.log_terminal("Página baixada. Analisando...")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            drive_links = {}
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Padrao 1: URLs novas (drive.google.com/file/d/)
                if 'drive.google.com/file/d/' in href:
                    match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', href)
                    if match:
                        file_id = match.group(1)
                        if file_id not in drive_links:
                            # Extrair resourcekey se existir
                            resourcekey_match = re.search(r'resourcekey=([^&\s]+)', href)
                            resourcekey = resourcekey_match.group(1) if resourcekey_match else None
                            
                            title = text if text else "Arquivo"
                            drive_links[file_id] = (title, resourcekey)
                
                # Padrao 2: URLs antigas (drive.usercontent.google.com/open?id=)
                elif 'drive.usercontent.google.com' in href and 'id=' in href:
                    match = re.search(r'id=([a-zA-Z0-9-_]+)', href)
                    if match:
                        file_id = match.group(1)
                        if file_id not in drive_links:
                            title = text if text else "Arquivo (antigo)"
                            drive_links[file_id] = (title, None)
            
            if drive_links:
                self.log_terminal(f"✓ Encontrados {len(drive_links)} arquivo(s)")
                
                self.files_listbox.delete(0, tk.END)
                self.selected_files = {}
                
                for i, (file_id, (title, resourcekey)) in enumerate(drive_links.items(), 1):
                    rk_flag = " [+resourcekey]" if resourcekey else ""
                    self.files_listbox.insert(tk.END, f"[{i}] {title[:50]}{rk_flag}")
                    self.selected_files[i-1] = (file_id, resourcekey)
                
                messagebox.showinfo("Sucesso", f"{len(drive_links)} arquivo(s) encontrado(s)!")
            else:
                self.log_terminal("⚠ Nenhum link encontrado")
                messagebox.showinfo("Resultado", "Nenhum link encontrado")
                
        except Exception as e:
            error_msg = f"Erro: {str(e)}"
            self.log_terminal(error_msg)
            messagebox.showerror("Erro", error_msg)
    
    def select_folder(self):
        """Selecionar pasta"""
        folder = filedialog.askdirectory(title="Selecionar pasta de destino")
        if folder:
            self.selected_folder = folder
            self.config['selected_folder'] = folder
            display_path = ("..." + folder[-35:]) if len(folder) > 38 else folder
            self.folder_label.config(text=f"✓ {display_path}", foreground="#00cc00")
            self.log_terminal(f"✓ Pasta selecionada: {folder}")
            self.save_config()
    
    def open_folder(self):
        """Abrir a pasta selecionada no explorador do sistema"""
        if not self.selected_folder or not os.path.exists(self.selected_folder):
            messagebox.showwarning("Pasta Não Selecionada", "Selecione uma pasta válida primeiro!")
            return
        
        try:
            if platform.system() == 'Windows':
                os.startfile(self.selected_folder)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', self.selected_folder])
            else:  # Linux
                subprocess.run(['xdg-open', self.selected_folder])
            self.log_terminal(f"Pasta aberta: {self.selected_folder}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta: {e}")
            self.log_terminal(f"Erro ao abrir pasta: {e}")
    
    def show_login(self):
        """Mostrar janela de autenticação Google"""
        self.login_window.show_login_dialog()
        self.update_auth_status()
    
    def update_auth_status(self):
        """Atualizar status de autenticação na interface"""
        if self.auth_manager.has_valid_session():
            self.auth_status.config(text="🟢 Autenticado", foreground="#00cc00")
        else:
            self.auth_status.config(text="⚫ Não autenticado", foreground="#ff9500")

    
    def start_download(self):
        """Iniciar download"""
        selected_indices = self.files_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("Aviso", "Selecione pelo menos um arquivo")
            return
        
        if not self.selected_folder:
            messagebox.showwarning("Aviso", "Selecione uma pasta")
            return
        
        if not self.check_wget_installed():
            messagebox.showerror("Erro", "wget não está instalado")
            return
        
        downloads_list = [self.selected_files[i] for i in selected_indices]
        
        self.download_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.downloads_paused = False
        
        self.download_thread = threading.Thread(target=self.download_files, args=(downloads_list,), daemon=True)
        self.download_thread.start()
    
    def download_files(self, downloads_list):
        """Download com wget"""
        total = len(downloads_list)
        
        self.log_terminal(f"\n{'='*60}")
        self.log_terminal(f"Download de {total} arquivo(s)")
        self.log_terminal(f"Destino: {self.selected_folder}")
        self.log_terminal(f"{'='*60}\n")
        
        # Gerar arquivo de cookies para wget se autenticado
        cookies_file = None
        if self.auth_manager.has_valid_session():
            self.log_terminal("✓ Sessão autenticada detectada")
            cookies_file = self.auth_manager.get_cookies_for_wget()
            if cookies_file:
                self.log_terminal(f"✓ Cookies carregados para autenticação\n")
        
        for idx, file_id in enumerate(downloads_list, 1):
            if self.downloads_paused:
                break
            
            progress = (idx - 1) / total * 100
            self.download_queue.put(('progress', progress))
            self.download_queue.put(('status', f"Download {idx}/{total}"))
            
            # Desempacotar (file_id, resourcekey) se for tupla, ou apenas file_id
            if isinstance(file_id, tuple):
                file_id, resourcekey = file_id
            else:
                resourcekey = None
            
            self.log_terminal(f"[{idx}/{total}] ID: {file_id}")
            if resourcekey:
                self.log_terminal(f"[{idx}/{total}] ✓ ResourceKey encontrado: {resourcekey[:20]}...")
            else:
                self.log_terminal(f"[{idx}/{total}] ⚠ Sem resourcekey (arquivo recente)")
            
            # Construir URL com resourcekey para arquivos antigos
            url = f"https://docs.google.com/uc?export=download&confirm=t&id={file_id}"
            if resourcekey:
                url += f"&resourcekey={resourcekey}"
            self.log_terminal(f"[{idx}/{total}] URL: {url[:100]}...") if len(url) > 100 else self.log_terminal(f"[{idx}/{total}] URL: {url}")
            
            filename = os.path.join(self.selected_folder, f"arquivo_{idx}.pdf")
            
            # Comando wget com headers para contornar bloqueio de autenticação
            # Headers extras para suportar redirecionamentos de URLs antigas
            wget_cmd = [
                'wget',
                '-q',
                '--show-progress',
                '--no-check-certificate',
                '--tries=3',  # Tentar 3 vezes para URLs antigas
                '--timeout=30',
                '-L',  # Follow redirects (IMPORTANTE para URLs antigas)
                '--max-redirect=10',  # Aumentar número de redirecionamentos
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--referer=https://drive.google.com/',
                '--header=Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                '--header=Accept-Language: pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                '--header=DNT: 1',
                '--header=Connection: keep-alive',
                '--header=Upgrade-Insecure-Requests: 1',
            ]
            
            # Adicionar cookies se disponíveis - DEVE VIR ANTES DA URL!
            if cookies_file:
                self.log_terminal(f"  Usando arquivo de cookies")
                wget_cmd.extend([
                    '--load-cookies', cookies_file,
                    '--save-cookies', cookies_file,
                    '--keep-session-cookies'
                ])
            else:
                self.log_terminal(f"  ⚠ Sem autenticação (cookies não disponíveis)")
            
            # Adicionar URL e output por último
            wget_cmd.extend(['-O', filename, url])
            
            try:
                self.log_terminal("Executando wget...")
                process = subprocess.Popen(
                    wget_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                for line in process.stdout:
                    if self.downloads_paused:
                        process.terminate()
                        self.log_terminal(f"[{idx}/{total}] Cancelado")
                        if os.path.exists(filename):
                            os.remove(filename)
                        return
                    
                    line = line.strip()
                    if line:
                        self.log_terminal(f"  {line}")
                
                process.wait()
                
                if process.returncode == 0:
                    size = os.path.getsize(filename) if os.path.exists(filename) else 0
                    
                    # Verificar se o arquivo é HTML (erro de autenticação)
                    is_html_error = False
                    try:
                        with open(filename, 'rb') as f:
                            header = f.read(500)
                            if (b'<!DOCTYPE' in header or b'<html' in header.lower() or 
                                b'<HTML' in header or b'google' in header.lower()):
                                is_html_error = True
                    except:
                        pass
                    
                    if is_html_error:
                        self.log_terminal(f"[{idx}/{total}] ⚠️  Erro de autenticação detectado (HTML recebido)")
                        
                        # Verificar se já existe sessão
                        if not self.auth_manager.has_valid_session():
                            self.log_terminal(f"[{idx}/{total}] 🔐 Autenticação necessária!")
                            
                            # Pedir login ao usuário
                            self.download_btn.config(state=tk.NORMAL)
                            self.stop_btn.config(state=tk.DISABLED)
                            
                            result = messagebox.askyesno(
                                "Autenticação Necessária",
                                "Este arquivo requer autenticação Google.\n\n"
                                "Deseja fazer login agora?"
                            )
                            
                            if result:
                                self.log_terminal(f"[{idx}/{total}] Abrindo janela de autenticação...")
                                self.login_window.show_login_dialog()
                                self.update_auth_status()
                                
                                if self.auth_manager.has_valid_session():
                                    self.log_terminal(f"[{idx}/{total}] ✓ Login bem-sucedido! Tentando nov amente...")
                                    # Retentar este download
                                    cookies_file = self.auth_manager.get_cookies_for_wget()
                                    
                                    self.download_btn.config(state=tk.DISABLED)
                                    self.stop_btn.config(state=tk.NORMAL)
                                    
                                    if os.path.exists(filename):
                                        os.remove(filename)
                                    
                                    # Retentar com cookies
                                    # Reconstruir URL com resourcekey se necessário
                                    retry_url = f"https://docs.google.com/uc?export=download&confirm=t&id={file_id}"
                                    if resourcekey:
                                        retry_url += f"&resourcekey={resourcekey}"
                                    
                                    self.log_terminal(f"[{idx}/{total}] ✓ Tentando com autenticação...")
                                    self.log_terminal(f"[{idx}/{total}] URL com resourcekey: {retry_url[:100]}...") if len(retry_url) > 100 else self.log_terminal(f"[{idx}/{total}] URL com resourcekey: {retry_url}")
                                    
                                    retry_wget_cmd = [
                                        'wget',
                                        '-q',
                                        '--show-progress',
                                        '--no-check-certificate',
                                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                        '--referer=https://drive.google.com/',
                                        '--header=Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                        '--header=Accept-Language: pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                                        '--header=DNT: 1',
                                        '-O', filename,
                                        retry_url
                                    ]
                                    
                                    if cookies_file:
                                        retry_wget_cmd.extend(['--load-cookies', cookies_file])
                                        retry_wget_cmd.extend(['--save-cookies', cookies_file])
                                        retry_wget_cmd.extend(['--keep-session-cookies'])
                                    
                                    try:
                                        self.log_terminal(f"[{idx}/{total}] Executando wget com autenticação...")
                                        retry_process = subprocess.Popen(
                                            retry_wget_cmd,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            universal_newlines=True,
                                            bufsize=1
                                        )
                                        
                                        for line in retry_process.stdout:
                                            if self.downloads_paused:
                                                retry_process.terminate()
                                                break
                                            line = line.strip()
                                            if line:
                                                self.log_terminal(f"  {line}")
                                        
                                        retry_process.wait()
                                        
                                        if retry_process.returncode == 0 and os.path.exists(filename):
                                            size = os.path.getsize(filename)
                                            is_still_html = False
                                            try:
                                                with open(filename, 'rb') as f:
                                                    content = f.read(100)
                                                    if b'<!DOCTYPE' in content or b'<html' in content.lower():
                                                        is_still_html = True
                                            except:
                                                pass
                                            
                                            if not is_still_html and size > 1000:
                                                self.log_terminal(f"[{idx}/{total}] ✓ OK ({size} bytes)\n")
                                            else:
                                                self.log_terminal(f"[{idx}/{total}] ✗ Arquivo inválido ou muito pequeno\n")
                                                if os.path.exists(filename):
                                                    os.remove(filename)
                                        else:
                                            self.log_terminal(f"[{idx}/{total}] ✗ Falha com autenticação\n")
                                            if os.path.exists(filename):
                                                os.remove(filename)
                                    except Exception as e:
                                        self.log_terminal(f"[{idx}/{total}] ✗ Erro: {str(e)}\n")
                                        if os.path.exists(filename):
                                            os.remove(filename)
                                    
                                    continue
                                else:
                                    self.log_terminal(f"[{idx}/{total}] ✗ Login cancelado\n")
                                    if os.path.exists(filename):
                                        os.remove(filename)
                                    continue
                            else:
                                self.log_terminal(f"[{idx}/{total}] ✗ Autenticação necessária mas não realizada\n")
                                if os.path.exists(filename):
                                    os.remove(filename)
                                continue
                        
                        self.log_terminal(f"[{idx}/{total}] Tentando com método alternativo...")
                        if os.path.exists(filename):
                            os.remove(filename)
                        
                        # Tentar com parâmetro de confirmação diferente
                        alt_url = f"https://docs.google.com/uc?export=download&id={file_id}"
                        if resourcekey:
                            alt_url += f"&resourcekey={resourcekey}"
                        
                        self.log_terminal(f"[{idx}/{total}] URL alternativa com resourcekey: {alt_url[:100]}...") if len(alt_url) > 100 else self.log_terminal(f"[{idx}/{total}] URL alternativa: {alt_url}")
                        alt_wget_cmd = [
                            'wget',
                            '-q',
                            '--show-progress',
                            '--no-check-certificate',
                            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            '--referer=https://drive.google.com/',
                            '-O', filename,
                            alt_url
                        ]
                        
                        # Adicionar cookies ao método alternativo também
                        if cookies_file:
                            alt_wget_cmd.extend(['--load-cookies', cookies_file])
                            alt_wget_cmd.extend(['--save-cookies', cookies_file])
                            alt_wget_cmd.extend(['--keep-session-cookies'])
                        
                        try:
                            self.log_terminal(f"  Executando wget com URL alternativa...")
                            alt_process = subprocess.Popen(
                                alt_wget_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                universal_newlines=True,
                                bufsize=1
                            )
                            
                            for line in alt_process.stdout:
                                if self.downloads_paused:
                                    alt_process.terminate()
                                    break
                                line = line.strip()
                                if line:
                                    self.log_terminal(f"  {line}")
                            
                            alt_process.wait()
                            
                            if alt_process.returncode == 0 and os.path.exists(filename):
                                size = os.path.getsize(filename)
                                is_still_html = False
                                try:
                                    with open(filename, 'rb') as f:
                                        content = f.read(100)
                                        if b'<!DOCTYPE' in content or b'<html' in content.lower():
                                            is_still_html = True
                                except:
                                    pass
                                
                                if not is_still_html and size > 1000:
                                    self.log_terminal(f"[{idx}/{total}] ✓ OK ({size} bytes)\n")
                                else:
                                    self.log_terminal(f"[{idx}/{total}] ✗ Arquivo inválido ou muito pequeno\n")
                                    if os.path.exists(filename):
                                        os.remove(filename)
                            else:
                                self.log_terminal(f"[{idx}/{total}] ✗ Falha no método alternativo\n")
                                if os.path.exists(filename):
                                    os.remove(filename)
                                
                                # Terceiro método: URL antiga de drive.usercontent.google.com
                                self.log_terminal(f"[{idx}/{total}] Tentando com URL antiga (drive.usercontent.google.com)...")
                                if os.path.exists(filename):
                                    os.remove(filename)
                                
                                # Construir URL antiga
                                old_url = f"https://drive.usercontent.google.com/open?id={file_id}&authuser=0"
                                if resourcekey:
                                    old_url += f"&resourcekey={resourcekey}"
                                
                                self.log_terminal(f"[{idx}/{total}] URL antiga: {old_url[:100]}...")
                                
                                old_wget_cmd = [
                                    'wget',
                                    '-q',
                                    '--show-progress',
                                    '--no-check-certificate',
                                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    '--referer=https://drive.google.com/',
                                    '--header=Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    '--header=Accept-Language: pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                                    '--header=DNT: 1',
                                    '-L',
                                    '--max-redirect=10',
                                    '-O', filename,
                                    old_url
                                ]
                                
                                if cookies_file:
                                    old_wget_cmd.extend(['--load-cookies', cookies_file])
                                    old_wget_cmd.extend(['--save-cookies', cookies_file])
                                
                                try:
                                    self.log_terminal(f"[{idx}/{total}] Executando wget com URL antiga...")
                                    old_process = subprocess.Popen(
                                        old_wget_cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True,
                                        bufsize=1
                                    )
                                    
                                    for line in old_process.stdout:
                                        if self.downloads_paused:
                                            old_process.terminate()
                                            break
                                        line = line.strip()
                                        if line:
                                            self.log_terminal(f"  {line}")
                                    
                                    old_process.wait()
                                    
                                    if old_process.returncode == 0 and os.path.exists(filename):
                                        size = os.path.getsize(filename)
                                        is_still_html = False
                                        try:
                                            with open(filename, 'rb') as f:
                                                content = f.read(100)
                                                if b'<!DOCTYPE' in content or b'<html' in content.lower():
                                                    is_still_html = True
                                        except:
                                            pass
                                        
                                        if not is_still_html and size > 1000:
                                            self.log_terminal(f"[{idx}/{total}] ✓ OK ({size} bytes)\n")
                                        else:
                                            self.log_terminal(f"[{idx}/{total}] ✗ Arquivo inválido ou muito pequeno\n")
                                            if os.path.exists(filename):
                                                os.remove(filename)
                                    else:
                                        self.log_terminal(f"[{idx}/{total}] ✗ Falha na URL antiga\n")
                                        if os.path.exists(filename):
                                            os.remove(filename)
                                except Exception as e:
                                    self.log_terminal(f"[{idx}/{total}] ✗ Erro: {str(e)}\n")
                                    if os.path.exists(filename):
                                        os.remove(filename)
                        except Exception as e:
                            self.log_terminal(f"[{idx}/{total}] ✗ Erro no método alternativo: {str(e)}\n")
                            if os.path.exists(filename):
                                os.remove(filename)
                    else:
                        self.log_terminal(f"[{idx}/{total}] ✓ OK ({size} bytes)\n")
                else:
                    self.log_terminal(f"[{idx}/{total}] ✗ Erro (código {process.returncode})\n")
                    if os.path.exists(filename):
                        os.remove(filename)
                
            except FileNotFoundError:
                self.log_terminal(f"[{idx}/{total}] ✗ wget não encontrado\n")
            except Exception as e:
                self.log_terminal(f"[{idx}/{total}] ✗ {str(e)}\n")
                if os.path.exists(filename):
                    os.remove(filename)
        
        self.download_queue.put(('progress', 100.0))
        self.download_queue.put(('status', "Concluído!"))
        self.download_queue.put(('done', None))
        
        self.log_terminal(f"{'='*60}\n")
    
    def stop_download(self):
        """Parar"""
        self.downloads_paused = True
        self.log_terminal("⚠️ Parado pelo usuário\n")
        self.download_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def check_wget_installed(self):
        """Verificar wget"""
        try:
            subprocess.run(['wget', '--version'], capture_output=True, timeout=5)
            return True
        except:
            return False
    
    def process_queue(self):
        """Processar fila"""
        try:
            while True:
                msg_type, data = self.download_queue.get_nowait()
                
                if msg_type == 'progress':
                    self.progress_var.set(data)
                elif msg_type == 'status':
                    self.progress_label.config(text=data)
                elif msg_type == 'done':
                    self.download_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                    messagebox.showinfo("Concluído", "Download finalizado!")
                
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_queue)


def main():
    root = tk.Tk()
    app = GoogleDriveDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
