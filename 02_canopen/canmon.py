"""candump 相当のバスモニタ。vcan も can-utils も root も不要。

can-utils の candump と違い、CANopen として COB-ID を解釈して表示する。
第2部-1 の「バス上を流れるものを見る」節で使う観測装置。
"""

import threading
import time

import can

# COB-ID の上位4bit (Function Code) から種別を引く
FUNCTION_CODES = {
    0x000: ("NMT", False),      # ブロードキャスト（Node-ID を持たない）
    0x080: ("SYNC/EMCY", True),
    0x100: ("TIME", False),
    0x180: ("TPDO1", True),
    0x200: ("RPDO1", True),
    0x280: ("TPDO2", True),
    0x300: ("RPDO2", True),
    0x380: ("TPDO3", True),
    0x400: ("RPDO3", True),
    0x480: ("TPDO4", True),
    0x500: ("RPDO4", True),
    0x580: ("SDO(tx)", True),
    0x600: ("SDO(rx)", True),
    0x700: ("HEARTBEAT", True),
}


def decode(cob_id: int) -> str:
    """COB-ID を Function Code と Node-ID に分解する"""
    if cob_id == 0x000:
        return "NMT        (broadcast)"
    if cob_id == 0x080:
        return "SYNC       (broadcast)"
    base = cob_id & 0x780
    node_id = cob_id & 0x07F
    name, has_node = FUNCTION_CODES.get(base, ("?", True))
    if base == 0x080:
        name = "EMCY"
    return f"{name:<10} node={node_id}" if has_node else f"{name:<10}"


class Monitor(can.Listener):
    def __init__(self) -> None:
        self.t0 = time.monotonic()
        self.count = 0

    def on_message_received(self, msg: can.Message) -> None:
        self.count += 1
        dt = time.monotonic() - self.t0
        data = msg.data.hex(" ") if msg.dlc else "(empty)"
        print(f"  {dt:7.3f}  0x{msg.arbitration_id:03X}  "
              f"{decode(msg.arbitration_id):<22} [{msg.dlc}]  {data}")


def demo() -> None:
    """モニタを付けた状態で、最小の CANopen 的やりとりを流してみる"""
    CHANNEL = "canmon-demo"
    NODE = 3

    mon_bus = can.Bus(interface="virtual", channel=CHANNEL)
    monitor = Monitor()
    notifier = can.Notifier(mon_bus, [monitor])

    node_ready = threading.Event()
    stop = threading.Event()

    def node() -> None:
        bus = can.Bus(interface="virtual", channel=CHANNEL)
        node_ready.set()
        bus.send(can.Message(arbitration_id=0x700 + NODE, data=b"\x00",
                             is_extended_id=False))          # ブートアップ
        position = 0
        while not stop.is_set():
            msg = bus.recv(timeout=0.1)
            if msg is None:
                continue
            if msg.arbitration_id == 0x080:                   # SYNC
                position += 250
                bus.send(can.Message(
                    arbitration_id=0x180 + NODE,
                    data=position.to_bytes(4, "little", signed=True) + b"\x37\x02",
                    is_extended_id=False))
        bus.shutdown()

    threading.Thread(target=node, daemon=True).start()
    node_ready.wait(timeout=5.0)

    master = can.Bus(interface="virtual", channel=CHANNEL)
    try:
        time.sleep(0.05)
        print("  時刻(s)   COB-ID  種別                   長さ  データ")
        print("  " + "-" * 66)

        # NMT: Start Remote Node (cs=1) を Node 3 へ
        master.send(can.Message(arbitration_id=0x000, data=bytes([1, NODE]),
                                is_extended_id=False))
        time.sleep(0.05)

        # SDO 要求: 0x607A (Target position) に 10000 を書く（expedited, 4byte）
        master.send(can.Message(
            arbitration_id=0x600 + NODE,
            data=bytes([0x23, 0x7A, 0x60, 0x00]) + (10000).to_bytes(4, "little"),
            is_extended_id=False))
        time.sleep(0.05)

        # SYNC を3回
        for _ in range(3):
            master.send(can.Message(arbitration_id=0x080, data=b"",
                                    is_extended_id=False))
            time.sleep(0.05)
    finally:
        # 例外が出ても Notifier とバスは必ず畳む
        stop.set()
        time.sleep(0.15)
        notifier.stop()
        master.shutdown()
        mon_bus.shutdown()

    print("  " + "-" * 66)
    print(f"  観測フレーム数: {monitor.count}")


if __name__ == "__main__":
    demo()
