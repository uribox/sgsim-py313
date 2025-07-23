// Assets/Scripts/Billboard.cs
using UnityEngine;

public class Billboard : MonoBehaviour
{
    void LateUpdate()
    {
        // カメラのTransformを取得
        Transform cameraTransform = Camera.main.transform;

        // 常にカメラの方を向くようにオブジェクトを回転させる
        // (これはオブジェクトのY軸をワールドのY軸に固定しつつ、カメラを見る)
        transform.LookAt(transform.position + cameraTransform.rotation * Vector3.forward, cameraTransform.rotation * Vector3.up);
    }
}
