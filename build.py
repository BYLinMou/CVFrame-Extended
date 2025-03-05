import os
import shutil
import subprocess

# 清理旧的构建目录
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# 使用 PyInstaller 打包，并指定图标
subprocess.run(['pyinstaller', 'main.py', '--onefile', '--windowed', '--name=CVFrameLabeler', '--icon=icon.ico'])

# 复制必要的资源文件到 dist 目录
# if os.path.exists('videos'):
#     shutil.copytree('videos', 'dist/videos')

print("Build completed! The executable is in the 'dist' directory.")
print("Note: This is a Beta version. Some features may be unstable or incomplete.") 