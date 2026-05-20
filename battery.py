"""
Battery monitoring module for Waveshare UPS HAT
Handles cases where battery is not connected (e.g., working on PC)
"""

import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global battery percentage variable
battery_percentage: int = 100
battery_voltage: float = 0.0
battery_available: bool = False

try:
    import smbus2
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False
    logger.info("smbus2 not available - running on PC mode")


class BatteryMonitor:
    """Monitor Waveshare UPS HAT battery status"""
    
    # Waveshare UPS HAT I2C parameters
    I2C_CHANNEL = 1  # Raspberry Pi I2C channel
    BATTERY_ADDR = 0x36  # I2C address for battery fuel gauge
    
    # Register addresses
    REG_CAPACITY = 0x02  # Battery capacity percentage
    REG_VOLTAGE = 0x0E   # Battery voltage
    
    def __init__(self):
        self.bus = None
        self.available = False
        self._initialize()
    
    def _initialize(self):
        """Initialize I2C bus and check if battery is available"""
        if not HAS_SMBUS:
            logger.warning("smbus2 module not available - battery monitoring disabled")
            self.available = False
            return
        
        try:
            self.bus = smbus2.SMBus(self.I2C_CHANNEL)
            # Try to read from battery device to confirm it exists
            self.get_percentage()
            self.available = True
            logger.info("Battery monitor initialized successfully")
        except Exception as e:
            self.available = False
            logger.warning(f"Battery not available: {e}")
    
    def get_percentage(self) -> int:
        """
        Get battery percentage (0-100)
        Returns 100 if battery not available
        """
        if not self.available or not self.bus:
            return 100
        
        try:
            data = self.bus.read_i2c_block_data(self.BATTERY_ADDR, self.REG_CAPACITY, 1)
            percentage = data[0] & 0xFF
            # Clamp value between 0 and 100
            return min(max(percentage, 0), 100)
        except Exception as e:
            logger.warning(f"Error reading battery percentage: {e}")
            return 100
    
    def get_voltage(self) -> float:
        """
        Get battery voltage in volts
        Returns 0.0 if battery not available
        """
        if not self.available or not self.bus:
            return 0.0
        
        try:
            data = self.bus.read_i2c_block_data(self.BATTERY_ADDR, self.REG_VOLTAGE, 2)
            # Voltage is stored in 2 bytes, big-endian
            voltage_raw = (data[0] << 8) | data[1]
            # Convert to volts (typically 1.25mV per unit)
            voltage = voltage_raw * 1.25 / 1000.0
            return round(voltage, 2)
        except Exception as e:
            logger.warning(f"Error reading battery voltage: {e}")
            return 0.0
    
    def update(self):
        """Update global battery variables"""
        global battery_percentage, battery_voltage, battery_available
        
        battery_percentage = self.get_percentage()
        battery_voltage = self.get_voltage()
        battery_available = self.available
    
    def close(self):
        """Close I2C bus"""
        if self.bus:
            try:
                self.bus.close()
            except Exception as e:
                logger.warning(f"Error closing I2C bus: {e}")


# Initialize global battery monitor
_monitor: Optional[BatteryMonitor] = None


def initialize_battery():
    """Initialize battery monitoring - call this at startup"""
    global _monitor
    _monitor = BatteryMonitor()
    _monitor.update()
    logger.info(f"Battery status - Available: {battery_available}, "
                f"Percentage: {battery_percentage}%, Voltage: {battery_voltage}V")


def update_battery():
    """Update battery status - call this regularly (e.g., every frame or every second)"""
    global _monitor
    if _monitor:
        _monitor.update()


def get_battery_percentage() -> int:
    """Get current battery percentage"""
    return battery_percentage


def get_battery_voltage() -> float:
    """Get current battery voltage"""
    return battery_voltage


def is_battery_available() -> bool:
    """Check if battery is available"""
    return battery_available


def shutdown_battery():
    """Cleanup battery monitoring - call this at shutdown"""
    global _monitor
    if _monitor:
        _monitor.close()
        _monitor = None
