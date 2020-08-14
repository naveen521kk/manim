rem switch to a temp directory, whichever works
cd /d "%TMP%"
cd /d "%TEMP%"

rem download install-tl.zip and unzip it
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest http://mirror.ctan.org/systems/texlive/tlnet/install-tl.zip -OutFile install-tl.zip"
powershell -Command "& { Add-Type -A 'System.IO.Compression.FileSystem'; [IO.Compression.ZipFile]::ExtractToDirectory('install-tl.zip', '.'); }"
del install-tl.zip

rem download manim.profile and modify it (set texdir to ./TinyTeX)
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest https://github.com/naveen521kk/manim/raw/master/latex/manim.profile -OutFile tinytex.profile" || exit /b
powershell -Command "(gc tinytex.profile) -replace '\./', './Tex/' | Out-File -encoding ASCII tinytex.profile"

echo TEXMFCONFIG $TEXMFSYSCONFIG>> tinytex.profile
echo TEXMFHOME $TEXMFLOCAL>> tinytex.profile
echo TEXMFVAR $TEXMFSYSVAR>> tinytex.profile

rem download the custom package list
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest https://yihui.org/gh/tinytex/tools/pkgs-custom.txt -OutFile pkgs-custom.txt"

rem an automated installation of TeXLive (infrastructure only)
cd install-tl-*
@echo | install-tl-windows.bat -no-gui -profile=../tinytex.profile

del TinyTeX\install-tl.log ..\tinytex.profile

rem TeXLive installed to ./Tex; move it to APPDATA
rd /s /q "%APPDATA%\Tex"
rd /s /q "%APPDATA%\Tex"
move /y Tex "%APPDATA%"

rem clean up the install-tl-* directory
cd ..
for /d %%G in ("install-tl-*") do rd /s /q "%%~G"

rem install all custom packages
@echo off
setlocal enabledelayedexpansion
set "pkgs="
for /F %%a in (pkgs-custom.txt) do set "pkgs=!pkgs! %%a"
@echo on

del pkgs-custom.txt

call "%APPDATA%\Tex\bin\win32\tlmgr" path add
call "%APPDATA%\Tex\bin\win32\tlmgr" install latex-bin xetex %pkgs%

pause
