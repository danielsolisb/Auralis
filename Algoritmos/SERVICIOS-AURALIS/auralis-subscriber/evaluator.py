from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from models import PolicyRow, SensorRow

@dataclass
class Thresholds:
    warn_low: Optional[float] = None
    alert_low: Optional[float] = None
    warn_high: Optional[float] = None
    alert_high: Optional[float] = None
    hysteresis: Optional[float] = None
    enable_low: bool = False

SCOPE_ORDER = ["GLOBAL", "COMPANY", "SENSOR_TYPE", "STATION", "SENSOR"]

def _conv(policy: PolicyRow, v: Optional[float], smin: float, smax: float) -> Optional[float]:
    if v is None:
        return None
    if policy.alert_mode == "ABS":
        return float(v)
    span = max(0.0, float(smax) - float(smin))
    return float(smin) + float(v) * span

def build_thresholds_for_sensor(policies_by_scope: Dict[str, list], sensor: SensorRow) -> Thresholds:
    smin = float(sensor.min_value or 0.0)
    smax = float(sensor.max_value or 1.0)
    th = Thresholds(enable_low=False)
    for scope in SCOPE_ORDER:
        for p in policies_by_scope.get(scope, []):
            if scope == "COMPANY" and p.company_id != sensor.company_id: continue
            if scope == "SENSOR_TYPE" and p.sensor_type_id != sensor.sensor_type_id: continue
            if scope == "STATION" and p.station_id != sensor.station_id: continue
            if scope == "SENSOR" and p.sensor_id != sensor.id: continue
            if p.warn_high is not None: th.warn_high = _conv(p, p.warn_high, smin, smax)
            if p.alert_high is not None: th.alert_high = _conv(p, p.alert_high, smin, smax)
            if p.hysteresis is not None: th.hysteresis = _conv(p, p.hysteresis, smin, smax)
            if p.enable_low_thresholds:
                th.enable_low = True
                if p.warn_low is not None: th.warn_low = _conv(p, p.warn_low, smin, smax)
                if p.alert_low is not None: th.alert_low = _conv(p, p.alert_low, smin, smax)
    return th

class StateTracker:
    def __init__(self, persistence_default: int = 0, use_hysteresis: bool = True):
        self.state: Dict[int, str] = {}
        self.since: Dict[int, datetime] = {}
        self.persistence_default = persistence_default
        self.use_hysteresis = use_hysteresis

    def classify(self, sensor: SensorRow, th: Thresholds, value: float, now: datetime, persistence_seconds: Optional[int]) -> Optional[str]:
        hys = th.hysteresis or 0.0 if self.use_hysteresis else 0.0
        band = "NORMAL"
        if th.alert_high is not None and value >= th.alert_high + hys:
            band = "ALERT_HIGH"
        elif th.warn_high is not None and value >= th.warn_high + hys:
            band = "WARN_HIGH"
        elif th.enable_low:
            if th.alert_low is not None and value <= th.alert_low - hys:
                band = "ALERT_LOW"
            elif th.warn_low is not None and value <= th.warn_low - hys:
                band = "WARN_LOW"

        prev = self.state.get(sensor.id, "NORMAL")
        if band == prev:
            self.since.pop(sensor.id, None)
            return band

        if band != "NORMAL":
            since = self.since.get(sensor.id)
            if not since:
                self.since[sensor.id] = now
                return None
            wait = persistence_seconds if persistence_seconds is not None else self.persistence_default
            if wait and (now - since).total_seconds() < wait:
                return None

        self.state[sensor.id] = band
        self.since.pop(sensor.id, None)
        return band
