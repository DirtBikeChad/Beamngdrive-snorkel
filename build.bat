@echo off
rem Packages the mod into dist\UniversalSnorkel.zip with the correct BeamNG
rem layout (lua\ and scripts\ at the top level of the zip).
cd /d "%~dp0"
if not exist dist mkdir dist
if exist dist\UniversalSnorkel.zip del dist\UniversalSnorkel.zip
powershell -NoProfile -Command "Compress-Archive -Path 'lua','scripts' -DestinationPath 'dist\UniversalSnorkel.zip' -Force"
echo Built dist\UniversalSnorkel.zip
