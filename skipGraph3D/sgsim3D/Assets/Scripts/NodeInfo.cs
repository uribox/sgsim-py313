// Assets/Scripts/NodeInfo.cs
using UnityEngine;
using TMPro; // TextMeshPro を使うため

public class NodeInfo : MonoBehaviour
{

    public string nodeId;
    public int nodeKey;
    public int nodeLevel;
    public string nodeMvValue;

    // ⭐ ADDED: 3DテキストPrefabへの参照 ⭐
    public GameObject nodeInfo3DTextPrefab;
    private GameObject currentInfoTextInstance; // 現在表示中のテキストインスタンス

    void Awake()
    {
        // Debug.Log("NodeInfo Awake on: " + gameObject.name, this);
    }

    // デバッグ表示用 (Unity EditorのInspectorで確認できる)
    void OnValidate()
    {
        if (!string.IsNullOrEmpty(nodeId) && !gameObject.name.Contains(nodeId))
        {
            gameObject.name = "Node_" + nodeId;
        }
    }

    // ⭐ ADDED: 3D情報テキストを表示/非表示するメソッド ⭐
    public void ToggleInfoDisplay(string infoContent)
    {
        if (currentInfoTextInstance == null)
        {
            // まだ表示されていない場合は生成して表示
            if (nodeInfo3DTextPrefab == null)
            {
                Debug.LogError("NodeInfo: nodeInfo3DTextPrefab is not assigned on " + gameObject.name + ". Cannot display 3D text.", this);
                return;
            }

            // まだ表示されていない場合は生成して表示
            currentInfoTextInstance = Instantiate(nodeInfo3DTextPrefab, transform); // ノードの子にする
            currentInfoTextInstance.transform.localPosition = new Vector3(0, 1.0f, 0); // ノードの上0.5mに配置 (調整可能)

            TextMeshPro textMesh = currentInfoTextInstance.GetComponent<TextMeshPro>();
            if (textMesh != null)
            {
                textMesh.text = infoContent;
            }
            else
            {
                Debug.LogError("NodeInfo: TextMeshPro component not found on NodeInfo3DTextPrefab for " + gameObject.name + ".", this);
            }
        }
        else
        {
            // 既に表示されている場合は非表示（またはDestroy）
            Destroy(currentInfoTextInstance);
            currentInfoTextInstance = null;
        }
    }

    public void HideInfoDisplay()
    {
        if (currentInfoTextInstance != null)
        {
            Destroy(currentInfoTextInstance);
            currentInfoTextInstance = null;
        }
    }
}

