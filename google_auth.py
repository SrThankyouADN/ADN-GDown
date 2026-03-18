#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import pickle
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class GoogleAuthManager:
    """Gerenciador de autenticação Google com cookies"""
    
    def __init__(self, session_dir: str = "session"):
        """
        Inicializar gerenciador de autenticação
        
        Args:
            session_dir: Diretório para armazenar cookies e sessões
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        
        self.cookies_file = self.session_dir / "google_cookies.pkl"
        self.credentials_file = self.session_dir / "credentials.json"
        self.driver = None
    
    def load_cookies(self):
        """
        Carregar cookies salvos
        
        Returns:
            List[dict] ou None se não existir arquivo
        """
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Erro ao carregar cookies: {e}")
                return None
        return None
    
    def save_cookies(self, cookies):
        """
        Salvar cookies em arquivo
        
        Args:
            cookies: List[dict] de cookies do Selenium
        """
        try:
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            return True
        except Exception as e:
            print(f"Erro ao salvar cookies: {e}")
            return False
    
    def has_valid_session(self):
        """
        Verificar se existe uma sessão válida
        
        Returns:
            bool
        """
        return self.cookies_file.exists()
    
    def cleanup_driver(self):
        """Fechar driver do Selenium"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def login_interactive(self, headless: bool = False, timeout: int = 300) -> bool:
        """
        Fazer login interativo no Google (CONTA PESSOAL)
        Versão SIMPLIFICADA - espera por cookies ao invés de elementos
        
        Args:
            headless: Se True, não mostra a janela do navegador
            timeout: Tempo máximo de espera em segundos
        
        Returns:
            bool: True se login bem-sucedido
        """
        try:
            # Configurar opções do Chrome
            chrome_options = webdriver.ChromeOptions()
            
            if headless:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Criar driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(5)
            
            print("Abrindo Google Drive (Conta Pessoal) para autenticação...")
            print("Se pedir para escolher conta, selecione sua conta PESSOAL (não workspace)...\n")
            
            # URL que força Google Drive pessoal
            login_url = "https://drive.google.com/drive/u/0/my-drive"
            self.driver.get(login_url)
            
            print("Aguardando autenticação do usuário...")
            print(f"Você tem {timeout} segundos para fazer login")
            print("Após fazer login, o programa detectará automaticamente.\n")
            
            start_time = time.time()
            last_cookie_count = 0
            no_change_count = 0
            
            # Loop simples: verifica cookies a cada segundo
            while time.time() - start_time < timeout:
                try:
                    current_url = self.driver.current_url
                    cookies = self.driver.get_cookies()
                    cookie_count = len(cookies)
                    
                    # Mostrar progresso a cada 5 segundos
                    elapsed = int(time.time() - start_time)
                    if elapsed % 5 == 0 and elapsed > 0:
                        print(f"[{elapsed}s] URL: {current_url[:50]}... | Cookies: {cookie_count}")
                    
                    # ✓ VERIFICAÇÃO 1: Detectar Workspace
                    if "workspace.google.com" in current_url:
                        print("\n⚠️  Detectado Google Workspace - é uma conta corporativa!")
                        print("Faça logout manualmente e selecione uma conta PESSOAL do Google\n")
                        self.driver.get("https://accounts.google.com/Logout")
                        time.sleep(2)
                        self.driver.get(login_url)
                        continue
                    
                    # ✓ VERIFICAÇÃO 2: NÃO está em accounts.google.com (página de login)
                    if "accounts.google.com" not in current_url:
                        # ✓ VERIFICAÇÃO 3: Está em drive.google.com
                        if "drive.google.com" in current_url:
                            # ✓ VERIFICAÇÃO 4: Tem MUITOS cookies (indica autenticação)
                            if cookie_count > 10:
                                print(f"\n✓ Detectado cookies de autenticação ({cookie_count} cookies found)")
                                print("Salvando cookies...")
                                
                                # Aguardar 2 segundos para garantir que tudo está pronto
                                time.sleep(2)
                                
                                # Tentar salvar novamente
                                cookies = self.driver.get_cookies()
                                if cookies:
                                    self.save_cookies(cookies)
                                    print(f"✓ Login bem-sucedido! {len(cookies)} cookies salvos.")
                                    self.cleanup_driver()
                                    return True
                    
                    # ✓ VERIFICAÇÃO 5: Cookie count aumentando (usuário fazendo login)
                    if cookie_count > last_cookie_count:
                        print(f"→ Cookies aumentando: {last_cookie_count} → {cookie_count}")
                        last_cookie_count = cookie_count
                        no_change_count = 0
                    else:
                        no_change_count += 1
                        # Se não mudou por 30 segundos e não está em login, pode estar pronto
                        if no_change_count > 30 and "drive.google.com" in current_url and cookie_count > 5:
                            print(f"\n✓ Cookies estáveis em {cookie_count}")
                            self.save_cookies(cookies)
                            print(f"✓ Login bem-sucedido! {len(cookies)} cookies salvos.")
                            self.cleanup_driver()
                            return True
                    
                except Exception as e:
                    pass
                
                time.sleep(1)
            
            print(f"\n✗ Timeout após {timeout} segundos")
            
            # Tentar uma última vez verificar cookies
            cookies = self.driver.get_cookies()
            if len(cookies) > 10:
                print(f"✓ Encontrados {len(cookies)} cookies no final!")
                self.save_cookies(cookies)
                print("✓ Login bem-sucedido! Cookies salvos.")
                self.cleanup_driver()
                return True
            
            self.cleanup_driver()
            return False
        
        except Exception as e:
            print(f"Erro ao fazer login: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup_driver()
            return False
    
    def get_cookies_for_wget(self):
        """
        Gerar arquivo de cookies compatível com wget
        
        Returns:
            str: Caminho do arquivo de cookies ou None
        """
        cookies = self.load_cookies()
        
        if not cookies:
            print("⚠ Nenhum cookie carregado")
            return None
        
        cookies_txt = self.session_dir / "cookies.txt"
        
        try:
            with open(cookies_txt, 'w') as f:
                # Cabeçalho do formato Netscape (compatível com wget)
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This is a generated file!  Do not edit.\n\n")
                
                conta_cookies = 0
                for cookie in cookies:
                    # Formatar cada cookie no padrão Netscape
                    domain = cookie.get('domain', '.google.com')
                    path = cookie.get('path', '/')
                    secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                    expiry = cookie.get('expiry', '0')
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    
                    # Pular cookies vazios
                    if not name or not value:
                        continue
                    
                    # Pular cookies de rastreamento/anúncios
                    if name in ['NID', 'ANID', '__Secure-1PSIDTS', '__Secure-3PSIDTS']:
                        continue
                    
                    # domain flag path secure expiry name value
                    line = f"{domain}\tTRUE\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n"
                    f.write(line)
                    conta_cookies += 1
            
            if conta_cookies == 0:
                print("⚠ Nenhum cookie válido para salvar")
                return None
            
            print(f"✓ Arquivo de cookies: {cookies_txt}")
            print(f"✓ Cookies salvos: {conta_cookies}")
            
            return str(cookies_txt)
        
        except Exception as e:
            print(f"Erro ao gerar arquivo de cookies: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_cookies_for_requests(self) -> dict:
        """
        Obter cookies no formato para requests library
        
        Returns:
            dict: Cookies formatados para requests
        """
        cookies = self.load_cookies()
        
        if not cookies:
            return {}
        
        cookies_dict = {}
        for cookie in cookies:
            cookies_dict[cookie['name']] = cookie['value']
        
        return cookies_dict
    
    def renew_session(self, headless: bool = False) -> bool:
        """
        Renovar sessão realizando novo login
        
        Args:
            headless: Se True, não mostra a janela do navegador
        
        Returns:
            bool: True se sucesso
        """
        # Remover cookies antigos
        if self.cookies_file.exists():
            try:
                self.cookies_file.unlink()
            except:
                pass
        
        # Fazer novo login
        return self.login_interactive(headless=headless)
    
    def clear_session(self):
        """Limpar todos os arquivos de sessão"""
        if self.cookies_file.exists():
            try:
                self.cookies_file.unlink()
            except:
                pass
        
        cookies_txt = self.session_dir / "cookies.txt"
        if cookies_txt.exists():
            try:
                cookies_txt.unlink()
            except:
                pass


if __name__ == "__main__":
    # Teste da funcionalidade
    auth = GoogleAuthManager()
    
    if not auth.has_valid_session():
        print("Nenhuma sessão válida encontrada.")
        print("Iniciando login interativo...")
        auth.login_interactive(headless=False)
    else:
        print("Sessão válida encontrada.")
    
    # Mostrar cookies em formato wget
    cookies_file = auth.get_cookies_for_wget()
    if cookies_file:
        print(f"Arquivo de cookies criado: {cookies_file}")
