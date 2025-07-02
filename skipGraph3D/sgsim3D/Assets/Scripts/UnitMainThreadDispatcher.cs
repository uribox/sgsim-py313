using System;
using System.Collections.Generic;
using System.Diagnostics;
using UnityEngine;

public class UnityMainThreadDispatcher : MonoBehaviour
{
    private static readonly Queue<Action> _executionQueue = new Queue<Action>();
    private static UnityMainThreadDispatcher _instance = null;

    // �V���O���g���C���X�^���X���擾���邽�߂̌��J�v���p�e�B
    public static UnityMainThreadDispatcher Instance
    {
        get
        {
            if (_instance == null)
            {
                // �V�[��������C���X�^���X��T��
                _instance = FindObjectOfType<UnityMainThreadDispatcher>();
                if (_instance == null)
                {
                    // ������Ȃ���΃G���[���o��
                    UnityEngine.Debug.LogError("UnityMainThreadDispatcher instance not found in the scene.");
                }
            }
            return _instance;
        }
    }

    // Unity�̃��C�t�T�C�N���ŁA�I�u�W�F�N�g���L���ɂȂ������ɌĂ΂��
    private void Awake()
    {
        // �܂��C���X�^���X�����݂��Ȃ��ꍇ
        if (_instance == null)
        {
            // ���̃I�u�W�F�N�g��B��̃C���X�^���X�Ƃ��Đݒ�
            _instance = this;
            // �V�[����؂�ւ��Ă����̃I�u�W�F�N�g���j�󂳂�Ȃ��悤�ɂ���
            DontDestroyOnLoad(this.gameObject);
        }
        // ���ɕʂ̃C���X�^���X�����݂���ꍇ
        else if (_instance != this)
        {
            // ���̃I�u�W�F�N�g�͕s�v�Ȃ̂Ŕj������
            Destroy(gameObject);
        }
    }

    // ���C���X���b�h�Ŏ��s�������������L���[�ɒǉ�����
    public void Enqueue(Action action)
    {
        lock (_executionQueue)
        {
            _executionQueue.Enqueue(action);
        }
    }

    // ���t���[���Ă΂�A�L���[�ɂ��܂������������s����
    private void Update()
    {
        lock (_executionQueue)
        {
            while (_executionQueue.Count > 0)
            {
                _executionQueue.Dequeue().Invoke();
            }
        }
    }
}