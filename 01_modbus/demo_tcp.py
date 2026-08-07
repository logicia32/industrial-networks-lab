"""第1回のハンズオン本体: Modbus TCP で読み書きし、線の上のバイト列を見る。

サーバとクライアントを1つのプロセスで動かすので、これ1本で完結する。

    python 01_modbus/demo_tcp.py
"""

import asyncio

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

HOST, PORT, DEVICE_ID = "127.0.0.1", 5020, 1


def trace(sending: bool, data: bytes) -> bytes:
    """線の上を流れる生バイトをそのまま表示する"""
    print(f"  {'TX' if sending else 'RX'} {data.hex(' ')}")
    return data


async def main() -> None:
    # 機器の中身を作る（コイル / 入力接点 / 保持レジスタ / 入力レジスタ）
    co = [SimData(0, count=8, values=False, datatype=DataType.BITS)]
    di = [SimData(0, count=8, values=True, datatype=DataType.BITS)]
    hr = [SimData(0, count=8, values=0, datatype=DataType.REGISTERS)]
    ir = [SimData(0, count=4, values=7, datatype=DataType.REGISTERS)]
    device = SimDevice(DEVICE_ID, simdata=(co, di, hr, ir))

    server = ModbusTcpServer(device, address=(HOST, PORT), trace_packet=trace)
    # background=True は listen まで済ませてから戻る。ここで失敗すれば例外が上がるので、
    # 「サーバが立っていないのに気づかないまま、たまたま同じポートにいる別の機器へ
    # 繋いでしまう」事故を防げる。create_task だと失敗が誰にも届かない。
    try:
        await server.serve_forever(background=True)
    except RuntimeError:
        raise SystemExit(
            f"{HOST}:{PORT} を使えませんでした。ほかのプログラムが使っていないか"
            f"確認してください（このシリーズでは 01_modbus/device.py が同じポートを使います）。")

    client = AsyncModbusTcpClient(HOST, port=PORT)
    await client.connect()
    try:
        print("--- 保持レジスタ 0〜3 を読む ---")
        rr = await client.read_holding_registers(0, count=4, device_id=DEVICE_ID)
        print("  ->", rr.registers)

        print("--- 保持レジスタ 0 に 1234 を書く ---")
        await client.write_register(0, 1234, device_id=DEVICE_ID)
        rr = await client.read_holding_registers(0, count=4, device_id=DEVICE_ID)
        print("  ->", rr.registers)

        print("--- 入力レジスタ 0〜2 を読む ---")
        rr = await client.read_input_registers(0, count=3, device_id=DEVICE_ID)
        print("  ->", rr.registers)

        print("--- 存在しない 9000 番地を読む ---")
        rr = await client.read_holding_registers(9000, count=1, device_id=DEVICE_ID)
        print("  isError:", rr.isError(), "|", rr)
    finally:
        client.close()
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
