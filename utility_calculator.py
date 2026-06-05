"""
Utility Calculator - Pure Python implementation
Converted from react-utility-logic.js

Handles calculation of utility bills with:
- Multi-month usage calculation (current - previous)
- Singapore electricity and water tariffs
- Tax and surcharge calculations
- Dynamic rate fetching via TariffRateManager
"""

from typing import Dict, Optional, Tuple, TYPE_CHECKING
from decimal import Decimal, ROUND_HALF_UP
from logger import logger

if TYPE_CHECKING:
    from tariff_rate_manager import TariffRateManager


class UtilityCalculator:
    """
    Pure calculation logic for utility bills
    Replaces React component with testable Python methods
    
    Supports both hardcoded rates and dynamic rates via TariffRateManager
    """
    
    def __init__(self, tariff_manager: Optional['TariffRateManager'] = None):
        """
        Initialize calculator
        
        Args:
            tariff_manager: TariffRateManager instance for dynamic rates (optional)
                          If None, uses hardcoded defaults
        """
        self.tariff_manager = tariff_manager
        
        # Hardcoded fallback rates
        self.DEFAULT_ELECTRICITY_RATE = Decimal("0.2674")
        
        # Water rates (Singapore PUB)
        self.DEFAULT_WATER_USAGE_RATE = Decimal("1.43")      # SGD/m³ usage charge
        self.DEFAULT_WATERBORNE_TAX_RATE = Decimal("1.09")   # SGD/m³ waterborne tax
        self.WATER_CONSERVATION_TAX_RATE = Decimal("0.5")     # 50% of usage charge
        
        self.DEFAULT_TAX_RATE = Decimal("0.09")  # 9% GST
        self.DEFAULT_SURCHARGE = Decimal("0.5")
    
    # =========================================================================
    # ELECTRICITY CALCULATIONS
    # =========================================================================
    
    def calculate_electricity_usage(
        self,
        current_reading: float,
        previous_reading: float
    ) -> Decimal:
        """
        Calculate electricity consumption
        
        Args:
            current_reading: Current month kWh reading
            previous_reading: Previous month kWh reading
        
        Returns:
            Usage in kWh (Decimal)
        
        Example:
            >>> calc = UtilityCalculator()
            >>> calc.calculate_electricity_usage(1245.5, 1200.0)
            Decimal('45.50')
        """
        try:
            current = Decimal(str(current_reading or 0))
            previous = Decimal(str(previous_reading or 0))
            usage = current - previous
            
            if usage < 0:
                logger.warn(f"Negative electricity usage: {usage} kWh")
                return Decimal("0")
            
            return usage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        except Exception as e:
            logger.error(f"Error calculating electricity usage: {str(e)}")
            return Decimal("0")
    
    def calculate_electricity_charge(
        self,
        usage: float,
        rate: Optional[float] = None
    ) -> Decimal:
        """
        Calculate electricity charge
        
        Args:
            usage: Electricity usage in kWh
            rate: Rate per kWh (uses default/dynamic rate if None)
        
        Returns:
            Charge in SGD (Decimal)
        
        Example:
            >>> calc = UtilityCalculator()
            >>> calc.calculate_electricity_charge(45.5, 0.2674)
            Decimal('12.16')
            
            >>> # With TariffRateManager (fetches from DB)
            >>> manager = TariffRateManager(supabase)
            >>> calc = UtilityCalculator(tariff_manager=manager)
            >>> calc.calculate_electricity_charge(45.5)  # Uses current DB rate
            Decimal('12.17')
        """
        try:
            usage_dec = Decimal(str(usage or 0))
            
            # Determine rate to use: explicit > dynamic > default
            if rate is None:
                if self.tariff_manager:
                    rate_dec = self.tariff_manager.get_current_rate('electricity')
                else:
                    rate_dec = self.DEFAULT_ELECTRICITY_RATE
            else:
                rate_dec = Decimal(str(rate))
            
            charge = usage_dec * rate_dec
            
            return charge.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        except Exception as e:
            logger.error(f"Error calculating electricity charge: {str(e)}")
            return Decimal("0")
    
    # =========================================================================
    # WATER CALCULATIONS (with tiered multipliers)
    # =========================================================================
    
    def calculate_water_usage(
        self,
        current_reading: float,
        previous_reading: float
    ) -> Decimal:
        """
        Calculate water consumption
        
        Args:
            current_reading: Current month m³ reading
            previous_reading: Previous month m³ reading
        
        Returns:
            Usage in m³ (Decimal)
        
        Example:
            >>> calc = UtilityCalculator()
            >>> calc.calculate_water_usage(58.5, 50.0)
            Decimal('8.50')
        """
        try:
            current = Decimal(str(current_reading or 0))
            previous = Decimal(str(previous_reading or 0))
            usage = current - previous
            
            if usage < 0:
                logger.warn(f"Negative water usage: {usage} m³")
                return Decimal("0")
            
            return usage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        except Exception as e:
            logger.error(f"Error calculating water usage: {str(e)}")
            return Decimal("0")
    
    def calculate_water_charge(
        self,
        usage: float,
        usage_rate: Optional[float] = None,
        waterborne_tax_rate: Optional[float] = None
    ) -> Dict[str, Decimal]:
        """
        Calculate water charges with breakdown (Singapore PUB structure)
        
        Components:
        1. Water Usage Charge: usage × usage_rate
        2. Waterborne Tax: usage × waterborne_tax_rate
        3. Water Conservation Tax: water_usage_charge × 0.5
        
        Args:
            usage: Water usage in m³
            usage_rate: Rate per m³ for usage charge (fetches from DB if None)
            waterborne_tax_rate: Rate per m³ for waterborne tax (fetches from DB if None)
        
        Returns:
            Dict with breakdown:
            {
                "water_usage_charge": Decimal,      # SGD
                "waterborne_tax": Decimal,           # SGD
                "water_conservation_tax": Decimal,   # SGD (50% of usage)
                "total_water": Decimal,              # SGD (sum of all)
            }
        
        Example:
            >>> calc = UtilityCalculator()
            >>> charges = calc.calculate_water_charge(8.3, 1.43, 1.09)
            >>> charges["water_usage_charge"]
            Decimal('11.87')
            >>> charges["waterborne_tax"]
            Decimal('9.05')
            >>> charges["water_conservation_tax"]
            Decimal('5.94')
            >>> charges["total_water"]
            Decimal('26.86')
        """
        try:
            usage_dec = Decimal(str(usage or 0))
            
            # Fetch dynamic rates if not provided
            if usage_rate is None:
                if self.tariff_manager:
                    usage_rate_dec = self.tariff_manager.get_current_rate('water_usage')
                else:
                    usage_rate_dec = self.DEFAULT_WATER_USAGE_RATE
            else:
                usage_rate_dec = Decimal(str(usage_rate))
            
            if waterborne_tax_rate is None:
                if self.tariff_manager:
                    waterborne_rate_dec = self.tariff_manager.get_current_rate('water_waterborne')
                else:
                    waterborne_rate_dec = self.DEFAULT_WATERBORNE_TAX_RATE
            else:
                waterborne_rate_dec = Decimal(str(waterborne_tax_rate))
            
            # Calculate individual components
            water_usage_charge = (usage_dec * usage_rate_dec).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            waterborne_tax = (usage_dec * waterborne_rate_dec).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            water_conservation_tax = (water_usage_charge * self.WATER_CONSERVATION_TAX_RATE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            # Total water charge
            total_water = water_usage_charge + waterborne_tax + water_conservation_tax
            
            result = {
                "water_usage_charge": water_usage_charge,
                "waterborne_tax": waterborne_tax,
                "water_conservation_tax": water_conservation_tax,
                "total_water": total_water,
            }
            
            logger.info("Water charges calculated", {
                "usage": float(usage_dec),
                "usage_charge": float(water_usage_charge),
                "waterborne_tax": float(waterborne_tax),
                "conservation_tax": float(water_conservation_tax),
                "total": float(total_water),
            })
            
            return result
        
        except Exception as e:
            logger.error(f"Error calculating water charge: {str(e)}")
            return {
                "water_usage_charge": Decimal("0"),
                "waterborne_tax": Decimal("0"),
                "water_conservation_tax": Decimal("0"),
                "total_water": Decimal("0"),
            }
    
    # =========================================================================
    # TAX & SURCHARGE CALCULATIONS
    # =========================================================================
    
    def calculate_gst(
        self,
        subtotal: float,
        rate: Optional[float] = None
    ) -> Decimal:
        """
        Calculate Goods and Services Tax (9% Singapore)
        
        Args:
            subtotal: Subtotal before tax
            rate: Tax rate (uses default 9% if None)
        
        Returns:
            GST amount in SGD (Decimal)
        
        Example:
            >>> calc = UtilityCalculator()
            >>> calc.calculate_gst(100.0, 0.09)
            Decimal('9.00')
        """
        try:
            subtotal_dec = Decimal(str(subtotal or 0))
            rate_dec = Decimal(str(rate or self.DEFAULT_TAX_RATE))
            gst = subtotal_dec * rate_dec
            return gst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        except Exception as e:
            logger.error(f"Error calculating GST: {str(e)}")
            return Decimal("0")
    
    # =========================================================================
    # COMBINED BILL CALCULATION
    # =========================================================================
    
    def calculate_total_bill(
        self,
        electricity_charge: float,
        water_charge: float,
        water_tax: float,
        tax_rate: Optional[float] = None,
        surcharge: Optional[float] = None
    ) -> Decimal:
        """
        Calculate final bill with tax and surcharge
        
        Formula: (electricity + water + water_tax) × (1 + tax_rate) + surcharge
        
        Args:
            electricity_charge: Electricity charge in SGD
            water_charge: Water charge in SGD
            water_tax: Water tax/surcharge in SGD
            tax_rate: Tax rate (uses default 9% if None)
            surcharge: Fixed surcharge (uses default $0.50 if None)
        
        Returns:
            Total bill in SGD (Decimal)
        
        Example:
            >>> calc = UtilityCalculator()
            >>> total = calc.calculate_total_bill(12.16, 30.94, 5.0)
            >>> print(total)
            Decimal('59.45')
        """
        try:
            elec_dec = Decimal(str(electricity_charge or 0))
            water_dec = Decimal(str(water_charge or 0))
            tax_dec = Decimal(str(water_tax or 0))
            tax_rate_dec = Decimal(str(tax_rate or self.DEFAULT_TAX_RATE))
            surcharge_dec = Decimal(str(surcharge or self.DEFAULT_SURCHARGE))
            
            # Subtotal before tax
            subtotal = elec_dec + water_dec + tax_dec
            
            # Apply tax and surcharge
            total = (subtotal * (Decimal("1") + tax_rate_dec)) + surcharge_dec
            
            return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        except Exception as e:
            logger.error(f"Error calculating total bill: {str(e)}")
            return Decimal("0")
    
    # =========================================================================
    # FULL CALCULATION WORKFLOW
    # =========================================================================
    
    def calculate_bill_breakdown(
        self,
        electricity_current: float,
        electricity_previous: float,
        electricity_rate: Optional[float] = None,
        water_current: float = 0,
        water_previous: float = 0,
        water_usage_rate: Optional[float] = None,
        water_waterborne_tax_rate: Optional[float] = None,
    ) -> Dict[str, any]:
        """
        Calculate complete bill breakdown with detailed water charges
        
        Args:
            electricity_current: Current month electricity reading (kWh)
            electricity_previous: Previous month electricity reading (kWh)
            electricity_rate: Electricity rate per kWh (optional)
            water_current: Current month water reading (m³)
            water_previous: Previous month water reading (m³)
            water_usage_rate: Water usage charge rate per m³ (optional)
            water_waterborne_tax_rate: Waterborne tax rate per m³ (optional)
        
        Returns:
            Dictionary with complete bill breakdown:
            {
                "electricity": {
                    "usage": float,
                    "rate": float,
                    "charge": float,
                },
                "water": {
                    "usage": float,
                    "usage_rate": float,
                    "waterborne_tax_rate": float,
                    "water_usage_charge": float,
                    "waterborne_tax": float,
                    "water_conservation_tax": float,
                    "total_water": float,
                },
                "subtotal": float,
                "gst_rate": float,
                "gst": float,
                "surcharge": float,
                "total": float,
            }
        
        Example:
            >>> calc = UtilityCalculator()
            >>> bill = calc.calculate_bill_breakdown(
            ...     electricity_current=1245.5,
            ...     electricity_previous=1200.0,
            ...     water_current=58.5,
            ...     water_previous=50.0,
            ... )
            >>> print(f"Total: ${bill['total']}")
        """
        try:
            # Calculate electricity
            elec_usage = self.calculate_electricity_usage(
                electricity_current, electricity_previous
            )
            elec_rate = Decimal(str(electricity_rate or self.DEFAULT_ELECTRICITY_RATE))
            elec_charge = self.calculate_electricity_charge(elec_usage, elec_rate)
            
            # Calculate water with detailed breakdown
            water_usage = self.calculate_water_usage(water_current, water_previous)
            water_charges = self.calculate_water_charge(
                water_usage, 
                water_usage_rate or self.DEFAULT_WATER_USAGE_RATE,
                water_waterborne_tax_rate or self.DEFAULT_WATERBORNE_TAX_RATE
            )
            
            # Calculate subtotal and tax
            subtotal = elec_charge + water_charges["total_water"]
            gst = self.calculate_gst(subtotal)
            
            # Calculate total
            total = subtotal + gst + self.DEFAULT_SURCHARGE
            
            result = {
                "electricity": {
                    "usage": float(elec_usage),
                    "rate": float(elec_rate),
                    "charge": float(elec_charge),
                },
                "water": {
                    "usage": float(water_usage),
                    "usage_rate": float(water_usage_rate or self.DEFAULT_WATER_USAGE_RATE),
                    "waterborne_tax_rate": float(water_waterborne_tax_rate or self.DEFAULT_WATERBORNE_TAX_RATE),
                    "water_usage_charge": float(water_charges["water_usage_charge"]),
                    "waterborne_tax": float(water_charges["waterborne_tax"]),
                    "water_conservation_tax": float(water_charges["water_conservation_tax"]),
                    "total_water": float(water_charges["total_water"]),
                },
                "subtotal": float(subtotal),
                "gst_rate": float(self.DEFAULT_TAX_RATE),
                "gst": float(gst),
                "surcharge": float(self.DEFAULT_SURCHARGE),
                "total": float(total),
            }
            
            logger.info("Bill calculated successfully", {
                "electricity_usage": result["electricity"]["usage"],
                "water_usage": result["water"]["usage"],
                "water_usage_charge": result["water"]["water_usage_charge"],
                "waterborne_tax": result["water"]["waterborne_tax"],
                "conservation_tax": result["water"]["water_conservation_tax"],
                "total": result["total"],
            })
            
            return result
        
        except Exception as e:
            logger.error(f"Error calculating bill breakdown: {str(e)}")
            return None
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    @staticmethod
    def format_currency(value: float) -> str:
        """
        Format value as currency string
        
        Args:
            value: Numeric value
        
        Returns:
            Formatted string (e.g., "12.34")
        
        Example:
            >>> UtilityCalculator.format_currency(12.345)
            '12.35'
            >>> UtilityCalculator.format_currency(None)
            '0.00'
        """
        if value is None or (isinstance(value, float) and value != value):  # NaN check
            return "0.00"
        
        try:
            decimal_value = Decimal(str(value))
            rounded = decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return f"{rounded:.2f}"
        except:
            return "0.00"
    
    @staticmethod
    def validate_readings(
        current: float,
        previous: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate meter readings
        
        Args:
            current: Current month reading
            previous: Previous month reading
        
        Returns:
            (is_valid, error_message)
        
        Example:
            >>> UtilityCalculator.validate_readings(1245, 1200)
            (True, None)
            >>> UtilityCalculator.validate_readings(1100, 1200)
            (False, 'Meter decreased: possible reset detected')
        """
        try:
            curr = Decimal(str(current or 0))
            prev = Decimal(str(previous or 0))
            
            if curr < 0 or prev < 0:
                return False, "Negative reading not allowed"
            
            if curr < prev:
                return False, "Meter decreased: possible reset detected"
            
            return True, None
        
        except Exception as e:
            return False, f"Invalid reading format: {str(e)}"
