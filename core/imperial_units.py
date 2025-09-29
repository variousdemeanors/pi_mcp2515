"""
Imperial Units Conversion Module

Provides comprehensive unit conversions for automotive data logging,
ensuring all measurements are displayed in imperial units (Fahrenheit, PSI, etc.).
"""

from typing import Any, Dict, Union


class ImperialConverter:
    """Converts various automotive measurements to imperial units."""
    
    @staticmethod
    def convert_temperature(value: Any) -> Union[float, str]:
        """Convert temperature to Fahrenheit."""
        # Duck-type for unit objects (python-obd Quantities): check for .magnitude and .units
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            try:
                unit_str = str(value.units).lower()
                # Handle various temperature units
                if unit_str in ['celsius', 'degc', '°c']:
                    return round(value.to('fahrenheit').magnitude, 1)
                elif str(value.units).lower() in ['kelvin', 'k']:
                    # Convert K to C first, then to F
                    celsius = value.magnitude - 273.15
                    return round((celsius * 9/5) + 32, 1)
                elif unit_str in ['fahrenheit', 'degf', '°f']:
                    return round(value.magnitude, 1)
                else:
                    # Assume celsius if units unclear
                    return round((value.magnitude * 9/5) + 32, 1)
            except Exception:
                return "N/A"
        elif isinstance(value, (int, float)):
            # Assume celsius and convert
            try:
                return round((float(value) * 9/5) + 32, 1)
            except Exception:
                return "N/A"
        else:
            return "N/A"
    
    @staticmethod
    def convert_pressure(value: Any) -> Union[float, str]:
        """Convert pressure to PSI."""
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            try:
                unit_str = str(value.units).lower()
                if unit_str in ['kilopascal', 'kpa']:
                    return round(value.to('psi').magnitude, 2)
                elif unit_str in ['pascal', 'pa']:
                    return round((value.magnitude / 1000) * 0.145038, 2)  # Pa to kPa to PSI
                elif unit_str in ['bar']:
                    return round(value.magnitude * 14.5038, 2)  # bar to PSI
                elif unit_str in ['psi', 'pounds_per_square_inch']:
                    return round(value.magnitude, 2)
                elif unit_str in ['millibar', 'mbar']:
                    return round(value.magnitude * 0.0145038, 2)  # mbar to PSI
                else:
                    # Try generic conversion if available
                    try:
                        return round(value.to('psi').magnitude, 2)
                    except Exception:
                        return "N/A"
            except Exception:
                return "N/A"
        elif isinstance(value, (int, float)):
            # Assume kPa if just a number
            try:
                return round(float(value) * 0.145038, 2)
            except Exception:
                return "N/A"
        else:
            return "N/A"
    
    @staticmethod
    def convert_speed(value: Any) -> Union[float, str]:
        """Convert speed to MPH."""
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            try:
                unit_str = str(value.units).lower()
                if unit_str in ['kilometer_per_hour', 'kph', 'km/h']:
                    return round(value.magnitude * 0.621371, 1)  # km/h to mph
                elif unit_str in ['meter_per_second', 'm/s']:
                    return round(value.magnitude * 2.23694, 1)  # m/s to mph
                elif unit_str in ['mile_per_hour', 'mph']:
                    return round(value.magnitude, 1)
                else:
                    try:
                        return round(value.to('mph').magnitude, 1)
                    except Exception:
                        return "N/A"
            except Exception:
                return "N/A"
        elif isinstance(value, (int, float)):
            # Assume km/h if just a number
            try:
                return round(float(value) * 0.621371, 1)
            except Exception:
                return "N/A"
        else:
            return "N/A"
    
    @staticmethod
    def convert_distance(value: Any) -> Union[float, str]:
        """Convert distance to miles."""
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            try:
                unit_str = str(value.units).lower()
                if unit_str in ['kilometer', 'km']:
                    return round(value.magnitude * 0.621371, 2)  # km to miles
                elif unit_str in ['meter', 'm']:
                    return round(value.magnitude * 0.000621371, 2)  # m to miles
                elif unit_str in ['mile', 'miles']:
                    return round(value.magnitude, 2)
                else:
                    try:
                        return round(value.to('mile').magnitude, 2)
                    except Exception:
                        return "N/A"
            except Exception:
                return "N/A"
        elif isinstance(value, (int, float)):
            # Assume km if just a number
            try:
                return round(float(value) * 0.621371, 2)
            except Exception:
                return "N/A"
        else:
            return "N/A"
    
    @staticmethod
    def convert_flow_rate(value: Any) -> Union[float, str]:
        """Convert flow rate to GPH (gallons per hour)."""
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            try:
                unit_str = str(value.units).lower()
                if unit_str in ['liter_per_hour', 'l/h']:
                    return round(value.magnitude * 0.264172, 2)  # L/h to GPH
                elif unit_str in ['gram_per_second', 'g/s']:
                    # Assume gasoline density ~0.75 kg/L
                    lps = value.magnitude / (750.0)  # g/s to L/s
                    lph = lps * 3600  # L/s to L/h
                    return round(lph * 0.264172, 2)  # L/h to GPH
                elif unit_str in ['gallon_per_hour', 'gph']:
                    return round(value.magnitude, 2)
                else:
                    return "N/A"
            except Exception:
                return "N/A"
        elif isinstance(value, (int, float)):
            # Assume L/h if just a number
            try:
                return round(float(value) * 0.264172, 2)
            except Exception:
                return "N/A"
        else:
            return "N/A"
    
    @staticmethod
    def convert_value_by_type(key: str, value: Any) -> Union[float, str, Any]:
        """
        Auto-convert values based on key name patterns.
        Returns converted value or original value if no conversion needed.
        """
        if value is None or value == "N/A":
            return value
        
        key_lower = key.lower()
        
        # Temperature conversions
        if any(temp_keyword in key_lower for temp_keyword in [
            'temp', 'temperature', 'coolant', 'intake', 'ambient', 'air', 'oil', 'exhaust'
        ]):
            return ImperialConverter.convert_temperature(value)
        
        # Pressure conversions
        elif any(pressure_keyword in key_lower for pressure_keyword in [
            'pressure', 'psi', 'bar', 'boost', 'vacuum', 'manifold', 'fuel_rail', 'barometric'
        ]):
            return ImperialConverter.convert_pressure(value)
        
        # Speed conversions
        elif any(speed_keyword in key_lower for speed_keyword in [
            'speed', 'velocity', 'mph', 'kph'
        ]):
            return ImperialConverter.convert_speed(value)
        
        # Distance conversions
        elif any(distance_keyword in key_lower for distance_keyword in [
            'distance', 'odometer', 'trip', 'mile', 'km'
        ]):
            return ImperialConverter.convert_distance(value)
        
        # Flow rate conversions
        elif any(flow_keyword in key_lower for flow_keyword in [
            'flow', 'fuel_rate', 'consumption', 'gph', 'lph'
        ]):
            return ImperialConverter.convert_flow_rate(value)
        
        # Return original value if no conversion pattern matches
        else:
            return value
    
    @staticmethod
    def convert_data_dict(data: Dict[str, Any], force_conversion: bool = False) -> Dict[str, Any]:
        """
        Convert all applicable values in a data dictionary to imperial units.
        
        Args:
            data: Dictionary of data to convert
            force_conversion: If True, converts all numeric values regardless of key name
        
        Returns:
            Dictionary with converted values
        """
        converted_data = {}
        
        for key, value in data.items():
            if force_conversion:
                # Try to convert everything that might be a unit
                if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                    try:
                        unit_str = str(value.units).lower()
                        if any(temp in unit_str for temp in ['celsius', 'kelvin']):
                            converted_data[key] = ImperialConverter.convert_temperature(value)
                        elif any(pressure in unit_str for pressure in ['pascal', 'bar', 'kpa']):
                            converted_data[key] = ImperialConverter.convert_pressure(value)
                        elif any(speed in unit_str for speed in ['kph', 'km/h', 'm/s']):
                            converted_data[key] = ImperialConverter.convert_speed(value)
                        else:
                            converted_data[key] = value
                    except Exception:
                        converted_data[key] = value
                else:
                    converted_data[key] = ImperialConverter.convert_value_by_type(key, value)
            else:
                # Smart conversion based on key names
                converted_data[key] = ImperialConverter.convert_value_by_type(key, value)
        
        return converted_data

def calculate_afr_from_lambda(lambda_value: Union[float, Any]) -> Union[float, str]:
    """
    Calculate Air-Fuel Ratio from lambda value.
    
    For gasoline: Stoichiometric AFR = 14.7:1
    AFR = lambda * 14.7
    """
    try:
        if hasattr(lambda_value, 'magnitude'):
            lam = float(lambda_value.magnitude)
        elif isinstance(lambda_value, (int, float)):
            lam = float(lambda_value)
        elif isinstance(lambda_value, str):
            lam = float(lambda_value)
        else:
            return "N/A"
        
        # Gasoline stoichiometric AFR is 14.7:1
        afr = lam * 14.7
        return round(afr, 2)
    except Exception:
        return "N/A"

def calculate_afr_from_wideband_o2(o2_current: Union[float, Any], sensor_type: str = "bosch_lsu4.9") -> Union[float, str]:
    """
    Calculate Air-Fuel Ratio from wideband O2 sensor current.
    
    This is a simplified conversion - actual conversion depends on specific sensor.
    For Bosch LSU 4.9 sensors (common wideband), approximate conversion.
    """
    try:
        if hasattr(o2_current, 'magnitude'):
            current_ma = float(o2_current.magnitude)
        elif isinstance(o2_current, (int, float)):
            current_ma = float(o2_current)
        elif isinstance(o2_current, str):
            current_ma = float(o2_current)
        else:
            return "N/A"
        
        # Simplified conversion for Bosch LSU 4.9
        # This is approximate - real conversion requires sensor calibration
        if sensor_type.lower() == "bosch_lsu4.9":
            # Very rough approximation: 0mA = rich (~10:1), 4mA = lean (~20:1)
            # Linear interpolation (not accurate, but gives ballpark)
            if 0 <= current_ma <= 8:
                afr = 10 + (current_ma / 8) * 10  # 0mA=10:1, 8mA=20:1
                return round(afr, 2)
            else:
                return "Out_of_Range"
        else:
            return "Unknown_Sensor"
    except Exception:
        return "N/A"