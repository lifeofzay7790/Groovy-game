@echo off
rem Leafy Manor launcher helper (called by "Play Leafy Manor.bat" and "Build Leafy Manor.bat").
rem Finds UnrealEditor.exe and the Unreal project (.uproject) that holds the level, asks when it can't tell,
rem and remembers the answers in local_paths.cfg next to this file (not committed; delete it to ask again).
rem Sets UE_EDITOR, UPROJECT and PROJDIR. The caller must use "setlocal EnableDelayedExpansion".
set "CFG=%~dp0local_paths.cfg"
if exist "%CFG%" for /f "usebackq tokens=1,* delims==" %%a in ("%CFG%") do (
  if /i "%%a"=="UE_EDITOR" set "UE_EDITOR=%%b"
  if /i "%%a"=="UPROJECT" set "UPROJECT=%%b"
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

rem ---- Project: look in Documents\Unreal Projects (also the OneDrive copy of Documents)
if not defined UPROJECT (
  set /a LM_N=0
  for %%r in ("%USERPROFILE%\Documents\Unreal Projects" "%USERPROFILE%\OneDrive\Documents\Unreal Projects") do (
    for /d %%p in ("%%~r\*") do for %%f in ("%%p\*.uproject") do (
      set /a LM_N+=1
      set "LM_P!LM_N!=%%f"
    )
  )
  if !LM_N! EQU 1 set "UPROJECT=!LM_P1!"
  if !LM_N! GTR 1 (
    echo Which Unreal project should open Leafy Manor? ^(the one you ran leafy_manor_build.py in^)
    for /l %%i in (1,1,!LM_N!) do echo   %%i. !LM_P%%i!
    set /p "LM_PICK=Number: "
    for %%i in (!LM_PICK!) do set "UPROJECT=!LM_P%%i!"
  )
)
if not defined UPROJECT (
  echo Drag your Unreal project's .uproject file into this window and press Enter:
  set /p "UPROJECT=> "
)
if defined UPROJECT set "UPROJECT=!UPROJECT:"=!"
if not defined UPROJECT ( echo No project given. & exit /b 1 )
if not exist "!UPROJECT!" ( echo Not found: "!UPROJECT!" & exit /b 1 )

> "%CFG%" (
  echo UE_EDITOR=!UE_EDITOR!
  echo UPROJECT=!UPROJECT!
)
for %%f in ("!UPROJECT!") do set "PROJDIR=%%~dpf"
echo Unreal:  !UE_EDITOR!
echo Project: !UPROJECT!
exit /b 0
