#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from google_auth import GoogleAuthManager


class LoginWindow:
    """Janela de login para autenticação Google"""
    
    def __init__(self, parent_window=None):
        """
        Inicializar janela de login
        
        Args:
            parent_window: Janela pai (se houver)
        """
        self.parent = parent_window
        self.auth_manager = GoogleAuthManager()
        self.login_result = None
        self.window = None
    
    def show_login_dialog(self):
        """
        Mostrar diálogo de login
        
        Returns:
            bool: True se login bem-sucedido
        """
        root = tk.Tk()
        root.title("Autenticação Google Drive")
        root.geometry("550x480")
        root.resizable(False, False)
        
        # Centralizar janela
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        bg_color = "#f5f5f5"
        fg_color = "#1e1e1e"
        accent_color = "#0066cc"
        
        root.configure(bg=bg_color)
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), 
                       background=accent_color, foreground='#ffffff')
        style.configure('Status.TLabel', font=('Segoe UI', 9))
        
        # Frame principal
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = ttk.Label(main_frame, text="Autenticação Google Drive", 
                               font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Ícone/Status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        if self.auth_manager.has_valid_session():
            status_label = ttk.Label(status_frame, text="✓ Sessão ativa encontrada", 
                                    foreground="#00aa00", font=('Segoe UI', 11, 'bold'))
        else:
            status_label = ttk.Label(status_frame, text="⚠ Nenhuma sessão ativa", 
                                    foreground="#ff6600", font=('Segoe UI', 11, 'bold'))
        
        status_label.pack(anchor=tk.W)
        
        # Descrição
        desc_text = tk.Text(main_frame, height=6, wrap=tk.WORD, bg="#ffffff", 
                           fg=fg_color, font=('Segoe UI', 10), relief=tk.FLAT)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        desc_text.insert('1.0', 
            "Para baixar arquivos que requerem autenticação, faça login com sua conta Google.\n\n"
            "⚠️ IMPORTANTE: Use sua conta PESSOAL do Google (não Google Workspace)!\n\n"
            "Ao clicar em 'Fazer Login', uma janela do navegador será aberta. "
            "Faça login com sua conta Google.\n\n"
            "⚠ IMPORTANTE: Não feche a janela do navegador imediatamente. "
            "Aguarde 2-3 segundos após fazer login para os cookies serem capturados.")
        desc_text.config(state=tk.DISABLED)
        
        # Frame para mensagens de status
        status_msg_frame = ttk.Frame(main_frame)
        status_msg_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_msg_label = ttk.Label(status_msg_frame, text="", style='Status.TLabel', foreground="#0066cc")
        status_msg_label.pack(anchor=tk.W)
        
        # Botões
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def do_login():
            try:
                status_msg_label.config(text="Abrindo navegador...")
                root.update()
                
                messagebox.showinfo("Login Google", 
                    "Uma janela do navegador será aberta.\n\n"
                    "1. Faça login com sua conta Google\n"
                    "2. Aguarde 2-3 segundos\n"
                    "3. A janela fechará automaticamente quando os cookies forem capturados\n\n"
                    "Clique OK para continuar...")
                
                status_msg_label.config(text="Aguardando login (pode levar de 10 a 60 segundos)...")
                root.update()
                
                success = self.auth_manager.login_interactive(headless=False, timeout=300)
                
                if success:
                    status_msg_label.config(text="✓ Login bem-sucedido!", foreground="#00aa00")
                    root.update()
                    messagebox.showinfo("Sucesso", "Login realizado com sucesso!\nOs cookies foram salvos.")
                    self.login_result = True
                else:
                    status_msg_label.config(text="✗ Falha ao fazer login", foreground="#cc0000")
                    root.update()
                    messagebox.showerror("Erro", "Falha ao fazer login ou tempo limite excedido.\n\nTentou fazer login?")
                    self.login_result = False
            except Exception as e:
                status_msg_label.config(text=f"✗ Erro: {str(e)}", foreground="#cc0000")
                root.update()
                messagebox.showerror("Erro", f"Erro durante o login: {str(e)}")
                self.login_result = False
        
        def do_renew():
            try:
                status_msg_label.config(text="Renovando sessão...")
                root.update()
                
                messagebox.showinfo("Renovar Sessão", 
                    "Uma janela do navegador será aberta.\n"
                    "Faça login novamente com sua conta Google.")
                
                status_msg_label.config(text="Aguardando novo login (pode levar de 10 a 60 segundos)...")
                root.update()
                
                success = self.auth_manager.renew_session(headless=False)
                
                if success:
                    status_msg_label.config(text="✓ Sessão renovada!", foreground="#00aa00")
                    root.update()
                    messagebox.showinfo("Sucesso", "Sessão renovada com sucesso!")
                else:
                    status_msg_label.config(text="✗ Falha ao renovar", foreground="#cc0000")
                    root.update()
                    messagebox.showerror("Erro", "Falha ao renovar sessão ou tempo limite excedido.")
            except Exception as e:
                status_msg_label.config(text=f"✗ Erro: {str(e)}", foreground="#cc0000")
                root.update()
                messagebox.showerror("Erro", f"Erro ao renovar sessão: {str(e)}")
        
        def do_clear():
            if messagebox.askyesno("Confirmar", "Limpar cookies salvos?"):
                self.auth_manager.clear_session()
                status_msg_label.config(text="✓ Cookies removidos", foreground="#00aa00")
                root.update()
                messagebox.showinfo("Sucesso", "Cookies removidos com sucesso.")
                # Atualizar status
                root.destroy()
                self.show_login_dialog()
        
        def do_continue():
            root.destroy()
        
        login_btn = ttk.Button(button_frame, text="🔐 Fazer Login", command=do_login, 
                              style='Accent.TButton')
        login_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        renew_btn = ttk.Button(button_frame, text="🔄 Renovar Sessão", command=do_renew)
        renew_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_btn = ttk.Button(button_frame, text="🗑️ Limpar Cookies", command=do_clear)
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        continue_btn = ttk.Button(button_frame, text="✓ Continuar", command=do_continue, 
                                 style='Accent.TButton')
        continue_btn.pack(side=tk.RIGHT)
        
        root.mainloop()
        
        return self.login_result if self.login_result is not None else True
    
    def show_login_if_needed(self):
        """
        Mostrar login apenas se não houver sessão ativa
        
        Returns:
            bool: True se autorizado a continuar
        """
        if not self.auth_manager.has_valid_session():
            response = messagebox.askyesno(
                "Autenticação Necessária",
                "Alguns arquivos requerem autenticação Google.\n\n"
                "Deseja fazer login agora?"
            )
            
            if response:
                return self.show_login_dialog()
            return False
        
        return True


class AuthenticationRequired(Exception):
    """Exceção para quando autenticação é necessária"""
    pass


if __name__ == "__main__":
    login_ui = LoginWindow()
    result = login_ui.show_login_dialog()
    print(f"Login result: {result}")
