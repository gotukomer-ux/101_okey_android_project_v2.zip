from pathlib import Path

project = Path("101_okey")
if not project.is_dir():
    raise SystemExit("Expected extracted project folder: 101_okey")

def replace_once(relative_path: str, old: str, new: str, count: int = 1) -> None:
    path = project / relative_path
    source = path.read_text(encoding="utf-8")
    occurrences = source.count(old)
    if occurrences < count:
        raise SystemExit(f"Patch context not found in {relative_path}: {old!r}")
    path.write_text(source.replace(old, new, count), encoding="utf-8")

# Avoid StreamSink extension methods on dart:io Socket, which is also a
# writable sink. Read the raw byte stream and split complete UTF-8 lines
# without transforming or casting the Socket object itself.
replace_once(
    "lib/multiplayer/lan_transport.dart",
    "import 'dart:io';",
    "import 'dart:io';\nimport 'dart:typed_data';",
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    "StreamSubscription<String>",
    "StreamSubscription<Uint8List>",
    count=2,
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    """_peerSubscriptions[peerId] = socket
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
    );""",
    """_peerSubscriptions[peerId] = _listenLines(
      socket,
      (line) => _handleLine(line, peerId),
      (error) => _emit(TransportEvent(
          type: TransportEventType.error,
          peerId: peerId,
          message: 'Oyuncu bağlantı hatası: $error')),
      () => _removePeer(peerId),
    );""",
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    """_clientSubscription = socket
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
    );""",
    """_clientSubscription = _listenLines(
      socket,
      (line) => _handleLine(line, 'lan-server'),
      (error) => _emit(TransportEvent(
          type: TransportEventType.error,
          message: 'Wi-Fi bağlantı hatası: $error')),
      () {
        _client = null;
        _emit(const TransportEvent(
            type: TransportEventType.disconnected, peerId: 'lan-server'));
      },
    );""",
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    "  void _handleLine(String line, String peerId) {",
    """  StreamSubscription<Uint8List> _listenLines(
    Socket socket,
    void Function(String) onLine,
    void Function(Object) onError,
    void Function() onDone,
  ) {
    final pending = <int>[];
    return socket.listen(
      (chunk) {
        pending.addAll(chunk);
        var consumed = 0;
        for (var index = 0; index < pending.length; index++) {
          if (pending[index] != 10) continue;
          final bytes = pending.sublist(consumed, index);
          if (bytes.isNotEmpty && bytes.last == 13) bytes.removeLast();
          try {
            onLine(utf8.decode(bytes));
          } on FormatException catch (error) {
            onError(error);
          }
          consumed = index + 1;
        }
        if (consumed > 0) pending.removeRange(0, consumed);
      },
      onError: onError,
      onDone: onDone,
      cancelOnError: false,
    );
  }

  void _handleLine(String line, String peerId) {""",
)

# The protocol test also reads Socket byte streams; Stream.map avoids
# invoking a StreamSink cast extension during UTF-8 conversion.
replace_once(
    "test/multiplayer/protocol_test.dart",
    ".transform(utf8.decoder)",
    ".map((chunk) => chunk as List<int>)\n          .transform(utf8.decoder)",
)

# Import the paired-device model in the lobby where its type is displayed.
replace_once(
    "lib/ui/multiplayer_lobby_screen.dart",
    "import '../multiplayer/room_state.dart';",
    "import '../multiplayer/room_state.dart';\nimport '../multiplayer/transport_event.dart';",
)

# Tests construct MeldTile values, so import their defining library explicitly.
replace_once(
    "test/bot/bot_strategy_test.dart",
    "import 'package:classic_101_okey/domain/tile.dart';",
    "import 'package:classic_101_okey/domain/tile.dart';\nimport 'package:classic_101_okey/domain/meld.dart';",
)
replace_once(
    "test/game/game_engine_test.dart",
    "import 'package:classic_101_okey/domain/tile.dart';",
    "import 'package:classic_101_okey/domain/tile.dart';\nimport 'package:classic_101_okey/domain/meld.dart';",
)

# Remove an unused test import.
replace_once(
    "test/bot/bot_strategy_test.dart",
    "import 'package:classic_101_okey/game/game_state.dart';\n",
    "",
)

# When an opening must include a just-taken discard, use disjoint search for
# every bot difficulty instead of a greedy candidate ordering.
replace_once(
    "lib/bot/bot_strategy.dart",
    "if (difficulty == BotDifficulty.hard) {\n      final result = _searchDisjoint(",
    "if (difficulty == BotDifficulty.hard || requiredTileId != null) {\n      final result = _searchDisjoint(",
)

# Put meld candidates containing the required discard first during the search.
replace_once(
    "lib/bot/bot_strategy.dart",
    "final ordered = [...candidates]..sort((a, b) => b.points.compareTo(a.points));",
    """final ordered = [...candidates]..sort((a, b) {
      if (requiredTileId != null) {
        final aHasRequired = a.ids.contains(requiredTileId);
        final bHasRequired = b.ids.contains(requiredTileId);
        if (aHasRequired != bHasRequired) return aHasRequired ? -1 : 1;
      }
      return b.points.compareTo(a.points);
    });""",
)

print("Applied compile, bot opening, and raw LAN socket listener fixes.")
