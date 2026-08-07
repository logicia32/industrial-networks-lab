"""第5回のハンズオン: ゲートウェイに OPC UA で繋いで、サーボを動かす。

    python 01_modbus/device.py      # ターミナル1
    python 03_opcua/gateway.py      # ターミナル2
    python 03_opcua/gw_client.py    # ターミナル3
"""

import asyncio

from asyncua import Client, ua

ENDPOINT = "opc.tcp://127.0.0.1:4840/gateway/"
NAMESPACE = "http://example.com/plant/"


async def show(nodes: dict) -> None:
    for label, node in nodes.items():
        dv = await node.read_data_value(raise_on_bad_status=False)
        value = dv.Value.Value
        if isinstance(value, int) and label == "Statusword":
            value = f"0x{value:04X}"
        print(f"  {label:<16} {str(value):<10} StatusCode = {dv.StatusCode.name}")


async def main() -> None:
    async with Client(ENDPOINT) as client:
        idx = await client.get_namespace_index(NAMESPACE)
        print(f"browse OK. namespace idx = {idx}")

        root = client.nodes.root
        n_temp = await root.get_child(
            ["0:Objects", f"{idx}:Plant", f"{idx}:TemperatureSensor", f"{idx}:Temperature"])
        n_actual = await root.get_child(
            ["0:Objects", f"{idx}:Plant", f"{idx}:AxisX", f"{idx}:ActualPosition"])
        n_target = await root.get_child(
            ["0:Objects", f"{idx}:Plant", f"{idx}:AxisX", f"{idx}:TargetPosition"])
        n_status = await root.get_child(
            ["0:Objects", f"{idx}:Plant", f"{idx}:AxisX", f"{idx}:Statusword"])

        watch = {"Temperature": n_temp, "ActualPosition": n_actual,
                 "Statusword": n_status}

        print()
        await show(watch)

        print()
        print("--> OPC UA から TargetPosition = 10000 を書く")
        await n_target.write_value(ua.Variant(10000, ua.VariantType.Int32))

        for _ in range(6):
            await asyncio.sleep(0.15)
            dv = await n_actual.read_data_value(raise_on_bad_status=False)
            st = await n_status.read_data_value(raise_on_bad_status=False)
            # Bad のとき値は None になる。数値の書式をそのまま当てると
            # TypeError で落ちるので、信用できないことを表示に出す。
            if dv.Value.Value is None or st.Value.Value is None:
                print(f"    ActualPosition = {'---':>6}   Statusword = ------   "
                      f"({dv.StatusCode.name})")
            else:
                print(f"    ActualPosition = {dv.Value.Value:6d}   "
                      f"Statusword = 0x{st.Value.Value:04X}")

        print()
        print("--> 最終状態")
        await show(watch)


if __name__ == "__main__":
    asyncio.run(main())
