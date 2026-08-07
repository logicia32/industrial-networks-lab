# industrial-networks-lab

産業用通信（Modbus / CANopen / OPC UA）を、ハードウェアを1つも買わずに PC の中だけで動かす自作ラボです。使うのはオープンソースのライブラリと、無料で読める仕様書だけ。線の上を流れるバイト列を、1バイトずつ確かめられます。

Zenn の連載「産業用通信をハードなしで学ぶ」（全5回）で使っているコード一式です。

| 回 | 内容 | ディレクトリ |
|---|---|---|
| 1 | [Modbus をPCの中で動かす](https://zenn.dev/logicia32/articles/2026-07-29-industrial-net-1-modbus) | `01_modbus/` |
| 2 | CANopen 前編・デバイスが自分の辞書を持つ | `02_canopen/` |
| 3 | CANopen 後編・仮想サーボを回す | `02_canopen/` |
| 4 | OPC UA 前編・情報モデルとサーバを立てる | `03_opcua/` |
| 5 | OPC UA 後編・3つを1つのゲートウェイに合流させる | `03_opcua/` |

## 中身

| ファイル | 役割 |
|---|---|
| `01_modbus/demo_tcp.py` | Modbus TCP のサーバとクライアントを1プロセスで動かし、送受信の生バイトを16進で表示する |
| `01_modbus/demo_rtu.py` | 同じことを RTU（シリアル）で。`pty.openpty()` で仮想シリアルのペアを作るので socat も root も要らない（Linux / macOS のみ） |
| `01_modbus/device.py` | 温度計を模した Modbus スレーブ。単体で起動して待ち受ける。第5回のゲートウェイがこれを読みに来る |
| `02_canopen/smoke_test.py` | python-can の `virtual` バックエンドで、SYNC と TPDO が成立することだけを確かめる最小の骨格 |
| `02_canopen/canmon.py` | バスモニタ。candump 相当だが、COB-ID を CANopen として解釈して表示する |
| `02_canopen/cia402.py` | CiA 402 の Controlword / Statusword のビット定義と、状態機械 |
| `02_canopen/servo.py` | 仮想サーボノード。SDO サーバ、RPDO 受信、SYNC ごとの追従計算、TPDO 送信 |
| `02_canopen/run_servo_demo.py` | NMT で起動し、SDO で通電させ、SYNC 10ms 周期で目標位置を送って追従カーブを記録する |
| `03_opcua/server.py` | OPC UA サーバ。変数を3つ持つだけの最小構成 |
| `03_opcua/client.py` | クライアント。アドレス空間を歩いて、型定義まで辿る |
| `03_opcua/gateway.py` | Modbus と CANopen を OPC UA で束ねるゲートウェイ。asyncio 2本 + スレッド1本の構成 |
| `03_opcua/gw_client.py` | ゲートウェイに OPC UA で繋いで、その先のサーボを動かす |
| `docs/gen_*.py`, `docs/figkit.py`, `figstyle.py` | 記事の図を書き出すスクリプトと共通スタイル |
| `docs/check_figures.py` | 図の文字はみ出し・重なりを bbox の測定で検出する。目視では取りこぼすので、図を直したらこれを通す |

## 走らせ方

```bash
python3 -m venv .venv                                # Windows: py -m venv .venv
./.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip install -r requirements.txt
```

以降のコマンドは Linux / macOS 形式です。Windows では `./.venv/bin/python` を `.venv\Scripts\python` に読み替えてください。

```bash
# 第1回 Modbus（1プロセスで完結）
./.venv/bin/python 01_modbus/demo_tcp.py
./.venv/bin/python 01_modbus/demo_rtu.py     # Linux / macOS のみ（pty を使うため）

# 第2回 CANopen の骨格とバスモニタ（どちらも1プロセスで完結）
./.venv/bin/python 02_canopen/smoke_test.py
./.venv/bin/python 02_canopen/canmon.py

# 第3回 仮想サーボ（1プロセスで完結。docs/figures/cia402_follow.png を書き出す）
./.venv/bin/python 02_canopen/run_servo_demo.py

# 第4回 OPC UA（ターミナル2枚）
./.venv/bin/python 03_opcua/server.py        # ターミナル1（Ctrl-C で止める）
./.venv/bin/python 03_opcua/client.py        # ターミナル2

# 第5回 ゲートウェイ（ターミナル3枚）
./.venv/bin/python 01_modbus/device.py       # ターミナル1
./.venv/bin/python 03_opcua/gateway.py       # ターミナル2
./.venv/bin/python 03_opcua/gw_client.py     # ターミナル3

# 記事の図を作り直す（docs/figures/ に書き出す）
./.venv/bin/python docs/gen_modbus_frame_overlay.py

# 図の文字はみ出し・重なりを測る（PNG は書き換えない。0 件で正常）
./.venv/bin/python docs/check_figures.py
```

## 出てくるもの

Modbus は、要求と応答がそのまま16進で出ます。

```
--- 保持レジスタ 0〜3 を読む ---
  RX 00 01 00 00 00 06 01 03 00 00 00 04
  TX 00 01 00 00 00 0b 01 03 08 00 00 00 00 00 00 00 00
  -> [0, 0, 0, 0]
--- 存在しない 9000 番地を読む ---
  RX 00 05 00 00 00 06 01 03 23 28 00 01
  TX 00 05 00 00 00 03 01 83 02
  isError: True | ExceptionResponse(dev_id=1, function_code=131, exception_code=2)
```

同じ読み取りを RTU で流すと `RX 01 03 00 00 00 04 44 09` になります。MBAP ヘッダの7バイトが消えて、先頭にアドレス1バイト、末尾に CRC 2バイトが付き、真ん中の `03 00 00 00 04` は TCP と同じままです。

サーボは CiA 402 の順番どおりに通電し、SYNC 10ms 周期で目標位置に寄っていきます。

```
  t=0.001s  target=     0  actual=     0  status=0x0237
  t=0.102s  target= 10000  actual=  6229  status=0x0237
  t=0.401s  target= 10000  actual=  9971  status=0x0237
  取りこぼした SYNC 応答: 0 / 60
```

ゲートウェイでは、OPC UA から書いた目標位置が CAN の RPDO まで貫通します。

```
--> OPC UA から TargetPosition = 10000 を書く
    ActualPosition =   8031   Statusword = 0x0237
    ActualPosition =  10000   Statusword = 0x0237
```

追従の途中の値は時間に依存するので、実行のたびに少し変わります。到達する位置と、状態遷移の順番は変わりません。

## 必要なもの

`requirements.txt` にピン留めしてあります。

| パッケージ | バージョン | ライセンス |
|---|---|---|
| pymodbus[serial] | 3.14.0 | BSD-3-Clause |
| python-can[multicast] | 4.6.1 | LGPL-3.0-only |
| asyncua | 2.0.1 | LGPL-3.0-or-later |
| matplotlib | 3.10.7 | PSF-based |

バージョンは固定してください。pymodbus は 3.x の中でも破壊的変更を続けていて、3.14.0 で datastore の API が変わっています。`[serial]` を外すと pyserial が入らず RTU が動かず、`[multicast]` を外すと発展課題が落ちます。

Python 3.10 以上が必要です（型注釈に `X | None` を使っているため）。動作確認は Python 3.12 / WSL2 Ubuntu 24.04。

## 正直な境界

- サーバは全部 127.0.0.1 に束ねてあります。外から繋ぐことは想定していません。`device.py` の `--host` にループバック以外を渡すと、起動を止めます。
- OPC UA は認証も暗号化も設定していません。起動時に asyncua が「暗号化ポリシーがない」と警告を出しますが、ループバックで学ぶための構成なので、そのままにしてあります。実運用では証明書と SecurityPolicy を設定します。
- CAN は python-can の `virtual` バックエンドです。同一プロセス内のバス同士しか繋がないので、調停もビットタイミングも再現していません。見えるのは、フレームの組み立てとプロトコルの手順です。
- RTU も pty の上なので、3.5文字ギャップのようなタイミングは再現しません。
- CiA 402 の仕様書そのものは会員限定です。ここの実装は、各社が無償公開しているサーボの取扱説明書とオープンソース実装から再構成したもので、規格の写しではありません。
- CANopen のライブラリ（canopen パッケージ）は使わず、フレームを自前で組み立てています。1バイトずつ見せるためです。

## ライセンス

MIT（`LICENSE`）。使っているライブラリはすべてオープンソースで、商用製品は1つも使っていません。
