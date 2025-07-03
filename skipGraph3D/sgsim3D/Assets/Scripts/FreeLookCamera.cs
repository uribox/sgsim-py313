using UnityEngine;

public class FreeLookCamera : MonoBehaviour
{
    // --- Public Variables ---
    [Header("Movement Speed")]
    public float panSpeed = 5.0f;       // �J�����̕��s�ړ����x
    public float zoomSpeed = 5.0f;      // �J�����̃Y�[�����x (�}�E�X�z�C�[��)
    public float orbitSpeed = 120.0f;   // �J�����̃I�[�r�b�g��]���x (�}�E�X�h���b�O)

    [Header("Zoom Settings")]
    public float minZoomDistance = 1.0f;   // �ŏ��Y�[������
    public float maxZoomDistance = 100.0f; // �ő�Y�[������

    [Header("Orbit Settings")]
    public Vector3 orbitTargetOffset = Vector3.zero; // �I�[�r�b�g�̒��S�ƂȂ�^�[�Q�b�g�̃I�t�Z�b�g
                                                     // ��: Vector3(0, 0, 0) �Ō��_
                                                     // �m�[�h��Y��0����n�܂�΁A���ꂪ�~���̒�̒��S�ɂȂ�܂�

    // --- Private Variables ---
    private Vector3 currentTargetPosition; // ���݂̃J�����̒����_
    private float currentZoomDistance;     // ���݂̃J�����ƃ^�[�Q�b�g�Ԃ̋���
    private float xRotation = 0.0f;        // Y������̉�] (����])
    private float yRotation = 0.0f;        // X������̉�] (�c��])

    void Start()
    {
        // ������Ԃ̃J�����̈ʒu����^�[�Q�b�g�ƃY�[�������𐄒�
        // �J���������ɃV�[���̒��S�����Ă���Ɖ���
        currentTargetPosition = transform.position + transform.forward * -transform.position.z; // Z��0�ɋ߂Â��鉼��
        if (orbitTargetOffset != Vector3.zero)
        {
            // ���[�U�[�������I�ɐݒ肵���I�t�Z�b�g��K�p
            currentTargetPosition = orbitTargetOffset;
        }
        else
        {
            // �f�t�H���g�̌��_���^�[�Q�b�g�ɐݒ�
            currentTargetPosition = Vector3.zero;
        }

        // �����Y�[���������v�Z
        currentZoomDistance = Vector3.Distance(transform.position, currentTargetPosition);
        currentZoomDistance = Mathf.Clamp(currentZoomDistance, minZoomDistance, maxZoomDistance);

        // ������]�p�x��ݒ� (���݂̃J�����̌�������擾)
        Vector3 angles = transform.eulerAngles;
        xRotation = angles.y;
        yRotation = angles.x;

        // Start() �ŃJ�����������ʒu�ɐݒ肵����
        ApplyCameraTransform();
    }

    void LateUpdate()
    {
        HandleInput();
        ApplyCameraTransform();
    }

    void HandleInput()
    {
        // --- �I�[�r�b�g��] (�}�E�X�E�{�^���������Ȃ���h���b�O) ---
        if (Input.GetMouseButton(1)) // �}�E�X�E�{�^��
        {
            xRotation += Input.GetAxis("Mouse X") * orbitSpeed * Time.deltaTime;
            yRotation -= Input.GetAxis("Mouse Y") * orbitSpeed * Time.deltaTime; // Y���͏㉺���]
            yRotation = ClampAngle(yRotation, -90.0f, 90.0f); // �c�����̉�]���� (-90:�^��, 90:�^��)
        }

        // --- �p���ړ� (�}�E�X���{�^���������Ȃ���h���b�O) ---
        if (Input.GetMouseButton(2)) // �}�E�X���{�^��
        {
            float mouseX = Input.GetAxis("Mouse X");
            float mouseY = Input.GetAxis("Mouse Y");

            Vector3 panDirection = Vector3.zero;
            // �J�����̃��[�J�����ɉ����Ĉړ�
            panDirection += transform.right * -mouseX;  // X������
            panDirection += transform.up * -mouseY;     // Y������

            currentTargetPosition += panDirection * panSpeed * Time.deltaTime;
        }

        // --- �Y�[�� (�}�E�X�z�C�[��) ---
        float scrollInput = Input.GetAxis("Mouse ScrollWheel");
        currentZoomDistance -= scrollInput * zoomSpeed;
        currentZoomDistance = Mathf.Clamp(currentZoomDistance, minZoomDistance, maxZoomDistance);
    }

    void ApplyCameraTransform()
    {
        // ��]��K�p
        Quaternion rotation = Quaternion.Euler(yRotation, xRotation, 0);

        // �V�����ʒu���v�Z
        // target����̋��� currentZoomDistance �� rotation �ŉ�]�����������̋t�����ɔz�u
        Vector3 position = currentTargetPosition + rotation * new Vector3(0.0f, 0.0f, -currentZoomDistance);

        transform.rotation = rotation;
        transform.position = position;
    }

    // �p�x�𐧌�����w���p�[�֐�
    float ClampAngle(float angle, float min, float max)
    {
        if (angle < -360) angle += 360;
        if (angle > 360) angle -= 360;
        return Mathf.Clamp(angle, min, max);
    }
}