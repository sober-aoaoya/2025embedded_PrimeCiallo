from random import random
import socket
import threading
import json
import queue
import time

class DataBroadcaster:
    """
    一个类，用于在后台运行一个TCP服务器，
    并能够将通过队列接收到的数据广播给所有连接的客户端。
    """
    def __init__(self, host='0.0.0.0', port=9999):
        """
        初始化服务器。
        :param host: 监听的主机地址，'0.0.0.0' 表示所有网络接口。
        :param port: 监听的端口。
        """
        self.host = host
        self.port = port
        self.clients = []  # 存储所有客户端 socket 连接
        self.clients_lock = threading.Lock()  # 用于线程安全地访问客户端列表
        self.message_queue = queue.Queue()  # 用于从外部接收待发送数据的队列
        self.stop_event = threading.Event()
        self.server_thread = None
        self.broadcast_thread = None

    def _accept_loop(self, server_socket):
        """[私有方法] 循环接受新的客户端连接。"""
        while not self.stop_event.is_set():
            try:
                conn, addr = server_socket.accept()
                print(f"[+] 接受来自 {addr} 的新连接")
                with self.clients_lock:
                    self.clients.append(conn)
            except socket.timeout:
                continue 
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"[!] 接受连接时出错: {e}")
                break

    def _broadcast_loop(self):
        """[私有方法] 从队列中获取数据并广播给所有客户端。"""
        while not self.stop_event.is_set():
            try:
                # 从队列中获取数据，设置超时以便能检查停止事件
                data = self.message_queue.get(timeout=1)
                
                # 将数据打包成 JSON 字符串
                message = json.dumps(data) + '\n'
                message_bytes = message.encode('utf-8')
                
                disconnected_clients = []
                with self.clients_lock:
                    # 遍历所有客户端并发送消息
                    for client in self.clients:
                        try:
                            client.sendall(message_bytes)
                        except (BrokenPipeError, ConnectionResetError):
                            # 如果发送失败（客户端已断开），则标记以便后续移除
                            disconnected_clients.append(client)
                            print(f"[-] 检测到客户端断开连接")
                
                # 移除已断开的客户端
                if disconnected_clients:
                    with self.clients_lock:
                        for client in disconnected_clients:
                            self.clients.remove(client)

            except queue.Empty:
                # 队列为空，这是正常情况，继续等待
                continue

    def start(self):
        """启动服务器的监听和广播线程。"""
        if self.server_thread is not None and self.server_thread.is_alive():
            print("[!] 服务器已经在运行中。")
            return

        print(f"[*] 准备在 {self.host}:{self.port} 上启动服务器...")
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            server_socket.settimeout(1.0) # 设置超时
        except Exception as e:
            print(f"[!] 服务器启动失败: {e}")
            return
        
        self.stop_event.clear()

        # 启动接受客户端连接的线程
        self.server_thread = threading.Thread(target=self._accept_loop, args=(server_socket,))
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # 启动广播消息的线程
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop)
        self.broadcast_thread.daemon = True
        self.broadcast_thread.start()
        
        print("[*] 服务器已成功启动，正在后台运行。")

    def stop(self):
        """停止服务器，并关闭所有连接。"""
        if self.server_thread is None or not self.server_thread.is_alive():
            print("[!] 服务器尚未运行。")
            return

        print("[*] 正在关闭服务器...")
        self.stop_event.set()
        # 等待线程结束
        self.server_thread.join(timeout=2)
        self.broadcast_thread.join(timeout=2)
        
        # 关闭所有客户端连接
        with self.clients_lock:
            for client in self.clients:
                client.close()
            self.clients.clear()
        
        print("[*] 服务器已关闭。")

    def send(self, count, score):
        """
        [公共API] 将数据放入待发送队列。
        """
        if not self.server_thread or not self.server_thread.is_alive():
            print("[!] 警告: 服务器未运行，数据无法发送。")
            return
            
        data = {"count": count, "score": score}
        self.message_queue.put(data)


server = DataBroadcaster()
def send_data_to_app(count, score):
    """
    一个简单的包装函数，用于向App发送数据。
    :param count: 次数 (x轴)
    :param score: 分数 (y轴)
    """
    server.send(count, score)

if __name__ == "__main__":
    server.start()
    
    print("\n服务器已在后台启动。现在模拟在另一个业务逻辑中调用 send_data_to_app 函数。")
    print("等待 App 连接... (请现在启动你的安卓应用并进入图表页)")
    print("将在5秒后开始发送数据。按 Ctrl+C 停止演示。")
    time.sleep(5)

    try:
        for i in range(1, 101):
            current_score = random.randint(60, 100)
            print(f"主项目逻辑: 生成数据 (次数={i}, 分数={current_score})，准备发送...")
            send_data_to_app(count=i, score=current_score)
            time.sleep(2) 
    except KeyboardInterrupt:
        print("\n检测到 Ctrl+C。")
    finally:
        server.stop()


