"""第5回のハンズオン: Modbus と CANopen を OPC UA で束ねるゲートウェイ。

構成は「asyncio 2本 + スレッド1本」:

  ┌─ asyncio イベントループ ─────────────────┐
  │  OPC UA サーバ (asyncua)                  │
  │  Modbus クライアント (pymodbus / await)   │
  │            │  threading.Lock + 共有 dict  │
  └────────────┼──────────────────────────────┘
               │
      ┌────────▼─────────┐
      │ CAN マスタ (別スレッド)  │
      │ bus.recv() は        │
      │ ブロッキングなので     │
      │ asyncio に乗らない     │
      └──────────────────┘

先に別ターミナルで Modbus デバイスを起動しておく:
    python 01_modbus/device.py
    python 03_opcua/gateway.py
"""

import asyncio
import pathlib
import sys
import threading
import time

import can
from asyncua import Server, ua
from pymodbus.client import AsyncModbusTcpClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "02_canopen"))
import cia402                                    # noqa: E402
from run_servo_demo import Master                # noqa: E402  SDO/PDO の面倒を見る係
from servo import Cia402Servo                    # noqa: E402

ENDPOINT = "opc.tcp://127.0.0.1:4840/gateway/"
NAMESPACE = "http://example.com/plant/"

MODBUS_HOST, MODBUS_PORT, MODBUS_DEVICE_ID = "127.0.0.1", 5020, 1
CAN_CHANNEL, CAN_NODE_ID = "gateway-can", 1
CAN_PERIOD = 0.010          # 10 ms
OPCUA_PERIOD = 0.05         # 50 ms
MODBUS_DEADLINE = 1.0       # Modbus 1往復に許す時間。相手が黙っていても周期を守る
CAN_STALE_LIMIT = 5         # TPDO をこの回数続けて取りこぼしたら、値を Bad にする

# --- 現場の番地（この対応表がゲートウェイの本体） ---
MB_IR_TEMPERATURE = 0       # 入力レジスタ0 = 温度 [0.1 degC]
MB_HR_SETPOINT = 0          # 保持レジスタ0 = 目標温度 [0.1 degC]


class CanWorker(threading.Thread):
    """CANopen サーボを10ms周期で回し、最新値を共有 dict に置く。

    python-can の recv() はブロッキングなので、ここは必ず別スレッドにする。
    asyncio のループの中で recv() を呼ぶと全体が止まる。
    """

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._shared = {"actual": 0, "statusword": 0, "target": 0, "misses": 0}
        self.ready = threading.Event()
        self.error: str | None = None

    def set_target(self, value: int) -> None:
        with self._lock:
            self._shared["target"] = int(value)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._shared)

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        servo = Cia402Servo(CAN_CHANNEL, node_id=CAN_NODE_ID, gain=0.15)
        servo.start()
        bus = None
        try:
            if not servo.ready.wait(timeout=5.0):
                # ここで黙って進むと、初期値の 0 を「正しい現在位置」として
                # OPC UA に出してしまう。起動できなかったことを持ち帰る。
                self.error = "仮想サーボノードが起動しませんでした"
                return

            bus = can.Bus(interface="virtual", channel=CAN_CHANNEL)
            master = Master(bus, CAN_NODE_ID)
            time.sleep(0.05)
            master.nmt_start()
            time.sleep(0.02)
            # CiA 402 の起動シーケンス（第3回でやったのと同じ）
            for cw in (cia402.CW_SHUTDOWN, cia402.CW_SWITCH_ON,
                       cia402.CW_ENABLE_OPERATION):
                master.sdo_write(*cia402.OD_CONTROLWORD, cw, 2)
            master.sdo_write(*cia402.OD_MODES_OF_OPERATION, cia402.MODE_CSP, 1)
            self.ready.set()

            t0 = time.monotonic()
            i = 0
            while not self._stop_event.is_set():
                with self._lock:
                    target = self._shared["target"]
                master.send_rpdo1(target, cia402.CW_ENABLE_OPERATION)
                got = master.sync_and_collect(timeout=CAN_PERIOD * 3)
                with self._lock:
                    if got:
                        self._shared["actual"] = master.last_actual
                        self._shared["statusword"] = master.last_status
                        self._shared["misses"] = 0
                    else:
                        # TPDO が返らなかった周期。前回の値をそのまま出し続けると
                        # 値が固まるので、動いている軸が止まって見えるし、
                        # 途切れたリンクの向こうのデータが生きているようにも見える。
                        self._shared["misses"] += 1
                i += 1
                time.sleep(max(0.0, t0 + i * CAN_PERIOD - time.monotonic()))
        finally:
            # 起動に失敗した場合も、待っている側を止めたままにしない
            self.ready.set()
            servo.stop()
            servo.join(timeout=1.0)
            if bus is not None:
                bus.shutdown()


async def set_bad(node, code: int) -> None:
    """「この値は今信用できない」を OPC UA の言葉で表明する。
    Modbus にも CANopen にも、これを運ぶ場所が無い。

    Value を省くと Null バリアントになる。0 を書いてしまうと
    「本当に 0 だった」と区別がつかなくなるので、値は載せない。
    （ua.Variant(None, ua.VariantType.Double) は UaError になる。
      None を持てるのは Null 型だけ）
    """
    await node.write_value(ua.DataValue(StatusCode=ua.StatusCode(code)))


async def main() -> None:
    can_worker = CanWorker()
    can_worker.start()
    modbus = None
    try:
        if not can_worker.ready.wait(timeout=10.0):
            raise RuntimeError("CAN スレッドが起動しませんでした")
        if can_worker.error:
            raise RuntimeError(can_worker.error)

        server = Server()
        await server.init()
        server.set_endpoint(ENDPOINT)
        server.set_server_name("Plant Gateway")
        idx = await server.register_namespace(NAMESPACE)

        plant = await server.nodes.objects.add_object(idx, "Plant")

        sensor = await plant.add_object(idx, "TemperatureSensor")
        n_temp = await sensor.add_variable(
            idx, "Temperature", 0.0, varianttype=ua.VariantType.Double)
        n_setpoint = await sensor.add_variable(
            idx, "Setpoint", 0.0, varianttype=ua.VariantType.Double)
        await n_setpoint.set_writable()

        axis = await plant.add_object(idx, "AxisX")
        n_actual = await axis.add_variable(
            idx, "ActualPosition", 0, varianttype=ua.VariantType.Int32)
        n_target = await axis.add_variable(
            idx, "TargetPosition", 0, varianttype=ua.VariantType.Int32)
        n_status = await axis.add_variable(
            idx, "Statusword", 0, varianttype=ua.VariantType.UInt16)
        await n_target.set_writable()

        modbus = AsyncModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT, timeout=0.5)
        await modbus.connect()

        print(f"OPC UA gateway listening on {ENDPOINT}")
        print(f"  namespace {NAMESPACE} -> ns={idx}")
        print(f"  Modbus  {MODBUS_HOST}:{MODBUS_PORT} -> Plant/TemperatureSensor")
        print(f"  CANopen node {CAN_NODE_ID} (virtual) -> Plant/AxisX")
        print("  Ctrl-C で停止")

        # 起動時に現場の目標温度を読んで、OPC UA 側の初期値をそれに合わせる。
        # これをしないと、まだ誰も書いていない初期値 0.0 を「変化した」と見なして、
        # 起動しただけで現場の設定値を 0 に落としてしまう。
        try:
            rq = await asyncio.wait_for(
                modbus.read_holding_registers(MB_HR_SETPOINT, count=1,
                                              device_id=MODBUS_DEVICE_ID),
                timeout=MODBUS_DEADLINE)
            last_setpoint = None if rq.isError() else rq.registers[0] / 10.0
        except Exception:
            last_setpoint = None
        if last_setpoint is None:
            # 現場が読めないうちは、こちらから書きに行かない。
            # 手元の値を「同期済み」と見なしておけば、余計な書き込みが出ない。
            last_setpoint = await n_setpoint.read_value()
        else:
            await n_setpoint.write_value(last_setpoint)

        pending = None      # 現場へまだ書けていない目標温度
        async with server:
            while True:
                # --- Modbus 側 ---------------------------------------------
                try:
                    # 時間を切らないと、繋がるが黙っている相手や再接続待ちで
                    # ここが返らず、CAN 側の更新まで巻き込んで止まる。
                    rr = await asyncio.wait_for(
                        modbus.read_input_registers(
                            MB_IR_TEMPERATURE, count=1,
                            device_id=MODBUS_DEVICE_ID),
                        timeout=MODBUS_DEADLINE)
                    if rr.isError():
                        # 例外応答 = 相手は生きているが、この要求は通らない
                        await set_bad(n_temp, ua.StatusCodes.BadConfigurationError)
                    else:
                        await n_temp.write_value(rr.registers[0] / 10.0)
                except Exception:
                    # 無応答 = 相手が見えない
                    await set_bad(n_temp, ua.StatusCodes.BadCommunicationError)

                # OPC UA から書かれた目標温度を Modbus に流す。
                # 指令は pending に持つ。ノードの値を頼りにできないのは、Bad を
                # 付けると asyncua が値を落とす（読み直すと None になる）ため。
                # 書けたときだけ last_setpoint を確定させる。先に更新してしまうと、
                # 失敗した書き込みが二度と再送されず、指令が黙って消える。
                dv = await n_setpoint.read_data_value(raise_on_bad_status=False)
                if dv.Value.Value is not None:
                    pending = dv.Value.Value
                if pending is not None and pending != last_setpoint:
                    try:
                        rq = await asyncio.wait_for(
                            modbus.write_register(MB_HR_SETPOINT, int(pending * 10),
                                                  device_id=MODBUS_DEVICE_ID),
                            timeout=MODBUS_DEADLINE)
                        # 例外応答は送出されず戻り値で返る。見ないと失敗が消える。
                        code = (ua.StatusCodes.BadConfigurationError
                                if rq.isError() else None)
                    except Exception:
                        code = ua.StatusCodes.BadCommunicationError
                    if code is None:
                        last_setpoint = pending
                        await n_setpoint.write_value(pending)   # Good に戻す
                        pending = None
                    else:
                        # 現場に届いていないことを読み手に見せる。pending は
                        # 残るので、次の周期でもう一度送りに行く。
                        await set_bad(n_setpoint, code)

                # --- CANopen 側 --------------------------------------------
                snap = can_worker.snapshot()
                if not can_worker.is_alive() or snap["misses"] >= CAN_STALE_LIMIT:
                    # TPDO が続けて返っていない。手元にあるのは古い値なので、
                    # 現在値のふりをさせない。Modbus 側と同じ扱いにする。
                    await set_bad(n_actual, ua.StatusCodes.BadCommunicationError)
                    await set_bad(n_status, ua.StatusCodes.BadCommunicationError)
                else:
                    await n_actual.write_value(
                        ua.Variant(snap["actual"], ua.VariantType.Int32))
                    await n_status.write_value(
                        ua.Variant(snap["statusword"], ua.VariantType.UInt16))

                # OPC UA から書かれた目標位置を CAN スレッドに渡す
                dv = await n_target.read_data_value(raise_on_bad_status=False)
                if dv.Value.Value is not None:
                    can_worker.set_target(dv.Value.Value)

                await asyncio.sleep(OPCUA_PERIOD)
    finally:
        # 例外で抜けても、CAN スレッドと Modbus 接続は必ず畳む。
        # ここが無いと CanWorker.stop() は誰からも呼ばれず、run() の finally
        # （サーボの停止と bus.shutdown）も一度も走らない。
        can_worker.stop()
        can_worker.join(timeout=2.0)
        if modbus is not None:
            modbus.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
