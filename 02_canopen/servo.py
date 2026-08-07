"""仮想 CiA 402 サーボノード。

CANopen のスレーブとして振る舞う:
  - SDO サーバ（expedited のみ）で OD を読み書きさせる
  - RPDO1 で目標位置と Controlword を受ける
  - SYNC ごとに追従計算をして TPDO1 で現在位置と Statusword を返す

python-can の `virtual` バックエンド上で動く。ハードも root も不要。
"""

import sys
import threading

import can

import cia402
from cia402 import State

# ---- COB-ID ----
COB_NMT = 0x000
COB_SYNC = 0x080

# ---- SDO アボートコード（CiA 301）----
# 実機は不正な要求を黙って捨てず、必ず理由付きで abort を返す。
ABORT_CMD_INVALID = 0x05040001       # コマンド指定子が不正／未対応
ABORT_NO_SUCH_OBJECT = 0x06020000    # そのオブジェクトは無い
ABORT_LENGTH_MISMATCH = 0x06070010   # データ長が型と合わない
ABORT_READ_ONLY = 0x06010002         # 読み出し専用のオブジェクトへ書こうとした

SDO_FRAME_LEN = 8                    # SDO は常に8バイト
RPDO1_LEN = 6                        # 0x607A(4) + 0x6040(2)

# 外から書けないオブジェクト。デバイス自身は更新するが、SDO の書き込みは断る。
READ_ONLY = frozenset({
    cia402.OD_DEVICE_TYPE,       # const
    cia402.OD_STATUSWORD,        # サーボが自分の状態を載せるところ
    cia402.OD_POSITION_ACTUAL,   # 現在位置は測定値
    cia402.OD_MODES_DISPLAY,     # 実際に効いているモード（指定は 0x6060 側）
})


class Cia402Servo(threading.Thread):
    """1軸ぶんの仮想サーボ。1つのスレッドで動く。"""

    def __init__(self, channel: str, node_id: int = 1, gain: float = 0.15) -> None:
        super().__init__(daemon=True)
        self.channel = channel
        self.node_id = node_id
        self.gain = gain

        self.ready = threading.Event()
        # 名前に注意: threading.Thread は内部に _stop() というメソッドを持っている。
        # ここを Event で上書きすると join() / is_alive() が
        # TypeError: 'Event' object is not callable で落ちる。
        self._stop_event = threading.Event()

        # COB-ID（すべて Node-ID を足して決まる）
        self.cob_tpdo1 = 0x180 + node_id
        self.cob_rpdo1 = 0x200 + node_id
        self.cob_sdo_tx = 0x580 + node_id   # サーボ → マスタ
        self.cob_sdo_rx = 0x600 + node_id   # マスタ → サーボ
        self.cob_heartbeat = 0x700 + node_id

        # NMT 状態（Operational でないと PDO は流れない）
        self.nmt_operational = False

        # CiA 402 の状態機械
        self.state = State.SWITCH_ON_DISABLED

        # オブジェクト辞書（値・サイズ[byte]・符号付きか）
        # 符号の有無は型ごとに違う。位置は INTEGER32 なので負の値を取る。
        # ここを一律 unsigned で扱うと、負方向に動いた瞬間に壊れる。
        self.od: dict[tuple[int, int], tuple[int, int, bool]] = {
            cia402.OD_DEVICE_TYPE: (0x00020192, 4, False),          # UNSIGNED32
            cia402.OD_CONTROLWORD: (0x0000, 2, False),              # UNSIGNED16
            cia402.OD_STATUSWORD: (cia402.STATUSWORD_OF[self.state], 2, False),
            cia402.OD_MODES_OF_OPERATION: (0, 1, True),             # INTEGER8
            cia402.OD_MODES_DISPLAY: (0, 1, True),                  # INTEGER8
            cia402.OD_POSITION_ACTUAL: (0, 4, True),                # INTEGER32
            cia402.OD_TARGET_POSITION: (0, 4, True),                # INTEGER32
        }
        self._position = 0.0
        self.transitions: list[tuple[int, State, State]] = []   # 記録用

        # OD・状態・位置はサーボスレッドが更新し、外からも読まれる。
        # 再入する経路（_handle_sdo -> _write_od -> _apply_controlword）があるので RLock。
        self._lock = threading.RLock()
        self.malformed_frames = 0        # 捨てた不正フレームの数（観測用）

    # ---------- OD アクセス ----------

    def _read_od(self, index: int, sub: int) -> tuple[int, int, bool] | None:
        return self.od.get((index, sub))

    def _write_od(self, index: int, sub: int, value: int) -> bool:
        entry = self.od.get((index, sub))
        if entry is None:
            return False
        self.od[(index, sub)] = (value, entry[1], entry[2])
        if (index, sub) == cia402.OD_CONTROLWORD:
            self._apply_controlword(value)
        elif (index, sub) == cia402.OD_MODES_OF_OPERATION:
            self.od[cia402.OD_MODES_DISPLAY] = (value, 1, True)
        return True

    def _apply_controlword(self, controlword: int) -> None:
        old = self.state
        self.state, _cmd = cia402.next_state(old, controlword)
        if self.state is not old:
            self.transitions.append((controlword, old, self.state))
        self.od[cia402.OD_STATUSWORD] = (cia402.STATUSWORD_OF[self.state], 2, False)

    # ---------- SDO サーバ（expedited のみ） ----------

    def _handle_sdo(self, bus: can.BusABC, data: bytes) -> None:
        # 長さを最初に確かめる。短いフレームをそのまま添字アクセスすると
        # IndexError でこのスレッドが落ちる（そして誰にも気づかれない）。
        if len(data) != SDO_FRAME_LEN:
            self.malformed_frames += 1
            self._sdo_abort(bus, 0x0000, 0x00, ABORT_CMD_INVALID)
            return

        ccs = data[0]
        index = int.from_bytes(data[1:3], "little")
        sub = data[3]

        with self._lock:
            if ccs == 0x40:                               # upload（読み出し）要求
                entry = self._read_od(index, sub)
                if entry is None:
                    self._sdo_abort(bus, index, sub, ABORT_NO_SUCH_OBJECT)
                    return
                value, size, signed = entry
                scs = {1: 0x4F, 2: 0x4B, 3: 0x47, 4: 0x43}[size]
                # 符号を型どおりに扱う。unsigned 固定にすると負の位置を読んだ瞬間に
                # OverflowError になり、このスレッドが無言で死ぬ。
                payload = value.to_bytes(4, "little", signed=signed)
                resp = bytes([scs]) + data[1:4] + payload

            elif ccs & 0xE3 == 0x23:                      # expedited download（書き込み）
                # 0x2F/0x2B/0x27/0x23 だけを受ける。0x21 のような分割転送の開始要求を
                # ここで通してしまうと、4バイト即値として誤って処理してしまう。
                entry = self._read_od(index, sub)
                if entry is None:
                    self._sdo_abort(bus, index, sub, ABORT_NO_SUCH_OBJECT)
                    return
                if (index, sub) in READ_ONLY:
                    # 実機は RO のオブジェクトへの書き込みを必ず断る。ここを通すと
                    # Statusword を外から書き換えられ、状態と表示がずれる。
                    self._sdo_abort(bus, index, sub, ABORT_READ_ONLY)
                    return
                size = 4 - ((ccs >> 2) & 0x03)
                if size != entry[1]:                      # OD の定義幅と一致するか
                    self._sdo_abort(bus, index, sub, ABORT_LENGTH_MISMATCH)
                    return
                value = int.from_bytes(data[4:4 + size], "little", signed=entry[2])
                if not self._write_od(index, sub, value):
                    self._sdo_abort(bus, index, sub, ABORT_NO_SUCH_OBJECT)
                    return
                resp = bytes([0x60]) + data[1:4] + b"\x00\x00\x00\x00"

            else:
                # 分割転送・ブロック転送は未対応。黙殺せず理由を返す
                self._sdo_abort(bus, index, sub, ABORT_CMD_INVALID)
                return

        bus.send(can.Message(arbitration_id=self.cob_sdo_tx, data=resp,
                             is_extended_id=False))

    def _sdo_abort(self, bus: can.BusABC, index: int, sub: int, code: int) -> None:
        resp = (bytes([0x80]) + index.to_bytes(2, "little") + bytes([sub])
                + code.to_bytes(4, "little"))
        bus.send(can.Message(arbitration_id=self.cob_sdo_tx, data=resp,
                             is_extended_id=False))

    # ---------- PDO ----------

    def _handle_rpdo1(self, data: bytes) -> None:
        """RPDO1 マッピング: 0x607A(4byte) + 0x6040(2byte)"""
        # マッピングより短い PDO は使ってはいけない（規格上もエラー扱い）。
        # 途中まで読んで使うと、目標位置が化けたまま動き続けることになる。
        if len(data) < RPDO1_LEN:
            self.malformed_frames += 1
            return
        with self._lock:
            target = int.from_bytes(data[0:4], "little", signed=True)
            self.od[cia402.OD_TARGET_POSITION] = (target, 4, True)
            self._apply_controlword(int.from_bytes(data[4:6], "little"))

    def _send_tpdo1(self, bus: can.BusABC) -> None:
        """TPDO1 マッピング: 0x6064(4byte) + 0x6041(2byte)"""
        pos = round(self._position)     # int() はゼロ方向に切るので負側で挙動が変わる
        status = self.od[cia402.OD_STATUSWORD][0]
        data = (pos.to_bytes(4, "little", signed=True)
                + status.to_bytes(2, "little"))
        bus.send(can.Message(arbitration_id=self.cob_tpdo1, data=data,
                             is_extended_id=False))

    # ---------- SYNC ごとの制御周期 ----------

    def _on_sync(self, bus: can.BusABC) -> None:
        with self._lock:
            mode = self.od[cia402.OD_MODES_OF_OPERATION][0]
            if self.state is State.OPERATION_ENABLED and mode == cia402.MODE_CSP:
                # csp: マスタが毎周期送ってくる目標位置に追従するだけ
                target = self.od[cia402.OD_TARGET_POSITION][0]
                self._position += (target - self._position) * self.gain
            elif self.state is State.QUICK_STOP_ACTIVE:
                self._position += (0 - self._position) * self.gain
            self.od[cia402.OD_POSITION_ACTUAL] = (round(self._position), 4, True)
            if self.nmt_operational:
                self._send_tpdo1(bus)

    # ---------- 外のスレッドから安全に覗くための窓 ----------

    def snapshot(self) -> dict:
        """内部状態のコピーを返す。属性を直接読むと更新中の値を掴みうる。"""
        with self._lock:
            return {
                "state": self.state,
                "position": round(self._position),
                "statusword": self.od[cia402.OD_STATUSWORD][0],
                "transitions": list(self.transitions),
                "malformed_frames": self.malformed_frames,
            }

    # ---------- メインループ ----------

    def run(self) -> None:
        bus = can.Bus(interface="virtual", channel=self.channel)
        self.ready.set()
        # ブートアップメッセージ（ハートビートと同じ COB-ID に値 0）
        bus.send(can.Message(arbitration_id=self.cob_heartbeat, data=b"\x00",
                             is_extended_id=False))

        try:
            while not self._stop_event.is_set():
                msg = bus.recv(timeout=0.05)
                if msg is None:
                    continue
                try:
                    self._dispatch(bus, msg)
                except Exception as exc:
                    # 想定外の例外でスレッドが黙って消えるのが一番たちが悪い。
                    # 落とさず、必ず見えるところに出してから続ける。
                    self.malformed_frames += 1
                    print(f"[servo node {self.node_id}] "
                          f"0x{msg.arbitration_id:03X} の処理で例外: "
                          f"{type(exc).__name__}: {exc}", file=sys.stderr)
        finally:
            bus.shutdown()

    def _dispatch(self, bus: can.BusABC, msg: can.Message) -> None:
        cob = msg.arbitration_id
        if cob == COB_NMT:
            if len(msg.data) < 2:
                self.malformed_frames += 1
                return
            cs, target_node = msg.data[0], msg.data[1]
            if target_node in (0, self.node_id):
                if cs == 1:      # Start Remote Node
                    self.nmt_operational = True
                elif cs == 2:    # Stop Remote Node
                    self.nmt_operational = False
                elif cs == 128:  # Enter Pre-operational
                    self.nmt_operational = False
        elif cob == COB_SYNC:
            self._on_sync(bus)
        elif cob == self.cob_sdo_rx:
            self._handle_sdo(bus, bytes(msg.data))         # SDO は Pre-op でも動く
        elif cob == self.cob_rpdo1 and self.nmt_operational:
            self._handle_rpdo1(bytes(msg.data))

    def stop(self) -> None:
        self._stop_event.set()
