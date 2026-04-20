from typing import Any, Dict


class VMContext:
    def __init__(self, state, tools, memory, llm):
        self.state = state
        self.tools = tools
        self.memory = memory
        self.llm = llm

        self.variables: Dict[str, Any] = {}
