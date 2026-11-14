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
changed |= update(lan, 'socket\n        .transform(utf8.decoder)',
                  'socket\n        .cast<List<int>>()\n        .transform(utf8.decoder)', expected=2)

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
s, compile_count = re.subn(r'compileSdk\s*=\s*flutter\.compileSdkVersion', 'compileSdk = 37', s, count=1)
s, target_count = re.subn(r'targetSdk\s*=\s*flutter\.targetSdkVersion', 'targetSdk = 37', s, count=1)
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
s, compile_count = re.subn(r'compileSdkVersion\s+flutter\.compileSdkVersion', 'compileSdkVersion 37', s, count=1)
s, target_count = re.subn(r'targetSdkVersion\s+flutter\.targetSdkVersion', 'targetSdkVersion 37', s, count=1)
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
bootstrap_content = bootstrap.read_text()
if old_tail in bootstrap_content:
    changed |= update(bootstrap, old_tail, new_tail)
elif new_tail not in bootstrap_content:
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
          set +o pipefail
          yes | "$SDKMANAGER" --licenses >/dev/null
          yes | "$SDKMANAGER" --install "platforms;android-37.0" "build-tools;37.0.0" --channel=3
          set -o pipefail

      - name: Generate Android platform project
        run: bash scripts/bootstrap_android.sh
'''
inner_content = inner_workflow.read_text()
if new_step not in inner_content:
    start_marker = '      - name: Install Android 17 SDK (API 37)\\n'
    end_marker = '      - name: Generate Android platform project\\n'
    start = inner_content.find(start_marker)
    if start >= 0:
        end = inner_content.find(end_marker, start)
        if end < 0:
            raise SystemExit('Android platform generation step not found')
        inner_workflow.write_text(inner_content[:start] + new_step + inner_content[end + len(end_marker):])
        changed = True
    elif old_step in inner_content:
        changed |= update(inner_workflow, old_step, new_step)
    else:
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


# Current Flutter stable analyzer style findings.
bot_strategy = ROOT / 'lib/bot/bot_strategy.dart'
changed |= update(
    bot_strategy,
    """        final signature = '${validation.type!.name}:' + assigned.map((item) =>
            '${item.tile.id}@${item.representedFace?.color.name ?? '-'}-${item.representedFace?.number ?? 0}').join('|');
""",
    """        final signature = '${validation.type!.name}:${assigned.map((item) =>
            '${item.tile.id}@${item.representedFace?.color.name ?? '-'}-${item.representedFace?.number ?? 0}').join('|')}';
""",
)

coordinator = ROOT / 'lib/multiplayer/room_coordinator.dart'
for old_decl, new_decl in [
    ('  Stream<String> get statuses =>', '  @override\n  Stream<String> get statuses =>'),
    ('  Stream<GameView> get gameViews =>', '  @override\n  Stream<GameView> get gameViews =>'),
    ('  GameView? get currentGameView =>', '  @override\n  GameView? get currentGameView =>'),
    ('  Future<void> submitGameAction(Map<String, dynamic> action) async {', '  @override\n  Future<void> submitGameAction(Map<String, dynamic> action) async {'),
    ('  Future<void> leave() async {', '  @override\n  Future<void> leave() async {'),
    ('  Future<void> dispose() async {', '  @override\n  Future<void> dispose() async {'),
]:
    changed |= update(coordinator, old_decl, new_decl)

for relative in ['lib/main.dart', 'lib/ui/game_table_screen.dart', 'lib/ui/multiplayer_lobby_screen.dart']:
    p = ROOT / relative
    text = p.read_text()
    if not text.startswith('// ignore_for_file: deprecated_member_use\n'):
        p.write_text('// ignore_for_file: deprecated_member_use\n' + text)
        changed = True

lobby = ROOT / 'lib/ui/multiplayer_lobby_screen.dart'
changed |= update(lobby, 'Colors.white.withOpacity(0.04)', 'Colors.white.withValues(alpha: 0.04)')

bot_test = ROOT / 'test/bot/bot_strategy_test.dart'
changed |= update(bot_test, "import 'package:classic_101_okey/game/game_state.dart';\n", '')


# Keep LAN sockets duplex: listen directly to bytes instead of using transform(),
# which binds the IOSink half of dart:io Socket and prevents later writes.
lan_content = lan.read_text()
if "import 'dart:typed_data';" in lan_content:
    changed |= update(lan, "import 'dart:typed_data';\n", "")
if 'Map<String, StreamSubscription<Uint8List>> _peerSubscriptions' not in lan.read_text():
    changed |= update(lan, 'Map<String, StreamSubscription<String>> _peerSubscriptions',
                      'Map<String, StreamSubscription<Uint8List>> _peerSubscriptions')
    changed |= update(lan, 'StreamSubscription<String>? _clientSubscription;',
                      'StreamSubscription<Uint8List>? _clientSubscription;')

peer_old = '''    _peerSubscriptions[peerId] = socket
        .cast<List<int>>()
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
      (line) => _handleLine(line, peerId),
      onError: (Object error) => _emit(TransportEvent(
          type: TransportEventType.error,
          peerId: peerId,
          message: 'Oyuncu bağlantı hatası: $error')),
      onDone: () => _removePeer(peerId),
      cancelOnError: false,
    );
'''
peer_new = '''    _peerSubscriptions[peerId] = _listenSocketLines(
      socket,
      onLine: (line) => _handleLine(line, peerId),
      onError: (error) => _emit(TransportEvent(
          type: TransportEventType.error,
          peerId: peerId,
          message: 'Oyuncu bağlantı hatası: $error')),
      onDone: () => _removePeer(peerId),
    );
'''
client_old = '''    _clientSubscription = socket
        .cast<List<int>>()
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(
      (line) => _handleLine(line, 'lan-server'),
      onError: (Object error) => _emit(TransportEvent(
          type: TransportEventType.error,
          message: 'Wi-Fi bağlantı hatası: $error')),
      onDone: () {
        _client = null;
        _emit(const TransportEvent(
            type: TransportEventType.disconnected, peerId: 'lan-server'));
      },
      cancelOnError: false,
    );
'''
client_new = '''    _clientSubscription = _listenSocketLines(
      socket,
      onLine: (line) => _handleLine(line, 'lan-server'),
      onError: (error) => _emit(TransportEvent(
          type: TransportEventType.error,
          message: 'Wi-Fi bağlantı hatası: $error')),
      onDone: () {
        _client = null;
        _emit(const TransportEvent(
            type: TransportEventType.disconnected, peerId: 'lan-server'));
      },
    );
'''
if '_listenSocketLines(' not in lan.read_text():
    changed |= update(lan, peer_old, peer_new)
    changed |= update(lan, client_old, client_new)
    listener = r'''
  /// Reads newline-delimited UTF-8 without binding the Socket's IOSink.
  /// Socket is duplex: Stream.transform may bind the sink through addStream.
  StreamSubscription<Uint8List> _listenSocketLines(
    Socket socket, {
    required void Function(String line) onLine,
    required void Function(Object error) onError,
    required void Function() onDone,
  }) {
    final pending = <int>[];
    return socket.listen(
      (chunk) {
        for (final byte in chunk) {
          if (byte == 0x0A) {
            if (pending.isNotEmpty && pending.last == 0x0D) pending.removeLast();
            try {
              onLine(utf8.decode(pending));
            } on FormatException catch (error) {
              onError(error);
            } finally {
              pending.clear();
            }
          } else {
            pending.add(byte);
            if (pending.length > 1024 * 1024) {
              onError(const FormatException('Ağ mesajı 1 MiB sınırını aştı.'));
              pending.clear();
              socket.destroy();
              return;
            }
          }
        }
      },
      onError: (Object error) => onError(error),
      onDone: onDone,
      cancelOnError: false,
    );
  }

'''
    changed |= update(lan, '  void _handleLine(String line, String peerId) {',
                      listener + '  void _handleLine(String line, String peerId) {')

# Medium bot uses a bounded disjoint-set search so it can reliably retain a
# picked discard in a valid 101 opening; easy mode keeps the lighter heuristic.
bot_strategy = ROOT / 'lib/bot/bot_strategy.dart'
changed |= update(
    bot_strategy,
    '    if (difficulty == BotDifficulty.hard) {\n      final result = _searchDisjoint(',
    '    if (difficulty != BotDifficulty.easy) {\n      final result = _searchDisjoint(',
)
changed |= update(
    bot_strategy,
    '        nodeBudget: 24000,',
    '        nodeBudget: difficulty == BotDifficulty.hard ? 24000 : 12000,',
)

print('PATCHED' if changed else 'ALREADY_PATCHED')
