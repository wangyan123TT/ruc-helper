"""
轻量内存限流 —— 单进程部署（一个 uvicorn 进程）够用，无需 Redis。

两种用法：
  throttle(key, max_hits, window)   滑动窗口：window 秒内最多 max_hits 次；超限返回需等待秒数。
  失败锁定：record_fail 累计失败，到阈值锁一段时间；is_locked 查剩余锁定；record_success 清零。

登录场景：按 IP 滑动窗口挡广撒网、按账号失败锁定挡定点爆破。
"""
import time
from collections import defaultdict, deque
from threading import Lock

_lock = Lock()
_hits: dict[str, deque] = defaultdict(deque)             # key -> 尝试时间戳
_fails: dict[str, list] = defaultdict(lambda: [0, 0.0])  # key -> [连续失败次数, 锁定到期时间戳]


def throttle(key: str, max_hits: int, window: int) -> int:
    """滑动窗口限流。放行返回 0 并记一次；超限返回需等待的秒数(>0)。"""
    now = time.time()
    with _lock:
        dq = _hits[key]
        while dq and dq[0] <= now - window:
            dq.popleft()
        if len(dq) >= max_hits:
            return int(dq[0] + window - now) + 1
        dq.append(now)
        return 0


def is_locked(key: str) -> int:
    """账号是否因失败过多被锁。返回剩余锁定秒数（0=未锁）。"""
    with _lock:
        remain = int(_fails[key][1] - time.time())
        return remain if remain > 0 else 0


def record_fail(key: str, max_fails: int, lock_seconds: int) -> None:
    """记一次失败；连续失败达 max_fails 则锁定 lock_seconds 秒。"""
    with _lock:
        rec = _fails[key]
        rec[0] += 1
        if rec[0] >= max_fails:
            rec[1] = time.time() + lock_seconds
            rec[0] = 0   # 计数清零，锁定到期后重新累计


def record_success(key: str) -> None:
    """成功即清除该账号的失败记录/锁定。"""
    with _lock:
        _fails.pop(key, None)
