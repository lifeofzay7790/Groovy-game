@echo off
setlocal EnableDelayedExpansion
rem Play the Leafy Manor entrance hall in Unreal, in its own window.
rem Your project's GameMode spawns your character in the vestibule. Alt+F4 closes the game.
rem First run: it finds Unreal and your project (or asks) and remembers them.
title Leafy Manor
call "%~dp0LeafyManor\Unreal\find_unreal.bat" || goto :fail
if not exist "!PROJDIR!Content\LeafyManor\Maps\LVL_LM_EntranceHall.umap" (
  echo.
  echo The Leafy Manor level isn't built in this project yet.
  echo Run "Build Leafy Manor.bat" first ^(once, and again after you pull new changes^).
  goto :fail
)
echo Starting Leafy Manor...
start "" "!UE_EDITOR!" "!UPROJECT!" /Game/LeafyManor/Maps/LVL_LM_EntranceHall -game -windowed -ResX=1600 -ResY=900
exit /b 0

:fail
echo.
pause
exit /b 1
