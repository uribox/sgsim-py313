using UnityEngine;
using NativeWebSocket;
using System.Collections.Generic;
using System.Net.WebSockets; // 必要な場合のみ (ClientWebSocketOptionsなど)
using System; // Action のため
using System.Linq; // LINQ メソッド (Where, Select, ToDictionaryなど) のため
using TMPro; // TextMeshPro を使う場合 (ノードにテキスト表示するなら)
//using Debug = UnityEngine.Debug;

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
    public LineRenderer edgePrefab; // 元のコード通り LineRenderer 型
    public Transform graphContainer;

    private Dictionary<string, GameObject> spawnedNodes = new Dictionary<string, GameObject>();
    private List<GameObject> spawnedEdges = new List<GameObject>(); // 元のコード通り List<GameObject>
    public GameObject node3DInfoTextPrefab; // ⭐ ADDED: Reference to the 3D Text Prefab ⭐
    private NodeInfo lastClickedNodeInfo;   // Holds info of the last clicked node for toggling 3D text

    async void Start()
    {
        if (graphContainer == null)
        {
            Debug.LogError("Graph Container is not assigned in the Inspector! Assign a parent Transform for graph objects.");
            return;
        }
        if (nodePrefab == null) Debug.LogError("Node Prefab is not assigned!");
        if (edgePrefab == null) Debug.LogError("Edge Prefab is not assigned!");
        if (node3DInfoTextPrefab == null) Debug.LogError("Node 3D Info Text Prefab is not assigned!"); // For 3D text display

        websocket = new NativeWebSocket.WebSocket("ws://localhost:8765");

        websocket.OnOpen += () => Debug.Log("✅ WebSocket Connection open!");
        websocket.OnError += (e) => Debug.LogError("❌ WebSocket Error: " + e);
        websocket.OnClose += (e) => Debug.Log("🔌 WebSocket Connection closed! Code: " + e.ToString());

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

        if (Input.GetMouseButtonDown(0))
        {
            Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
            RaycastHit hit;

            if (Physics.Raycast(ray, out hit))
            {
                Debug.Log($"Raycast hit: {hit.collider.name} (Layer: {LayerMask.LayerToName(hit.collider.gameObject.layer)}) at position: {hit.point}");
                
                ClickSoundPlayer soundPlayer = hit.collider.GetComponent<ClickSoundPlayer>();
                NodeInfo clickedNodeInfo = hit.collider.GetComponent<NodeInfo>();

                // Hide info for previously clicked node if it's different or if clicking elsewhere
                if (lastClickedNodeInfo != null && lastClickedNodeInfo != clickedNodeInfo)
                {
                    lastClickedNodeInfo.HideInfoDisplay();
                }

                

                if (soundPlayer != null)
                {
                    soundPlayer.PlaySound();
                    Debug.Log("Played sound for: " + hit.collider.name);

                    //NodeInfo nodeInfo = hit.collider.GetComponent<NodeInfo>();
                    //if (nodeInfo != null)
                    //{
                    //    Debug.Log($"Node Clicked: ID={nodeInfo.nodeId}, Key={nodeInfo.nodeKey}, Level={nodeInfo.nodeLevel}");
                    //}

                    if (clickedNodeInfo != null) // If a Node was clicked
                    {
                        Debug.Log($"ノード情報を表示！");
                        string infoContent =
                            $"Node Information\n" +
                            $"ID: {clickedNodeInfo.nodeId}\n" +
                            $"Key: {clickedNodeInfo.nodeKey}\n" +
                            $"Level: {clickedNodeInfo.nodeLevel}\n" +
                            $"MV Value: {clickedNodeInfo.nodeMvValue}";

                        clickedNodeInfo.ToggleInfoDisplay(infoContent); // Show/Hide 3D text
                        lastClickedNodeInfo = clickedNodeInfo; // Record this node as last clicked
                    }
                    else // If an Edge was clicked (has sound but not NodeInfo)
                    {
                        Debug.Log($"Edge Clicked: {hit.collider.name}");
                        lastClickedNodeInfo = null; // Clear node info display if clicking an edge
                    }


                }
                else
                {
                    Debug.Log("Clicked on: " + hit.collider.name + ", but no ClickSoundPlayer found.");
                    if (lastClickedNodeInfo != null) lastClickedNodeInfo.HideInfoDisplay();
                    lastClickedNodeInfo = null;
                }
            }
            else
            {
                Debug.Log("Clicked on empty space (Raycast hit nothing).");
                if (lastClickedNodeInfo != null) lastClickedNodeInfo.HideInfoDisplay();
                lastClickedNodeInfo = null;
            }
        }
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

                // ⭐ ADDED: NodeInfo に 3D Text Prefab を渡す ⭐
                nodeInfo.nodeInfo3DTextPrefab = node3DInfoTextPrefab;

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
                GameObject sourceNode, targetNode;
                if (!spawnedNodes.TryGetValue(edge.source, out sourceNode))
                {
                    Debug.LogWarning($"Missing source node for edge: {edge.source}. Skipping edge creation.");
                    continue;
                }
                if (!spawnedNodes.TryGetValue(edge.target, out targetNode))
                {
                    Debug.LogWarning($"Missing target node for edge: {edge.target}. Skipping edge creation.");
                    continue;
                }

                GameObject edgeObject = Instantiate(edgePrefab.gameObject, graphContainer); // ⭐ .gameObject を追加 ⭐
                LineRenderer line = edgeObject.GetComponent<LineRenderer>();

                if (line == null)
                {
                    Debug.LogError($"Edge Prefab '{edgePrefab.name}' is missing a LineRenderer component. Cannot draw edge.");
                    Destroy(edgeObject);
                    continue;
                }

                Vector3 startPos = sourceNode.transform.position;
                Vector3 endPos = targetNode.transform.position;

                line.positionCount = 2;
                line.SetPosition(0, startPos);
                line.SetPosition(1, endPos);

                line.startWidth = 0.1f;
                line.endWidth = 0.1f;
                line.material = new Material(Shader.Find("Sprites/Default"));
                line.startColor = Color.gray;
                line.endColor = Color.gray;
                line.name = $"Edge_{edge.source}_to_{edge.target}";
                spawnedEdges.Add(line.gameObject);
            }
            Debug.Log("Finished generating " + data.edges.Count + " edges.");
        }
    }

    void ClearExistingGraph()
    {

        // 1. まず、現在表示中の3Dテキストがあれば非表示にする
        if (lastClickedNodeInfo != null)
        {
            lastClickedNodeInfo.HideInfoDisplay(); // NodeInfoのHideInfoDisplayを呼び出す
            lastClickedNodeInfo = null; // 参照もクリアする
        }

        // 2. 既存のノードとエッジを全て削除
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

