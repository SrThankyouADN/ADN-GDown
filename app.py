#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Launcher para ADN GDown
Interface para scraping e download de arquivos do Google Drive
"""

def main():
    """Lançar interface"""
    import tkinter as tk
    from downloader_gui import GoogleDriveDownloader
    
    root = tk.Tk()
    app = GoogleDriveDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
