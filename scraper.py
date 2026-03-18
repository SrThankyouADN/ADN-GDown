#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs

url = "https://www.estudioarmon.com.br/p/actionhiken.html"

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'utf-8'
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Procura por links do Google Drive
    drive_links = {}
    
    # Padrão 1: Links diretos do Google Drive
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        if 'drive.google.com' in href and '/file/d/' in href:
            # Extrai o ID do arquivo
            match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', href)
            if match:
                file_id = match.group(1)
                clean_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                
                # Procura por "Revista Action Hiken" no texto
                if 'Revista Action Hiken' in text or 'Action Hiken' in text:
                    drive_links[clean_url] = text if text else f"Revista Action Hiken"
    
    # Padrão 2: Procura por títulos mencionando "Revista Action Hiken" e links nas proximidades
    all_text = soup.get_text()
    
    # Padrão 3: Procura por td ou divs com números de edições
    for div in soup.find_all(['div', 'td', 'p']):
        text_content = div.get_text(strip=True)
        # Procura por padrões como "Revista Action Hiken #123"
        if re.search(r'Revista\s+Action\s+Hiken\s+#\d+', text_content):
            # Procura por links do Google Drive próximos
            for link in div.find_all('a', href=True):
                href = link.get('href', '')
                if 'drive.google.com' in href:
                    match = re.search(r'/file/d/([a-zA-Z0-9-_]+)', href)
                    if match:
                        file_id = match.group(1)
                        clean_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                        # Extrai do texto original
                        match_title = re.search(r'Revista\s+Action\s+Hiken\s+#\d+[^<]*', text_content)
                        if match_title:
                            drive_links[clean_url] = match_title.group(0)
    
    # Salva em arquivo BAT
    if drive_links:
        with open('download.bat', 'w', encoding='utf-8') as f:
            f.write('@echo off\nREM Lista de downloads da Revista Action Hiken\nREM\n\n')
            
            for url_drive, titulo in drive_links.items():
                f.write(f'REM {titulo}\n')
                f.write(f'REM {url_drive}\n')
                f.write('echo.\n\n')
        
        print(f"Encontrados {len(drive_links)} links do Google Drive")
        print("\nLinks encontrados:")
        for url_drive, titulo in drive_links.items():
            print(f"{url_drive}  {titulo}")
    else:
        print("Nenhum link do Google Drive encontrado com títulos Revista Action Hiken")
        print("\nVerificando links Google Drive na página...")
        
        all_links = soup.find_all('a', href=True)
        drive_found = False
        
        for link in all_links:
            href = link.get('href', '')
            if 'drive.google.com' in href:
                print(f"Google Drive encontrado: {href[:80]}...")
                drive_found = True
        
        if not drive_found:
            print("Nenhum link do Google Drive foi encontrado na página.")
            print("Verifique se a página tem links do tipo: https://drive.google.com/...")
            
except Exception as e:
    print(f"Erro ao fazer o scraping: {e}")
    import traceback
    traceback.print_exc()
