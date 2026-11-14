#!/usr/bin/env python3
"""Apply the Android 16/17 and Dart socket compatibility fixes to the source ZIP checkout."""
from pathlib import Path
import re

ROOT = Path('101_okey')


def update(path: Path, old: str, new: str, expected: int = 1) -> bool:
    content = path.read_text()
    count = content.count(old)
    if count == 0:
        if new in content:
            return False
        raise SystemExit(f'Expected patch point not found in {path}: {old[:80]!r}')
    if count != expected:
        raise SystemExit(f'Expected {expected} patch points in {path}, found {count}')
    path.write_text(content.replace(old, new))
    return True

changed = False

lan = ROOT / 'lib/multiplayer/lan_transport.dart'
changed |= update(
    lan,
    'socket\n        .transform(utf8.decoder)',
    'socket\n        .cast<List<int>>()\n        .transform(utf8.decoder)',
    expected=2,
)

bootstrap = ROOT / 'scripts/bootstrap_android.sh'
old_tail = '''cp "$ROOT/android_template/app/src/main/kotlin/com/example/classic_101_okey/MainActivity.kt" \\
  "$ROOT/android/app/src/main/kotlin/com/example/classic_101_okey/MainActivity.kt"
echo "Android platform klasörü oluşturuldu ve Wi-Fi yerel ağ entegrasyonu eklendi."
echo "Sonraki adım: flutter pub get && flutter test && flutter build apk --debug"
'''
new_tail = '''cp "$ROOT/android_template/app/src/main/kotlin/com/example/classic_101_okey/MainActivity.kt" \\
  "$ROOT/android/app/src/main/kotlin/com/example/classic_101_okey/MainActivity.kt"

# Android 17 is API 37. Targeting API 37 enables ACCESS_LOCAL_NETWORK;
# Android 16 (API 36) remains supported and does not show this permission prompt.
GRADLE_KTS="$ROOT/android/app/build.gradle.kts"
GRADLE_GROOVY="$ROOT/android/app/build.gradle"
if [[ -f "$GRADLE_KTS" ]]; then
  python3 - "$GRADLE_KTS" <<'PYTHON'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
s = p.read_text()
s, compile_count = re.subn(r'compileSdk\\s*=\\s*flutter\\.compileSdkVersion', 'compileSdk = 37', s, count=1)
s, target_count = re.subn(r'targetSdk\\s*=\\s*flutter\\.targetSdkVersion', 'targetSdk = 37', s, count=1)
if compile_count != 1 or target_count != 1:
    raise SystemExit('Gradle Kotlin DSL: compileSdk/targetSdk API 37 ayarlanamadı.')
p.write_text(s)
PYTHON
elif [[ -f "$GRADLE_GROOVY" ]]; then
  python3 - "$GRADLE_GROOVY" <<'PYTHON'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
s = p.read_text()
s, compile_count = re.subn(r'compileSdkVersion\\s+flutter\\.compileSdkVersion', 'compileSdkVersion 37', s, count=1)
s, target_count = re.subn(r'targetSdkVersion\\s+flutter\\.targetSdkVersion', 'targetSdkVersion 37', s, count=1)
if compile_count != 1 or target_count != 1:
    raise SystemExit('Gradle Groovy: compileSdk/targetSdk API 37 ayarlanamadı.')
p.write_text(s)
PYTHON
else
  echo "Android app Gradle dosyası bulunamadı." >&2
  exit 1
fi

echo "Android platformu oluşturuldu; compileSdk/targetSdk 37 (Android 17) olarak ayarlandı."
echo "Android 16 (API 36) uyumluluğu korunuyor."
'''
if old_tail in bootstrap.read_text():
    changed |= update(bootstrap, old_tail, new_tail)
elif new_tail not in bootstrap.read_text():
    raise SystemExit('Android bootstrap patch point not found')

inner_workflow = ROOT / '.github/workflows/android-apk.yml'
old_step = '''      - name: Generate Android platform project
        run: bash scripts/bootstrap_android.sh
'''
new_step = '''      - name: Install Android 17 SDK (API 37)
        shell: bash
        run: |
          SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
          if [[ -z "$SDK_ROOT" ]]; then
            echo "ANDROID_HOME / ANDROID_SDK_ROOT tanımlı değil." >&2
            exit 1
          fi
          SDKMANAGER="$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager"
          if [[ ! -x "$SDKMANAGER" ]]; then
            SDKMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -name sdkmanager -print -quit)"
          fi
          if [[ ! -x "$SDKMANAGER" ]]; then
            echo "Android sdkmanager bulunamadı." >&2
            exit 1
          fi
          yes | "$SDKMANAGER" --licenses >/dev/null
          yes | "$SDKMANAGER" --install "platforms;android-37" "build-tools;37.0.0"

      - name: Generate Android platform project
        run: bash scripts/bootstrap_android.sh
'''
if old_step in inner_workflow.read_text():
    changed |= update(inner_workflow, old_step, new_step)
elif new_step not in inner_workflow.read_text():
    raise SystemExit('Android workflow patch point not found')

pubspec = ROOT / 'pubspec.yaml'
changed |= update(pubspec, 'version: 0.7.0+7', 'version: 0.7.1+8')

readme = ROOT / 'README.md'
section = '''## Android OS and SDK compatibility

- Android 16 (API 36) and Android 17 (API 37) are supported.
- Release builds compile and target Android 17 (API 37).
- Android 17 requires the runtime `ACCESS_LOCAL_NETWORK` permission for direct same-Wi-Fi TCP play; the app requests it before opening the LAN socket.
- On Android 16, the app does not request the API 37-only permission.

'''
marker = '## Development environment\n'
if section not in readme.read_text():
    changed |= update(readme, marker, section + marker)

print('PATCHED' if changed else 'ALREADY_PATCHED')
