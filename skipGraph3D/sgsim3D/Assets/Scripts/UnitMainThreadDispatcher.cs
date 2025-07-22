using System;
using System.Collections.Generic;
using UnityEngine;
// using System.Diagnostics; // ⭐ この行を削除またはコメントアウトする ⭐

public class UnityMainThreadDispatcher : MonoBehaviour
{
    private static readonly Queue<Action> _executionQueue = new Queue<Action>();
    private static UnityMainThreadDispatcher _instance;

    public static UnityMainThreadDispatcher Instance
    {
        get
        {
            if (_instance == null)
            {
                _instance = FindObjectOfType<UnityMainThreadDispatcher>();
                if (_instance == null)
                {
                    GameObject singletonObject = new GameObject("UnityMainThreadDispatcher");
                    _instance = singletonObject.AddComponent<UnityMainThreadDispatcher>();
                    DontDestroyOnLoad(singletonObject);
                    // Debug.Log("UnityMainThreadDispatcher: New instance created automatically."); 
                }
            }
            return _instance;
        }
    }

    private void Awake()
    {
        if (_instance != null && _instance != this)
        {
            // Debug.LogWarning の前に UnityEngine. を明示的につける
            UnityEngine.Debug.LogWarning("UnityMainThreadDispatcher: Duplicate instance detected. Destroying this one.", this);
            Destroy(gameObject);
        }
        else if (_instance == null)
        {
            _instance = this;
            DontDestroyOnLoad(this.gameObject);
            // Debug.Log("UnityMainThreadDispatcher: First instance established.");
        }
    }

    public void Enqueue(Action action)
    {
        lock (_executionQueue)
        {
            _executionQueue.Enqueue(action);
        }
    }

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