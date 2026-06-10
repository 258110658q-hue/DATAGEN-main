"""StateUpdater 协议，用于解耦特定于 agent 的状态更新逻辑。

本模块定义了 agent 可以实现的协议，以指定其输出应如何映射到状态更新，
从而避免在 agent_node 中使用硬编码的 if-elif 分支链。
"""

from typing import Protocol, Dict, Any, runtime_checkable

from .state import State


@runtime_checkable
class StateUpdater(Protocol):
    """agent 定义其状态更新逻辑的协议。

    实现此协议的 agent 可以控制其输出如何映射到状态字段更新。
    """

    def get_state_updates(self, state: State, output: Any) -> Dict[str, Any]:
        """根据 agent 输出返回状态字段更新的字典。

        Args:
            state: 当前工作流状态。
            output: agent 的结构化或原始输出。

        Returns:
            将状态字段名映射到其新值的字典。
        """
        ...
