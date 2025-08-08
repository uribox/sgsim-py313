import subprocess
import time
import os
import sys
from pathlib import Path

# launch_all.py が存在するディレクトリ (src/)
CURRENT_SCRIPT_DIR = Path(os.path.abspath(__file__)).parent

# プロジェクトのルートディレクトリを自動的に特定する
# src/ から見て二つ上のディレクトリがプロジェクトルート (sgsim-py313)
PROJECT_ROOT = (CURRENT_SCRIPT_DIR / ".." / "..").resolve()

# --- 設定 ---
# Unity Editorの代わりにビルド済みアプリのパスを指定
BUILT_UNITY_APP_RELATIVE_PATH = Path("Builds") / "sgsim3D_App" / "sgsim3D.exe"

# ビルド済みUnityアプリケーションのLinux形式パス (WSL環境でパスを扱うため)
BUILT_UNITY_APP_PATH_LINUX = PROJECT_ROOT / BUILT_UNITY_APP_RELATIVE_PATH

# WSLパスをWindowsパスに変換するヘルパー関数
def convert_wsl_path_to_windows_format(wsl_path_obj: Path):
    path_str = str(wsl_path_obj)
    if path_str.startswith("/mnt/") and len(path_str) >= 6 and path_str[5].isalpha():
        drive_letter = path_str[5].upper()
        rest_of_path = path_str[6:]
        return f"{drive_letter}:\\{rest_of_path.replace('/', os.sep)}" # os.sep はOSに応じたパス区切り文字
    return path_str

# ビルド済みUnityアプリケーションのWindows形式パス (Unityアプリに渡すため)
BUILT_UNITY_APP_PATH_WIN = convert_wsl_path_to_windows_format(BUILT_UNITY_APP_PATH_LINUX)

# --- プロジェクトルートからの相対パス (誰の環境でも同じ) ---
GUI_SCRIPT = (PROJECT_ROOT / "gui" / "main_gui.py").as_posix()
GRAPH_SERVER_SCRIPT = (PROJECT_ROOT / "skipGraph3D" / "graph_server.py").as_posix()
SGSIM_MAIN_SCRIPT = (CURRENT_SCRIPT_DIR / "sg_main.py").as_posix() 

# --- Helper for launching processes ---
def launch_process(command, name="Process"):
    print(f"🚀 Launching {name} with command: {' '.join(command)}")

    creation_flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0

    if command[0] == sys.executable: # Pythonスクリプトの場合 (sg_main.pyなど)
        return subprocess.Popen(
            command, 
            creationflags=creation_flags, # この行が有効になっているか 
            text=True, 
            encoding='utf-8', 
            errors='replace'
        )
    else: # Unityアプリなど
        return subprocess.Popen(
            command, 
            shell=False, 
            creationflags=creation_flags #  この行が有効になっているか 
        )

def main():
    processes = []

    try:
        # 1. 3Dグラフサーバーを起動 (一番最初に起動して待ち受ける)
        graph_server_process = launch_process([sys.executable, GRAPH_SERVER_SCRIPT], "3D Graph Server")
        processes.append(graph_server_process)
        time.sleep(2) # サーバーが起動するのを少し待つ (必要に応じて調整)

        # 2. ビルド済みUnityアプリケーションを起動
        if not os.path.exists(BUILT_UNITY_APP_PATH_WIN):
            print(f"\nWarning: Built Unity application not found at expected path: '{BUILT_UNITY_APP_PATH_WIN}'")
            print("Please ensure the Unity project is built and the .exe is placed at this location.")
            print("Skipping Built Unity App launch.")
            print("If your Unity project is built elsewhere, you will need to manually edit 'BUILT_UNITY_APP_RELATIVE_PATH' in launch_all.py.")
        else:
            unity_app_process = launch_process([BUILT_UNITY_APP_PATH_WIN], "Built Unity App")
            processes.append(unity_app_process)
            time.sleep(5) # アプリケーションが起動するのを少し待つ

        # 3. GUIを起動 (GUI操作に移行)
        gui_process = launch_process([sys.executable, GUI_SCRIPT], "GUI")
        processes.append(gui_process)

        print("\nAll components launched. Please operate the GUI.")
        print("Press Ctrl+C to terminate all launched processes.")

        # すべてのプロセスが終了するまで待機する
        while True:
            all_terminated = True
            for p in processes:
                if p.poll() is None:
                    all_terminated = False
                    break
            if all_terminated:
                break
            time.sleep(1)

        print("All launched processes have been terminated.")

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Terminating all processes...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # すべてのサブプロセスを終了
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()

        print("All launched processes have been terminated.")

if __name__ == "__main__":
    main()

