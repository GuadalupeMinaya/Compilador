@echo off
REM Empaqueta la interfaz del mini-C ampliado. En Windows el lexer portatil
REM incluido permite usar todas las nuevas instrucciones sin Flex ni GCC.
REM Requiere: py -m pip install pyinstaller
py -m PyInstaller --noconfirm --onefile --windowed --name CompiladorMiniC_JS --hidden-import lexico_portable --hidden-import sintactico --hidden-import semantico --hidden-import traductor --hidden-import intermedio --hidden-import motor --hidden-import diagnosticos gui.py
pause
