import random
import matplotlib.pyplot as plt

def generate_timestamps(num_blocks, base_interval=600, variance=60):
    """
    Generate synthetic block timestamps.
    - num_blocks: total number of blocks to simulate.
    - base_interval: average time between blocks (in seconds, default 10 minutes).
    - variance: standard deviation for sampling block intervals.
    Returns a list of cumulative timestamps.
    """
    timestamps = []
    current_time = 0.0
    for _ in range(num_blocks):
        # Sample next interval from a normal distribution
        interval = random.gauss(base_interval, variance)
        interval = max(1.0, interval)  # Ensure positive interval
        current_time += interval
        timestamps.append(current_time)
    return timestamps

def calculate_new_target(old_target, period_timestamps, target_timespan, pow_limit):
    """
    Compute the new difficulty target for one adjustment period.
    - old_target: difficulty target at start of period (float).
    - period_timestamps: list of 2016 timestamps.
    - target_timespan: desired total timespan (2016 * base_interval).
    - pow_limit: maximum allowable target (min difficulty).
    Returns the adjusted target, clamped within allowed bounds.
    """
    # 1. Actual timespan between first and last block in the period
    actual_timespan = period_timestamps[-1] - period_timestamps[0]

    # 2. Clamp to [¼ × target_timespan, 4 × target_timespan]
    min_span = target_timespan / 4.0
    max_span = target_timespan * 4.0
    actual_timespan = max(min(actual_timespan, max_span), min_span)

    # 3. Retarget formula: scale old target by the ratio
    new_target = old_target * (actual_timespan / target_timespan)

    # 4. Enforce proof-of-work limit
    if new_target > pow_limit:
        new_target = pow_limit

    return new_target

def simulate_difficulty(total_blocks, interval=2016, base_interval=600, variance=60):
    """
    Run the full difficulty adjustment simulation.
    - total_blocks: total blocks to simulate (e.g., 2016 * number_of_cycles).
    - interval: blocks per adjustment (default 2016).
    - base_interval and variance: parameters for timestamp generation.
    Returns a list of (block_height, target) at each adjustment point.
    """
    # Initialize constants
    initial_target = 1.0           # Starting difficulty target
    pow_limit = initial_target * 4 # Maximum target for minimum difficulty
    timestamps = generate_timestamps(total_blocks, base_interval, variance)

    history = []
    current_target = initial_target

    # Loop through each retarget period
    for start in range(0, total_blocks, interval):
        end = start + interval
        if end > total_blocks:
            break  # Skip incomplete final interval

        # Record difficulty before adjustment
        history.append((end, current_target))

        # Compute new target for this period
        period_times = timestamps[start:end]
        current_target = calculate_new_target(
            old_target=current_target,
            period_timestamps=period_times,
            target_timespan=interval * base_interval,
            pow_limit=pow_limit
        )

    return history

def plot_difficulty(history):
    """
    Plot the difficulty target history.
    - history: list of (block_height, target) pairs.
    """
    heights = [h for h, _ in history]
    targets = [t for _, t in history]

    plt.figure(figsize=(10, 5))
    plt.plot(heights, targets, marker='o')
    plt.xlabel("Block Height")
    plt.ylabel("Difficulty Target")
    plt.title("Simulated Bitcoin Difficulty Adjustment Over Time")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    # Simulate 10 adjustment cycles (approx. 20 weeks of blocks)
    cycles = 10
    total_blocks = cycles * 2016

    history = simulate_difficulty(
        total_blocks=total_blocks,
        interval=2016,
        base_interval=600,  # 10 minutes
        variance=120        # allow ±2 minutes on average
    )

    plot_difficulty(history)

if __name__ == "__main__":
    main()

