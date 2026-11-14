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

# Socket implements both Stream and StreamSink. Use Stream.map explicitly,
# avoiding StreamSink.cast which can bind the socket's write side.
replace_once(
    "lib/multiplayer/lan_transport.dart",
    ".transform(utf8.decoder)",
    ".map((chunk) => chunk as List<int>)\n        .transform(utf8.decoder)",
    count=2,
)
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

print("Applied source fixes for analysis, mandatory side-discard use, and LAN socket handling.")
