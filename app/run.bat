@echo off
REM Helper untuk menjalankan server di Windows
pushd "%~dp0.."
python -m app.backend.app
popd
