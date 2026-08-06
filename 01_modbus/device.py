"""Modbus TCP デバイス（第1回・第5回で使う）。

温度計を1台ぶん模したもの。単体で起動するとサーバとして待ち受け、
Ctrl-C で止まる。第5回のゲートウェイはこれを読みに来る。

    python 01_modbus/device.py
"""

import argparse
import asyncio
import ipaddress

from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

HOST = "127.0.0.1"
PORT = 5020
DEVICE_ID = 1

# レジスタの割り当て（この対応表が「意味」であり、線の上には流れない）
IR_TEMPERATURE = 0      # 入力レジスタ 0: 温度 [0.1 degC]  読み取り専用
HR_SETPOINT = 0         # 保持レジスタ 0: 目標温度 [0.1 degC]  読み書き


def build_device(device_id: int = DEVICE_ID) -> SimDevice:
    """4つの領域すべてに中身を用意する。

    空のリストを渡すと SimDevice が IndexError で落ちるので、
    使わない領域にも最低1つ SimData を置く。
    """
    coils = [SimData(0, count=8, values=False, datatype=DataType.BITS)]
    discrete = [SimData(0, count=8, values=True, datatype=DataType.BITS)]
    holding = [SimData(0, count=8, values=0, datatype=DataType.REGISTERS)]
    inputs = [SimData(0, count=4, values=235, datatype=DataType.REGISTERS)]  # 23.5 degC
    return SimDevice(device_id, simdata=(coils, discrete, holding, inputs))


def make_server(host: str = HOST, port: int = PORT, trace=None) -> ModbusTcpServer:
    return ModbusTcpServer(build_device(), address=(host, port), trace_packet=trace)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=HOST,
                    help="待ち受けアドレス（ループバックのみ）")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--trace", action="store_true", help="線の上のバイト列を表示する")
    args = ap.parse_args()

    # Modbus には認証も暗号化も無い。学習用のこの機器を外に出さないため、
    # ループバック以外の待ち受けアドレスは受け付けない。
    try:
        loopback = ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        loopback = False
    if not loopback:
        ap.error("--host に指定できるのはループバックアドレスだけです "
                 "（この機器は認証も暗号化も持ちません）")

    def trace(sending: bool, data: bytes) -> bytes:
        print(f"  {'TX' if sending else 'RX'} {data.hex(' ')}")
        return data

    server = make_server(args.host, args.port, trace if args.trace else None)
    print(f"Modbus TCP device listening on {args.host}:{args.port} "
          f"(device_id={DEVICE_ID})")
    print("  入力レジスタ 0 = 温度 [0.1 degC] / 保持レジスタ 0 = 目標温度 [0.1 degC]")
    print("  Ctrl-C で停止")
    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
