import sys
import networkx as nx
from matplotlib import axes
from matplotlib import pyplot as plt

import requests #  必要: HTTP POSTのために必要 
import json     #  必要: JSONデータを扱うために必要 

import sg
from sg import SGNode, MembershipVector, UnicastBase

import random

# ADDED: graph_server.py の URL 定数 (sg_draw.py の冒頭に追加) 
GRAPH_SERVER_HTTP_PORT = 8001 
GRAPH_SERVER_URL = f"http://localhost:{GRAPH_SERVER_HTTP_PORT}/"

FIG_SIZE = (10, 7.5)

def node_with_level(node: SGNode, level: int) -> str:
    # sg_main.py と graph_server.py での ID 形式と合わせる
    return f"node_{node.key}@{level}"


def ingredients(nodes: list[SGNode], max_level: int) -> \
        tuple[nx.Graph, nx.Graph, dict[str, int], dict[str, tuple[int, int]]]:
    """
    Generate ingredients for rendering a skip graph
    :param nodes
    :param max_level the max level (inclusive) for drawing a skip graph.
    :return tuple of (the base graph, left-side legends, node labels, positions of each object).
    """
    g = nx.Graph()
    g_aux = nx.Graph()
    labels: dict[str, int] = {}
    pos: dict[str, tuple[int, int]] = {}
    y = 0 
    x_coords = {
        "level": 0,
        "mv": 2,
        "nodes": 4
    }
    done = {} 
    for level in range(0, max_level + 1):
        prefix = 0
        level_string = f"lv {level}"
        g_aux.add_node(level_string)
        pos[level_string] = (x_coords["level"], y)
        if level != 0:
            plt.axhline(y=y-0.5, xmin=0, xmax=1) 
        for i in range(sg.ALPHA**level):
            mv = MembershipVector(prefix)
            mv.reverse_prefix(level) 
            u = None
            exists = False
            edge_drawn = False
            for ind, j in enumerate(range(len(nodes))):
                w = nodes[j]
                if w.key in done:
                    continue
                if w.mv.common_prefix_length(mv) >= level:
                    exists = True
                    w_string = node_with_level(w, level)
                    g.add_node(w_string)
                    pos[w_string] = (x_coords["nodes"] + ind, y)
                    labels[w_string] = w.key
                    if u is not None:
                        u_string = node_with_level(u, level)
                        g.add_edge(u_string, w_string)
                        edge_drawn = True
                    u = w
            if u is not None and not edge_drawn: 
                done[u.key] = True
            prefix += 1
            if exists:
                # 修正: MembershipVector.MAX_LEVEL は sg.py で定義されるはず 
                # もし sg.py を修正できないなら、ここでは固定値を使うか、動的に算出する
                mv_max_level = sg.MembershipVector.MAX_LEVEL if hasattr(sg.MembershipVector, 'MAX_LEVEL') else 32 
                prefix_string = f"{mv}"[0:level] + "*" * (mv_max_level - level)
                g_aux.add_node(prefix_string)
                pos[prefix_string] = (x_coords["mv"], y)
                y += 1
    return g, g_aux, labels, pos

def render_topology_base(ax: axes.Axes, nodes: list[SGNode], max_level: int):
    g, g_aux, labels, pos = ingredients(nodes, max_level)
    nx.draw_networkx(g, pos=pos, node_color="c", labels=labels, ax=ax)
    nx.draw_networkx(g_aux, pos=pos, node_shape="", ax=ax)
    return labels, pos

def output_topology(nodes: list[SGNode], max_level: int, filename: str) -> None:
    _, ax = plt.subplots(figsize=FIG_SIZE)
    render_topology_base(ax, nodes, max_level)
    plt.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.95)
    if filename is None:
        print("Showing the topology. Close the window to proceed.", file=sys.stderr) 
        plt.show()
    else:
        plt.savefig(filename)
    plt.close('all')

def render_hop_graph(root_msg: UnicastBase, nodes: list[SGNode], filename: str, diagonal=False) -> None:
    def recurse(parent: UnicastBase):
        nonlocal highest_level, edge_labels
        highest_level = max(highest_level, parent.render_level)
        for msg in parent.children:
            if diagonal:
                u = node_with_level(parent.receiver, parent.render_level)
                v = node_with_level(msg.receiver, msg.render_level)
                unicast_graph.add_edge(u, v)
                edge_labels[(u, v)] = msg.hop
            else:
                u = node_with_level(parent.receiver, parent.render_level)
                v = node_with_level(parent.receiver, msg.render_level)
                w = node_with_level(msg.receiver, msg.render_level)
                unicast_graph.add_edge(u, v)
                unicast_graph.add_edge(v, w)
                edge_labels[(v, w)] = msg.hop
            recurse(msg)

    unicast_graph = nx.DiGraph()
    highest_level = 0
    edge_labels = {}
    recurse(root_msg)
    print(f"unicast edges={list(unicast_graph.edges())}")

    # ADDED: 3D データ送信ロジックをここに追加 
    # 2D 描画に必要なノードとエッジの情報を抽出・整形
    sim_nodes_data_for_json = []
    sim_edges_data_for_json = []
    sim_path_data_for_json = []

    #2Dのシミュレーションデータ抽出
    _, ax = plt.subplots(figsize=FIG_SIZE)
    labels, pos = render_topology_base(ax, nodes, highest_level)
    nx.draw_networkx(unicast_graph, pos=pos, labels=labels, edge_color="orange", ax=ax, width=2)

    #3Dデータ抽出
    for node_id_str in labels:
        
        # node_id_str から key と level を再度抽出
        # "node_KEY@LEVEL" 形式を想定
        parts = node_id_str.split('@')
        node_actual_key = int(parts[0].replace('node_', '')) # "node_100" -> 100
        node_level = int(parts[1]) if len(parts) > 1 else 0 # "@0" -> 0

        mv_dummy_value = random.randint(0, 10000)
    
        sim_nodes_data_for_json.append({
            'key': node_actual_key,          # 元の数値キー
            'id': node_id_str,               # "key@level" 形式のID
            "position": {"x": 0, "y": 0, "z": 0},
            'level': node_level,             # レベル
            'mv_value': mv_dummy_value,     # 2Dのingredientsからは直接取れないため、ここには仮の値
                  
        })

        # デバッグ用にノード情報を表示--------------------------------------------------------------------
        print(f'key:{node_actual_key}')
        print(f'level:{node_level}')
        print(f'mv_value:{mv_dummy_value}')
        print(f'id:{node_id_str}')
        print('---------------------------------------------------------------')
        #-----------------------------------------------------------------------------------------------

    #print(f"DEBUG(sg_main): Total SGNode objects generated: {len(nodes)}")
    ## 全ノード情報をコピー (graph_server.py の calculate_cylindrical_positions に渡すため)
    #for node_obj in nodes:
    #    # node_with_level を使って ID を生成し、node_obj.routing_table_height() でレベルを取得
    #    sim_nodes_data_for_json.append({
    #        'key': node_obj.key,
    #        'level': node_obj.routing_table_height(), 
    #        'mv_value': str(node_obj.mv), # mv_value は str に変換
    #        'id': node_with_level(node_obj, node_obj.routing_table_height()) 
    #    })
    #    # デバッグ用にノード情報を表示--------------------------------------------------------------------
    #    #print(f'key:{node_obj.key}')
    #    #print(f'level:{node_obj.routing_table_height()}')
    #    #print(f'mv_value:{str(node_obj.mv)}')
    #    #print(f'id:{node_with_level(node_obj, node_obj.routing_table_height())}')
    #    #-----------------------------------------------------------------------------------------------
    
    # unicast_graph からエッジ情報を抽出 (ID は "key@level" 形式を想定)
    for u_id, v_id in unicast_graph.edges():
        sim_edges_data_for_json.append({
            "source": u_id, # u_id は "node_KEY@LEVEL" 形式の文字列
            "target": v_id  # v_id も同様
        })

    # パス情報も unicast_graph から抽出可能であれば追加
    for (u, v), hop_count in edge_labels.items():
        sim_path_data_for_json.append({
            "source": u, # "node_KEY@LEVEL" 形式
            "target": v,  # "node_KEY@LEVEL" 形式
            "hop": hop_count
        })

    data_for_3d_update = {
        "nodes": sim_nodes_data_for_json,
        "edges": sim_edges_data_for_json,
        "path": sim_path_data_for_json
    }

    #3Dデータ送信処理
    try:
        print(f"\n--- sg_draw.py: Sending 3D data for Hop Graph to server ---") 
        # print(json.dumps(data_for_3d_update, indent=2)) # デバッグ用にデータ全体を表示する場合
        response = requests.post(GRAPH_SERVER_URL, json=data_for_3d_update, timeout=100) # 短いタイムアウト
        response.raise_for_status() 
        print(f"🎉 3D data sent successfully from sg_draw.py: {response.json()}") 
    except requests.exceptions.ConnectionError as e:
        print(f"🚨 ERROR (sg_draw): Could not connect to graph server at {GRAPH_SERVER_URL}. Is it running? Error: {e}") 
    except requests.exceptions.Timeout as e:
        print(f"🚨 ERROR (sg_draw): Connection to graph server timed out from {GRAPH_SERVER_URL}. Error: {e}") 
    except requests.exceptions.RequestException as e:
        print(f"🚨 ERROR (sg_draw): Failed to send 3D data: {e}") 

    
    #2Dの描画
    if filename is None:
        print("Showing the hop graph. Close the window to proceed.") 
        plt.show()
    else:
        plt.savefig(filename)
    plt.close('all')

