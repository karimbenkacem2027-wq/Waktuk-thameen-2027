from pathlib import Path
import re
p=Path("android/app/build.gradle")
if not p.exists(): raise SystemExit("android/app/build.gradle not found; run npx cap add android first")
s=p.read_text()
s=re.sub(r"versionCode\s+\d+", "versionCode 3", s, count=1)
s=re.sub(r'versionName\s+"[^"]+"', 'versionName "3.0.0"', s, count=1)
p.write_text(s)
print("Android version set to 3.0.0 (versionCode 3)")
