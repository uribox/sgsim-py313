using UnityEngine;

public class AnimateLineRenderer : MonoBehaviour
{
    public float scrollSpeed = -1.0f; // �e�N�X�`��������鑬��
    private LineRenderer lineRenderer;

    void Start()
    {
        // ���̃X�N���v�g���A�^�b�`����Ă���I�u�W�F�N�g��LineRenderer���擾
        lineRenderer = GetComponent<LineRenderer>();
    }

    void Update()
    {
        // ���݂̃e�N�X�`���I�t�Z�b�g���擾
        Vector2 currentOffset = lineRenderer.material.mainTextureOffset;

        // X�����Ƀe�N�X�`�����X�N���[��������
        currentOffset.x += Time.deltaTime * scrollSpeed;

        // �V�����I�t�Z�b�g��ݒ�
        lineRenderer.material.mainTextureOffset = currentOffset;
    }
}