"""解释器启动时挂载 litellm 调用记账（仅对 papi/paperpipe 调用生效）。

由 airesearch/activate.sh 放进 PYTHONPATH。只在该进程看起来是 papi 调用（或显式
NIU_LITELLM_HOOK=1/force）时才 import litellm —— 否则会给该 shell 里每条 python 命令
都加上 litellm 的启动开销。任何异常都吞掉，绝不影响正常启动。
"""
import os
import sys


def _enabled() -> bool:
    flag = os.environ.get("NIU_LITELLM_HOOK", "").strip().lower()
    if flag in {"0", "off", "false", "no"}:
        return False
    if flag in {"1", "on", "true", "yes", "force"}:
        return True
    joined = " ".join(sys.argv[:3]).lower()
    return "papi" in joined or "paperpipe" in joined


if _enabled():
    try:
        import litellm

        from papi_litellm_log import log_failure, log_success

        if log_success not in litellm.success_callback:
            litellm.success_callback.append(log_success)
        if log_failure not in litellm.failure_callback:
            litellm.failure_callback.append(log_failure)
    except Exception:
        pass
