"""
ExecutionVM — детерминированный исполнитель DSL-программ на базе llm-nano-vm.

Контракт: δ(S, Program) → S'

Program теперь использует стандартный DSL llm-nano-vm:
    {
        "name": "my_pipeline",
        "steps": [
            {
                "id": "step1",
                "type": "llm",
                "prompt": "Привет, $user_name",
                "output_key": "greeting"
            },
            {
                "id": "step2",
                "type": "tool",
                "tool": "send_message",
                "args": {"text": "$greeting"}
            }
        ]
    }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Callable

from nano_vm import ExecutionVM as NanoVM, Program, Trace, TraceStatus

from app.runtime.context import VMContext
from app.runtime.state_context import StateContext
from app.runtime.step_result import StepResult

logger = logging.getLogger(__name__)


class VMRunResult:
    """
    Результат прогона программы.
    Адаптирован для сохранения совместимости с остальной архитектурой бота.
    """

    def __init__(
        self,
        state: StateContext,
        results: List[StepResult],
        aborted: bool = False,
        trace: Optional[Trace] = None,
    ):
        self.state = state
        self.results = results
        self.aborted = aborted
        self.trace = trace  # Сохраняем оригинальный Trace от nano-vm для логов/отладки

    @property
    def outbox(self):
        return self.state.outbox

    @property
    def failed_steps(self) -> List[StepResult]:
        return [r for r in self.results if r.status == "error"]


class ExecutionVM:
    """
    Stateless исполнитель-обертка вокруг llm-nano-vm.
    Транслирует контекст бота в контекст VM и обратно.
    """

    def __init__(self, llm_adapter: Any, tools: Dict[str, Callable]):
        """
        Инициализация движка.
        Вместо старого InstructionRegistry передаем tools напрямую в nano_vm.
        """
        self.nano_vm = NanoVM(llm=llm_adapter, tools=tools)

    async def run(self, program_dict: Dict, ctx: VMContext) -> VMRunResult:
        """
        Выполнить программу через детерминированный FSM.

        Возвращает VMRunResult с итоговым state и всеми StepResult.
        Не бросает исключений: ошибки шагов обрабатываются внутри nano-vm.
        """
        # 1. Валидация и загрузка программы в формате llm-nano-vm
        try:
            program = Program.from_dict(program_dict)
        except Exception as e:
            logger.error("Failed to parse Program dict: %s", e)
            return VMRunResult(ctx.state, [], aborted=True)

        # 2. Подготовка контекста переменных (клонируем, чтобы не мутировать исходный до завершения)
        vm_context_vars = ctx.variables.copy()

        # 3. Запуск детерминированного исполнения
        logger.info("Starting execution of program: %s", program.name)
        trace = await self.nano_vm.run(program, context=vm_context_vars)

        step_results: List[StepResult] = []

        # Анализ статуса: SUCCESS, FAILED, BUDGET_EXCEEDED, STALLED
        aborted = trace.status != TraceStatus.SUCCESS

        # 4. Трансляция Trace обратно в StepResult и применение к StateContext
        for step in trace.steps:
            # Маппинг статусов nano-vm на статусы бота
            bot_status = "success" if step.status == "SUCCESS" else "error"

            result = StepResult(
                step_id=step.step_id,
                name=step.step_id,  # В nano-vm тип шага это 'llm'/'tool', используем id как имя
                status=bot_status,
                output=step.output,
                error=str(step.error) if step.error else None,
            )
            step_results.append(result)

            # Обновляем переменные контекста бота для истории
            if step.output is not None:
                ctx.variables[step.step_id] = step.output

            # Применяем к стейту бота (иммутабельный паттерн)
            ctx.state = ctx.state.apply(result)

            if bot_status == "error":
                logger.warning(
                    "Step %s failed: %s | Duration: %sms",
                    step.step_id,
                    step.error,
                    step.duration_ms,
                )

        if aborted:
            logger.warning(
                "Program aborted with status %s. Error: %s", trace.status, trace.error
            )
        else:
            # Выводим статистику бюджета, если доступна
            logger.info(
                "Program completed successfully. Total tokens: %s, Cost: $%s",
                trace.total_tokens(),
                trace.total_cost_usd(),
            )

        return VMRunResult(ctx.state, step_results, aborted=aborted, trace=trace)
