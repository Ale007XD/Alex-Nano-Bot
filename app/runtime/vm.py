from typing import Dict, Any

from .context import VMContext
from .registry import InstructionRegistry


class ExecutionVM:
    def __init__(self, registry: InstructionRegistry):
        self.registry = registry

    async def run(self, program: Dict, ctx: VMContext):
        steps = program.get("plan", [])

        for step in steps:
            step_id = step["id"]
            name = step["instruction"]
            params = self._resolve(step.get("params", {}), ctx)

            instr_cls = self.registry.get(name)
            instr = instr_cls()

            result = await instr.execute(step_id, params, ctx)

            # сохранить output
            ctx.variables[step_id] = result.output

            # применить к state
            ctx.state = ctx.state.apply(result)

        return ctx.state

    def _resolve(self, params: Dict[str, Any], ctx: VMContext):
        def resolve_value(v):
            if isinstance(v, str) and v.startswith("$"):
                key = v[1:]
                return ctx.variables.get(key)
            return v

        return {k: resolve_value(v) for k, v in params.items()}
