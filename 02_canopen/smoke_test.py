"""Phase 1: 単一プロセス + python-can `virtual` の最小骨格。

記事の第2部-1 ハンズオンの土台。全OS（Windows含む）で動くことが要件。
`virtual` バックエンドは同一プロセス内のバス同士しか繋がないため、
マスタ役とノード役を「1つのプロセスの中の2つのオブジェクト」として動かす。
"""

import threading
import time

import can

CHANNEL = "canopen-demo"
NODE_ID = 1
SYNC_COB_ID = 0x080
TPDO1 = 0x180 + NODE_ID  # ノード → マスタ（TPDO はデバイス視点）
RPDO1 = 0x200 + NODE_ID  # マスタ → ノード


def servo_node(stop: threading.Event, ready: threading.Event) -> None:
    """SYNC を受けたら現在位置を TPDO で返すだけの最小ノード。"""
    bus = can.Bus(interface="virtual", channel=CHANNEL)
    ready.set()  # ← バス生成前に送られたフレームは捨てられるので、必ず待たせる
    position = 0
    target = 0
    while not stop.is_set():
        msg = bus.recv(timeout=0.1)
        if msg is None:
            continue
        if msg.arbitration_id == RPDO1:
            target = int.from_bytes(msg.data[:4], "little", signed=True)
        elif msg.arbitration_id == SYNC_COB_ID:
            position += (target - position) // 4  # 1次遅れ相当の追従
            bus.send(can.Message(
                arbitration_id=TPDO1,
                data=position.to_bytes(4, "little", signed=True),
                is_extended_id=False,
            ))
    bus.shutdown()


def main() -> None:
    stop = threading.Event()
    ready = threading.Event()
    t = threading.Thread(target=servo_node, args=(stop, ready), daemon=True)
    t.start()
    if not ready.wait(timeout=5.0):
        raise RuntimeError("ノード側のバスが起動しなかった")

    bus = can.Bus(interface="virtual", channel=CHANNEL)
    bus.send(can.Message(
        arbitration_id=RPDO1,
        data=(10000).to_bytes(4, "little", signed=True),
        is_extended_id=False,
    ))

    replies = 0
    for i in range(20):
        bus.send(can.Message(arbitration_id=SYNC_COB_ID, data=b"", is_extended_id=False))
        deadline = time.monotonic() + 0.05
        while time.monotonic() < deadline:
            msg = bus.recv(timeout=0.05)
            if msg is not None and msg.arbitration_id == TPDO1:
                actual = int.from_bytes(msg.data[:4], "little", signed=True)
                replies += 1
                if i % 5 == 0:
                    print(f"  sync #{i:2d}  target=10000  actual={actual:6d}")
                break
        time.sleep(0.01)

    stop.set()
    t.join(timeout=1.0)
    bus.shutdown()
    print(f"\nTPDO replies: {replies}/20")
    assert replies == 20, "SYNC に対する TPDO 応答が欠落している"
    print("OK: 単一プロセス virtual バスで SYNC → TPDO が成立")


if __name__ == "__main__":
    main()
