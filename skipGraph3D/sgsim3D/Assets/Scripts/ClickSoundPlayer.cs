// Assets/Scripts/ClickSoundPlayer.cs
//using System.Diagnostics;
using UnityEngine;

[RequireComponent(typeof(AudioSource))] // このスクリプトにはAudioSourceが必須であることを示す
public class ClickSoundPlayer : MonoBehaviour
{
    public AudioClip soundToPlay; // Inspectorで再生したい音を割り当てる

    private AudioSource audioSource;

    void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        audioSource.playOnAwake = false; // 自動再生はしない
        audioSource.loop = false;        // ループ再生もしない
    }

    // 外部からこのメソッドを呼び出して音を再生する
    public void PlaySound()
    {
        if (soundToPlay != null)
        {
            // 現在再生中の音があれば停止し、新しい音を再生
            audioSource.Stop();
            audioSource.clip = soundToPlay;
            audioSource.Play();
        }
        else
        {
            Debug.LogWarning("ClickSoundPlayer: No AudioClip assigned to 'soundToPlay' on " + gameObject.name);
        }
    }
}