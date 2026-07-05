import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle, Polygon
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg

# --- 1. Simulation & Orbital Parameters ---
R_earth = 6371.0 # km
altitude = 2500.0 # km (Increased to make Earth look smaller proportionally)
R_orbit = R_earth + altitude
orbit_period = 92.5 # realistic period in minutes
total_time = 2 * orbit_period # Simulate 2 orbits
time = np.arange(0, total_time + 1, 1) # 1 minute resolution

# Calculate Angle over time (Sun is in +X direction, so angle 0 is facing the sun)
# Let's start the orbit at the sunlit side (angle 0)
angle = (time / orbit_period) * 2 * np.pi
sat_x = R_orbit * np.cos(angle)
sat_y = R_orbit * np.sin(angle)

# Illumination Model with Penumbra
# Sun is at +X. The shadow (Umbra) is basically y in [-R_earth, R_earth] and x < 0.
# Penumbra is a small transition zone.
illumination = np.zeros_like(time, dtype=float)
for i in range(len(time)):
    x, y = sat_x[i], sat_y[i]
    if x >= 0:
        # Sunlit side
        illumination[i] = 1.0
    else:
        # Night side
        # Distance from center line
        dist_y = abs(y)
        penumbra_width = 2500.0 # Widen transition for a smoother, less square curve
        if dist_y < (R_earth - penumbra_width/2): # Deep Umbra
            illumination[i] = 0.0
        elif dist_y > (R_earth + penumbra_width/2): # Clear of shadow
            illumination[i] = 1.0
        else:
            # Penumbra smooth transition
            illumination[i] = (dist_y - (R_earth - penumbra_width/2)) / penumbra_width

# Temperature Model
temperature = np.zeros_like(time, dtype=float)
tau = 20.0 # thermal time constant (minutes)
curr_temp = 25.0 # Initial temp

# Power Consumption Estimates (mA)
baseline_power = np.full_like(time, 40.0086, dtype=float)
improved_power = np.zeros_like(time, dtype=float)

overheat_threshold = 95 # degrees C, more realistic limit
overheat_timer = 0
is_overheated = False

for i in range(len(time)):
    # 1. Thermal Model
    # Target temp based on illumination
    target_temp = -40 + (illumination[i] * (100 - (-40))) # Scale from -40 (eclipse) to +100 (sun)
    curr_temp += (target_temp - curr_temp) / tau
    temperature[i] = curr_temp

    # 2. Power and Protection Logic
    if illumination[i] < 0.1: # Deep eclipse
        improved_power[i] = 0.0111 # Deep sleep during eclipse
        overheat_timer = 0 
        is_overheated = False 
    else:
        # Check danger zone
        if temperature[i] >= overheat_threshold:
            overheat_timer += 1
        else:
            overheat_timer = 0
            
        if overheat_timer >= 5:
            is_overheated = True
            
        if is_overheated:
            improved_power[i] = 0.0111 # Deep sleep due to overheating
        else:
            improved_power[i] = 40.0086 # Normal operation

# --- 3. Calculate Final Statistics ---
baseline_energy = np.trapezoid(baseline_power, time)
improved_energy = np.trapezoid(improved_power, time)
savings = ((baseline_energy - improved_energy) / baseline_energy) * 100

final_textstr = (f"MISSION COMPLETE - 2 ORBITS\n"
                 f"---------------------------\n"
                 f"Baseline Energy: {baseline_energy:.0f} mA·min\n"
                 f"Improved Energy: {improved_energy:.0f} mA·min\n"
                 f"TOTAL POWER SAVED: {savings:.1f}%")

print(final_textstr)

# --- 4. Setup the Animated Figure ---
fig = plt.figure(figsize=(15, 8))
fig.canvas.manager.set_window_title('Realistic LEO Satellite Power Simulation')

# GridSpec Layout
gs = fig.add_gridspec(3, 2, width_ratios=[1, 1.2])

# Left: Orbit Animation
ax_spatial = fig.add_subplot(gs[:, 0])
ax_spatial.set_aspect('equal')
ax_spatial.set_xlim(-R_orbit * 1.5, R_orbit * 1.5)
ax_spatial.set_ylim(-R_orbit * 1.5, R_orbit * 1.5)
ax_spatial.axis('off')
ax_spatial.set_title("2D Orbital View")

# Draw Earth
earth = Circle((0, 0), R_earth, color='#1f77b4', zorder=2)
ax_spatial.add_patch(earth)

# Draw Shadow Cone
shadow_y = R_earth
shadow_x = R_orbit * 1.5
shadow = Polygon([ (0, shadow_y), (-shadow_x, shadow_y), (-shadow_x, -shadow_y), (0, -shadow_y) ], color='black', alpha=0.3, zorder=1)
ax_spatial.add_patch(shadow)

# Draw Orbit Path
orbit_path = Circle((0, 0), R_orbit, color='gray', linestyle='--', fill=False, zorder=1)
ax_spatial.add_patch(orbit_path)

# Add Sun Direction Arrows
ax_spatial.annotate('SUN', xy=(R_orbit * 1.2, 0), xytext=(R_orbit * 1.4, 0),
            arrowprops=dict(facecolor='yellow', shrink=0.05),
            fontsize=12, fontweight='bold', color='orange', zorder=1)

# Load CubeSat Image
img_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'cubesat.png')
try:
    sat_img = mpimg.imread(img_path)
    imagebox = OffsetImage(sat_img, zoom=0.05) # Adjusted zoom down from 0.15 for better scale
    sat_ab = AnnotationBbox(imagebox, (sat_x[0], sat_y[0]), frameon=False, zorder=5)
    ax_spatial.add_artist(sat_ab)
except FileNotFoundError:
    sat_ab = None
    sat_marker, = ax_spatial.plot(sat_x[0], sat_y[0], 'ro', markersize=10, zorder=5)

# Right: 3 Graphs
ax_env = fig.add_subplot(gs[0, 1])
ax_temp = fig.add_subplot(gs[1, 1], sharex=ax_env)
ax_pow = fig.add_subplot(gs[2, 1], sharex=ax_env)

line_env, = ax_env.plot([], [], color='#FFB300', linewidth=2, label="Illumination Factor")
ax_env.set_ylim(-0.1, 1.1)
ax_env.set_xlim(0, total_time)
ax_env.set_ylabel("Illumination")
ax_env.set_title("Real-Time Simulation: Telemetry")
ax_env.legend(loc="upper right")
ax_env.grid(True, alpha=0.5)

line_temp, = ax_temp.plot([], [], color='#E53935', linewidth=2, label="Satellite Temp (°C)")
ax_temp.axhline(y=overheat_threshold, color='darkred', linestyle='--', label=f"Threshold ({overheat_threshold}°C)")
ax_temp.set_ylim(-50, 110) 
ax_temp.set_ylabel("Temperature (°C)")
ax_temp.legend(loc="upper right")
ax_temp.grid(True, alpha=0.5)

line_base_power, = ax_pow.plot([], [], color='#757575', linestyle='--', linewidth=2, label="Baseline (~40mA)")
line_imp_power, = ax_pow.plot([], [], color='#43A047', linewidth=2, label="Improved (Smart Sleep)")
ax_pow.set_ylim(-5, 60) 
ax_pow.set_xlabel("Time (Minutes)")
ax_pow.set_ylabel("Power (mA)")
ax_pow.legend(loc="upper right")
ax_pow.grid(True, alpha=0.5)

plt.tight_layout()

# --- 5. Animation Function ---
def animate(frame):
    # frame is the index from frame_sequence
    t_data = time[:frame+1]
    
    # 1. Update Spatial View
    if sat_ab is not None:
        sat_ab.xybox = (sat_x[frame], sat_y[frame])
    else:
        sat_marker.set_data([sat_x[frame]], [sat_y[frame]])
        
    # 2. Update Graphs
    line_env.set_data(t_data, illumination[:frame+1])
    line_temp.set_data(t_data, temperature[:frame+1])
    line_base_power.set_data(t_data, baseline_power[:frame+1])
    line_imp_power.set_data(t_data, improved_power[:frame+1])

    if sat_ab is not None:
        return sat_ab, line_env, line_temp, line_base_power, line_imp_power
    else:
        return sat_marker, line_env, line_temp, line_base_power, line_imp_power

# Use all frames and slow down interval
frame_sequence = np.arange(0, len(time), 1)
ani = FuncAnimation(fig, animate, frames=frame_sequence, interval=50, blit=True, repeat=False)

import matplotlib
if matplotlib.get_backend().lower() == 'agg' or not matplotlib.is_interactive():
    gif_path = 'simulation.gif'
    print(f"Non-interactive backend detected. Saving animation to '{gif_path}'...")
    # FPS = 15 for slower playback
    ani.save(gif_path, writer='pillow', fps=15)
    print(f"Animation saved successfully to '{gif_path}'.")
else:
    plt.show()