
from src.models.coldplate import ColdPlateModel

model = ColdPlateModel(
    gpu_power_w=700,
    num_gpus=1,
    coolant_type="water",
    ambient_temp_c=25
)

# Check performance at min flow (5 LPM)
result_min = model.calculate_performance(flow_rate_lpm=5.0)
print(f"At 5 LPM: {result_min['junction_temp_c']}°C")

# Check performance at max flow (30 LPM)
result_max = model.calculate_performance(flow_rate_lpm=30.0)
print(f"At 30 LPM: {result_max['junction_temp_c']}°C")

# Run optimization
opt = model.optimize_flow_rate(target_temp_c=80.0)
print(f"Optimized: {opt['flow_rate_lpm']} LPM -> {opt['junction_temp_c']}°C")
