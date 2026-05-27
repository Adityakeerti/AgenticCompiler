@echo off
setlocal enabledelayedexpansion

set "OUTDIR=%~dp0out"
set "DO_COMPILE=0"
set "DO_RUN=0"
set "FILE="

:parse
if "%~1"=="" goto execute
if /i "%~1"=="compile" ( set "DO_COMPILE=1" & shift & goto parse )
if /i "%~1"=="run"     ( set "DO_RUN=1"     & shift & goto parse )
set "FILE=%~1"
shift
goto parse

:execute
if "%FILE%"=="" ( echo Usage: cpy compile run file.cpy & exit /b 1 )

if "%DO_COMPILE%"=="1" (
    java -cp "%OUTDIR%" Main compile "%FILE%"
    if errorlevel 1 exit /b 1
)

if "%DO_RUN%"=="1" (
    set "CPYC=!FILE:.cpy=.cpyc!"
    java -cp "%OUTDIR%" Main run "!CPYC!"
)

endlocal
