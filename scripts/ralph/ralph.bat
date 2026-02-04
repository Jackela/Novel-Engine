@echo off
REM Ralph for Windows - Using --continue instead of --print
REM This avoids the --print hanging bug on Windows

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PRD_FILE=%SCRIPT_DIR%prd.json
set MAX_ITERATIONS=10

REM Parse arguments
set MAX_ITERATIONS=10
:parse_args
if "%~1"=="" goto done_parsing
if "%~1"=="--tool" (
    shift
    shift
    goto parse_args
)
if "%~1"=="--tool=*" (
    shift
    goto parse_args
)
echo %~1| findstr /R "^[0-9][0-9]*$" >nul
if !errorlevel! equ 0 (
    set MAX_ITERATIONS=%~1
)
shift
goto parse_args
:done_parsing

echo Starting Ralph - Tool: claude - Max iterations: %MAX_ITERATIONS%
echo.

for /L %%i in (1,1,%MAX_ITERATIONS%) do (
    echo ===============================================================
    echo   Ralph Iteration %%i of %MAX_ITERATIONS%
    echo ===============================================================

    REM Check if this is the first iteration
    if %%i equ 1 (
        REM First iteration - start fresh with CLAUDE.md
        type "%SCRIPT_DIR%CLAUDE.md" | claude --dangerously-skip-permissions
    ) else (
        REM Subsequent iterations - continue previous session
        echo Continuing previous session...
        claude -c --dangerously-skip-permissions
    )

    REM Check if all stories are complete
   REM We'd need to parse the JSON, but for now just continue

    echo Iteration %%i complete. Continuing...
    timeout /t 2 /nobreak >nul
)

echo.
echo Ralph reached max iterations (%MAX_ITERATIONS%).
echo Check %PROGRESS_FILE% for status.

endlocal
