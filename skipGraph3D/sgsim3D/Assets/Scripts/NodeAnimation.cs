using UnityEngine;

public class NodeAnimator : MonoBehaviour
{
    // Unity�G�f�B�^�̃C���X�y�N�^�Œ����ł���ϐ�
    public float scaleAmount = 0.5f; // �g��E�k�������
    public float speed = 2.5f;       // �A�j���[�V�����̑���

    private Vector3 initialScale;    // �����̑傫����ۑ�����ϐ�

    void Start()
    {
        // ���s�J�n���́A���̃I�u�W�F�N�g�̑傫�����L�����Ă���
        initialScale = transform.localScale;
    }

    void Update()
    {
        // ���Ԃ̌o�߂Ƌ���-1����1�̊Ԃ����炩�ɕω�����l�����
        float scaleFactor = Mathf.Sin(Time.time * speed) * scaleAmount;

        // �����̑傫���ɁA�v�Z�����ω��ʂ����Z���āA�V�����傫���ɐݒ肷��
        transform.localScale = initialScale + new Vector3(scaleFactor, scaleFactor, scaleFactor);
    }
}