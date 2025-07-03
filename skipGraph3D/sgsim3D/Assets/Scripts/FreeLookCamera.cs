using UnityEngine;

public class FreeLookCamera : MonoBehaviour
{
    // --- Public Variables ---
    [Header("Movement Speed")]
    public float panSpeed = 5.0f;       // カメラの平行移動速度
    public float zoomSpeed = 5.0f;      // カメラのズーム速度 (マウスホイール)
    public float orbitSpeed = 120.0f;   // カメラのオービット回転速度 (マウスドラッグ)

    [Header("Zoom Settings")]
    public float minZoomDistance = 1.0f;   // 最小ズーム距離
    public float maxZoomDistance = 100.0f; // 最大ズーム距離

    [Header("Orbit Settings")]
    public Vector3 orbitTargetOffset = Vector3.zero; // オービットの中心となるターゲットのオフセット
                                                     // 例: Vector3(0, 0, 0) で原点
                                                     // ノードのYが0から始まれば、これが円筒の底の中心になります

    // --- Private Variables ---
    private Vector3 currentTargetPosition; // 現在のカメラの注視点
    private float currentZoomDistance;     // 現在のカメラとターゲット間の距離
    private float xRotation = 0.0f;        // Y軸周りの回転 (横回転)
    private float yRotation = 0.0f;        // X軸周りの回転 (縦回転)

    void Start()
    {
        // 初期状態のカメラの位置からターゲットとズーム距離を推定
        // カメラが既にシーンの中心を見ていると仮定
        currentTargetPosition = transform.position + transform.forward * -transform.position.z; // Zを0に近づける仮定
        if (orbitTargetOffset != Vector3.zero)
        {
            // ユーザーが明示的に設定したオフセットを適用
            currentTargetPosition = orbitTargetOffset;
        }
        else
        {
            // デフォルトの原点をターゲットに設定
            currentTargetPosition = Vector3.zero;
        }

        // 初期ズーム距離を計算
        currentZoomDistance = Vector3.Distance(transform.position, currentTargetPosition);
        currentZoomDistance = Mathf.Clamp(currentZoomDistance, minZoomDistance, maxZoomDistance);

        // 初期回転角度を設定 (現在のカメラの向きから取得)
        Vector3 angles = transform.eulerAngles;
        xRotation = angles.y;
        yRotation = angles.x;

        // Start() でカメラを初期位置に設定し直す
        ApplyCameraTransform();
    }

    void LateUpdate()
    {
        HandleInput();
        ApplyCameraTransform();
    }

    void HandleInput()
    {
        // --- オービット回転 (マウス右ボタンを押しながらドラッグ) ---
        if (Input.GetMouseButton(1)) // マウス右ボタン
        {
            xRotation += Input.GetAxis("Mouse X") * orbitSpeed * Time.deltaTime;
            yRotation -= Input.GetAxis("Mouse Y") * orbitSpeed * Time.deltaTime; // Y軸は上下反転
            yRotation = ClampAngle(yRotation, -90.0f, 90.0f); // 縦方向の回転制限 (-90:真下, 90:真上)
        }

        // --- パン移動 (マウス中ボタンを押しながらドラッグ) ---
        if (Input.GetMouseButton(2)) // マウス中ボタン
        {
            float mouseX = Input.GetAxis("Mouse X");
            float mouseY = Input.GetAxis("Mouse Y");

            Vector3 panDirection = Vector3.zero;
            // カメラのローカル軸に沿って移動
            panDirection += transform.right * -mouseX;  // X軸方向
            panDirection += transform.up * -mouseY;     // Y軸方向

            currentTargetPosition += panDirection * panSpeed * Time.deltaTime;
        }

        // --- ズーム (マウスホイール) ---
        float scrollInput = Input.GetAxis("Mouse ScrollWheel");
        currentZoomDistance -= scrollInput * zoomSpeed;
        currentZoomDistance = Mathf.Clamp(currentZoomDistance, minZoomDistance, maxZoomDistance);
    }

    void ApplyCameraTransform()
    {
        // 回転を適用
        Quaternion rotation = Quaternion.Euler(yRotation, xRotation, 0);

        // 新しい位置を計算
        // targetからの距離 currentZoomDistance を rotation で回転させた方向の逆向きに配置
        Vector3 position = currentTargetPosition + rotation * new Vector3(0.0f, 0.0f, -currentZoomDistance);

        transform.rotation = rotation;
        transform.position = position;
    }

    // 角度を制限するヘルパー関数
    float ClampAngle(float angle, float min, float max)
    {
        if (angle < -360) angle += 360;
        if (angle > 360) angle -= 360;
        return Mathf.Clamp(angle, min, max);
    }
}