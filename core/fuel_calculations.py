"""
Fuel Delivery Calculations Module

Calculates fuel delivery, injector duty cycle, fuel flow rates, and fuel economy
metrics using OBD-II data and mathematical models.
"""

from typing import Any, Dict, Union, Optional
import math

class FuelCalculator:
    """Calculates fuel delivery and related metrics from OBD-II data."""
    
    # Engine-specific constants (can be customized per vehicle)
    DEFAULT_INJECTOR_FLOW_RATE = 24.0  # lb/hr at 43.5 PSI (modify for your injectors)
    DEFAULT_NUM_CYLINDERS = 4
    DEFAULT_DISPLACEMENT = 2.0  # liters (modify for your engine)
    
    # Fuel type constants
    FUEL_TYPES = {
        'gasoline': {'stoich_afr': 14.7, 'density_lb_gal': 6.0},
        'e10': {'stoich_afr': 14.1, 'density_lb_gal': 6.1},
        'e30': {'stoich_afr': 9.76, 'density_lb_gal': 6.4},
        'e85': {'stoich_afr': 9.65, 'density_lb_gal': 6.6}
    }
    
    # Injection system constants
    PORT_INJECTION_PRESSURE = 43.5  # PSI standard
    DI_BASE_PRESSURE = 500  # PSI minimum for direct injection
    DI_MAX_PRESSURE = 3000  # PSI maximum for direct injection
    
    @staticmethod
    def calculate_airflow_from_map(map_pressure_kpa: float, rpm: float, 
                                 displacement: float, intake_temp_c: float = 20.0,
                                 volumetric_efficiency: float = 85.0) -> float:
        """
        Calculate estimated mass air flow using MAP sensor (Speed-Density method).
        
        This is the method used by MAP-based engine management systems.
        
        Args:
            map_pressure_kpa: Manifold Absolute Pressure in kPa
            rpm: Engine RPM
            displacement: Engine displacement in liters
            intake_temp_c: Intake air temperature in Celsius
            volumetric_efficiency: Estimated volumetric efficiency (75-100% for NA, can be >100% for forced induction)
            
        Returns:
            Estimated mass air flow in g/s
        """
        try:
            if rpm <= 0 or displacement <= 0 or map_pressure_kpa <= 0:
                return 0.0
            
            # Convert intake temp to Kelvin
            intake_temp_k = intake_temp_c + 273.15
            
            # Air density at MAP conditions using ideal gas law
            # R = 287 J/(kg·K) for air
            air_density_kg_m3 = (map_pressure_kpa * 1000) / (287 * intake_temp_k)
            
            # Engine displacement per cycle (4-stroke = displacement/2 per revolution)
            displacement_per_cycle = displacement / 2  # liters per revolution
            
            # Volumetric flow rate: displacement * RPM * volumetric efficiency
            volumetric_flow_rate_lpm = displacement_per_cycle * rpm * (volumetric_efficiency / 100)
            
            # Convert to m³/s
            volumetric_flow_rate_m3s = (volumetric_flow_rate_lpm / 1000) / 60
            
            # Mass flow = volumetric flow * air density
            mass_flow_kg_s = volumetric_flow_rate_m3s * air_density_kg_m3
            
            # Convert to g/s
            mass_flow_gs = mass_flow_kg_s * 1000
            
            return mass_flow_gs
            
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    @staticmethod
    def estimate_volumetric_efficiency(map_pressure_kpa: float, 
                                     barometric_pressure_kpa: float = 101.325,
                                     engine_load: float = 50.0) -> float:
        """
        Estimate volumetric efficiency based on MAP and engine load.
        
        Args:
            map_pressure_kpa: Manifold Absolute Pressure in kPa
            barometric_pressure_kpa: Barometric pressure in kPa
            engine_load: Engine load percentage
            
        Returns:
            Estimated volumetric efficiency percentage
        """
        try:
            if map_pressure_kpa <= 0 or barometric_pressure_kpa <= 0:
                return 85.0  # Default assumption
            
            # Calculate pressure ratio (boost/vacuum)
            pressure_ratio = map_pressure_kpa / barometric_pressure_kpa
            
            # Base volumetric efficiency estimates
            if pressure_ratio > 1.0:
                # Forced induction - can exceed 100%
                base_ve = 85 + (pressure_ratio - 1.0) * 50  # Rough scaling
                base_ve = min(base_ve, 130)  # Cap at 130%
            else:
                # Naturally aspirated
                base_ve = 70 + (pressure_ratio * 20)  # Scale with manifold vacuum
                base_ve = min(base_ve, 95)  # Cap at 95% for NA
            
            # Adjust for engine load (higher load = better VE up to a point)
            load_factor = 0.8 + (engine_load / 100) * 0.3
            adjusted_ve = base_ve * load_factor
            
            return max(50.0, min(adjusted_ve, 150.0))  # Reasonable bounds
            
        except (ValueError, ZeroDivisionError):
            return 85.0
    
    @staticmethod
    def get_fuel_properties(fuel_type: str = 'gasoline', ethanol_content: int = 0) -> Dict[str, float]:
        """
        Get fuel properties based on fuel type and ethanol content.
        
        Args:
            fuel_type: Base fuel type ('gasoline')
            ethanol_content: Ethanol percentage (0, 10, 30, 85)
            
        Returns:
            Dictionary with stoichiometric AFR and fuel density
        """
        # Determine fuel properties based on ethanol content
        if ethanol_content <= 5:
            return FuelCalculator.FUEL_TYPES['gasoline']
        elif ethanol_content <= 15:
            return FuelCalculator.FUEL_TYPES['e10']
        elif ethanol_content <= 50:
            return FuelCalculator.FUEL_TYPES['e30']
        else:
            return FuelCalculator.FUEL_TYPES['e85']
    
    @staticmethod
    def calculate_pressure_corrected_flow(base_flow_rate: float, 
                                        actual_pressure: float,
                                        rated_pressure: float = 43.5) -> float:
        """
        Calculate pressure-corrected injector flow rate.
        For direct injection, pressure can vary from 500-3000 PSI vs standard 43.5 PSI.
        
        Args:
            base_flow_rate: Injector flow rate at rated pressure (lb/hr)
            actual_pressure: Current fuel rail pressure (PSI)
            rated_pressure: Pressure at which flow rate was measured (PSI)
            
        Returns:
            Pressure-corrected flow rate (lb/hr)
        """
        try:
            if actual_pressure <= 0 or rated_pressure <= 0:
                return base_flow_rate
            
            # Flow rate scales with square root of pressure ratio
            pressure_ratio = actual_pressure / rated_pressure
            corrected_flow = base_flow_rate * math.sqrt(pressure_ratio)
            
            return corrected_flow
            
        except (ValueError, ZeroDivisionError):
            return base_flow_rate
    
    @staticmethod
    def estimate_di_fuel_pressure(engine_load: float, rpm: float, 
                                map_pressure_kpa: float = 100.0) -> float:
        """
        Estimate direct injection fuel pressure based on engine conditions.
        Modern DI systems vary pressure from 500-3000 PSI based on load and RPM.
        
        Args:
            engine_load: Engine load percentage (0-100)
            rpm: Engine RPM
            map_pressure_kpa: Manifold pressure for additional context
            
        Returns:
            Estimated fuel pressure in PSI
        """
        try:
            if engine_load < 0:
                engine_load = 0
            if engine_load > 100:
                engine_load = 100
                
            # Base pressure starts at 500 PSI
            base_pressure = FuelCalculator.DI_BASE_PRESSURE
            
            # Pressure increases with load (main factor)
            load_pressure = (engine_load / 100) * (FuelCalculator.DI_MAX_PRESSURE - base_pressure)
            
            # Additional pressure for high RPM (atomization improvement)
            rpm_factor = min(rpm / 6000.0, 1.0) * 300  # Up to 300 PSI boost at 6000+ RPM
            
            # Higher pressure under boost conditions
            boost_factor = 0
            if map_pressure_kpa > 101.325:  # Above atmospheric
                boost_ratio = map_pressure_kpa / 101.325
                boost_factor = (boost_ratio - 1.0) * 200  # Up to 200 PSI additional under boost
            
            estimated_pressure = base_pressure + load_pressure + rpm_factor + boost_factor
            
            # Clamp to realistic bounds
            return max(FuelCalculator.DI_BASE_PRESSURE, 
                      min(estimated_pressure, FuelCalculator.DI_MAX_PRESSURE))
            
        except (ValueError, ZeroDivisionError):
            return FuelCalculator.DI_BASE_PRESSURE
    
    @staticmethod
    def calculate_theoretical_fuel_flow(maf_rate: float = None, afr: float = 14.7,
                                      map_pressure_kpa: float = None, rpm: float = None,
                                      displacement: float = DEFAULT_DISPLACEMENT,
                                      intake_temp_c: float = 20.0, engine_load: float = 50.0,
                                      barometric_pressure_kpa: float = 101.325,
                                      fuel_type: str = 'gasoline', 
                                      ethanol_content: int = 0) -> float:
        """
        Calculate theoretical fuel flow rate. Can use either MAF or MAP-based calculation.
        
        Args:
            maf_rate: Mass Air Flow in g/s (if available)
            afr: Air-Fuel Ratio (default 14.7 for gasoline stoichiometric)
            map_pressure_kpa: Manifold Absolute Pressure in kPa (for MAP-based calculation)
            rpm: Engine RPM (for MAP-based calculation)
            displacement: Engine displacement in liters
            intake_temp_c: Intake air temperature in Celsius
            engine_load: Engine load percentage
            barometric_pressure_kpa: Barometric pressure in kPa
            fuel_type: Fuel type ('gasoline')
            ethanol_content: Ethanol percentage (0 for pure gas, 30 for E30, etc.)
            
        Returns:
            Fuel flow rate in g/s
        """
        try:
            # Get fuel properties for correct AFR
            fuel_props = FuelCalculator.get_fuel_properties(fuel_type, ethanol_content)
            actual_afr = fuel_props['stoich_afr']
            
            # If MAF is available, use it directly
            if maf_rate is not None and maf_rate > 0:
                return maf_rate / actual_afr
            
            # Otherwise, calculate airflow from MAP (Speed-Density method)
            elif (map_pressure_kpa is not None and rpm is not None and 
                  map_pressure_kpa > 0 and rpm > 0):
                
                # Estimate volumetric efficiency
                vol_eff = FuelCalculator.estimate_volumetric_efficiency(
                    map_pressure_kpa, barometric_pressure_kpa, engine_load)
                
                # Calculate estimated airflow
                estimated_airflow = FuelCalculator.calculate_airflow_from_map(
                    map_pressure_kpa, rpm, displacement, intake_temp_c, vol_eff)
                
                # Calculate fuel flow
                return estimated_airflow / actual_afr
            
            else:
                return 0.0
                
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    @staticmethod
    def calculate_injector_duty_cycle(fuel_flow_gs: float, rpm: float, 
                                    injector_flow_rate: float = DEFAULT_INJECTOR_FLOW_RATE,
                                    num_cylinders: int = DEFAULT_NUM_CYLINDERS,
                                    fuel_pressure_psi: float = 43.5,
                                    rated_pressure_psi: float = 43.5,
                                    injection_type: str = 'port') -> float:
        """
        Calculate injector duty cycle percentage with pressure correction.
        
        Args:
            fuel_flow_gs: Required fuel flow in g/s
            rpm: Engine RPM
            injector_flow_rate: Injector flow rating in lb/hr at rated pressure
            num_cylinders: Number of cylinders
            fuel_pressure_psi: Current fuel rail pressure in PSI
            rated_pressure_psi: Pressure at which injector was rated (usually 43.5 PSI for port, variable for DI)
            injection_type: 'port' or 'direct'
            
        Returns:
            Injector duty cycle as percentage (0-100%)
        """
        try:
            if rpm <= 0 or injector_flow_rate <= 0:
                return 0.0
            
            # Apply pressure correction to flow rate
            corrected_flow_rate = FuelCalculator.calculate_pressure_corrected_flow(
                injector_flow_rate, fuel_pressure_psi, rated_pressure_psi)
            
            # Convert injector flow from lb/hr to g/s
            injector_flow_gs = (corrected_flow_rate * 453.592) / 3600  # lb/hr to g/s
            
            # Calculate max fuel delivery per injector at current RPM
            # At RPM, each injector fires RPM/2 times per minute (4-stroke)
            injections_per_second = (rpm / 2) / 60
            max_fuel_per_injection = injector_flow_gs / injections_per_second
            
            # Calculate required fuel per injection per cylinder
            required_fuel_per_injection = fuel_flow_gs / (injections_per_second * num_cylinders)
            
            # Duty cycle = (required fuel per injection / max fuel per injection) * 100
            duty_cycle = (required_fuel_per_injection / max_fuel_per_injection) * 100
            
            return min(duty_cycle, 100.0)  # Cap at 100%
            
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    @staticmethod
    def calculate_fuel_economy_mpg(speed_mph: float, fuel_flow_gs: float) -> float:
        """
        Calculate instantaneous fuel economy in MPG.
        
        Args:
            speed_mph: Vehicle speed in MPH
            fuel_flow_gs: Fuel flow rate in g/s
            
        Returns:
            Fuel economy in MPG
        """
        try:
            if speed_mph <= 0 or fuel_flow_gs <= 0:
                return 0.0
            
            # Convert fuel flow from g/s to gallons/hour
            # Gasoline density ~737 g/L, 1 gallon = 3.78541 L
            fuel_flow_gph = (fuel_flow_gs * 3600) / (737 * 3.78541)  # g/s to GPH
            
            # MPG = MPH / GPH
            return speed_mph / fuel_flow_gph
            
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    @staticmethod
    def calculate_volumetric_efficiency(maf_rate: float, rpm: float, 
                                      displacement: float = DEFAULT_DISPLACEMENT,
                                      intake_temp_f: float = 70.0,
                                      manifold_pressure_psi: float = 14.7) -> float:
        """
        Calculate volumetric efficiency of the engine.
        
        Args:
            maf_rate: Mass Air Flow in g/s
            rpm: Engine RPM
            displacement: Engine displacement in liters
            intake_temp_f: Intake air temperature in Fahrenheit
            manifold_pressure_psi: Manifold absolute pressure in PSI
            
        Returns:
            Volumetric efficiency as percentage (0-100%)
        """
        try:
            if rpm <= 0 or displacement <= 0:
                return 0.0
            
            # Convert intake temp to Kelvin
            intake_temp_k = ((intake_temp_f - 32) * 5/9) + 273.15
            
            # Convert manifold pressure to kPa
            manifold_pressure_kpa = manifold_pressure_psi * 6.89476
            
            # Air density at intake conditions (ideal gas law)
            # R = 287 J/(kg·K) for air
            air_density = (manifold_pressure_kpa * 1000) / (287 * intake_temp_k)  # kg/m³
            
            # Theoretical air flow (displacement * rpm/2 * air density)
            # rpm/2 because 4-stroke engine completes 1 intake stroke per 2 revolutions
            theoretical_flow_m3s = (displacement / 1000) * (rpm / 2) / 60  # m³/s
            theoretical_mass_flow = theoretical_flow_m3s * air_density * 1000  # g/s
            
            # Volumetric efficiency = actual flow / theoretical flow
            vol_efficiency = (maf_rate / theoretical_mass_flow) * 100
            
            return min(vol_efficiency, 150.0)  # Cap at 150% (turbo/supercharged)
            
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    @staticmethod
    def calculate_brake_specific_fuel_consumption(fuel_flow_gs: float, 
                                                engine_load: float, 
                                                displacement: float = DEFAULT_DISPLACEMENT) -> float:
        """
        Calculate Brake Specific Fuel Consumption (BSFC).
        
        Args:
            fuel_flow_gs: Fuel flow rate in g/s
            engine_load: Engine load percentage (0-100)
            displacement: Engine displacement in liters
            
        Returns:
            BSFC in g/kWh (grams per kilowatt-hour)
        """
        try:
            if engine_load <= 0 or displacement <= 0:
                return 0.0
            
            # Estimate power output based on engine load and displacement
            # This is a rough approximation: 50 kW per liter at 100% load
            estimated_power_kw = (displacement * 50) * (engine_load / 100)
            
            if estimated_power_kw <= 0:
                return 0.0
            
            # Convert fuel flow from g/s to g/h
            fuel_flow_gh = fuel_flow_gs * 3600
            
            # BSFC = fuel flow (g/h) / power (kW)
            bsfc = fuel_flow_gh / estimated_power_kw
            
            return bsfc
            
        except (ValueError, ZeroDivisionError):
            return 0.0

def calculate_fuel_metrics(data_store: Dict[str, Any], 
                          injector_flow_rate: float = FuelCalculator.DEFAULT_INJECTOR_FLOW_RATE,
                          num_cylinders: int = FuelCalculator.DEFAULT_NUM_CYLINDERS,
                          displacement: float = FuelCalculator.DEFAULT_DISPLACEMENT,
                          fuel_type: str = 'gasoline',
                          ethanol_content: int = 0,
                          injection_type: str = 'port',
                          fuel_pressure_psi: float = 43.5,
                          high_pressure_pump_enabled: bool = False) -> Dict[str, Union[float, str]]:
    """
    Calculate comprehensive fuel delivery metrics from OBD data store.
    
    Args:
        data_store: Dictionary containing OBD data
        injector_flow_rate: Injector flow rating in lb/hr
        num_cylinders: Number of engine cylinders
        displacement: Engine displacement in liters
        
    Returns:
        Dictionary containing calculated fuel metrics
    """
    
    # Extract required values from data store
    def safe_extract(key: str, default: float = 0.0) -> float:
        value = data_store.get(key, default)
        try:
            if hasattr(value, 'magnitude'):
                return float(value.magnitude)
            elif isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str) and value != "N/A":
                return float(value)
            else:
                return default
        except (ValueError, TypeError):
            return default
    
    # Extract OBD values - prioritize MAP over MAF
    maf_rate = safe_extract('MAF')  # g/s (may not be available)
    map_pressure = safe_extract('INTAKE_PRESSURE')  # kPa (MAP sensor)
    barometric_pressure = safe_extract('BAROMETRIC_PRESSURE', 101.325)  # kPa
    rpm = safe_extract('RPM')
    speed = safe_extract('SPEED')  # km/h, will convert to mph
    engine_load = safe_extract('ENGINE_LOAD')  # %
    commanded_afr = safe_extract('Commanded_AFR', 14.7)
    intake_temp = safe_extract('INTAKE_TEMP')  # Celsius
    
    # Try multiple fuel pressure PIDs (different vehicles use different ones)
    fuel_rail_pressure = (safe_extract('FUEL_RAIL_PRESSURE_DIRECT') or 
                         safe_extract('FUEL_RAIL_PRESSURE') or 
                         safe_extract('FUEL_RAIL_PRESSURE_ABS') or 
                         safe_extract('FUEL_RAIL_PRESSURE_VAC'))  # kPa
    
    short_ft = safe_extract('SHORT_FUEL_TRIM_1')  # %
    long_ft = safe_extract('LONG_FUEL_TRIM_1')  # %
    throttle_pos = safe_extract('THROTTLE_POS')  # %
    
    # Convert units
    speed_mph = speed * 0.621371 if speed > 0 else 0.0
    intake_temp_f = (intake_temp * 9/5) + 32 if intake_temp != 0 else 70.0
    map_pressure_psi = map_pressure * 0.145038 if map_pressure > 0 else 14.7
    fuel_rail_pressure_psi = fuel_rail_pressure * 0.145038 if fuel_rail_pressure > 0 else 43.5
    
    # Adjust AFR based on fuel trims
    if commanded_afr > 0:
        total_fuel_trim = ((100 + short_ft) / 100) * ((100 + long_ft) / 100)
        actual_afr = commanded_afr / total_fuel_trim
    else:
        actual_afr = 14.7
    
    # Calculate fuel metrics
    metrics = {}
    
    # Use actual fuel rail pressure from OBD-II PID (much more accurate!)
    if fuel_rail_pressure_psi > 0:
        # Real fuel pressure from vehicle's sensor
        actual_fuel_pressure = fuel_rail_pressure_psi
        pressure_source = "OBD-II Sensor"
        
        # Determine rated pressure based on injection type and actual pressure range
        if injection_type == 'direct' or fuel_rail_pressure_psi > 100:
            rated_pressure = FuelCalculator.DI_BASE_PRESSURE  # 500 PSI for DI
            metrics['fuel_system_type'] = 'Direct Injection (detected from pressure)'
        else:
            rated_pressure = FuelCalculator.PORT_INJECTION_PRESSURE  # 43.5 PSI for port
            metrics['fuel_system_type'] = 'Port Injection (detected from pressure)'
    else:
        # Fallback to configured/estimated pressure if PID not available
        if injection_type == 'direct' and high_pressure_pump_enabled:
            # Estimate DI pressure if sensor not available
            actual_fuel_pressure = FuelCalculator.estimate_di_fuel_pressure(
                engine_load, rpm, map_pressure)
            rated_pressure = FuelCalculator.DI_BASE_PRESSURE
            pressure_source = "Estimated (no sensor)"
            metrics['fuel_system_type'] = 'Direct Injection (estimated)'
        else:
            actual_fuel_pressure = fuel_pressure_psi if fuel_pressure_psi > 0 else 43.5
            rated_pressure = FuelCalculator.PORT_INJECTION_PRESSURE
            pressure_source = "Configuration"
            metrics['fuel_system_type'] = 'Port Injection (configured)'
    
    metrics['pressure_source'] = pressure_source
    
    # Get fuel properties for correct AFR calculation
    fuel_props = FuelCalculator.get_fuel_properties(fuel_type, ethanol_content)
    stoich_afr = fuel_props['stoich_afr']
    
    # Adjust AFR based on fuel trims (if using OBD commanded AFR, otherwise use stoich)
    if commanded_afr > 0:
        total_fuel_trim = ((100 + short_ft) / 100) * ((100 + long_ft) / 100)
        actual_afr = commanded_afr / total_fuel_trim
    else:
        # Use stoichiometric AFR for fuel type
        total_fuel_trim = ((100 + short_ft) / 100) * ((100 + long_ft) / 100)
        actual_afr = stoich_afr / total_fuel_trim
    
    # Fuel flow calculation - use MAP if MAF not available
    if maf_rate > 0:
        # MAF-based calculation (preferred if available)
        fuel_flow_gs = FuelCalculator.calculate_theoretical_fuel_flow(
            maf_rate=maf_rate, afr=actual_afr, fuel_type=fuel_type, 
            ethanol_content=ethanol_content)
        metrics['airflow_method'] = 'MAF'
        metrics['estimated_airflow_gs'] = round(maf_rate, 2)
    else:
        # MAP-based calculation (Speed-Density method)
        fuel_flow_gs = FuelCalculator.calculate_theoretical_fuel_flow(
            maf_rate=None, afr=actual_afr,
            map_pressure_kpa=map_pressure, rpm=rpm, 
            displacement=displacement, intake_temp_c=intake_temp,
            engine_load=engine_load, barometric_pressure_kpa=barometric_pressure,
            fuel_type=fuel_type, ethanol_content=ethanol_content)
        
        # Calculate estimated airflow for display
        vol_eff = FuelCalculator.estimate_volumetric_efficiency(
            map_pressure, barometric_pressure, engine_load)
        estimated_airflow = FuelCalculator.calculate_airflow_from_map(
            map_pressure, rpm, displacement, intake_temp, vol_eff)
        
        metrics['airflow_method'] = 'MAP (Speed-Density)'
        metrics['estimated_airflow_gs'] = round(estimated_airflow, 2)
        metrics['estimated_vol_efficiency'] = round(vol_eff, 1)
        
    # Fuel type information
    metrics['fuel_type'] = f"{fuel_type.title()}"
    if ethanol_content > 0:
        metrics['fuel_type'] += f" (E{ethanol_content})"
    metrics['stoich_afr'] = round(stoich_afr, 2)
    metrics['fuel_flow_gs'] = round(fuel_flow_gs, 3)
    metrics['fuel_flow_gph'] = round((fuel_flow_gs * 3600) / (737 * 3.78541), 2)  # Convert to GPH
    
    # Injector duty cycle with pressure correction
    duty_cycle = FuelCalculator.calculate_injector_duty_cycle(
        fuel_flow_gs, rpm, injector_flow_rate, num_cylinders,
        fuel_pressure_psi=actual_fuel_pressure, 
        rated_pressure_psi=rated_pressure,
        injection_type=injection_type)
    metrics['injector_duty_cycle'] = round(duty_cycle, 1)
    metrics['actual_fuel_pressure_psi'] = round(actual_fuel_pressure, 1)
    
    # Fuel economy
    mpg = FuelCalculator.calculate_fuel_economy_mpg(speed_mph, fuel_flow_gs)
    metrics['fuel_economy_mpg'] = round(mpg, 1) if mpg > 0 else "N/A"
    
    # Volumetric efficiency
    if maf_rate > 0:
        # Use actual MAF vs theoretical for VE calculation
        vol_eff = FuelCalculator.calculate_volumetric_efficiency(
            maf_rate, rpm, displacement, intake_temp_f, map_pressure_psi)
    else:
        # Use estimated VE from MAP calculation
        vol_eff = metrics.get('estimated_vol_efficiency', 85.0)
    
    metrics['volumetric_efficiency'] = round(vol_eff, 1)
    
    # Brake Specific Fuel Consumption
    bsfc = FuelCalculator.calculate_brake_specific_fuel_consumption(
        fuel_flow_gs, engine_load, displacement)
    metrics['bsfc_g_kwh'] = round(bsfc, 0) if bsfc > 0 else "N/A"
    
    # Fuel system status
    metrics['fuel_rail_pressure_psi'] = round(fuel_rail_pressure_psi, 1)
    metrics['actual_afr'] = round(actual_afr, 2)
    metrics['total_fuel_trim'] = round(((total_fuel_trim - 1) * 100), 1)  # Convert back to %
    
    # Performance indicators
    if duty_cycle > 85:
        metrics['injector_status'] = "Near Maximum"
    elif duty_cycle > 70:
        metrics['injector_status'] = "High Load"
    elif duty_cycle > 30:
        metrics['injector_status'] = "Normal"
    else:
        metrics['injector_status'] = "Light Load"
    
    return metrics

def get_fuel_recommendations(metrics: Dict[str, Any]) -> list:
    """Generate fuel system recommendations based on calculated metrics."""
    recommendations = []
    
    duty_cycle = metrics.get('injector_duty_cycle', 0)
    bsfc = metrics.get('bsfc_g_kwh', 0)
    vol_eff = metrics.get('volumetric_efficiency', 0)
    fuel_trim = metrics.get('total_fuel_trim', 0)
    
    # Injector duty cycle warnings
    if duty_cycle > 85:
        recommendations.append({
            'type': 'Critical',
            'message': f'Injector duty cycle at {duty_cycle}% - consider larger injectors',
            'action': 'Upgrade to higher flow rate injectors'
        })
    elif duty_cycle > 75:
        recommendations.append({
            'type': 'Warning', 
            'message': f'High injector duty cycle at {duty_cycle}%',
            'action': 'Monitor fuel delivery capacity'
        })
    
    # Fuel trim issues
    if abs(fuel_trim) > 15:
        recommendations.append({
            'type': 'Warning',
            'message': f'Large fuel trim correction: {fuel_trim}%',
            'action': 'Check for fuel delivery or sensor issues'
        })
    
    # Volumetric efficiency
    if vol_eff > 100:
        recommendations.append({
            'type': 'Info',
            'message': f'High volumetric efficiency: {vol_eff}% (forced induction working well)',
            'action': 'Good turbo/supercharger performance'
        })
    elif vol_eff < 70:
        recommendations.append({
            'type': 'Warning',
            'message': f'Low volumetric efficiency: {vol_eff}%',
            'action': 'Check intake restrictions or valve timing'
        })
    
    # BSFC efficiency
    if isinstance(bsfc, (int, float)) and bsfc > 350:
        recommendations.append({
            'type': 'Warning',
            'message': f'High fuel consumption: {bsfc} g/kWh',
            'action': 'Check engine tune and mechanical condition'
        })
    
    return recommendations