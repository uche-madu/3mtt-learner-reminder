# utils/batching.py
import psutil
import math


def get_adaptive_batch_size(
    min_batch: int = 200, max_batch: int = 1000, target_memory_fraction: float = 0.05
) -> int:
    """
    Dynamically compute a safe batch size based on system memory.

    Args:
        min_batch (int): Smallest batch size allowed.
        max_batch (int): Largest batch size allowed.
        target_memory_fraction (float): Fraction of total memory to allocate to one batch.

    Returns:
        int: Chosen batch size within [min_batch, max_batch].
    """
    # Estimate average learner size (roughly 500 bytes = 0.0005 MB)
    avg_learner_size_mb = 0.0005

    # Total system memory in MB
    total_mb = psutil.virtual_memory().total / (1024 * 1024)

    # Target memory budget for one batch
    budget_mb = total_mb * target_memory_fraction

    # Compute max learners per batch under budget
    learners_fit = int(math.floor(budget_mb / avg_learner_size_mb))

    # Clamp to range
    return max(min_batch, min(learners_fit, max_batch))
