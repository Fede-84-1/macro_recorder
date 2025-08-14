import os, shutil, sys
base = os.path.abspath(os.path.dirname(__file__))
src = os.path.join(base, '.venv', 'Lib', 'site-packages', 'PySide6', 'plugins', 'platforms')
if not os.path.isdir(src):
    src = os.path.join(base, '.venv', 'Lib', 'site-packages', 'PySide6', 'Qt', 'plugins', 'platforms')
if not os.path.isdir(src):
    print("SOURCE_NOT_FOUND:", src); sys.exit(1)
dst = os.path.join(base, 'dist', 'AutoKey', 'platforms')
os.makedirs(dst, exist_ok=True)
shutil.copytree(src, dst, dirs_exist_ok=True)
print("COPIED_FROM:", src)
print("DST_LIST:")
for f in sorted(os.listdir(dst)):
    print(f)
