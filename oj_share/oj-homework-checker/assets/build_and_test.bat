@echo off
setlocal
set "VCVARS=D:\VS\VC\Auxiliary\Build\vcvarsall.bat"
set "DIR=C:\Users\<user>\WorkBuddy\<project>\oj_homework\code\cid1766"
set "LOG=%DIR%\tests\result.txt"

call "%VCVARS%" amd64
cd /d "%DIR%"
if not exist bin mkdir bin

echo ==== BUILD ==== > "%LOG%"
for %%F in (A_seqlist_create B_seqlist_dearest C_linklist_create D_linklist_sort E_linklist_merge) do (
  echo --- compile %%F --- >> "%LOG%"
  cl /nologo /utf-8 /EHsc /std:c++17 /Fo"bin\\" /Fe"bin\%%F.exe" "%%F.cpp" >> "%LOG%" 2>&1
  if errorlevel 1 echo COMPILE_FAIL %%F >> "%LOG%"
)

echo ==== RUN ==== >> "%LOG%"
call :runtest A_seqlist_create A books.in
call :runtest B_seqlist_dearest B B.in
call :runtest C_linklist_create C books.in
call :runtest D_linklist_sort D books.in
call :runtest E_linklist_merge E E.in

echo ==== DONE ==== >> "%LOG%"
endlocal
exit /b 0

:runtest
set "SRC=%~1"
set "TAG=%~2"
set "IN=%~3"
if not exist "bin\%SRC%.exe" (
  echo [%TAG%] SKIP: exe not found >> "%LOG%"
  exit /b 0
)
"bin\%SRC%.exe" < "tests\%IN%" > "tests\%TAG%.actual" 2>>"%LOG%"
echo [%TAG%] ---- actual ---- >> "%LOG%"
type "tests\%TAG%.actual" >> "%LOG%"
echo [%TAG%] ---- expected ---- >> "%LOG%"
type "tests\%TAG%.expected" >> "%LOG%"
fc /N "tests\%TAG%.expected" "tests\%TAG%.actual" > "tests\%TAG%.diff" 2>&1
if errorlevel 1 (
  echo [%TAG%] FAIL >> "%LOG%"
) else (
  echo [%TAG%] PASS >> "%LOG%"
)
exit /b 0
