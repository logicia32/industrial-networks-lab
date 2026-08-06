"""CiA 402（ドライブプロファイル）の定数と状態機械。

第2部-2 の中核。Controlword / Statusword のビット定義と、
PDS（Power Drive System）有限状態機械をここに閉じ込める。

注意: CiA 402-2 / 402-3 の仕様書そのものは CiA 会員限定のため、
      本実装は各社が無償公開しているサーボの取扱説明書と
      オープンソース実装から再構成したもの。
"""

from enum import Enum

# ---- オブジェクト辞書のインデックス ----
OD_DEVICE_TYPE = (0x1000, 0)
OD_CONTROLWORD = (0x6040, 0)
OD_STATUSWORD = (0x6041, 0)
OD_MODES_OF_OPERATION = (0x6060, 0)
OD_MODES_DISPLAY = (0x6061, 0)
OD_POSITION_ACTUAL = (0x6064, 0)
OD_TARGET_POSITION = (0x607A, 0)

# ---- 動作モード (0x6060) ----
MODE_PP = 1     # Profile position     : 軌道生成はドライブ側
MODE_PV = 3     # Profile velocity     : 同上
MODE_HM = 6     # Homing
MODE_CSP = 8    # Cyclic sync position : 軌道生成はマスタ側（毎周期1点を送る）
MODE_CSV = 9    # Cyclic sync velocity
MODE_CST = 10   # Cyclic sync torque


class State(Enum):
    NOT_READY_TO_SWITCH_ON = "Not ready to switch on"
    SWITCH_ON_DISABLED = "Switch on disabled"
    READY_TO_SWITCH_ON = "Ready to switch on"
    SWITCHED_ON = "Switched on"
    OPERATION_ENABLED = "Operation enabled"
    QUICK_STOP_ACTIVE = "Quick stop active"
    FAULT_REACTION_ACTIVE = "Fault reaction active"
    FAULT = "Fault"


# ---- Statusword (0x6041) が示す状態 ----
#
# bit0 Ready to switch on / bit1 Switched on / bit2 Operation enabled
# bit3 Fault / bit4 Voltage enabled / bit5 Quick stop(アクティブLow)
# bit6 Switch on disabled / bit10 Target reached
#
# 判定マスクが 2 種類ある点に注意。bit5 が don't care の状態があるため、
# 0x6F ひとつで判定すると Switch on disabled と Fault 系を取りこぼす。
STATE_PATTERNS = [
    # (マスク, 一致値, 状態)
    (0x4F, 0x00, State.NOT_READY_TO_SWITCH_ON),
    (0x4F, 0x40, State.SWITCH_ON_DISABLED),      # bit5 は見ない
    (0x6F, 0x21, State.READY_TO_SWITCH_ON),
    (0x6F, 0x23, State.SWITCHED_ON),
    (0x6F, 0x27, State.OPERATION_ENABLED),
    (0x6F, 0x07, State.QUICK_STOP_ACTIVE),       # bit5=0 が急停止中
    (0x4F, 0x0F, State.FAULT_REACTION_ACTIVE),   # bit5 は見ない
    (0x4F, 0x08, State.FAULT),                   # bit5 は見ない
]

# 各状態が返す Statusword の代表値
# bit4(Voltage enabled)=1, bit9(Remote)=1 を立てた実機的な値にしてある
_BASE = 0x0210
STATUSWORD_OF = {
    State.NOT_READY_TO_SWITCH_ON: 0x0000,
    State.SWITCH_ON_DISABLED: _BASE | 0x40,      # 0x0250
    State.READY_TO_SWITCH_ON: _BASE | 0x21,      # 0x0231
    State.SWITCHED_ON: _BASE | 0x23,             # 0x0233
    State.OPERATION_ENABLED: _BASE | 0x27,       # 0x0237
    State.QUICK_STOP_ACTIVE: _BASE | 0x07,       # 0x0217
    State.FAULT_REACTION_ACTIVE: _BASE | 0x0F,   # 0x021F
    State.FAULT: _BASE | 0x08,                   # 0x0218
}


def decode_state(statusword: int) -> State:
    """Statusword から状態を判定する。マスクを 2 種類使い分けるのが要点。"""
    for mask, value, state in STATE_PATTERNS:
        if statusword & mask == value:
            return state
    raise ValueError(f"未知の Statusword: 0x{statusword:04X}")


# ---- Controlword (0x6040) のコマンド ----
#
# bit0 Switch on / bit1 Enable voltage / bit2 Quick stop(アクティブLow)
# bit3 Enable operation / bit7 Fault reset(立ち上がりエッジ)
class Command(Enum):
    SHUTDOWN = "Shutdown"
    SWITCH_ON = "Switch on"
    DISABLE_VOLTAGE = "Disable voltage"
    QUICK_STOP = "Quick stop"
    DISABLE_OPERATION = "Disable operation"
    ENABLE_OPERATION = "Enable operation"
    FAULT_RESET = "Fault reset"


CW_SHUTDOWN = 0x06
CW_SWITCH_ON = 0x07
CW_ENABLE_OPERATION = 0x0F
CW_DISABLE_VOLTAGE = 0x00
CW_QUICK_STOP = 0x02
CW_FAULT_RESET = 0x80

# 判定は上から順に行う（Fault reset が最優先）
COMMAND_PATTERNS = [
    (0x80, 0x80, Command.FAULT_RESET),
    (0x8F, 0x0F, Command.ENABLE_OPERATION),
    (0x8F, 0x07, Command.SWITCH_ON),        # ← Disable operation と同じビット列
    (0x8F, 0x06, Command.SHUTDOWN),
    (0x86, 0x02, Command.QUICK_STOP),
    (0x82, 0x00, Command.DISABLE_VOLTAGE),
]


def decode_command(controlword: int) -> Command | None:
    for mask, value, cmd in COMMAND_PATTERNS:
        if controlword & mask == value:
            return cmd
    return None


# ---- 状態遷移表 ----
#
# ここに CiA 402 の面白さが凝縮されている:
#   0x07 (Command.SWITCH_ON) は、
#     Ready to switch on から見れば「投入せよ」   → Switched on へ進む
#     Operation enabled から見れば「運転を止めよ」 → Switched on へ戻る
#   同じビット列が、受け手の状態によって正反対の意味になる。
TRANSITIONS = {
    (State.SWITCH_ON_DISABLED, Command.SHUTDOWN): State.READY_TO_SWITCH_ON,
    (State.READY_TO_SWITCH_ON, Command.SWITCH_ON): State.SWITCHED_ON,
    (State.READY_TO_SWITCH_ON, Command.ENABLE_OPERATION): State.OPERATION_ENABLED,  # 近道
    (State.READY_TO_SWITCH_ON, Command.DISABLE_VOLTAGE): State.SWITCH_ON_DISABLED,
    (State.SWITCHED_ON, Command.ENABLE_OPERATION): State.OPERATION_ENABLED,
    (State.SWITCHED_ON, Command.SHUTDOWN): State.READY_TO_SWITCH_ON,
    (State.SWITCHED_ON, Command.DISABLE_VOLTAGE): State.SWITCH_ON_DISABLED,
    (State.OPERATION_ENABLED, Command.SWITCH_ON): State.SWITCHED_ON,   # = Disable operation
    (State.OPERATION_ENABLED, Command.SHUTDOWN): State.READY_TO_SWITCH_ON,
    (State.OPERATION_ENABLED, Command.DISABLE_VOLTAGE): State.SWITCH_ON_DISABLED,
    (State.OPERATION_ENABLED, Command.QUICK_STOP): State.QUICK_STOP_ACTIVE,
    (State.QUICK_STOP_ACTIVE, Command.DISABLE_VOLTAGE): State.SWITCH_ON_DISABLED,
    (State.FAULT, Command.FAULT_RESET): State.SWITCH_ON_DISABLED,
}


def next_state(current: State, controlword: int) -> tuple[State, Command | None]:
    """Controlword を受けて次の状態を返す。遷移がなければ現状維持。"""
    cmd = decode_command(controlword)
    if cmd is None:
        return current, None
    return TRANSITIONS.get((current, cmd), current), cmd
