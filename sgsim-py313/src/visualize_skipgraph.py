# viz_skipgraph_ipcolor.py
import socket, threading, time, requests, json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import sg_draw
import sg                          # sg_draw が参照するので import 必須
from realtime_node import RealNode  # ← 既存のクラス

LEVELS = 4

# (ip, port) -> last info
DISCOVERED_NODES = {}

GRAPH_SERVER_HTTP_PORT = 8001 
GRAPH_SERVER_URL = f"http://localhost:{GRAPH_SERVER_HTTP_PORT}/"


# ---- 経路計算ヘルパ ----
def greedy_route(nmap, src, dst):
    if src not in nmap or dst not in nmap:
        return []
    path = [src]
    cur = src
    visited = {src}
    while cur != dst:
        best = None
        best_d = abs(dst - cur)
        cur_info = nmap.get(cur)
        if not cur_info:
            break
        for nb in cur_info["neighbors"]:
            for side in ("LEFT", "RIGHT"):
                for k in nb[side]:
                    if k is None or k in visited or k not in nmap:
                        continue
                    d = abs(dst - k)
                    if d < best_d:
                        best_d = d
                        best = k
        if best is None:
            break
        visited.add(best)
        path.append(best)
        cur = best
    return path

def find_level_between(nmap, a, b):
    for nb in nmap.get(a, {}).get("neighbors", []):
        if b in nb["LEFT"] or b in nb["RIGHT"]:
            return nb["level"]
    return 0

# ---- UDP 受信 ----
def listen_for_nodes(port=12000):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', port))
    while True:
        msg, addr = s.recvfrom(1024)
        try:
            info = json.loads(msg.decode())
            p = info.get("port", 8000)
            DISCOVERED_NODES[(addr[0], p)] = info
        except Exception:
            pass

# ---- HTTP 取得 ----
def fetch_node_info(ip, port):
    try:
        r = requests.get(f"http://{ip}:{port}/", timeout=1.5)
        return r.json()
    except Exception:
        return None

# ---- 描画 ----
def plot_skipgraph(ax, nodes_json):
    ax.clear()
    if not nodes_json:
        ax.text(0.5, 0.5, "no nodes yet", transform=ax.transAxes,
                ha="center", va="center")
        ax.figure.canvas.draw_idle()
        plt.pause(0.1)
        return

    # JSON -> RealNode
    rnodes = [RealNode(n["key"], n["mv"], n["neighbors"]) for n in nodes_json]
    max_lvl = max((max([nb["level"] for nb in n["neighbors"]], default=0)
                   for n in nodes_json), default=0)

    labels, pos = sg_draw.render_topology_base(ax, rnodes, max_lvl)

    # --------- 経路線 ---------
    nmap = {n["key"]: n for n in nodes_json}
    if len(nmap) >= 2:
        src_key = min(nmap)
        dst_key = max(nmap)
        route = greedy_route(nmap, src_key, dst_key)
        if len(route) >= 2:
            for a, b in zip(route, route[1:]):
                lvl = find_level_between(nmap, a, b)
                an, bn = f"{a}@{lvl}", f"{b}@{lvl}"
                if an not in pos or bn not in pos:
                    for cand in range(max_lvl + 1):
                        an, bn = f"{a}@{cand}", f"{b}@{cand}"
                        if an in pos and bn in pos:
                            break
                if an in pos and bn in pos:
                    ax.plot([pos[an][0], pos[bn][0]],
                            [pos[an][1], pos[bn][1]],
                            color='orange', lw=2, zorder=5)
            ax.text(0, max(y for (_, y) in pos.values()),
                    f"{src_key}->{dst_key}", color="magenta")

    # --------- IP 色分けリング ---------
    ips = sorted({n["_ip"] for n in nodes_json})
    cmap = plt.get_cmap("tab20")
    ip_color = {ip: cmap(i % 20) for i, ip in enumerate(ips)}

    for n in nodes_json:
        key = n["key"]
        col = ip_color[n["_ip"]]
        # 最初に見つかった level の座標を使う
        nid = None
        for nb in n["neighbors"]:
            nid_cand = f"{key}@{nb['level']}"
            if nid_cand in pos:
                nid = nid_cand
                break
        if nid is None:
            # レベル情報が空でも保険
            nid = next((k for k in pos if k.startswith(f"{key}@")), None)
        if nid is None:
            continue
        x, y = pos[nid]
        ax.scatter([x], [y], s=470, facecolors='none',
                   edgecolors=col, linewidths=4, zorder=6)

    # 凡例
    handles = [mpatches.Patch(color=ip_color[ip], label=ip) for ip in ips]
    ax.legend(handles=handles, loc="upper right")

    # データ送信（route が存在する場合）
    send_graph_to_server(nodes_json, route if 'route' in locals() else [])


    ax.figure.canvas.draw_idle()
    plt.pause(0.1)

def send_graph_to_server(nodes_json, route):
    sim_nodes_data_for_json = []
    sim_edges_data_for_json = []
    sim_path_data_for_json = []

    nmap = {n["key"]: n for n in nodes_json}
    
    # node情報
    for n in nodes_json:
        key = n["key"]
        mv_value = n["mv"]
        for nb in n["neighbors"]:
            lvl = nb["level"]
            node_id = f"node_{key}@{lvl}"
            sim_nodes_data_for_json.append({
                "key": key,
                "id": node_id,
                "position": {"x": 0, "y": 0, "z": 0},  # 必要に応じて補完
                "level": lvl,
                "mv_value": mv_value
            })

            # デバッグ用にノード情報を表示--------------------------------------------------------------------
            print(f'key:{key}')
            print(f'id:{node_id}')
            print(f'level:{lvl}')
            print(f'mv_value:{mv_value}')
            print('---------------------------------------------------------------')
            #-----------------------------------------------------------------------------------------------

            # エッジ情報（重複回避）
            for side in ("LEFT", "RIGHT"):
                for neighbor_key in nb[side]:
                    if neighbor_key is not None:
                        source = node_id
                        target = f"node_{neighbor_key}@{lvl}"
                        edge = {"source": source, "target": target}
                        if edge not in sim_edges_data_for_json and \
                           {"source": target, "target": source} not in sim_edges_data_for_json:
                            sim_edges_data_for_json.append(edge)

    # 経路情報（Hop Path）
    for i in range(len(route) - 1):
        a = route[i]
        b = route[i + 1]
        lvl = find_level_between(nmap, a, b)
        sim_path_data_for_json.append({
            "source": f"node_{a}@{lvl}",
            "target": f"node_{b}@{lvl}",
            "hop": 1
        })

    data_for_3d_update = {
        "nodes": sim_nodes_data_for_json,
        "edges": sim_edges_data_for_json,
        "path": sim_path_data_for_json
    }

    
    # ---- POST送信処理 ----
    try:
        print(f"\n--- visualize_skipgraph.py: Sending 3D data for Hop Graph to server ---") 
        response = requests.post(GRAPH_SERVER_URL, json=data_for_3d_update, timeout=100)
        response.raise_for_status()
        print(f"🎉 3D data sent successfully from visualize_skipgraph.py: {response.json()}")
    except requests.exceptions.ConnectionError as e:
        print(f"🚨 ERROR: Could not connect to graph server at {GRAPH_SERVER_URL}. Is it running? Error: {e}")
    except requests.exceptions.Timeout as e:
        print(f"🚨 ERROR: Connection to graph server timed out. Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"🚨 ERROR: Failed to send 3D data: {e}")


# ---- main ----
if __name__ == "__main__":
    print("動的探索モードでSkipGraphノードを可視化します（IPごと色分け）")
    threading.Thread(target=listen_for_nodes, daemon=True).start()

    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 7.5))

    try:
        while True:
            nodes = []
            for (ip, port), _ in list(DISCOVERED_NODES.items()):
                info = fetch_node_info(ip, port)
                if info:
                    info["_ip"] = ip
                    info["_port"] = port
                    nodes.append(info)
            plot_skipgraph(ax, nodes)
            time.sleep(100.0)
    except KeyboardInterrupt:
        print("終了")

