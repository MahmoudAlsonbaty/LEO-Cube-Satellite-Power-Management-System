import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- 1. Simulation Parameters ---
orbit_period = 100  # 100 minutes total per orbit
eclipse_duration = 30 # 30 minutes in eclipse
sunlit_duration = orbit_period - eclipse_duration # 70 minutes in sunlight
total_time = 2 * orbit_period # Simulate 2 orbits (200 minutes)

time = np.arange(0, total_time + 1, 1)

# --- 2. Pre-calculate the Environment & Data ---
is_eclipse = (time % orbit_period) >= sunlit_duration

# Temperature model (Tuned to only pass 120C for ~9 minutes)
temperature = np.zeros_like(time, dtype=float)
tau = 30 # Slower thermal time constant
curr_temp = 50.0 # Starts exactly at 50 degrees

# Power Consumption Estimates (mA)
baseline_power = np.full_like(time, 40.1, dtype=float)
improved_power = np.zeros_like(time, dtype=float)

overheat_threshold = 120 # degrees C
overheat_timer = 0
is_overheated = False

for i in range(len(time)):
    # 1. Calculate temperature for this minute
    # Target temp adjusted to 130 so the peak stays under control
    target_temp = 130 if not is_eclipse[i] else -40
    curr_temp += (target_temp - curr_temp) / tau
    temperature[i] = curr_temp

    # 2. Power and Protection Logic
    if is_eclipse[i]:
        improved_power[i] = 0.01 # Deep sleep during eclipse
        # Reset protection flags when it cools down in eclipse
        overheat_timer = 0 
        is_overheated = False 
    else:
        # Check if we are in the danger zone
        if temperature[i] >= overheat_threshold:
            overheat_timer += 1
        else:
            overheat_timer = 0 # Reset if it drops below 120
            
        # If we've been at or above 120 for 5 continuous minutes, trigger protection
        if overheat_timer >= 5:
            is_overheated = True
            
        # Apply Power Draw
        if is_overheated:
            improved_power[i] = 0.01 # Deep sleep due to overheating
        else:
            improved_power[i] = 40.1 # Normal operation in safe sunlight

# --- 3. Calculate Final Statistics ---
baseline_energy = np.trapz(baseline_power, time)
improved_energy = np.trapz(improved_power, time)
savings = ((baseline_energy - improved_energy) / baseline_energy) * 100

final_textstr = (f"MISSION COMPLETE - 2 ORBITS\n"
                 f"---------------------------\n"
                 f"Baseline Energy: {baseline_energy:.0f} mA·min\n"
                 f"Improved Energy: {improved_energy:.0f} mA·min\n"
                 f"TOTAL POWER SAVED: {savings:.1f}%")

# --- 4. Setup the Animated Figure ---
fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
fig.canvas.manager.set_window_title('LEO Satellite Power Simulation')

line_env, = axs[0].plot([], [], color='#FFB300', drawstyle="steps-mid", linewidth=2, label="Sunlight (1=Sun, 0=Eclipse)")
fill_env = None

line_temp, = axs[1].plot([], [], color='#E53935', linewidth=2, label="Satellite Temp (°C)")
axs[1].axhline(y=overheat_threshold, color='darkred', linestyle='--', label="Overheat Threshold (120°C)")
fill_temp = None

line_base_power, = axs[2].plot([], [], color='#757575', linestyle='--', linewidth=2, label="Baseline Power")
line_imp_power, = axs[2].plot([], [], color='#43A047', linewidth=2, label="Improved Power (Smart Sleep)")
fill_power = None

props = dict(boxstyle='round,pad=0.8', facecolor='#E8F5E9', alpha=0.95, edgecolor='#43A047', linewidth=2)
summary_text = axs[2].text(0.5, 0.5, "", transform=axs[2].transAxes, fontsize=14, 
                           fontweight='bold', verticalalignment='center', horizontalalignment='center', 
                           bbox=props, zorder=10)
summary_text.set_visible(False)

# Format Axes
axs[0].set_ylim(-0.2, 1.2)
axs[0].set_xlim(0, total_time)
axs[0].set_yticks([0, 1])
axs[0].set_yticklabels(['Eclipse', 'Sunlight'])
axs[0].set_ylabel("Illumination")
axs[0].set_title("Real-Time Simulation: 2 Orbits (Fast Mode: 4 Mins/Sec)")
axs[0].legend(loc="upper right")
axs[0].grid(True, alpha=0.5)

axs[1].set_ylim(-45, 140) 
axs[1].set_ylabel("Temperature (°C)")
axs[1].legend(loc="lower right")
axs[1].grid(True, alpha=0.5)

axs[2].set_ylim(-5, 55) 
axs[2].set_xlabel("Time (Minutes)")
axs[2].set_ylabel("Power Consumption (mA)")
axs[2].legend(loc="upper right")
axs[2].grid(True, alpha=0.5)

plt.tight_layout()

# --- 5. Animation Function ---
def animate(frame):
    global fill_env, fill_temp, fill_power
    
    t_data = time[:frame]
    
    # 1. Update Environment
    env_data = ~is_eclipse[:frame]
    line_env.set_data(t_data, env_data)
    
    if fill_env is not None: fill_env.remove()
    if frame > 0:
        fill_env = axs[0].fill_between(t_data, 0, env_data, color='#FFB300', alpha=0.2)
    
    # 2. Update Temperature
    temp_data = temperature[:frame]
    line_temp.set_data(t_data, temp_data)
    
    if fill_temp is not None: fill_temp.remove()
    if frame > 0:
        fill_temp = axs[1].fill_between(t_data, overheat_threshold, temp_data, 
                                        where=(temp_data > overheat_threshold), color='red', alpha=0.4)
    
    # 3. Update Power
    line_base_power.set_data(t_data, baseline_power[:frame])
    imp_power_data = improved_power[:frame]
    line_imp_power.set_data(t_data, imp_power_data)
    
    if fill_power is not None: fill_power.remove()
    if frame > 0:
        fill_power = axs[2].fill_between(t_data, 0, imp_power_data, color='#43A047', alpha=0.2)

    # # 4. Final Results Box
    # if frame == len(time) - 1:
    #     summary_text.set_text(final_textstr)
    #     summary_text.set_visible(True)

    return line_env, line_temp, line_base_power, line_imp_power, summary_text

# Set interval=250 for 250ms per frame (4 times faster than before)
ani = FuncAnimation(fig, animate, frames=len(time), interval=250, repeat=False)

plt.show()