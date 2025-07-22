using UnityEngine;
using NativeWebSocket;
using System.Collections.Generic;
using System.Net.WebSockets; // 必要な場合のみ (ClientWebSocketOptionsなど)
using System; // Action のため
using System.Linq; // LINQ メソッド (Where, Select, ToDictionaryなど) のため
// using TMPro; // TextMeshPro を使う場合 (ノードにテキスト表示するなら)

// JSONデータに対応するC#クラス
[System.Serializable]
public class Vector3Data { public float x, y, z; }

[System.Serializable]
public class NodeData
{
    public string id;           // 例: "100@0" (key@level 形式, GameObject名と辞書キーに使う)
    public Vector3Data position;
    public int level;           // Pythonのシミュレーション結果から来るノードのレベル
    public string mv_value;     // PythonのMembershipVectorの値 (string または int)
    public int key;             // Pythonのシミュレーション結果から来るノードの論理キー
    // Pythonが送る可能性のある他のフィールドもここに追加
    // public int logical_key; 
}

[System.Serializable]
public class EdgeData
{
    public string source;       // 例: "100@0" (source node ID, key@level 形式)
    public string target;       // 例: "101@0" (target node ID, key@level 形式)
}

[System.Serializable]
public class PathData
{
    public string source;       // 例: "100@0"
    public string target;       // 例: "101@0"
    public int hop;
}

[System.Serializable]
public class GraphData
{
    public List<NodeData> nodes;
    public List<EdgeData> edges;
    public List<PathData> path;
    public string status;
}


public class GraphManager : MonoBehaviour
{
    NativeWebSocket.WebSocket websocket;

    public GameObject nodePrefab;
    public LineRenderer edgePrefab;
    public Transform graphContainer;

    private Dictionary<string, GameObject> spawnedNodes = new Dictionary<string, GameObject>();
    // ⭐ 修正: List<GameObject> に統一 ⭐
    private List<GameObject> spawnedEdges = new List<GameObject>();

    async void Start()
    {
        if (graphContainer == null)
        {
            Debug.LogError("Graph Container is not assigned in the Inspector! Assign a parent Transform for graph objects.");
            return;
        }
        if (nodePrefab == null) Debug.LogError("Node Prefab is not assigned!");
        if (edgePrefab == null) Debug.LogError("Edge Prefab is not assigned!");


        websocket = new NativeWebSocket.WebSocket("ws://localhost:8765");

        websocket.OnOpen += () => Debug.Log("✅ WebSocket Connection open!");
        websocket.OnError += (e) => Debug.LogError("❌ WebSocket Error: " + e);
        // ⭐ 修正: OnClose イベントハンドラの引数とログ出力 ⭐
        websocket.OnClose += (e) => Debug.Log("🔌 WebSocket Connection closed! Code: " + e.ToString()); // e.ToString() を使用
        // 備考: NativeWebSocketの古いバージョンでは OnClose は引数なし (Action) の場合もあります。
        // その場合は websocket.OnClose += () => Debug.Log("..."); と修正してください。

        websocket.OnMessage += (bytes) =>
        {
            var message = System.Text.Encoding.UTF8.GetString(bytes);
            Debug.Log("Received WebSocket message (raw): " + message);
            GraphData receivedData = JsonUtility.FromJson<GraphData>(message);

            if (UnityMainThreadDispatcher.Instance != null)
            {
                UnityMainThreadDispatcher.Instance.Enqueue(() => UpdateGraphVisuals(receivedData));
            }
            else
            {
                Debug.LogError("UnityMainThreadDispatcher instance is not found in the scene! Cannot update graph visuals.");
            }
        };

        await websocket.Connect();
    }

    void Update()
    {
        if (websocket != null) { websocket.DispatchMessageQueue(); }
    }

    void UpdateGraphVisuals(GraphData data)
    {
        if (data == null)
        {
            Debug.LogError("GraphData received is null. Failed to parse JSON.");
            return;
        }

        if (data.status == "no_data_yet")
        {
            Debug.Log("Server reports no real data yet. Displaying dummy or waiting for simulation results.");
            return;
        }

        Debug.Log($"Parsed data: {data.nodes.Count} nodes, {data.edges.Count} edges, {data.path.Count} paths.");

        ClearExistingGraph();

        if (data.nodes != null)
        {
            foreach (var node in data.nodes)
            {
                Vector3 pos = new Vector3(node.position.x, node.position.y, node.position.z);
                GameObject nodeObject = Instantiate(nodePrefab, pos, Quaternion.identity, graphContainer);
                nodeObject.name = "Node_" + node.id;
                nodeObject.transform.localScale = Vector3.one * 0.5f;

                NodeInfo nodeInfo = nodeObject.GetComponent<NodeInfo>();
                if (nodeInfo == null) nodeInfo = nodeObject.AddComponent<NodeInfo>();
                nodeInfo.nodeId = node.id;
                nodeInfo.nodeKey = node.key;
                nodeInfo.nodeLevel = node.level;
                nodeInfo.nodeMvValue = node.mv_value;

                SphereCollider collider = nodeObject.GetComponent<SphereCollider>();
                if (collider == null) collider = nodeObject.AddComponent<SphereCollider>();
                collider.radius = 0.5f;

                if (!spawnedNodes.ContainsKey(node.id))
                {
                    spawnedNodes.Add(node.id, nodeObject);
                }
                else
                {
                    Debug.LogWarning($"Duplicate node ID encountered: {node.id}. Overwriting existing node in dictionary.");
                    spawnedNodes[node.id] = nodeObject;
                }
            }
            Debug.Log("Finished generating " + data.nodes.Count + " nodes.");
        }

        if (data.edges != null)
        {
            foreach (var edge in data.edges)
            {
                if (spawnedNodes.TryGetValue(edge.source, out GameObject sourceNode) && spawnedNodes.TryGetValue(edge.target, out GameObject targetNode))
                {
                    LineRenderer line = Instantiate(edgePrefab, graphContainer);
                    line.SetPosition(0, sourceNode.transform.position);
                    line.SetPosition(1, targetNode.transform.position);

                    line.startWidth = 0.1f;
                    line.endWidth = 0.1f;
                    line.material = new Material(Shader.Find("Sprites/Default"));
                    line.startColor = Color.gray;
                    line.endColor = Color.gray;
                    line.name = $"Edge_{edge.source}_to_{edge.target}";
                    spawnedEdges.Add(line.gameObject);
                }
                else
                {
                    Debug.LogWarning($"Missing node(s) for edge: {edge.source} -> {edge.target}. One or both nodes not found in spawnedNodes dictionary. Skipping edge creation.");
                }
            }
            Debug.Log("Finished generating " + data.edges.Count + " edges.");
        }
    }

    void ClearExistingGraph()
    {
        foreach (Transform child in graphContainer)
        {
            Destroy(child.gameObject);
        }
        spawnedNodes.Clear();
        spawnedEdges.Clear();
        Debug.Log("Cleared existing graph objects.");
    }

    private async void OnApplicationQuit()
    {
        if (websocket != null) { await websocket.Close(); }
    }
}