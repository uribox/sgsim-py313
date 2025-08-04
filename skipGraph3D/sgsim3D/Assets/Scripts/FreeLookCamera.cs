//using System.Diagnostics;
using UnityEngine;

public class FreeLookCamera : MonoBehaviour
{
    // --- Public Variables ---
    [Header("Movement Speed")]
    public float panSpeed = 5.0f;       // カメラの平行移動速度
    public float zoomSpeed = 5.0f;      // カメラのズーム速度 (マウスホイール)
    public float orbitSpeed = 120.0f;   // カメラのオービット回転速度 (マウスドラッグ)

    [Header("Zoom Settings")]
    public float minZoomDistance = 0.1f;    // 最小ズーム距離
    public float maxZoomDistance = 1000.0f; // 最大ズーム距離

    [Header("Orbit Settings")]
    public Vector3 orbitTargetOffset = Vector3.zero; // オービットの中心となるターゲットのオフセット

    // 自動回転の設定
    [Header("Auto Rotate Settings")]
    public float autoRotateSpeed = 0.5f; // 超スローな回転速度（度/秒）
    public bool enableAutoRotate = true; // 自動回転を有効にするかどうかのフラグ
    public Vector3 fixedRotationCenter = Vector3.zero; // 自動回転の中心（デフォルトは原点）

    // --- Private Variables ---
    private Vector3 currentTargetPosition;  // 現在のカメラの注視点
    private float currentZoomDistance;      // 現在のカメラとターゲット間の距離
    private float xRotation = 0.0f;         // Y軸周りの回転 (横回転)
    private float yRotation = 0.0f;         // X軸周りの回転 (縦回転)

    void Start()
    {
        // currentTargetPosition の初期設定
        if (orbitTargetOffset != Vector3.zero)
        {
            currentTargetPosition = orbitTargetOffset;
        }
        else
        {
            currentTargetPosition = Vector3.zero; // デフォルトの原点をターゲットに設定
        }

        // 初期ズーム距離を計算
        currentZoomDistance = Vector3.Distance(transform.position, currentTargetPosition);
        currentZoomDistance = Mathf.Clamp(currentZoomDistance, minZoomDistance, maxZoomDistance);

        // 初期回転角度を設定
        Vector3 initialAngles = transform.eulerAngles;
        xRotation = initialAngles.y;
        yRotation = initialAngles.x;
        yRotation = ClampAngle(yRotation, -90.0f, 90.0f);

        ApplyCameraTransform();
    }

    void LateUpdate()
    {
        HandleInput();

        // デバッグログ
        //Debug.Log($"[AutoRotate Debug] enableAutoRotate: {enableAutoRotate}, Mouse(1): {Input.GetMouseButton(1)}, Mouse(2): {Input.GetMouseButton(2)}", this);

        if (enableAutoRotate)
        {
            if (!Input.GetMouseButton(1) && !Input.GetMouseButton(2))
            {
                //Debug.Log($"[AutoRotate Debug] --- Performing Auto Rotation ---", this);
                //Debug.Log($"[AutoRotate Debug]   Speed: {autoRotateSpeed}, DeltaTime: {Time.deltaTime}", this);

                // Y軸周りに時計回りに回転
                xRotation += -autoRotateSpeed * Time.deltaTime; // 時計回りなのでマイナス

                //Debug.Log($"[AutoRotate Debug]   xRotation updated to: {xRotation}", this);
            }
            else
            {
                //Debug.Log("[AutoRotate Debug] Auto-rotate paused due to mouse input.", this);
            }
        }
        else
        {
            //Debug.Log("[AutoRotate Debug] Auto-rotate disabled via Inspector.", this);
        }

        ApplyCameraTransform();
    }

    void HandleInput()
    {
        // オービット回転 (マウス右ボタンを押しながらドラッグ)
        if (Input.GetMouseButton(1))
        {
            xRotation += Input.GetAxis("Mouse X") * orbitSpeed * Time.deltaTime;
            yRotation -= Input.GetAxis("Mouse Y") * orbitSpeed * Time.deltaTime;
            yRotation = ClampAngle(yRotation, -90.0f, 90.0f);
        }

        // パン移動 (マウス中ボタンを押しながらドラッグ)
        if (Input.GetMouseButton(2))
        {
            float mouseX = Input.GetAxis("Mouse X");
            float mouseY = Input.GetAxis("Mouse Y");

            Vector3 panDirection = Vector3.zero;
            panDirection += transform.right * -mouseX;
            panDirection += transform.up * -mouseY;

            currentTargetPosition += panDirection * panSpeed * Time.deltaTime;
        }

        // ズーム (マウスホイール)
        float scrollInput = Input.GetAxis("Mouse ScrollWheel");
        currentZoomDistance -= scrollInput * zoomSpeed;
        currentZoomDistance = Mathf.Clamp(currentZoomDistance, minZoomDistance, maxZoomDistance);
    }

    void ApplyCameraTransform()
    {
        // xRotation と yRotation はカメラが currentTargetPosition を中心に回転する角度
        Quaternion rotation = Quaternion.Euler(yRotation, xRotation, 0);

        // カメラの最終位置は currentTargetPosition を中心に、回転とズーム距離に基づいて計算
        Vector3 finalPosition = currentTargetPosition + rotation * new Vector3(0, 0, -currentZoomDistance);

        transform.rotation = rotation;
        transform.position = finalPosition;

        // カメラが常に currentTargetPosition を向くようにする
        transform.LookAt(currentTargetPosition);
    }

    // 角度を制限するヘルパー関数
    float ClampAngle(float angle, float min, float max)
    {
        if (angle < -360) angle += 360;
        if (angle > 360) angle -= 360;
        return Mathf.Clamp(angle, min, max);
    }
}