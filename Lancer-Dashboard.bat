@echo off
title BTC Dashboard
cd /d "%~dp0"
echo.
echo  Lancement du dashboard BTC...
echo  Le navigateur va s'ouvrir tout seul dans quelques secondes.
echo  Pour arreter le dashboard : ferme cette fenetre.
echo.
".venv\Scripts\streamlit.exe" run app.py
pause
