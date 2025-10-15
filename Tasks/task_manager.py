import asyncio
import logging
import importlib
from . import __all__ as task_modules

logger = logging.getLogger(__name__)

# Track registered tasks to prevent duplicates
_registered_tasks = set()


def register_tasks(bot):
    """
    Registers all task coroutines found in the Tasks package.
    Each task module must define a function: `start_task(bot)`.
    """
    global _registered_tasks

    logger.info(f"=== TASK MANAGER: register_tasks() called with {len(task_modules)} modules: {task_modules} ===")

    # Clear previous registrations if bot is restarting
    if hasattr(bot, '_tasks_registered'):
        logger.warning("Tasks already registered for this bot instance, skipping duplicate registration")
        return

    for module_name in task_modules:
        logger.info(f"=== TASK MANAGER: Processing module '{module_name}' ===")

        if module_name in _registered_tasks:
            logger.warning(f"Task {module_name} already registered, skipping")
            continue

        try:
            # Import the module directly
            logger.debug(f"Attempting to import: Tasks.{module_name}")
            module = importlib.import_module(f"Tasks.{module_name}")
            logger.info(f"✅ Successfully imported module: {module_name}")

            if hasattr(module, "start_task"):
                logger.info(f"✅ Module {module_name} has start_task function, creating task...")
                task = bot.loop.create_task(module.start_task(bot))
                task.set_name(f"task_{module_name}")  # Name the task for easier debugging
                _registered_tasks.add(module_name)
                logger.info(f"✅ Task registered: {module_name} (Task ID: {id(task)}, Task Name: {task.get_name()})")
            else:
                logger.warning(f"❌ Module {module_name} has no start_task(bot) function.")

        except ImportError as e:
            logger.error(f"❌ Failed to import task module {module_name}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"❌ Error registering task {module_name}: {e}", exc_info=True)

    # Mark bot as having tasks registered
    bot._tasks_registered = True
    logger.info(f"=== TASK MANAGER: Task registration complete. Total tasks registered: {len(_registered_tasks)} ===")


def cleanup_tasks():
    """Clean up task registry - call this when bot shuts down."""
    global _registered_tasks
    _registered_tasks.clear()
    logger.info("Task registry cleaned up")