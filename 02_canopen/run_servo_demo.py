"""第2部-2 のハンズオン本体: 仮想サーボを規格どおりに起動して動かす。

  1. NMT で Operational にする
  2. SDO で Controlword を 0x06 → 0x07 → 0x0F と進めて通電させる
  3. 動作モードを csp（Cyclic synchronous position）にする
  4. SYNC 10ms 周期で目標位置を送り、追従カーブを記録する
  5. 同じ 0x07 が「運転停止」にもなることを見せる

実行: ./.venv/bin/python 02_canopen/run_servo_demo.py
"""

import pathlib
import sys
import time

import can

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import cia402
from cia402 import State, decode_state
from servo import Cia402Servo

CHANNEL = "cia402-demo"
NODE_ID = 1
SYNC_PERIOD = 0.010          # 10 ms
COB_NMT = 0x000
COB_SYNC = 0x080


class Master:
    def __init__(self, bus: can.BusABC, node_id: int) -> None:
        self.bus = bus
        self.node_id = node_id
        self.sdo_tx = 0x580 + node_id     # サーボ → マスタ
        self.sdo_rx = 0x600 + node_id     # マスタ → サーボ
        self.tpdo1 = 0x180 + node_id
        self.rpdo1 = 0x200 + node_id
        self.last_actual = 0
        self.last_status = 0

    # ---- NMT ----
    def nmt_start(self) -> None:
        self.bus.send(can.Message(arbitration_id=COB_NMT,
                                  data=bytes([1, self.node_id]),
                                  is_extended_id=False))

    # ---- SDO クライアント（expedited のみ） ----
    def _wait_sdo(self, timeout: float = 1.0) -> bytes:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg = self.bus.recv(timeout=deadline - time.monotonic())
            if msg is None:
                break
            if msg.arbitration_id == self.tpdo1:
                self._absorb_tpdo(msg)
                continue
            if msg.arbitration_id == self.sdo_tx:
                return bytes(msg.data)
        raise TimeoutError("SDO 応答が来ない")

    def _check_sdo(self, resp: bytes, index: int, sub: int) -> None:
        """応答が「今出した要求への応答」であることを確かめる。
        バス上には他のフレームも流れるので、無検証だと別物を掴む。"""
        if resp[0] == 0x80:
            raise RuntimeError(f"SDO abort: 0x{int.from_bytes(resp[4:8], 'little'):08X}")
        got_index = int.from_bytes(resp[1:3], "little")
        if got_index != index or resp[3] != sub:
            raise RuntimeError(
                f"SDO 応答の宛先が違う: 要求 0x{index:04X}:{sub} / "
                f"応答 0x{got_index:04X}:{resp[3]}")

    def sdo_read(self, index: int, sub: int = 0, signed: bool = False) -> int:
        """OD を読む。符号の有無は本来 EDS を見ないと分からないので、呼び側が指定する。"""
        req = bytes([0x40]) + index.to_bytes(2, "little") + bytes([sub, 0, 0, 0, 0])
        self.bus.send(can.Message(arbitration_id=self.sdo_rx, data=req,
                                  is_extended_id=False))
        resp = self._wait_sdo()
        self._check_sdo(resp, index, sub)
        size = {0x4F: 1, 0x4B: 2, 0x47: 3, 0x43: 4}.get(resp[0])
        if size is None:
            raise RuntimeError(f"expedited upload の応答ではない: 0x{resp[0]:02X}")
        return int.from_bytes(resp[4:4 + size], "little", signed=signed)

    def sdo_write(self, index: int, sub: int, value: int, size: int) -> None:
        ccs = {1: 0x2F, 2: 0x2B, 3: 0x27, 4: 0x23}[size]
        payload = value.to_bytes(4, "little", signed=value < 0)
        req = bytes([ccs]) + index.to_bytes(2, "little") + bytes([sub]) + payload
        self.bus.send(can.Message(arbitration_id=self.sdo_rx, data=req,
                                  is_extended_id=False))
        resp = self._wait_sdo()
        self._check_sdo(resp, index, sub)
        if resp[0] != 0x60:
            raise RuntimeError(f"download の応答ではない: 0x{resp[0]:02X}")

    # ---- PDO ----
    def send_rpdo1(self, target: int, controlword: int) -> None:
        data = (target.to_bytes(4, "little", signed=True)
                + controlword.to_bytes(2, "little"))
        self.bus.send(can.Message(arbitration_id=self.rpdo1, data=data,
                                  is_extended_id=False))

    def _absorb_tpdo(self, msg: can.Message) -> None:
        self.last_actual = int.from_bytes(msg.data[0:4], "little", signed=True)
        self.last_status = int.from_bytes(msg.data[4:6], "little")

    def sync_and_collect(self, timeout: float = 0.05) -> bool:
        """SYNC を1発打って、TPDO1 が返るまで待つ"""
        self.bus.send(can.Message(arbitration_id=COB_SYNC, data=b"",
                                  is_extended_id=False))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            msg = self.bus.recv(timeout=deadline - time.monotonic())
            if msg is None:
                break
            if msg.arbitration_id == self.tpdo1:
                self._absorb_tpdo(msg)
                return True
        return False


def show_state(master: Master, label: str) -> State:
    sw = master.sdo_read(*cia402.OD_STATUSWORD)
    st = decode_state(sw)
    print(f"  {label:<34} Statusword = 0x{sw:04X}  ->  {st.value}")
    return st


def main() -> None:
    servo = Cia402Servo(CHANNEL, node_id=NODE_ID, gain=0.15)
    servo.start()
    bus = None
    try:
        if not servo.ready.wait(timeout=5.0):
            raise RuntimeError("サーボが起動しない")

        bus = can.Bus(interface="virtual", channel=CHANNEL)
        master = Master(bus, NODE_ID)
        time.sleep(0.05)

        print("=" * 74)
        print("1. NMT: Pre-operational -> Operational")
        print("=" * 74)
        master.nmt_start()
        time.sleep(0.02)
        dt = master.sdo_read(*cia402.OD_DEVICE_TYPE)
        print(f"  SDO read 0x1000 (Device type)      = 0x{dt:08X}")

        print()
        print("=" * 74)
        print("2. CiA 402 状態機械: 0x06 -> 0x07 -> 0x0F")
        print("=" * 74)
        show_state(master, "起動直後")
        for cw, name in ((cia402.CW_SHUTDOWN, "Shutdown"),
                         (cia402.CW_SWITCH_ON, "Switch on"),
                         (cia402.CW_ENABLE_OPERATION, "Enable operation")):
            master.sdo_write(*cia402.OD_CONTROLWORD, cw, 2)
            show_state(master, f"Controlword = 0x{cw:02X} ({name})")

        print()
        print("=" * 74)
        print("3. 動作モードを csp (Cyclic synchronous position) にする")
        print("=" * 74)
        master.sdo_write(*cia402.OD_MODES_OF_OPERATION, cia402.MODE_CSP, 1)
        mode = master.sdo_read(*cia402.OD_MODES_DISPLAY, signed=True)
        print(f"  SDO write 0x6060 = {cia402.MODE_CSP}  ->  0x6061 (実際のモード) = {mode}  (csp)")

        print()
        print("=" * 74)
        print("4. SYNC 10ms 周期で目標位置を送り、追従を記録する")
        print("=" * 74)
        curve: list[tuple[float, int, int]] = []
        target = 0
        t0 = time.monotonic()
        misses = 0
        for i in range(60):
            if i == 5:
                target = 10000        # ステップ入力
            master.send_rpdo1(target, cia402.CW_ENABLE_OPERATION)
            if not master.sync_and_collect():
                misses += 1
            t = time.monotonic() - t0
            curve.append((t, target, master.last_actual))
            if i % 10 == 0 or i == 59:
                print(f"  t={t:5.3f}s  target={target:6d}  actual={master.last_actual:6d}"
                      f"  status=0x{master.last_status:04X}")
            # 周期は絶対時刻で刻む。sleep(0.010) だと処理時間ぶん毎回ずれていく
            time.sleep(max(0.0, t0 + (i + 1) * SYNC_PERIOD - time.monotonic()))

        print(f"\n  取りこぼした SYNC 応答: {misses} / 60")

        print()
        print("=" * 74)
        print("5. 同じ 0x07 が、今度は「運転停止」になる")
        print("=" * 74)
        show_state(master, "現在")
        master.sdo_write(*cia402.OD_CONTROLWORD, cia402.CW_SWITCH_ON, 2)
        show_state(master, "Controlword = 0x07 (Disable operation)")
        print("  → Ready to switch on から書けば「投入」、Operation enabled から書けば「停止」。")
        print("    同じビット列が、受け手の状態によって正反対の意味になる。")

        print()
        print("  --- 状態遷移の記録 ---")
        snap = servo.snapshot()      # 属性を直接読まず、ロック越しにコピーを取る
        for cw, old, new in snap["transitions"]:
            print(f"    0x{cw:04X} : {old.value:<22} -> {new.value}")
        if snap["malformed_frames"]:
            print(f"\n  捨てた不正フレーム: {snap['malformed_frames']}")

    finally:
        # 例外で抜けても、スレッドとバスは必ず畳む。canmon.py と同じ作法。
        servo.stop()
        servo.join(timeout=1.0)   # 内部名の衝突を直したので join() が使える
        if bus is not None:
            bus.shutdown()

    _plot(curve)


def _plot(curve: list[tuple[float, int, int]]) -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    try:
        import figstyle
    except ImportError:
        print("\n  (matplotlib が無いのでグラフは省略)")
        return

    out = root / "docs" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "cia402_follow.png"

    t = [c[0] for c in curve]
    tgt = [c[1] for c in curve]
    act = [c[2] for c in curve]

    fig, ax = figstyle.figure()
    # 値は SYNC の瞬間にしか確定しないので、両系列とも階段で描く。
    # 折れ線で補間すると、実位置が指令より先に動いたように見えてしまう。
    ax.step(t, tgt, where="post", color=figstyle.SERIES[0], linewidth=2.0,
            label="Target position  0x607A", zorder=2)
    ax.step(t, act, where="post", color=figstyle.SERIES[1], linewidth=2.0,
            label="Actual position  0x6064", zorder=3)

    figstyle.label_axes(ax, "time [s]   (SYNC period = 10 ms)", "position [counts]",
                        "CiA 402 csp mode — position following")
    figstyle.annotate(ax, 0.175, 10330, "Target  0x607A")
    figstyle.annotate(ax, 0.175, 6100, "Actual  0x6064")
    figstyle.legend(ax, loc="lower right")
    ax.set_ylim(-600, 11100)
    figstyle.save(fig, path)
    print(f"\n  グラフを書き出しました: {path}")


if __name__ == "__main__":
    main()
