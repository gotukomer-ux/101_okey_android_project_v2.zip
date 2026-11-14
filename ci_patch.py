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

# Read Socket input as raw bytes; do not use transform/cast on the bidirectional
# Socket object, because it is also the outbound IOSink.
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

# Add a per-socket write queue. Room snapshot broadcasts and game-start views
# may be emitted concurrently; IOSink.flush must not overlap with another write.
replace_once(
    "lib/multiplayer/lan_transport.dart",
    "  final Map<String, Socket> _peers = {};",
    "  final Map<String, Socket> _peers = {};\n  final Map<Socket, Future<void>> _sendQueues = {};",
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    """  @override
  Future<void> send(Map<String, dynamic> message, {String? peerId}) async {
    final line = '${jsonEncode(message)}\\n';
    if (_isHost) {
      if (peerId != null) {
        final socket = _peers[peerId];
        if (socket == null) throw StateError('Oyuncu bağlantısı bulunamadı.');
        socket.write(line);
        await socket.flush();
      } else {
        for (final socket in _peers.values.toList()) {
          socket.write(line);
          await socket.flush();
        }
      }
    } else {
      final socket = _client;
      if (socket == null) throw StateError('Sunucuya bağlı değil.');
      socket.write(line);
      await socket.flush();
    }
  }""",
    """  Future<void> _queueWrite(Socket socket, String line) {
    final previous = _sendQueues[socket] ?? Future<void>.value();
    final operation = previous.then((_) async {
      socket.write(line);
      await socket.flush();
    });
    // Keep the queue usable after an individual send fails, while returning
    // the original error to the caller that requested that send.
    _sendQueues[socket] =
        operation.then<void>((_) {}, onError: (Object _, StackTrace __) {});
    return operation;
  }

  @override
  Future<void> send(Map<String, dynamic> message, {String? peerId}) async {
    final line = '${jsonEncode(message)}\\n';
    if (_isHost) {
      if (peerId != null) {
        final socket = _peers[peerId];
        if (socket == null) throw StateError('Oyuncu bağlantısı bulunamadı.');
        await _queueWrite(socket, line);
      } else {
        for (final socket in _peers.values.toList()) {
          await _queueWrite(socket, line);
        }
      }
    } else {
      final socket = _client;
      if (socket == null) throw StateError('Sunucuya bağlı değil.');
      await _queueWrite(socket, line);
    }
  }""",
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    """  void _removePeer(String peerId) {
    _peerSubscriptions.remove(peerId)?.cancel();
    _peers.remove(peerId)?.destroy();
    _emit(TransportEvent(
        type: TransportEventType.disconnected, peerId: peerId));
  }""",
    """  void _removePeer(String peerId) {
    _peerSubscriptions.remove(peerId)?.cancel();
    final socket = _peers.remove(peerId);
    if (socket != null) {
      _sendQueues.remove(socket);
      socket.destroy();
    }
    _emit(TransportEvent(
        type: TransportEventType.disconnected, peerId: peerId));
  }""",
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    """    if (socket != null) {
      socket.destroy();
      _emit(TransportEvent(type: TransportEventType.disconnected, peerId: peerId));
    }""",
    """    if (socket != null) {
      _sendQueues.remove(socket);
      socket.destroy();
      _emit(TransportEvent(type: TransportEventType.disconnected, peerId: peerId));
    }""",
)
replace_once(
    "lib/multiplayer/lan_transport.dart",
    """    _peers.clear();
    await _clientSubscription?.cancel();""",
    """    _peers.clear();
    _sendQueues.clear();
    await _clientSubscription?.cancel();""",
)

# Protocol test reads Socket bytes through Stream.map.
replace_once(
    "test/multiplayer/protocol_test.dart",
    ".transform(utf8.decoder)",
    ".map((chunk) => chunk as List<int>)\n          .transform(utf8.decoder)",
)

# Import paired-device model in the lobby.
replace_once(
    "lib/ui/multiplayer_lobby_screen.dart",
    "import '../multiplayer/room_state.dart';",
    "import '../multiplayer/room_state.dart';\nimport '../multiplayer/transport_event.dart';",
)

# Tests construct MeldTile values, so import their defining library.
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

# For mandatory use of a side-discard, use disjoint search at all difficulties.
replace_once(
    "lib/bot/bot_strategy.dart",
    "if (difficulty == BotDifficulty.hard) {\n      final result = _searchDisjoint(",
    "if (difficulty == BotDifficulty.hard || requiredTileId != null) {\n      final result = _searchDisjoint(",
)
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


# Correlate each client action with its own host acknowledgement so an older
# game snapshot cannot accidentally complete a newer pending action.
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    "  Completer<void>? _pendingActionResult;",
    "  Completer<void>? _pendingActionResult;\n  String? _pendingActionId;\n  int _actionSequence = 0;",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    """    final pending = Completer<void>();
    _pendingActionResult = pending;
    final acknowledgement = pending.future.timeout(const Duration(seconds: 12));""",
    """    final pending = Completer<void>();
    final actionId = '$localPlayerId-' + (++_actionSequence).toString();
    _pendingActionResult = pending;
    _pendingActionId = actionId;
    final acknowledgement = pending.future.timeout(const Duration(seconds: 12));""",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    "      await transport.send({'type': 'game_action', 'actionData': action});",
    "      await transport.send({'type': 'game_action', 'actionId': actionId, 'actionData': action});",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    "      if (identical(_pendingActionResult, pending)) _pendingActionResult = null;",
    """      if (identical(_pendingActionResult, pending)) {
        _pendingActionResult = null;
        _pendingActionId = null;
      }""",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    "        if (pending != null && !pending.isCompleted) pending.complete();",
    "        if (pending != null && !pending.isCompleted && data['actionId'] == _pendingActionId) pending.complete();",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    "      if (pending != null && !pending.isCompleted) pending.completeError(StateError(reason));",
    "      if (pending != null && !pending.isCompleted && data['actionId'] == _pendingActionId) pending.completeError(StateError(reason));",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    "    final rawAction = data['actionData'];",
    "    final actionId = data['actionId'];\n    final rawAction = data['actionData'];",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    """        {'type': 'action_rejected', 'reason': 'Oyuncu bağlantısı veya hamle verisi geçersiz.'},""",
    """        {'type': 'action_rejected', 'actionId': actionId, 'reason': 'Oyuncu bağlantısı veya hamle verisi geçersiz.'},""",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    """        {'type': 'action_rejected', 'reason': error.toString()},""",
    """        {'type': 'action_rejected', 'actionId': actionId, 'reason': error.toString()},""",
)
old_action_broadcast = (
    "    await _broadcastGameViews();\n"
    "    _status('" + "$" + "{player.name} hamlesi kabul edildi.');"
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    old_action_broadcast,
    """    await _broadcastGameViews(
      acknowledgementPeerId: peerId,
      acknowledgementActionId: actionId is String ? actionId : null,
    );
    _status(player.name + ' hamlesi kabul edildi.');""",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    "  Future<void> _broadcastGameViews() async {",
    "  Future<void> _broadcastGameViews({String? acknowledgementPeerId, String? acknowledgementActionId}) async {",
)
replace_once(
    "lib/multiplayer/room_coordinator.dart",
    """        await transport.send(
          {'type': 'game_snapshot', 'game': engine.viewFor(seat).toJson()},
          peerId: peerId,
        );""",
    """        await transport.send(
          {
            'type': 'game_snapshot',
            'game': engine.viewFor(seat).toJson(),
            if (peerId == acknowledgementPeerId && acknowledgementActionId != null)
              'actionId': acknowledgementActionId,
          },
          peerId: peerId,
        );""",
)


print("Applied compile, LAN write-queue, bot side-discard, and action-correlation fixes.")
