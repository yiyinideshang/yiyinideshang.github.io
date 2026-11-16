@echo off
chcp 65001 >nul
cd /d "%~dp0"

git add -A
git diff --cached --quiet
if errorlevel 1 goto changed

echo 没有改动，不需要推送。
pause
exit /b

:changed
set msg=update: %date% %time%
git commit -m "%msg%"
git push -u origin main
if errorlevel 1 goto failed

echo.
echo 推送成功。等 30 秒左右，刷新网页即可。
pause
exit /b

:failed
echo.
echo 推送失败。先确认 Steam++ / 代理已开启，或改用 GitHub Desktop 推送。
pause
