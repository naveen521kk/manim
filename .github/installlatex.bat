@echo off
echo "Download miktexsetup and Uzip it"
wget -q https://miktex.org/download/ctan/systems/win32/miktex/setup/windows-x86/miktexsetup-4.0.zip --no-check-certificate -O miktexsetup-4.0-x64.zip
unzip ./miktexsetup-4.0-x64.zip
echo "Starting Miktex Install"
miktexsetup.exe ^
  --verbose ^
  --modify-path ^
  --local-package-repository="C:\temp\miktex" ^
  --package-set=basic ^
  --shared=yes ^
  download
echo "Completed Downloading Installing Now"
miktexsetup.exe ^
  --verbose ^
  --modify-path ^
  --local-package-repository="C:\temp\miktex" ^
  --user-config="<APPDATA>\MiKTeX" ^
  --user-data="<LOCALAPPDATA>\MiKTeX" ^
  --user-install="<APPDATA>\MiKTeX" ^
  --package-set=basic ^
  install
dir "C:\Program Files\MiKTeX\miktex\bin\x64\"
dir "C:\Program Files\MiKTeX\miktex\bin\x86\"
setx PATH "%PATH%;C:\Program Files\MiKTeX\miktex\bin\x64\"
setx PATH "%PATH%;C:\Program Files\MiKTeX\miktex\bin\x86\"
set PATH=%PATH%;C:\Program Files\MiKTeX\miktex\bin\x86\
set PATH=%PATH%;C:\Program Files\MiKTeX\miktex\bin\x64\
refreshenv
mpm --admin --update
mpm --admin --install=standalone --install=preview --install=doublestroke --install=relsize --install=fundus-calligra --install=wasysym --install=physics --install=rsfs --install=wasy --install=cm-super
latex --version
latex intro.tex
