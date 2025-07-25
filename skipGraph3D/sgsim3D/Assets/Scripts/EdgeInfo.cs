// Assets/Scripts/EdgeInfo.cs
using UnityEngine;
using TMPro; // TextMeshPro を使うため

public class EdgeInfo : MonoBehaviour
{
    public string sourceNodeId; // エッジの始点ノードID
    public string targetNodeId; // エッジの終点ノードID
    public int hop; // エッジの終点ノードID

    // ⭐ ADDED: 3DテキストPrefabへの参照 ⭐
    public GameObject edgeInfo3DTextPrefab;
    private GameObject currentInfoTextInstance; // 現在表示中のテキストインスタンス

    void Awake()
    {
        // Debug.Log("EdgeInfo Awake on: " + gameObject.name, this);
    }

    // ⭐ ADDED: 3D情報テキストを表示/非表示するメソッド ⭐
    public void ToggleInfoDisplay(string infoContent)
    {
        if (currentInfoTextInstance == null)
        {
            // まだ表示されていない場合は生成して表示
            if (edgeInfo3DTextPrefab == null)
            {
                Debug.LogError("EdgeInfo: edgeInfo3DTextPrefab is not assigned on " + gameObject.name + ". Cannot display 3D text.", this);
                return;
            }

            // エッジの中間点にテキストPrefabをインスタンス化
            // エッジのTransformを回転させているため、ローカル座標(0,0,0)は始点、(0,0,distance)は終点
            // その中間点は (0,0,distance/2)
            LineRenderer line = GetComponent<LineRenderer>();
            Vector3 localMidPoint = Vector3.zero;
            if (line != null && line.positionCount > 1)
            {
                // LineRendererのローカル座標の始点と終点から中間点を計算
                Vector3 lineLocalStart = line.GetPosition(0);
                Vector3 lineLocalEnd = line.GetPosition(1);
                localMidPoint = (lineLocalStart + lineLocalEnd) / 2f;
            }
            
            currentInfoTextInstance = Instantiate(edgeInfo3DTextPrefab, transform); // エッジの子にする
            currentInfoTextInstance.transform.localPosition = localMidPoint + new Vector3(0, 1.0f, 0); // エッジの中間点より少し上に配置 (調整可能)
            currentInfoTextInstance.transform.localPosition = new Vector3(0, 1.0f, 0);

            TextMeshPro textMesh = currentInfoTextInstance.GetComponent<TextMeshPro>();
            if (textMesh != null)
            {
                textMesh.text = infoContent;
            }
            else
            {
                Debug.LogError("EdgeInfo: TextMeshPro component not found on EdgeInfo3DTextPrefab for " + gameObject.name + ". Check prefab setup.", this);
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