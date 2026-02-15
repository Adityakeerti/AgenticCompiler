@echo off
echo ============================================
echo    CPY Language - Installer
echo ============================================
echo.

:: Check Java
where java >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Java not found. Please install JDK 8 or later.
    echo         Download: https://adoptium.net
    pause
    exit /b 1
)

where javac >nul 2>nul
if errorlevel 1 (
    echo [ERROR] javac not found. Please install JDK (not just JRE).
    echo         Download: https://adoptium.net
    pause
    exit /b 1
)

echo [OK] Java found.
echo.

:: Compile
echo [1/3] Compiling CPY compiler...
set "CPYDIR=%~dp0"
javac -d "%CPYDIR%out" "%CPYDIR%src\Main.java" "%CPYDIR%src\lexer\*.java" "%CPYDIR%src\parser\*.java" "%CPYDIR%src\ast\*.java" "%CPYDIR%src\semantic\*.java" "%CPYDIR%src\compiler\*.java" "%CPYDIR%src\vm\*.java"
if errorlevel 1 (
    echo [ERROR] Compilation failed.
    pause
    exit /b 1
)
echo [OK] Compiled successfully.
echo.

:: Add to PATH
echo [2/3] Adding CPY to system PATH...
set "CURRENT_PATH=%PATH%"
echo %CURRENT_PATH% | findstr /i /c:"%CPYDIR%" >nul
if errorlevel 1 (
    setx PATH "%PATH%;%CPYDIR%" >nul 2>nul
    echo [OK] Added to PATH.
) else (
    echo [OK] Already in PATH.
)
echo.

:: Verify
echo [3/3] Verifying installation...
echo let x = 42; > "%CPYDIR%_verify.cpy"
echo print(x); >> "%CPYDIR%_verify.cpy"
java -cp "%CPYDIR%out" Main compile "%CPYDIR%_verify.cpy" >nul 2>nul
java -cp "%CPYDIR%out" Main run "%CPYDIR%_verify.cpyc" > "%CPYDIR%_verify_out.txt" 2>nul
set /p RESULT=<"%CPYDIR%_verify_out.txt"
del "%CPYDIR%_verify.cpy" "%CPYDIR%_verify.cpyc" "%CPYDIR%_verify_out.txt" >nul 2>nul

if "%RESULT%"=="42" (
    echo [OK] Verification passed!
) else (
    echo [WARNING] Verification failed. Installation may be incomplete.
)

echo.
echo ============================================
echo    Installation complete!
echo    Close and reopen your terminal, then:
echo.
echo    cpy compile run yourfile.cpy
echo ============================================
pause
