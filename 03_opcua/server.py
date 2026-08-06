"""第4回のハンズオン: OPC UA サーバを立てる。

    python 03_opcua/server.py

止めるまで動き続ける（Ctrl-C）。別のターミナルで client.py を実行する。
"""

import asyncio

from asyncua import Server, ua

ENDPOINT = "opc.tcp://127.0.0.1:4840/freeopcua/server/"
NAMESPACE = "http://example.com/industrial-demo/"


async def main() -> None:
    server = Server()
    await server.init()
    server.set_endpoint(ENDPOINT)
    server.set_server_name("Industrial Demo Server")

    # 自分の名前空間を登録する。恒久的な識別子はこの URI のほうで、
    # 返ってくる idx はこのサーバのこの時点での短縮番号にすぎない。
    idx = await server.register_namespace(NAMESPACE)

    device = await server.nodes.objects.add_object(idx, "MyDevice")
    temperature = await device.add_variable(idx, "Temperature", 23.5)
    pressure = await device.add_variable(idx, "Pressure", 101.3)
    motor = await device.add_variable(idx, "MotorEnabled", False)
    await motor.set_writable()

    print(f"OPC UA server listening on {ENDPOINT}")
    print(f"  namespace {NAMESPACE} -> ns={idx}")
    print("  Ctrl-C で停止")

    async with server:
        t = 0.0
        while True:
            await asyncio.sleep(1.0)
            t += 1.0
            # 値が動いていたほうがクライアント側で見て面白い
            await temperature.write_value(round(23.5 + 0.5 * (t % 4 - 1.5), 2))
            await pressure.write_value(round(101.3 + 0.1 * (t % 3 - 1), 2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
