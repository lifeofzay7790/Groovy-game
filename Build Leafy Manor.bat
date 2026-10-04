@echo off
setlocal EnableDelayedExpansion
rem Build or rebuild the Leafy Manor level in your Unreal project: opens the editor and runs
rem LeafyManor\Unreal\Python\leafy_manor_build.py (needs the Python Editor Script Plugin enabled in the project).
rem Run it once, and again after you pull new changes. Then press Play in the editor, or use "Play Leafy Manor.bat".
title Leafy Manor - build
call "%~dp0LeafyManor\Unreal\find_unreal.bat" || goto :fail
set "BUILD=%~dp0LeafyManor\Unreal\Python\leafy_manor_build.py"
if not exist "!BUILD!" ( echo Missing "!BUILD!" & goto :fail )
echo Opening Unreal and building the level. The first build imports the models and takes a few minutes.
echo When it finishes, the level is open: press Play in the editor, or close Unreal and run "Play Leafy Manor.bat".
start "" "!UE_EDITOR!" "!UPROJECT!" -ExecutePythonScript="!BUILD!"
exit /b 0

:fail
echo.
pause
exit /b 1
