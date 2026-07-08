"""Multi-proxy rotation — auto-failover across comma-separated proxies."""
import os, time, random, threading
from typing import Optional

class ProxyRotator:
    def __init__(self, proxy_list, cooldown_seconds=300):
        self.proxies = [p.strip() for p in proxy_list if p.strip()]
        self.cooldown = cooldown_seconds
        self._failures = {}
        self._lock = threading.Lock()

    def __bool__(self): return bool(self.proxies)
    def __len__(self): return len(self.proxies)

    def get_proxy(self):
        if not self.proxies: return None
        with self._lock:
            now = time.time()
            available = [p for p in self.proxies if p not in self._failures or (now - self._failures[p]) > self.cooldown]
            if available: return random.choice(available)
            if self._failures: return min(self._failures.items(), key=lambda x: x[1])[0]
            return self.proxies[0]

    def mark_failed(self, proxy_url):
        with self._lock:
            self._failures[proxy_url] = time.time()

    def mark_success(self, proxy_url):
        with self._lock:
            self._failures.pop(proxy_url, None)

    def status(self):
        now = time.time()
        with self._lock:
            return {
                "total": len(self.proxies),
                "available": sum(1 for p in self.proxies if p not in self._failures or (now - self._failures[p]) > self.cooldown),
                "in_cooldown": sum(1 for p in self.proxies if p in self._failures and (now - self._failures[p]) <= self.cooldown),
            }

_raw = os.getenv("PROXY_URL", "").strip()
_proxy_list = [p.strip() for p in _raw.split(",") if p.strip()] if _raw else []
rotator = ProxyRotator(_proxy_list) if _proxy_list else None

def get_proxy_for_request():
    if rotator is None: return None
    return rotator.get_proxy()

def mark_proxy_failed(proxy_url):
    if rotator and proxy_url: rotator.mark_failed(proxy_url)

def mark_proxy_success(proxy_url):
    if rotator and proxy_url: rotator.mark_success(proxy_url)

def get_proxy_status():
    if rotator is None: return {"configured": False, "total": 0, "available": 0, "in_cooldown": 0}
    s = rotator.status()
    s["configured"] = True
    return s
