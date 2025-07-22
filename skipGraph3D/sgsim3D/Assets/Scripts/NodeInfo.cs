using UnityEngine;

public class NodeInfo : MonoBehaviour
{
    public string nodeId;        // 例: "100@0" (key@level 形式のユニークID)
    public int nodeKey;          // 例: 100 (論理的なノードのキー)
    public int nodeLevel;        // 例: 0 (ノードが属するレベル)
    public string nodeMvValue;   // 例: "MV(100)" (MembershipVector の文字列表現)

    // デバッグ表示用 (Unity EditorのInspectorで確認できる)
    void OnValidate()
    {
        // GameObjectの名前を ID と同期させる (Optional, デバッグに便利)
        if (!string.IsNullOrEmpty(nodeId) && !gameObject.name.Contains(nodeId))
        {
            gameObject.name = "Node_" + nodeId;
        }
    }
}