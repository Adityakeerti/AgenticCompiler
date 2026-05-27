@echo off
echo ============================================
echo    CPY Agent -- TensorBoard Dashboard
echo ============================================
echo.
echo Starting TensorBoard on http://localhost:6006
echo Press Ctrl+C to stop.
echo.
tensorboard --logdir ./tb_logs --port 6006
