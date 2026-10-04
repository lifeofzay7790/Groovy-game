@echo off
rem Leafy Manor launcher helper (called by "Play Leafy Manor.bat" and "Build Leafy Manor.bat").
rem Finds UnrealEditor.exe and uses only the bundled standalone Leafy Manor project,
rem and remembers the answers in local_paths.cfg next to this file (not committed; delete it to ask again).
rem Sets UE_EDITOR, UPROJECT and PROJDIR. The caller must use "setlocal EnableDelayedExpansion".
set "CFG=%~dp0local_paths.cfg"
if exist "%CFG%" for /f "usebackq tokens=1,* delims==" %%a in ("%CFG%") do (
  if /i "%%a"=="UE_EDITOR" set "UE_EDITOR=%%b"
)
if defined UE_EDITOR if not exist "!UE_EDITOR!" set "UE_EDITOR="
if defined UPROJECT if not exist "!UPROJECT!" set "UPROJECT="

rem ---- Unreal Editor: the newest UE 5 install in the usual Epic Games folders
if not defined UE_EDITOR for %%r in ("%ProgramFiles%\Epic Games" "C:\Epic Games" "D:\Epic Games" "D:\Program Files\Epic Games" "E:\Epic Games") do (
  for /d %%d in ("%%~r\UE_5.*") do if exist "%%d\Engine\Binaries\Win64\UnrealEditor.exe" set "UE_EDITOR=%%d\Engine\Binaries\Win64\UnrealEditor.exe"
)
if not defined UE_EDITOR (
  echo Could not find Unreal Engine 5.
  echo Drag UnrealEditor.exe ^(in your UE folder, under Engine\Binaries\Win64^) into this window and press Enter:
  set /p "UE_EDITOR=> "
)
if defined UE_EDITOR set "UE_EDITOR=!UE_EDITOR:"=!"
if not defined UE_EDITOR ( echo No Unreal Editor given. & exit /b 1 )
if not exist "!UE_EDITOR!" ( echo Not found: "!UE_EDITOR!" & exit /b 1 )

rem ---- Always use the independent project shipped in this repository.
for %%f in ("%~dp0..\UnrealProject\LeafyManor\LeafyManor.uproject") do set "UPROJECT=%%~ff"
if not exist "!UPROJECT!" (
  echo Missing standalone Leafy Manor project: "!UPROJECT!"
  exit /b 1
)

> "%CFG%" (
  echo UE_EDITOR=!UE_EDITOR!
  echo UPROJECT=!UPROJECT!
)
for %%f in ("!UPROJECT!") do set "PROJDIR=%%~dpf"
echo Unreal:  !UE_EDITOR!
echo Project: !UPROJECT!
exit /b 0
