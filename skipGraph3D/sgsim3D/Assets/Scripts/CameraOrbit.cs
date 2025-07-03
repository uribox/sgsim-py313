// C#スクリプトの例 (CameraOrbit.cs のような名前でAssetsフォルダに保存)
using UnityEngine;

public class CameraOrbit : MonoBehaviour
{
    public Transform target; // カメラが中心とするオブジェクト (なければ原点)
    public float distance = 20.0f; // カメラとターゲット間の距離
    public float xSpeed = 120.0f;
    public float ySpeed = 120.0f;
    public float scrollSpeed = 5.0f;

    private float x = 0.0f;
    private float y = 0.0f;

    void Start()
    {
        Vector3 angles = transform.eulerAngles;
        x = angles.y;
        y = angles.x;

        // もしターゲットが設定されていなければ、カメラの初期位置をベースに回転中心を決定
        if (target == null)
        {
            target = new GameObject("CameraTarget").transform;
            target.position = transform.position + transform.forward * distance;
        }
    }

    void LateUpdate()
    {
        if (target)
        {
            // マウス左ボタンドラッグで回転
            if (Input.GetMouseButton(0))
            {
                x += Input.GetAxis("Mouse X") * xSpeed * 0.02f;
                y -= Input.GetAxis("Mouse Y") * ySpeed * 0.02f;
                y = ClampAngle(y, -90.0f, 90.0f); // 上下方向の制限
            }

            // マウススクロールでズーム
            distance -= Input.GetAxis("Mouse ScrollWheel") * scrollSpeed;
            distance = Mathf.Clamp(distance, 0.1f, 100.0f); // ズーム距離の制限

            Quaternion rotation = Quaternion.Euler(y, x, 0);
            Vector3 position = rotation * new Vector3(0.0f, 0.0f, -distance) + target.position;

            transform.rotation = rotation;
            transform.position = position;
        }
    }

    // 角度を制限するヘルパー関数
    float ClampAngle(float angle, float min, float max)
    {
        if (angle < -360) angle += 360;
        if (angle > 360) angle -= 360;
        return Mathf.Clamp(angle, min, max);
    }
}