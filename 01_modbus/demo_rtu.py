"""第1回の付録: Modbus RTU をシリアルポートなしで動かす（Linux / macOS 限定）。

`pty` で仮想シリアルポートのペアを作り、片方をサーバ、片方をクライアントに渡す。
socat も root 権限も要らない。

    python 01_modbus/demo_rtu.py

Windows では動かない（`pty` / `termios` / `tty` が標準ライブラリに無い）。
"""

import asyncio
import os
import sys
import threading

# pty / termios / tty は Windows の標準ライブラリに無い。
# import の時点で落ちると main() の案内も出せないので、ここで分けておく。
if sys.platform != "win32":
    import pty
    import termios
    import tty

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.server import ModbusSerialServer
from pymodbus.simulator import DataType, SimData, SimDevice

DEVICE_ID = 1
BAUDRATE = 9600


def make_serial_pair() -> tuple[str, str]:
    """互いに繋がった仮想シリアルポートを2本作って、その名前を返す。"""
    m1, s1 = pty.openpty()
    m2, s2 = pty.openpty()
    for fd in (m1, s1, m2, s2):
        tty.setraw(fd, termios.TCSANOW)

    def pump(src: int, dst: int) -> None:
        try:
            while True:
                os.write(dst, os.read(src, 1024))
        except OSError:
            pass

    threading.Thread(target=pump, args=(m1, m2), daemon=True).start()
    threading.Thread(target=pump, args=(m2, m1), daemon=True).start()
    return os.ttyname(s1), os.ttyname(s2)


def trace(sending: bool, data: bytes) -> bytes:
    print(f"  {'TX' if sending else 'RX'} {data.hex(' ')}")
    return data


async def main() -> None:
    if sys.platform == "win32":
        print("この付録は Windows では動きません（pty が無いため）")
        return

    device_port, client_port = make_serial_pair()
    print(f"仮想シリアルポート: デバイス側 {device_port} / クライアント側 {client_port}")

    co = [SimData(0, count=8, values=False, datatype=DataType.BITS)]
    di = [SimData(0, count=8, values=True, datatype=DataType.BITS)]
    hr = [SimData(0, count=4, values=22, datatype=DataType.REGISTERS)]
    ir = [SimData(0, count=4, values=7, datatype=DataType.REGISTERS)]
    device = SimDevice(DEVICE_ID, simdata=(co, di, hr, ir))

    server = ModbusSerialServer(device, port=device_port, baudrate=BAUDRATE,
                                trace_packet=trace)
    # demo_tcp.py と同じ理由。開けなければここで止める（create_task だと失敗が届かない）。
    await server.serve_forever(background=True)

    client = AsyncModbusSerialClient(client_port, baudrate=BAUDRATE)
    await client.connect()
    try:
        print("--- 保持レジスタ 0〜3 を読む ---")
        rr = await client.read_holding_registers(0, count=4, device_id=DEVICE_ID)
        print("  ->", rr.registers)

        print("--- 保持レジスタ 0 に 4321 を書く ---")
        await client.write_register(0, 4321, device_id=DEVICE_ID)
        rr = await client.read_holding_registers(0, count=4, device_id=DEVICE_ID)
        print("  ->", rr.registers)
    finally:
        client.close()
        await server.shutdown()

    print()
    print("TCP と見比べてください。MBAP ヘッダ（7バイト）が消えて、")
    print("代わりに先頭にデバイスアドレス1バイト、末尾に CRC 2バイトが付いています。")


if __name__ == "__main__":
    asyncio.run(main())
