"""第4回のハンズオン: OPC UA クライアントでアドレス空間を歩く。

先に別のターミナルで server.py を起動しておくこと。

    python 03_opcua/server.py      # ターミナル1
    python 03_opcua/client.py      # ターミナル2
"""

import asyncio

from asyncua import Client, ua

ENDPOINT = "opc.tcp://127.0.0.1:4840/freeopcua/server/"
NAMESPACE = "http://example.com/industrial-demo/"


async def main() -> None:
    async with Client(ENDPOINT) as client:
        print(f"Connected to {ENDPOINT}")

        # URI から index を引く。ns=2 のような番号を直書きしない。
        idx = await client.get_namespace_index(NAMESPACE)
        print(f"  namespace {NAMESPACE} -> ns={idx}")
        print()

        # Objects の下に何がいるか見る
        print("Objects")
        for child in await client.nodes.objects.get_children():
            name = await child.read_browse_name()
            print(f" └ {name.Name}")

        device = await client.nodes.root.get_child(
            ["0:Objects", f"{idx}:MyDevice"])
        print()
        print("MyDevice")
        for var in await device.get_children():
            name = await var.read_browse_name()
            # 値ではなく DataValue を読む。値・信頼度・時刻がまとめて返る。
            dv = await var.read_data_value(raise_on_bad_status=False)
            dtype = await var.read_data_type_as_variant_type()
            print(f" ├ {name.Name:<14} = {str(dv.Value.Value):<8} "
                  f"({dtype.name:<8}) StatusCode: {dv.StatusCode.name}")

        # 型定義もアドレス空間の中のノードなので、実行時に辿れる
        temp = await device.get_child([f"{idx}:Temperature"])
        type_id = await temp.read_type_definition()
        type_node = client.get_node(type_id)          # get_node は同期メソッド
        type_name = await type_node.read_browse_name()
        print()
        print("--> Temperature の型定義を辿る")
        print(f"    {type_name.Name}  (ns={type_id.NamespaceIndex};i={type_id.Identifier})")


if __name__ == "__main__":
    asyncio.run(main())
