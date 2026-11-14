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

# Socket is Stream<Uint8List>; cast its chunks to List<int> before UTF-8 decoding.
replace_once(
    "lib/multiplayer/lan_transport.dart",
    ".transform(utf8.decoder)",
    ".cast<List<int>>()\n        .transform(utf8.decoder)",
    count=2,
)
replace_once(
    "test/multiplayer/protocol_test.dart",
    ".transform(utf8.decoder)",
    ".cast<List<int>>()\n          .transform(utf8.decoder)",
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

# Remove an unused test import so Flutter analyze has no warning-level failures.
replace_once(
    "test/bot/bot_strategy_test.dart",
    "import 'package:classic_101_okey/game/game_state.dart';\n",
    "",
)

print("Applied compile-analysis fixes to the extracted Flutter project.")
