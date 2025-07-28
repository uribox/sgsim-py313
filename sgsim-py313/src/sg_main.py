from __future__ import annotations

import argparse
import itertools
import math
import random
import sys 
from typing import TypeVar, Type, cast
import os 

import matplotlib.pyplot as plt
import pandas as pd
import requests 
import json 

# 変更: sg と sg_draw のインポート方法を調整 
# sg_main.py と sg.py, sg_draw.py は同じ src/ ディレクトリにあると仮定
try:
    import sg 
    import sg_draw as draw 
    from sg import SGNode, MembershipVector, UnicastGreedy, UnicastOriginal, UnicastBase
    ALPHA = sg.ALPHA 
except ImportError as e:
    print(f"Error: Could not import core modules (sg/sg_draw) in sg_main.py: {e}") 
    print("Please ensure your project structure is correct and sg.py/sg_draw.py are accessible.") 
    sys.exit(1) 

from discrete_ev_sim import SchedEvent, EventExecutor


FIG_SIZE = (10, 7.5) 


class SGArguments:
    """
    This class is for a type hint of an instance returned by argparse.parse_args()
    """
    def __init__(self):
        self.n = 0
        self.alpha = 0
        self.exp = ''
        self.unicast_algorithm = ''
        self.fast_join = False
        self.seed = 0
        self.interactive = False
        self.output_topology_max_level = 0
        self.output_hop_graph = False
        self.hop_graph_diagonal = False
        self.verbose = False

    @classmethod
    def get_parser(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="sgsim: Skip Graph Simulator and Visualizer")
        parser.add_argument('-n', help=f'number of nodes (default: {sg.DEFAULT_N})', default=sg.DEFAULT_N, type=int)
        parser.add_argument('-a', '--alpha', help=f'base of membership vector (default: {sg.DEFAULT_ALPHA})',
                             default=sg.DEFAULT_ALPHA, dest='alpha', type=int)
        parser.add_argument('--exp', help=f'experiment type', choices=['basic', 'unicast', 'unicast_vary_n'],
                             type=str, default='basic')
        algorithms = list(cls.unicast_algorithms_map().keys())
        parser.add_argument('--unicast-algorithm', help='unicast algorithm', choices=algorithms,
                             type=str, default=algorithms[0], dest='unicast_algorithm')
        parser.add_argument('--fast-join', help=f'use fast (cheat) join', action='store_true', dest='fast_join')
        parser.add_argument('--seed', help=f'give a random seed', type=int)
        parser.add_argument('--interactive', help='display graphs on a window rather than save to files',
                             action='store_true')
        parser.add_argument('--output-topology-max-level',
                             help=f'render a topology from level 0 to the specified level (use with --exp basic)',
                             default=0, type=int, dest='output_topology_max_level')
        parser.add_argument('--output-hop-graph', help=f'render a hop graph (use with --exp unicast)',
                             action='store_true', dest='output_hop_graph')
        parser.add_argument('--diagonal', help=f'draw diagonal line (use with --output-hop-graph)',
                             action='store_true', dest='hop_graph_diagonal')
        parser.add_argument('-v', '--verbose', help='verbose output', action='store_true', dest='verbose')
        return parser

    @classmethod
    def unicast_algorithms_map(cls) -> dict[str, Type[UnicastBase]]:
        return {
            'greedy': UnicastGreedy,
            'original': UnicastOriginal
        }


# MODIFIED: UnicastExperiment クラスを SGMain クラスの前に移動 
class UnicastExperiment:
    def __init__(self, main: SGMain, unicast_class: Type[UnicastBase]):
        self.nodes: list[SGNode] = []
        self.number_of_trials = 0
        self.msgs: list[UnicastBase] = []
        self.main = main
        self.unicast_class = unicast_class

    def unicast_exp(self, number_of_nodes: int, *, fast_join=False) -> pd.DataFrame:
        print("Unicast Experiment:") 
        nodes = self.main.construct_overlay(number_of_nodes, fast_join=fast_join)

        number_of_nodes = len(nodes)
        self.nodes = nodes
        self.number_of_trials = number_of_nodes * 4
        self.msgs: list[UnicastBase] = []
        for i in range(self.number_of_trials):
            src = random.randint(0, number_of_nodes - 1)
            dst = random.randint(0, number_of_nodes * self.main.NODE_INDEX_TO_KEY_FACTOR)
            msg = self.unicast_class(nodes[src], target=dst)
            self.msgs.append(msg)
            EventExecutor.register_event(msg, latency=i * 1000)

        EventExecutor.sim(self.number_of_trials * 1000 * 2, verbose=sg.VERBOSE)

        data = []
        for i, msg in enumerate(self.msgs):
            if sg.VERBOSE:
                print(f"{i}: Unicast {msg.source_node}->{msg.target}"
                      f": #msgs={msg.number_of_messages}"
                      f", path lengths={msg.path_lengths}") 
            data.append({"no": i,
                         "from": msg.source_node.key,
                         "to": msg.target,
                         "nhops": msg.path_lengths,
                         "nmsgs": msg.number_of_messages})
        df = pd.DataFrame(data)
        df.set_index("no")
        return df

    def output_results(self, df: pd.DataFrame, filenames: tuple[str, str], mean_columns=None) -> None:
        if mean_columns is None:
            mean_columns = ['nmsgs', 'min_hops']
        df_min = df['nhops'].apply(lambda h: min(h))
        df_min.name = "min_hops"
        df_max = df['nhops'].apply(lambda h: max(h))
        df_max.name = "max_hops"
        merged = pd.concat([df, df_min, df_max], axis=1)
        print(merged.to_string(index=False)) 
        print("Means") 
        means = merged[mean_columns].mean()
        print(means.to_frame().T.to_string(index=False)) 

        df_nhops = merged["min_hops"]
        fig = plt.figure(figsize=(10, 5))
        df_nhops.plot.hist(fig=fig, histtype='step', color="grey",
                           bins=range(0, math.ceil(df_nhops.max()) + 1), title="# of hops", density=True)
        plt.xticks(list(range(0, math.ceil(df_nhops.max()) + 1)))
        if filenames[0] is None:
            plt.show()
        else:
            plt.savefig(filenames[0])
        plt.close('all')

        df_nmsgs = merged["nmsgs"]
        fig = plt.figure(figsize=(10, 5))
        df_nmsgs.plot.hist(fig=fig, histtype='step', color="grey",
                           bins=range(0, df_nmsgs.max()), title="# of msgs", density=True)
        if filenames[1] is None:
            plt.show()
        else:
            plt.savefig(filenames[1])
        plt.close('all')

    hop_graph_number = 0

    def render_hop_graphs(self, diagonal=False, interactive=False) -> None:
        for i, m in enumerate(self.msgs):
            print(f"{i}: Unicast {m.source_node}->{m.target}") 
            if interactive:
                filename = None
            else:
                filename = f"unicast-{m.short_name()}-{self.hop_graph_number}.png"
                self.hop_graph_number += 1
            draw.render_hop_graph(m, self.nodes, diagonal=diagonal, filename=filename)


class SGMain:
    #  SGMain クラスの直下に移動 (クラス変数として定義) 
    NODE_INDEX_TO_KEY_FACTOR = 10 
    T = TypeVar('T', bound=SGNode) 


    def __init__(self):
        self.unicast_class = None

    def main(self) -> None:
        args = self.init_from_arguments(SGArguments)
        if not self.unicast_class:
            raise Exception("unknown unicast algorithm")
        if not args.fast_join:
            raise Exception("use --fast-join (for now)")
        self.do_exp(args)
     

    # SGMain クラス内に新しいメソッドを追加: GUIからの引数をパースするヘルパー関数 
    def parse_gui_args(self, args_list: list) -> SGArguments:
        parser = SGArguments.get_parser()
        args = cast(SGArguments, parser.parse_args(args_list))
        return args

    # SGMain クラス内に新しいメソッドを追加: シミュレーションを実行し、結果を返す関数 
    def run_skipgraph_simulation(self, args: SGArguments) -> dict:
        """
        Skip Graph シミュレーションを実行し、その結果データを辞書形式で返します。
        この関数は、sg.py や discrete_ev_sim.py などの実際のシミュレーションコードを呼び出します。
        """
        print(f"\n--- Starting SkipGraph Simulation (Exp Type: {args.exp}, N: {args.n}, Alpha: {args.alpha}) ---") 
        
        sg.VERBOSE = args.verbose
        sg.ALPHA = args.alpha
        if args.seed is not None:
            random.seed(args.seed)
            print(f"random.seed={args.seed}") 
        
        self.unicast_class = SGArguments.unicast_algorithms_map().get(args.unicast_algorithm)
        if not self.unicast_class:
            raise Exception(f"unknown unicast algorithm: {args.unicast_algorithm}. Check --unicast-algorithm argument.")

        sim_nodes_data_for_json = []
        sim_edges_data_for_json = []
        sim_path_data_for_json = []
        
        nodes_sg_objects = [] # SGNodeオブジェクトのリスト (2D描画や内部処理用)
        messages = [] # UnicastBaseオブジェクトのリスト (ホップグラフ描画用)

        # ==== ここが最重要！実際のシミュレーションロジックをここに移植または呼び出し====
        if args.exp == 'basic':
            nodes_sg_objects = self.construct_overlay(args.n, fast_join=args.fast_join)
            
            for node in nodes_sg_objects:
                sim_nodes_data_for_json.append({
                    'key': node.key,
                    'level': node.routing_table_height(), 
                    'mv_value': str(node.mv),
                    'id': f"node_{node.key}@{node.routing_table_height()}" # 修正: id に key@level 形式を付加 
                })
            
            sim_edges_data_for_json = [] 
            sim_path_data_for_json = []
            
        elif args.exp == 'unicast' or args.exp == 'unicast_vary_n':
            exp_instance = UnicastExperiment(self, unicast_class=self.unicast_class) 
            df = exp_instance.unicast_exp(args.n, fast_join=args.fast_join)
            messages = exp_instance.msgs 

            nodes_sg_objects = exp_instance.nodes 

            for node in nodes_sg_objects:
                sim_nodes_data_for_json.append({
                    'key': node.key,
                    'level': node.routing_table_height(), 
                    'mv_value': str(node.mv),
                    'id': f"node_{node.key}@{node.routing_table_height()}" 
                })
            
            edges_data_for_json = []
            path_data_for_json = []
            if args.output_hop_graph:
                for msg in messages:
                    if hasattr(msg, 'path_nodes') and msg.path_nodes:
                        for i in range(len(msg.path_nodes) - 1):
                            src_key = msg.path_nodes[i].key
                            dst_key = msg.path_nodes[i+1].key
                            src_level = msg.path_nodes[i].routing_table_height() 
                            dst_level = msg.path_nodes[i+1].routing_table_height()
                            
                            edges_data_for_json.append({'source': f"node_{src_key}@{src_level}", 'target': f"node_{dst_key}@{dst_level}"})
                            
                            if hasattr(msg, 'path_lengths') and len(msg.path_lengths) > 0:
                                for i_path in range(len(msg.path_nodes) - 1): 
                                    hop_count = msg.path_lengths[i_path] if len(msg.path_lengths) > i_path else 1
                                    path_data_for_json.append({
                                        'source': f"node_{src_key}@{src_level}", 
                                        'target': f"node_{dst_key}@{dst_level}",   
                                        'hop': hop_count
                                    })
            sim_edges_data_for_json = [dict(t) for t in {tuple(sorted(d.items())) for d in sim_edges_data_for_json}]

        else:
            raise Exception(f"unknown experiment: {args.exp}")
        
        print(f"--- Simulation Completed. Generated {len(sim_nodes_data_for_json)} nodes and {len(sim_edges_data_for_json)} edges. ---")

        # 2D/3D 同期描画ロジック 
        # 出力ディレクトリを作成
        print("try to start to output 2D/3D graphs...")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output")
        os.makedirs(output_dir, exist_ok=True) 

        GRAPH_SERVER_HTTP_PORT = 8001 
        server_url = f"http://localhost:{GRAPH_SERVER_HTTP_PORT}/"

        # --- シナリオ1: トポロジーグラフの出力 (Basic実験) ---
        if args.exp == 'basic' and args.output_topology_max_level > 0:
            data_for_3d_update = {
                "nodes": sim_nodes_data_for_json, 
                "edges": sim_edges_data_for_json, 
                "path": [] 
            }
            
            try:
                print("\n--- sg_main.py: Final Data Prepared for HTTP POST (Topology) ---")
                print(json.dumps(data_for_3d_update, indent=2))
                print("----------------------------------------------------------------")

                response = requests.post(server_url, json=data_for_3d_update, timeout=100000)
                response.raise_for_status() 
                print(f"🎉 Topology data sent to graph server for 3D update: {response.json()}")
            except requests.exceptions.ConnectionError:
                print(f"🚨 ERROR: Could not connect to graph server at {server_url}. Is graph_server.py running?")
                sys.exit(1)
            except requests.exceptions.RequestException as e:
                print(f"🚨 ERROR: Failed to send topology data: {e}")
                sys.exit(1)

            # 2Dトポロジーグラフの表示/保存 (3D更新後にブロックされる)
            filename = None
            if not args.interactive: 
                filename = os.path.join(output_dir, f"{self.output_file_prefix()}_topology.png")
            print(f"Generating 2D topology graph. Interactive: {args.interactive}")
            if 'draw' in sys.modules and hasattr(draw, 'output_topology'):
                draw.output_topology(nodes_sg_objects, args.output_topology_max_level, filename=filename)
            else:
                print("Warning: sg_draw module not available for 2D topology output.")


        # --- シナリオ2: ホップグラフの出力 (Unicast実験) ---
        elif (args.exp == 'unicast' or args.exp == 'unicast_vary_n') and args.output_hop_graph:
            if not messages:
                print("No unicast messages generated to display hop graph.")
            else:
                for i, m in enumerate(messages):
                    nodes_for_this_hop_graph = sim_nodes_data_for_json 
                    edges_for_this_hop_graph = [] 
                    path_for_this_hop_graph = []
                    
                    if hasattr(m, 'path_nodes') and m.path_nodes:
                        for j in range(len(m.path_nodes) - 1):
                            src_key = m.path_nodes[j].key
                            dst_key = m.path_nodes[j+1].key
                            src_level = m.path_nodes[j].routing_table_height() 
                            dst_level = m.path_nodes[j+1].routing_table_height()
                            
                            edges_for_this_hop_graph.append({'source': f"node_{src_key}@{src_level}", 'target': f"node_{dst_key}@{dst_level}"})
                            
                            if hasattr(m, 'path_lengths') and len(m.path_lengths) > 0:
                                for i_path in range(len(m.path_nodes) - 1): 
                                    hop_count = m.path_lengths[i_path] if len(m.path_lengths) > i_path else 1
                                    path_for_this_hop_graph.append({ 
                                        'source': f"node_{src_key}@{src_level}", 
                                        'target': f"node_{dst_key}@{dst_level}",   
                                        'hop': hop_count
                                    })
                    
                    data_for_3d_update = {
                        "nodes": nodes_for_this_hop_graph, 
                        "edges": edges_for_this_hop_graph, 
                        "path": path_for_this_hop_graph   
                    }
                    
                    try:
                        print(f"\n--- sg_main.py: Final Data Prepared for HTTP POST (HopGraph {i}) ---")
                        print(json.dumps(data_for_3d_update, indent=2))
                        print("----------------------------------------------------------------")

                        response = requests.post(server_url, json=data_for_3d_update, timeout=100000)
                        response.raise_for_status() 
                        print(f"🎉 Hop graph data for msg {i} sent to graph server for 3D update: {response.json()}")
                    except requests.exceptions.ConnectionError:
                        print(f"🚨 ERROR: Could not connect to graph server for hop graph data. Is graph_server.py running?")
                        sys.exit(1)
                    except requests.exceptions.RequestException as e:
                        print(f"🚨 ERROR: Failed to send hop graph data for msg {i}: {e}")
                        sys.exit(1)

                    filename = None
                    if not args.interactive:
                        filename = os.path.join(output_dir, f"unicast-{m.short_name()}-{i}.png") 
                    print(f"Generating 2D hop graph for msg {i}. Interactive: {args.interactive}")
                    if 'draw' in sys.modules and hasattr(draw, 'render_hop_graph'):
                        draw.render_hop_graph(m, nodes_sg_objects, diagonal=args.hop_graph_diagonal, filename=filename)
                    else:
                        print("Warning: sg_draw module not available for 2D hop graph output.")
        # --- Final return for simulation results ---
        return {
            "nodes": sim_nodes_data_for_json,
            "edges": sim_edges_data_for_json,
            "path": sim_path_data_for_json 
        }

    def do_exp(self, args: SGArguments) -> None:
        print("Note: do_exp is largely superseded by run_skipgraph_simulation for data output.")
        exptype = args.exp
        if exptype == 'basic':
            self.basic(args)
        elif exptype == 'unicast':
            self.unicast(args)
        elif exptype == 'unicast_vary_n':
            self.unicast_vary_n(args)
        else:
            raise Exception(f"unknown experiment: {exptype}")

    def unicast_experiment_factory(self) -> UnicastExperiment:
        return UnicastExperiment(self, unicast_class=self.unicast_class)

    def init_from_arguments(self, clazz: Type[SGArguments]) -> SGArguments:
        parser = clazz.get_parser()
        args = cast(SGArguments, parser.parse_args())
        sg.VERBOSE = args.verbose
        sg.ALPHA = args.alpha
        print(f"alpha={sg.ALPHA}") 
        if args.seed is not None:
            random.seed(args.seed)
            print(f"random.seed={args.seed}") 
        self.unicast_class = clazz.unicast_algorithms_map().get(args.unicast_algorithm)
        if not self.unicast_class:
            raise Exception("unknown unicast algorithm")
        return args

    @classmethod
    def output_file_prefix(cls):
        return "sg"

    def basic(self, args: SGArguments) -> None:
        print("Basic experiment is handled by run_skipgraph_simulation for data output.")
        if args.output_topology_max_level > 0:
            nodes = self.construct_overlay(args.n, fast_join=args.fast_join)
            if args.interactive:
                filename = None
            else:
                filename = f"{self.output_file_prefix()}_topology.png"
            draw.output_topology(nodes, args.output_topology_max_level, filename=filename)


    def unicast(self, args: SGArguments) -> None:
        print("Unicast experiment is handled by run_skipgraph_simulation for data output.")
        if args.output_hop_graph:
            exp = self.unicast_experiment_factory()
            exp.unicast_exp(args.n, fast_join=args.fast_join) 
            exp.render_hop_graphs(diagonal=args.hop_graph_diagonal, interactive=args.interactive)


    def unicast_vary_n(self, args: SGArguments) -> None:
        print("Unicast vary N experiment is handled by run_skipgraph_simulation for data output.")
        results = []
        ntrials = 3
        nlist = [100, 200, 400, 800]
        for n in nlist:
            for i in range(ntrials):
                exp = self.unicast_experiment_factory()
                EventExecutor.reset()
                df = exp.unicast_exp(n, fast_join=True)
                df['n'] = n
                df['hop'] = df['nhops'].apply(lambda h: min(h))
                results.append(df)
            merged = pd.concat(results)
        print(merged.to_string()) 
        print() 
        print("Average Hops") 
        hops_vs_n_mean = merged.groupby('n')['hop'].mean()
        print(hops_vs_n_mean) 
        fig = plt.figure(figsize=(10, 5))
        ax = hops_vs_n_mean.plot(fig=fig, style='ob-', logx=True, grid=True)
        ax.set_xticks(nlist)
        ax.set_xticklabels(nlist)
        plt.title("average hops vs n", size=20)
        plt.xlabel("# of nodes", size=20)
        plt.ylabel("# of hops", size=20)
        if args.interactive:
            plt.show()
        else:
            plt.savefig(f"{self.output_file_prefix()}_hops_vs_n.png")
        plt.close('all')

    
    def construct_overlay(self, number_of_nodes: int, fast_join=False, node_class: Type[T] = SGNode) -> list[T]:
        """
        construct an overlay network
        :param number_of_nodes
        :param fast_join: use fast join method rather than join()
        :param node_class: class of a node
        :return an array of SGNode that has been joined
        """
        nodes = []
        for i in range(number_of_nodes):
            mv = MembershipVector()
            # if you want to use regular membership vectors...
            # mv = MembershipVector(i)
            nodes.append(node_class(i * self.NODE_INDEX_TO_KEY_FACTOR, mv))
        dump_nodes_mv(nodes)

        if fast_join:
            node_class.fast_join_all(nodes)
        else:
            self.join_nodes_all(nodes)

        dump_nodes_routing_table(nodes)
        return nodes

    @classmethod
    def do_basic_stat(cls, nodes: list[SGNode]) -> pd.DataFrame:
        data = []
        max_length = 0
        for cur in nodes:
            s = cur.routing_table_size_per_level()
            data.append([cur.key, cur.routing_table_height(), cur.number_of_unique_nodes_in_routing_table()] + s)
            max_length = max(max_length, len(s))
        tuples = [('key', ''), ('height', ''), ('uniq', '')]
        tuples += itertools.product(['table_size'], range(0, max_length))

        df = pd.DataFrame(data, columns=pd.MultiIndex.from_tuples(tuples))
        df.set_index('key')
        print("Routing Table Statistics (raw)") 
        print(df.to_string(index=False)) 
        print() 
        print("Routing Table Statistics (mean)") 
        m = df[['height', 'uniq', 'table_size']].mean()
        print(m.to_string()) 
        return df

    @classmethod
    def join_nodes_all(cls, nodes: list[SGNode]) -> None:
        introducer = nodes[0]
        introducer.initialize_as_introducer()
        for i, n in enumerate(nodes):
            if i == 0:
                continue
            ev = SchedEvent(lambda _n=n: _n.join(introducer))
            EventExecutor.register_event(ev, i * 1000)
        EventExecutor.sim(len(nodes) * 1000)
        EventExecutor.reset()


class UnicastExperiment:
    def __init__(self, main: SGMain, unicast_class: Type[UnicastBase]):
        self.nodes: list[SGNode] = []
        self.number_of_trials = 0
        self.msgs: list[UnicastBase] = []
        self.main = main
        self.unicast_class = unicast_class

    def unicast_exp(self, number_of_nodes: int, *, fast_join=False) -> pd.DataFrame:
        """
        Perform unicast experiments.
        :param number_of_nodes
        :param fast_join
        :return results
        """
        print("Unicast Experiment:") 
        nodes = self.main.construct_overlay(number_of_nodes, fast_join=fast_join)

        number_of_nodes = len(nodes)
        self.nodes = nodes
        # number_of_trials = 100
        self.number_of_trials = number_of_nodes * 4
        self.msgs: list[UnicastBase] = []
        for i in range(self.number_of_trials):
            src = random.randint(0, number_of_nodes - 1)
            dst = random.randint(0, number_of_nodes * self.main.NODE_INDEX_TO_KEY_FACTOR)
            msg = self.unicast_class(nodes[src], target=dst)
            self.msgs.append(msg)
            # perform a unicast every 1000 abstract time
            EventExecutor.register_event(msg, latency=i * 1000)

        EventExecutor.sim(self.number_of_trials * 1000 * 2, verbose=sg.VERBOSE)

        data = []
        for i, msg in enumerate(self.msgs):
            if sg.VERBOSE:
                print(f"{i}: Unicast {msg.source_node}->{msg.target}"
                      f": #msgs={msg.number_of_messages}"
                      f", path lengths={msg.path_lengths}") 
            data.append({"no": i,
                         "from": msg.source_node.key,
                         "to": msg.target,
                         "nhops": msg.path_lengths,
                         "nmsgs": msg.number_of_messages})
        df = pd.DataFrame(data)
        df.set_index("no")
        return df

    def output_results(self, df: pd.DataFrame, filenames: tuple[str, str], mean_columns=None) -> None:
        if mean_columns is None:
            mean_columns = ['nmsgs', 'min_hops']
        # extract min and max from 'nhops' (which is a list)
        df_min = df['nhops'].apply(lambda h: min(h))
        df_min.name = "min_hops"
        df_max = df['nhops'].apply(lambda h: max(h))
        df_max.name = "max_hops"
        # append min and max to the right
        merged = pd.concat([df, df_min, df_max], axis=1)
        print(merged.to_string(index=False)) 
        print("Means") 
        means = merged[mean_columns].mean()
        print(means.to_frame().T.to_string(index=False)) 

        # generate a histogram of # of hops
        df_nhops = merged["min_hops"]
        fig = plt.figure(figsize=(10, 5))
        df_nhops.plot.hist(fig=fig, histtype='step', color="grey",
                           bins=range(0, math.ceil(df_nhops.max()) + 1), title="# of hops", density=True)
        plt.xticks(list(range(0, math.ceil(df_nhops.max()) + 1)))
        if filenames[0] is None:
            plt.show()
        else:
            plt.savefig(filenames[0])
        plt.close('all')

        df_nmsgs = merged["nmsgs"]
        fig = plt.figure(figsize=(10, 5))
        df_nmsgs.plot.hist(fig=fig, histtype='step', color="grey",
                           bins=range(0, df_nmsgs.max()), title="# of msgs", density=True)
        # plt.xticks(list(range(0, math.ceil(df_nmsgs.max()))))
        if filenames[1] is None:
            plt.show()
        else:
            plt.savefig(filenames[1])
        plt.close('all')

    hop_graph_number = 0

    def render_hop_graphs(self, diagonal=False, interactive=False) -> None:
        for i, m in enumerate(self.msgs):
            print(f"{i}: Unicast {m.source_node}->{m.target}") 
            if interactive:
                filename = None
            else:
                filename = f"unicast-{m.short_name()}-{self.hop_graph_number}.png"
                self.hop_graph_number += 1
            draw.render_hop_graph(m, self.nodes, diagonal=diagonal, filename=filename)


def dump_nodes_mv(nodes: list[SGNode]) -> None:
    for i, n in enumerate(nodes):
        print(f"node[{i}]={repr(n)}") 


def dump_nodes_routing_table(nodes: list[SGNode]) -> None:
    for n in nodes:
        print(f"{n}: {n.mv}") 
        print("  ", "\n  ".join(n.routing_table_string()), sep='') 
    print(f"  # of unique nodes: {n.number_of_unique_nodes_in_routing_table()}") 
    print() 


# sgsim-py313/sgsim-py313/src/sg_main.py (ファイルの最終部分)

# ... (dump_nodes_mv, dump_nodes_routing_table 関数など、他のグローバル関数はそのまま) ...

# MODIFIED: main 処理ブロックのみを残し、デバッグ用データを送信 
if __name__ == "__main__":
    SGMain().main()

