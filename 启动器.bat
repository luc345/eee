@echo off
rem ============================================================
rem  OJ homework automation - one click launcher
rem
rem  Order of preference:
rem    1) run oj_share\oj_setup.py with a real python.exe
rem       -> the process IS the trusted Python interpreter, so
rem          Windows "unknown program" / firewall dialogs are less likely
rem    2) fall back to OJ作业自动化配置助手.exe (nothing to install)
rem
rem  Keep this file together with the exe (and oj_share if present).
rem  NOTE: this file must stay CRLF; LF line endings break cmd.exe.
rem ============================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
title OJ 作业自动化

set "ROOT=%~dp0"
set "EXE=%ROOT%OJ作业自动化配置助手.exe"
set "SRC=%ROOT%oj_share\oj_setup.py"

rem ---------- 1) locate a python ----------
set "PY="
for %%V in ("%USERPROFILE%\.workbuddy\binaries\python\versions") do (
  if exist %%V (
    for /f "delims=" %%D in ('dir /b /ad /o-n %%V 2^>nul') do (
      if exist "%%~V\%%D\python.exe" if not defined PY set "PY=%%~V\%%D\python.exe"
    )
  )
)
if not defined PY for /f "delims=" %%P in ('where python.exe 2^>nul') do (
  if not defined PY set "PY=%%P"
)
if not defined PY for /f "delims=" %%P in ('where python3.exe 2^>nul') do (
  if not defined PY set "PY=%%P"
)

rem ---------- 2) prefer the .py path ----------
if defined PY if exist "%SRC%" (
  echo   用 Python 运行（进程是已受信任的 python.exe，弹窗更少）：
  echo     Python：%PY%
  echo     源码  ：%SRC%
  echo.
  "%PY%" "%SRC%"
  set "RC=!ERRORLEVEL!"
  if "!RC!"=="0" goto :done
  echo.
  echo   [提示] 用 Python 跑退出码 !RC!，改用打包版再试一次。
  echo.
)

rem ---------- 3) fall back to the exe ----------
if not exist "%EXE%" (
  echo [错误] 找不到可运行的东西：
  echo         %EXE%
  echo         或 %SRC%
  echo   请把启动器和 exe（或 oj_share 文件夹）放在同一个目录里。
  echo.
  pause
  exit /b 1
)
"%EXE%"
if errorlevel 1 (
  echo.
  echo [提示] 退出码 %ERRORLEVEL%。
  pause
)

:done
exit /b 0
