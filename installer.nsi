; LinkedIn AutoBot Professional Installer Script
; NSIS (Nullsoft Scriptable Install System) Script
; Creates professional Windows installer

;--------------------------------
; Includes
!include "MUI2.nsh"
!include "FileFunc.nsh"

;--------------------------------
; General Settings
Name "LinkedIn AutoBot Professional"
OutFile "LinkedInAutoBot_Professional_Setup.exe"
Unicode True

; Default installation directory
InstallDir "$PROGRAMFILES64\LinkedIn AutoBot Professional"

; Get installation folder from registry if available
InstallDirRegKey HKCU "Software\LinkedIn AutoBot Professional" ""

; Request application privileges
RequestExecutionLevel admin

;--------------------------------
; Version Information
VIProductVersion "2.0.0.0"
VIAddVersionKey "ProductName" "LinkedIn AutoBot Professional"
VIAddVersionKey "Comments" "Professional LinkedIn automation tool"
VIAddVersionKey "CompanyName" "Your Company Name"
VIAddVersionKey "LegalTrademarks" "LinkedIn AutoBot Professional"
VIAddVersionKey "LegalCopyright" "© 2025 Your Company"
VIAddVersionKey "FileDescription" "LinkedIn AutoBot Professional Installer"
VIAddVersionKey "FileVersion" "2.0.0.0"
VIAddVersionKey "ProductVersion" "2.0.0.0"
VIAddVersionKey "InternalName" "LinkedInAutoBot"
VIAddVersionKey "OriginalFilename" "LinkedInAutoBot_Professional_Setup.exe"

;--------------------------------
; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "resources\icon.ico"
!define MUI_UNICON "resources\icon.ico"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to LinkedIn AutoBot Professional Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of LinkedIn AutoBot Professional.$\r$\n$\r$\nLinkedIn AutoBot Professional is a powerful automation tool for LinkedIn job applications and networking.$\r$\n$\r$\nClick Next to continue."

; License page
!define MUI_LICENSEPAGE_TEXT_TOP "Please review the license terms before installing LinkedIn AutoBot Professional."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "If you accept the terms of the agreement, click I Agree to continue. You must accept the agreement to install LinkedIn AutoBot Professional."

; Components page
!define MUI_COMPONENTSPAGE_SMALLDESC

; Directory page
!define MUI_DIRECTORYPAGE_TEXT_TOP "Setup will install LinkedIn AutoBot Professional in the following folder. To install in a different folder, click Browse and select another folder. Click Next to continue."

; Start menu page
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "LinkedIn AutoBot Professional"
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\LinkedIn AutoBot Professional"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

; Finish page
!define MUI_FINISHPAGE_TITLE "LinkedIn AutoBot Professional Installation Complete"
!define MUI_FINISHPAGE_TEXT "LinkedIn AutoBot Professional has been successfully installed on your computer.$\r$\n$\r$\nClick Finish to close this wizard."
!define MUI_FINISHPAGE_RUN "$INSTDIR\LinkedInAutoBot.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch LinkedIn AutoBot Professional"
!define MUI_FINISHPAGE_LINK "Visit our website for support and updates"
!define MUI_FINISHPAGE_LINK_LOCATION "https://yourwebsite.com"

;--------------------------------
; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY

Var StartMenuFolder
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

;--------------------------------
; Languages
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Sections

Section "Core Application" SecCore
    SectionIn RO ; Make this section required
    
    ; Set output path to the installation directory
    SetOutPath $INSTDIR
    
    ; Program files
    File "dist\LinkedInAutoBot.exe"
    File "README.txt"
    File "LICENSE.txt"
    
    ; Configuration files
    SetOutPath $INSTDIR\config
    File /nonfatal "config\*.py"
    
    ; Templates
    SetOutPath $INSTDIR\templates
    File /r "templates\*"
    
    ; Static files
    SetOutPath $INSTDIR\static
    File /r /x ".git" "static\*"
    
    ; Chrome driver
    SetOutPath $INSTDIR\drivers
    File /nonfatal "setup\chromedriver\chromedriver.exe"
    
    ; Create data directories
    CreateDirectory "$INSTDIR\logs"
    CreateDirectory "$INSTDIR\uploads"
    CreateDirectory "$INSTDIR\exports"
    CreateDirectory "$INSTDIR\resumes"
    
    ; Store installation folder
    WriteRegStr HKCU "Software\LinkedIn AutoBot Professional" "" $INSTDIR
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Add to Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "DisplayName" "LinkedIn AutoBot Professional"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "DisplayIcon" "$INSTDIR\LinkedInAutoBot.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "Publisher" "Your Company Name"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "DisplayVersion" "2.0.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "NoRepair" 1
    
    ; Calculate and store size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional" "EstimatedSize" "$0"

SectionEnd

Section "Desktop Shortcut" SecDesktop
    CreateShortcut "$DESKTOP\LinkedIn AutoBot Professional.lnk" "$INSTDIR\LinkedInAutoBot.exe" "" "$INSTDIR\LinkedInAutoBot.exe" 0
SectionEnd

Section "Quick Launch Shortcut" SecQuickLaunch
    CreateShortcut "$QUICKLAUNCH\LinkedIn AutoBot Professional.lnk" "$INSTDIR\LinkedInAutoBot.exe" "" "$INSTDIR\LinkedInAutoBot.exe" 0
SectionEnd

Section "Chrome Extension Support" SecChrome
    ; Check if Chrome is installed
    ReadRegStr $0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" ""
    StrCmp $0 "" 0 +3
        MessageBox MB_OK "Google Chrome not found. Please install Chrome for full functionality."
        Goto +2
    DetailPrint "Chrome found at: $0"
    
    ; Create batch file for easy startup
    SetOutPath $INSTDIR
    FileOpen $9 "$INSTDIR\Start LinkedIn AutoBot.bat" w
    FileWrite $9 "@echo off$\r$\n"
    FileWrite $9 "echo Starting LinkedIn AutoBot Professional...$\r$\n"
    FileWrite $9 "echo.$\r$\n"
    FileWrite $9 "echo Dashboard will be available at: http://localhost:5000$\r$\n"
    FileWrite $9 "echo.$\r$\n"
    FileWrite $9 "echo Close this window to stop the application$\r$\n"
    FileWrite $9 "echo.$\r$\n"
    FileWrite $9 "cd /d $\"$INSTDIR$\"$\r$\n"
    FileWrite $9 "LinkedInAutoBot.exe$\r$\n"
    FileWrite $9 "pause$\r$\n"
    FileClose $9
SectionEnd

;--------------------------------
; Start Menu Shortcuts

Section "Start Menu Shortcuts" SecStartMenu
    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\LinkedIn AutoBot Professional.lnk" "$INSTDIR\LinkedInAutoBot.exe"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Start LinkedIn AutoBot.lnk" "$INSTDIR\Start LinkedIn AutoBot.bat"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\User Manual.lnk" "$INSTDIR\README.txt"
    CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    
    !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

;--------------------------------
; Component Descriptions

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core application files (required)"
!insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create desktop shortcut"
!insertmacro MUI_DESCRIPTION_TEXT ${SecQuickLaunch} "Create quick launch shortcut"
!insertmacro MUI_DESCRIPTION_TEXT ${SecChrome} "Chrome integration and startup scripts"
!insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Start menu shortcuts and documentation"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Installer Functions

Function .onInit
    ; Check if already installed
    ReadRegStr $R0 HKCU "Software\LinkedIn AutoBot Professional" ""
    StrCmp $R0 "" done
    
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
    "LinkedIn AutoBot Professional is already installed at $R0.$\n$\nClick OK to upgrade, or Cancel to quit." \
    IDOK done
    Abort
    
    done:
    
    ; Check Windows version
    ${IfNot} ${AtLeastWin10}
        MessageBox MB_OK "LinkedIn AutoBot Professional requires Windows 10 or later."
        Abort
    ${EndIf}
    
    ; Check if user has admin rights
    UserInfo::GetAccountType
    pop $0
    ${If} $0 != "admin"
        MessageBox MB_OK "Administrator privileges required for installation."
        SetErrorLevel 740 ; ERROR_ELEVATION_REQUIRED
        Abort
    ${EndIf}
FunctionEnd

Function .onInstSuccess
    ; Create registry entries for auto-update
    WriteRegStr HKCU "Software\LinkedIn AutoBot Professional" "Version" "2.0.0"
    WriteRegStr HKCU "Software\LinkedIn AutoBot Professional" "InstallDate" "$INSTDATE"
    
    ; Show success message
    MessageBox MB_OK "LinkedIn AutoBot Professional has been successfully installed!$\n$\nClick the desktop shortcut or use Start Menu to launch the application."
FunctionEnd

;--------------------------------
; Uninstaller Section

Section "Uninstall"
    ; Remove program files
    Delete "$INSTDIR\LinkedInAutoBot.exe"
    Delete "$INSTDIR\README.txt"
    Delete "$INSTDIR\LICENSE.txt"
    Delete "$INSTDIR\Start LinkedIn AutoBot.bat"
    Delete "$INSTDIR\Uninstall.exe"
    
    ; Remove directories
    RMDir /r "$INSTDIR\config"
    RMDir /r "$INSTDIR\templates"
    RMDir /r "$INSTDIR\static"
    RMDir /r "$INSTDIR\drivers"
    
    ; Ask user about data directories
    MessageBox MB_YESNO "Do you want to remove all application data (logs, uploads, exports)?$\n$\nChoose No to keep your data for future installations." IDYES removedata IDNO keepdata
    
    removedata:
        RMDir /r "$INSTDIR\logs"
        RMDir /r "$INSTDIR\uploads"
        RMDir /r "$INSTDIR\exports"
        RMDir /r "$INSTDIR\resumes"
        Delete "$INSTDIR\*.json"
        Delete "$INSTDIR\*.csv"
        Delete "$INSTDIR\*.log"
        Goto continue
    
    keepdata:
        DetailPrint "Keeping user data files"
    
    continue:
    
    ; Remove installation directory if empty
    RMDir "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$DESKTOP\LinkedIn AutoBot Professional.lnk"
    Delete "$QUICKLAUNCH\LinkedIn AutoBot Professional.lnk"
    
    ; Remove Start Menu shortcuts
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    Delete "$SMPROGRAMS\$StartMenuFolder\LinkedIn AutoBot Professional.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\Start LinkedIn AutoBot.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\User Manual.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LinkedIn AutoBot Professional"
    DeleteRegKey HKCU "Software\LinkedIn AutoBot Professional"
    
SectionEnd

Function un.onInit
    MessageBox MB_YESNO "Are you sure you want to completely remove LinkedIn AutoBot Professional and all of its components?" IDYES +2
    Abort
FunctionEnd

Function un.onUninstSuccess
    MessageBox MB_OK "LinkedIn AutoBot Professional has been successfully removed from your computer."
FunctionEnd