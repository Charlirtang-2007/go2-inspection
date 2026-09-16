# app/utils/mdns_service.py
import socket
import threading
from zeroconf import ServiceInfo, Zeroconf


class MDNSService:
    def __init__(self, port: int = 8000):
        self.port = port
        self.zeroconf = None
        self.service_info = None
        self._thread = None

    def get_local_ip(self) -> str:
        """获取本机在局域网中的真实IP"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def _register_in_thread(self):
        """在独立线程中注册mDNS"""
        try:
            ip = self.get_local_ip()
            print(f"📡 mDNS广播中... 本机IP: {ip}:{self.port}")

            self.service_info = ServiceInfo(
                "_go2-backend._tcp.local.",
                "Go2-Backend._go2-backend._tcp.local.",  # 纯英文服务名
                addresses=[socket.inet_aton(ip)],
                port=self.port,
                properties={
                    "version": "2.0.0",
                    "service": "go2-inspection",
                    "ip": ip,
                },
                server="go2-backend.local.",
            )

            # 不指定接口，让zeroconf自动选择所有可用接口
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)
            print("✅ mDNS注册成功")
        except Exception as e:
            print(f"⚠️ mDNS注册失败: {e}")
            import traceback
            traceback.print_exc()

    def start(self):
        self._thread = threading.Thread(target=self._register_in_thread, daemon=True)
        self._thread.start()

    def stop(self):
        try:
            if self.zeroconf:
                print("📡 停止mDNS广播")
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
        except Exception as e:
            print(f"⚠️ 停止mDNS失败: {e}")