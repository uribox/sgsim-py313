import asyncio
import websockets
import json
import random
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import queue
import sys
import os


# ⭐ ADDED: Block to dynamically add sg.py's directory to sys.path ⭐
# graph_server.py が存在するディレクトリ (skipGraph3D/)
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# プロジェクトのルートディレクトリ (sgsim-py313) へ移動
project_root = os.path.abspath(os.path.join(current_script_dir, ".."))
# sg.py がある src ディレクトリのパス (sgsim-py313/sgsim-py313/src/)
sg_module_path = os.path.join(project_root, "sgsim-py313", "src")

# このパスがまだ sys.path に含まれていなければ追加
if sg_module_path not in sys.path:
    sys.path.insert(0, sg_module_path)


# ⭐ MODIFIED: sg.py のインポートとダミークラスの改善（最終版） ⭐
try:
    import sg
    from sg import SGNode, MembershipVector, UnicastBase

    if not hasattr(sg.MembershipVector, 'value'):
        original_mv_init = sg.MembershipVector.__init__
        def new_mv_init_patched(self, value=0):
            if original_mv_init is not object.__init__:
                original_mv_init(self, value)
            try:
                self._dummy_value = int(value)
            except (ValueError, TypeError):
                self._dummy_value = 0
        sg.MembershipVector.__init__ = new_mv_init_patched

        @property
        def new_mv_value_property(self):
            return self._dummy_value
        sg.MembershipVector.value = new_mv_value_property
        print("Patched sg.MembershipVector with .value property at runtime.")

except ImportError:
    print("Error: Could not import 'sg' module in graph_server.py. Please ensure sg.py is accessible.")
    print("Using dummy SGNode, MembershipVector, UnicastBase, sg.ALPHA.")
    # --- Start of Dummy Class Definitions for Fallback (CORRECTED) ---
    class MembershipVector:
        def __init__(self, value=0):
            try:
                self._value = int(value)
            except (ValueError, TypeError):
                self._value = 0
        @property
        def value(self):
            return self._value
        def common_prefix_length(self, other): return 0
        def reverse_prefix(self, level): pass
        def __str__(self): return str(self._value)
        def __repr__(self): return f"MV({self._value})"

    class SGNode:
        def __init__(self, key, mv=None):
            self.key = key
            self.mv = mv if mv is not None else MembershipVector(key)
            self.level = 0 # Dummy level (このダミーは sg_main.py からの id_str を持たない)
            self.id_str = str(key) # ダミーノードにも id_str を持たせる
        def routing_table_height(self): return 0
        def __repr__(self): return f"SGNode({self.key})"

    class UnicastBase:
        def short_name(self): return "dummy"
    class SgDummy:
        DEFAULT_N = 10
        DEFAULT_ALPHA = 2
        ALPHA = 2
        VERBOSE = False
    sg = SgDummy
    # --- End of Dummy Class Definitions ---


# --- グローバル変数: 最新のグラフデータを保持 ---
_latest_graph_data = None
_latest_graph_data_lock = threading.Lock()
_graph_data_updated_event = asyncio.Event() # ⭐ ADDED: データ更新を通知するためのイベント ⭐


# ⭐ ADDED: ダミーデータ生成関数 ⭐
# ⭐ MODIFIED: ダミーデータ生成関数をよりランダムに、レベルによってノード数を変化させる ⭐
def generate_dummy_graph_data_for_unity() -> dict:
    """
    Unityに送信するための構造化されたダミーグラフデータを生成します。
    ノードの数、配置、エッジの接続がよりランダムになります。
    特に、レベルが上がるにつれてノード数が減少する傾向を模倣します。
    """
    nodes = []
    edges = []

    num_levels = random.randint(1, 10)
    nodes_per_level_base = random.randint(2, 100)
    level_height = random.uniform(2.0, 5.0)
    radius = random.uniform(8.0, 20.0)

    total_dummy_nodes_generated = 0

    dummy_node_key_counter = 0
    for level in range(num_levels):
        nodes_in_this_level = max(2, int(nodes_per_level_base / (2**level)))
        nodes_in_this_level = max(nodes_in_this_level, 2)

        nodes_in_this_level += random.randint(-1, 1)
        nodes_in_this_level = max(1, nodes_in_this_level)

        if nodes_in_this_level == 0:
            continue

        for i in range(nodes_in_this_level):
            node_key = dummy_node_key_counter
            dummy_node_key_counter += 1

            angle_offset = random.uniform(-0.1, 0.1)
            angle = (i / float(nodes_in_this_level)) * 2 * math.pi + angle_offset

            x_offset = random.uniform(-1.0, 1.0)
            z_offset = random.uniform(-1.0, 1.0)

            x = radius * math.cos(angle) + x_offset
            z = radius * math.sin(angle) + z_offset
            y = level * level_height + random.uniform(-0.5, 0.5)

            mv_dummy_value = random.randint(0, 10000)

            nodes.append({
                "key": node_key,
                "id": f"node_{node_key}@{level}",
                "position": {"x": x, "y": y, "z": z},
                "level": level,
                "mv_value": mv_dummy_value
            })
            total_dummy_nodes_generated += 1

    if len(nodes) > 1:
        num_dummy_edges = random.randint(len(nodes), len(nodes) * 3)

        all_node_ids = [n['id'] for n in nodes]

        for _ in range(num_dummy_edges):
            source_id_str = random.choice(all_node_ids)
            target_id_str = random.choice(all_node_ids)

            if source_id_str != target_id_str:
                edges.append({
                    "source": source_id_str,
                    "target": target_id_str
                })
        unique_edges = []
        seen_edges = set()
        for edge in edges:
            normalized_edge = tuple(sorted((edge['source'], edge['target'])))
            if normalized_edge not in seen_edges:
                seen_edges.add(normalized_edge)
                unique_edges.append(edge)
        edges = unique_edges

    return {
        "nodes": nodes,
        "edges": edges,
        "path": []
    }


def calculate_cylindrical_positions(nodes_dict_list: list, max_level: int) -> dict[str, dict]:
    """
    Skip Graphのノードの辞書リストとレベルに基づいて円筒座標を計算します。
    ノードの 'level' 属性を基にY座標を決定し、円周上に配置します。
    最もノード数の多いレベルを基準に円筒の半径と円周上のスロット数を動的に調整し、
    ノード間の間隔に十分な余裕を持たせ、同じレベルのノード間隔を均等にします。

    :param nodes_dict_list: sg_main.py からの SGNode の情報を含む dict のリスト。
                            各dictには 'key', 'level' (推奨), 'mv_value' (推奨) が必要。
                            'id' (key@level形式) も含まれる想定。
    :param max_level: 描画する最大レベル（ノードデータから検出された最大値）。
    :return: 各ノードID (str) に対応する {x, y, z} 座標の辞書。
    """
    pos: dict[str, dict] = {}

    sg_node_objects = []
    for n_dict in nodes_dict_list:
        node_key = n_dict['key']
        mv_numerical_value = n_dict.get('mv_value', node_key)
        node_mv = MembershipVector(mv_numerical_value)
        node_obj = SGNode(node_key, mv=node_mv)

        node_obj.level = n_dict.get('level', random.randint(0, 3))

        node_obj.id_str = n_dict.get('id', str(node_key))

        sg_node_objects.append(node_obj)

    if not sg_node_objects:
        print("DEBUG(calculate_cylindrical_positions): No nodes to draw. Returning empty positions.")
        return pos

    ALPHA = sg.ALPHA

    total_nodes_to_draw = len(sg_node_objects)

    nodes_per_level_counts = {}
    for node_obj in sg_node_objects:
        nodes_per_level_counts[node_obj.level] = nodes_per_level_counts.get(node_obj.level, 0) + 1

    max_nodes_in_any_single_level = max(nodes_per_level_counts.values()) if nodes_per_level_counts else 1

    min_nodes_per_circle = 10
    spacing_factor = 1

    NODES_PER_LEVEL_IN_CYLINDER = max(min_nodes_per_circle, max_nodes_in_any_single_level * spacing_factor)

    min_radius_val = 8.0
    base_radius_factor = 0.5

    RADIUS = min_radius_val + (NODES_PER_LEVEL_IN_CYLINDER * base_radius_factor)
    RADIUS = max(min_radius_val, RADIUS)

    num_actual_levels_to_draw = (max(n.level for n in sg_node_objects) + 1) if sg_node_objects else 1

    min_level_height = 2.0
    dynamic_height_scale_base = 50.0
    dynamic_height_scale_factor = RADIUS / dynamic_height_scale_base
    dynamic_height_scale_factor = max(1.0, dynamic_height_scale_factor)

    height_base_coefficient = 1.2

    LEVEL_HEIGHT = max(min_level_height, RADIUS * height_base_coefficient * dynamic_height_scale_factor / num_actual_levels_to_draw)

    print(f"DEBUG(calculate_cylindrical_positions): Total nodes: {total_nodes_to_draw}, Max nodes in a level: {max_nodes_in_any_single_level}, Calculated NODES_PER_LEVEL_IN_CYLINDER: {NODES_PER_LEVEL_IN_CYLINDER}, Calculated RADIUS: {RADIUS}, Calculated LEVEL_HEIGHT: {LEVEL_HEIGHT}")

    sg_node_objects.sort(key=lambda n: n.key)

    actual_max_level_in_objects = max(n.level for n in sg_node_objects) if sg_node_objects else 0

    max_level_to_loop = max(max_level, actual_max_level_in_objects)

    for level in range(0, max_level_to_loop + 1):
        level_y_pos = level * LEVEL_HEIGHT

        #print(f"DEBUG(calculate_cylindrical_positions): Processing visual level {level}, calculated Y position: {level_y_pos}", file=sys.stderr)

        nodes_at_current_visual_level = [n for n in sg_node_objects if n.level == level]
        nodes_at_current_visual_level.sort(key=lambda n: n.key)

        if nodes_at_current_visual_level:
            num_nodes_in_this_visual_level = len(nodes_at_current_visual_level)

            if num_nodes_in_this_visual_level == 1:
                start_angle = 0.0
            else:
                start_angle = random.uniform(0, 2 * math.pi / num_nodes_in_this_visual_level)

            for idx_in_visual_level, node_in_group in enumerate(nodes_at_current_visual_level):
                angle = start_angle + (idx_in_visual_level / float(num_nodes_in_this_visual_level)) * 2 * math.pi

                x = RADIUS * math.cos(angle)
                z = RADIUS * math.sin(angle)
                y = level_y_pos

                node_id_for_pos_key = node_in_group.id_str

                if node_id_for_pos_key not in pos:
                    pos[node_id_for_pos_key] = {"x": x, "y": y, "z": z}

    return pos


# skipGraph3D/graph_server.py の convert_sg_data_to_unity_json 関数部分
# ... (関数の冒頭部分から node_positions_3d の計算まで) ...
# ⭐⭐ MODIFIED: convert_sg_data_to_unity_json 関数全体 ⭐⭐
def convert_sg_data_to_unity_json(sg_raw_data: dict) -> dict:
    sg_nodes_dicts = sg_raw_data.get('nodes', [])
    sg_edges_dicts = sg_raw_data.get('edges', [])
    sg_path_dicts = sg_raw_data.get('path', [])

    max_level_from_nodes = 0
    if sg_nodes_dicts:
        all_levels_in_data = [n.get('level', 0) for n in sg_nodes_dicts]
        if all_levels_in_data: 
            max_level_from_nodes = max(all_levels_in_data)
        #print(f"DEBUG(convert_sg_data_to_unity_json): Nodes received. Total: {len(sg_nodes_dicts)}, Max level detected from data: {max_level_from_nodes}, All levels in data: {all_levels_in_data}", file=sys.stderr)
    else:
        #print("DEBUG(convert_sg_data_to_unity_json): No nodes in received data for conversion.", file=sys.stderr)
        pass

    node_positions_3d = calculate_cylindrical_positions(sg_nodes_dicts, max_level_from_nodes)

    # ⭐ ヘルパー関数: ノードキーからレベルを検索する ⭐
    # sg_nodes_dicts (生の辞書リスト) から key に対応する level を取得
    # これを convert_sg_data_to_unity_json の中で定義
    node_key_to_level_map = {n['key']: n.get('level', 0) for n in sg_nodes_dicts}

    unity_nodes = []
    for node_dict in sg_nodes_dicts:
        node_key = node_dict['key']
        node_level = node_dict.get('level', 0) 

        node_unique_id_for_unity = f"node_{node_key}@{node_level}" # sg_main.py の id と合わせる

        position = node_positions_3d.get(node_unique_id_for_unity, {"x":0, "y":0, "z":0}) 
        
        unity_nodes.append({
            "key": node_key,
            "id": node_unique_id_for_unity, 
            "position": position,
            "level": node_level, 
            "mv_value": node_dict.get('mv_value', '') 
        })

    unity_edges = []
    for edge_dict in sg_edges_dicts:
        # source/target は 'key@level' 文字列形式か、'source_key' / 'target_key' 数値形式か、両方に対応
        source_id_or_key = edge_dict.get('source', edge_dict.get('source_key'))
        target_id_or_key = edge_dict.get('target', edge_dict.get('target_key'))

        # 受け取った形式が数値キーの場合、レベルをルックアップして 'key@level' 形式に変換
        if isinstance(source_id_or_key, (int, float)):
            src_node_key = int(source_id_or_key)
            src_node_level = node_key_to_level_map.get(src_node_key, 0)
            source_final_id = f"node_{src_node_key}@{src_node_level}"
        else: # 既に 'key@level' 文字列の場合
            source_final_id = str(source_id_or_key)

        if isinstance(target_id_or_key, (int, float)):
            dst_node_key = int(target_id_or_key)
            dst_node_level = node_key_to_level_map.get(dst_node_key, 0)
            target_final_id = f"node_{dst_node_key}@{dst_node_level}"
        else: # 既に 'key@level' 文字列の場合
            target_final_id = str(target_id_or_key)
        
        unity_edges.append({
            "source": source_final_id, 
            "target": target_final_id  
        })
    
    unity_path = []
    for path_segment in sg_path_dicts:
        from_id_or_key = path_segment.get('from_node_key', path_segment.get('source')) # sourceも許容
        to_id_or_key = path_segment.get('to_node_key', path_segment.get('target')) # targetも許容
        
        if isinstance(from_id_or_key, (int, float)):
            from_node_key = int(from_id_or_key)
            from_node_level = node_key_to_level_map.get(from_node_key, 0)
            from_final_id = f"node_{from_node_key}@{from_node_level}"
        else:
            from_final_id = str(from_id_or_key)

        if isinstance(to_id_or_key, (int, float)):
            to_node_key = int(to_id_or_key)
            to_node_level = node_key_to_level_map.get(to_node_key, 0)
            to_final_id = f"node_{to_node_key}@{to_node_level}"
        else:
            to_final_id = str(to_id_or_key)

        unity_path.append({
            "source": from_final_id, 
            "target": to_final_id,    
            "hop": path_segment.get('hop')
        })

    return {
        "nodes": unity_nodes,
        "edges": unity_edges,
        "path": unity_path
    }

# --- WebSocketサーバーハンドラー ---
async def websocket_handler(websocket, path):
    global _graph_data_updated_event  # ⭐ ADDED: イベントをグローバルとして参照 ⭐
    print("✅ Unity client connected!")
    try:
        while True:
            try:
                with _latest_graph_data_lock:
                    data_to_send = None
                    if _latest_graph_data:
                        data_to_send = _latest_graph_data
                        converted_data = convert_sg_data_to_unity_json(data_to_send)
                        print("--- SENDING TO UNITY (simulation data) ---")

                        # ⭐ MODIFIED: シミュレーションデータ送信後の待機ロジック ⭐
                        _graph_data_updated_event.clear() # 次の更新を待つためにイベントをクリア

                    else:
                        data_to_send = generate_dummy_graph_data_for_unity()
                        converted_data = convert_sg_data_to_unity_json(data_to_send)
                        print("--- SENDING TO UNITY (dummy data) ---")
                        
                    # ⭐⭐⭐ ADDED: Print converted data before sending to Unity ⭐⭐⭐
                    #print("--- SENDING TO UNITY (converted data) ---")
                    # Print only first 1000 characters to prevent console overflow
                    #print(json.dumps(converted_data, indent=2)[:1000] + "...")
                    #print(json.dumps(converted_data, indent=2)) # データ全体を表示
                    #print("-----------------------------------------")
                    # ⭐⭐⭐ END ADDED ⭐⭐⭐
    
                    try:
                        # ⭐ 実際の WebSocket 送信処理 ⭐
                        await websocket.send(json.dumps(converted_data)) 
                        # 送信成功ログは残す
                        print("DEBUG(websocket_handler): Data sent via WebSocket.") 
                    except Exception as send_err:
                        # 送信失敗時のエラーログも残す
                        print(f"🚨 ERROR (websocket_handler): Failed to send via WebSocket: {send_err}")
    
                # ⭐ MODIFIED: データ送信後の待機ロジック ⭐
                if _latest_graph_data: # シミュレーションデータが利用可能な場合
                    await _graph_data_updated_event.wait() # 次のデータ更新まで待機
                else: # ダミーデータの場合
                    await asyncio.sleep(5) # 5秒待機

            except Exception as e: # ⭐ 外側の try-except は、while ループに入る前に発生するエラー用 ⭐
                #print(f"WebSocket handler failed to start: {str(e)}")
                pass
    except websockets.exceptions.ConnectionClosed:
        print("🔌 Unity client disconnected.")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        

# --- HTTPサーバーハンドラー ---
class GraphDataReceiverHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global _graph_data_updated_event # ⭐ ADDED: イベントをグローバルとして参照 ⭐
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            received_data = json.loads(post_data.decode('utf-8'))

            with _latest_graph_data_lock:
                global _latest_graph_data
                _latest_graph_data = received_data
                print("Received new graph data from GUI. _latest_graph_data updated.")
                _graph_data_updated_event.set() # ⭐ ADDED: データが更新されたことを通知 ⭐

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Graph data received"}).encode('utf-8'))

            # ⭐⭐ ADDED: Print received raw data from sg_main.py ⭐⭐
            print("📈 Received new graph data via HTTP POST.")
            print("--- RECEIVED RAW DATA from sg_main.py ---")
            print(json.dumps(received_data, indent=2)) # Print full received data
            print("------------------------------------------")
            # ⭐⭐ END ADDED ⭐⭐

        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid JSON"}).encode('utf-8'))
            print("🚨 ERROR: Received invalid JSON via HTTP POST.")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": f"Server error: {e}"}).encode('utf-8'))
            print(f"🚨 ERROR: HTTP POST handler error: {e}")


# --- サーバー起動ロジック ---
async def start_servers():
    websocket_server = await websockets.serve(websocket_handler, "localhost", 8765)
    print("🚀 Python WebSocket server started at ws://localhost:8765")

    http_server_address = ('localhost', 8001)
    httpd = HTTPServer(http_server_address, GraphDataReceiverHandler)
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()
    print(f"🌐 Python HTTP server started at http://localhost:{http_server_address[1]}")

    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(start_servers())
    except KeyboardInterrupt:
        print("Server terminated by user.")
    except Exception as e:
        print(f"Server exited with error: {e}")


# import asyncio
# import websockets
# import json
# import random
# import math

# def create_cylindrical_graph_data():
#     """
#     ノードを円筒・階層型に配置し、一本の連続した経路を持つデータを生成する関数。
#     """
#     nodes = []
    
#     # --- レイアウト設定 ---
#     num_levels = 8
#     nodes_per_level = 20
#     level_height = 3.0
#     radius = 15.0
#     # ---------------------

#     for level in range(num_levels):
#         for i in range(nodes_per_level):
#             angle = (i / float(nodes_per_level)) * 2 * math.pi
#             x = radius * math.cos(angle)
#             z = radius * math.sin(angle)
#             y = level * level_height
#             nodes.append({
#                 "id": f"node_{level}_{i}",
#                 "position": {"x": x, "y": y, "z": z}
#             })

#     # === 経路生成ロジックの変更箇所 START ===

#     edges = []
#     path_length = 20  # 経路の長さを設定

#     # 1. 経路の最初のノードをランダムに選ぶ
#     start_level = random.randint(0, num_levels - 1)
#     start_node_index = random.randint(0, nodes_per_level - 1)
#     previous_target_id = f"node_{start_level}_{start_node_index}"

#     # 2. 指定した長さの連続した経路を生成
#     for _ in range(path_length):
#         # 現在の始点は、前の終点
#         source_id = previous_target_id
        
#         # 次の終点をランダムに選択
#         next_target_level = random.randint(0, num_levels - 1)
#         next_target_node_index = random.randint(0, nodes_per_level - 1)
#         next_target_id = f"node_{next_target_level}_{next_target_node_index}"

#         # 始点と終点が同じにならないようにする
#         while source_id == next_target_id:
#             next_target_level = random.randint(0, num_levels - 1)
#             next_target_node_index = random.randint(0, nodes_per_level - 1)
#             next_target_id = f"node_{next_target_level}_{next_target_node_index}"

#         # 経路（edge）を作成してリストに追加
#         edges.append({
#             "source": source_id,
#             "target": next_target_id
#         })
        
#         # 次のループのため、今回の終点を記憶しておく
#         previous_target_id = next_target_id

#     # === 経路生成ロジックの変更箇所 END ===
        
#     return {"nodes": nodes, "edges": edges}


# # Unityからの接続を処理するメイン部分
# async def handler(websocket, path):
#     print("✅ Unity client connected!")
#     try:
#         while True:
#             graph_data = create_cylindrical_graph_data()
#             await websocket.send(json.dumps(graph_data))
#             await asyncio.sleep(3)  # 5秒ごとにデータを更新
#     except websockets.exceptions.ConnectionClosed:
#         print("🔌 Unity client disconnected.")


# # サーバーを起動
# async def main():
#     print("🚀 Python WebSocket server started at ws://localhost:8765")
#     async with websockets.serve(handler, "localhost", 8765):
#         await asyncio.Future()


# if __name__ == "__main__":
#     asyncio.run(main())


