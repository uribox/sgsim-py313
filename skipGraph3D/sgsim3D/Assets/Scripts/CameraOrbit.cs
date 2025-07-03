// C#�X�N���v�g�̗� (CameraOrbit.cs �̂悤�Ȗ��O��Assets�t�H���_�ɕۑ�)
using UnityEngine;

public class CameraOrbit : MonoBehaviour
{
    public Transform target; // �J���������S�Ƃ���I�u�W�F�N�g (�Ȃ���Ό��_)
    public float distance = 20.0f; // �J�����ƃ^�[�Q�b�g�Ԃ̋���
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

        // �����^�[�Q�b�g���ݒ肳��Ă��Ȃ���΁A�J�����̏����ʒu���x�[�X�ɉ�]���S������
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
            // �}�E�X���{�^���h���b�O�ŉ�]
            if (Input.GetMouseButton(0))
            {
                x += Input.GetAxis("Mouse X") * xSpeed * 0.02f;
                y -= Input.GetAxis("Mouse Y") * ySpeed * 0.02f;
                y = ClampAngle(y, -90.0f, 90.0f); // �㉺�����̐���
            }

            // �}�E�X�X�N���[���ŃY�[��
            distance -= Input.GetAxis("Mouse ScrollWheel") * scrollSpeed;
            distance = Mathf.Clamp(distance, 0.1f, 100.0f); // �Y�[�������̐���

            Quaternion rotation = Quaternion.Euler(y, x, 0);
            Vector3 position = rotation * new Vector3(0.0f, 0.0f, -distance) + target.position;

            transform.rotation = rotation;
            transform.position = position;
        }
    }

    // �p�x�𐧌�����w���p�[�֐�
    float ClampAngle(float angle, float min, float max)
    {
        if (angle < -360) angle += 360;
        if (angle > 360) angle -= 360;
        return Mathf.Clamp(angle, min, max);
    }
}