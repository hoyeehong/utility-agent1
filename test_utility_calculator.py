"""
Unit tests for UtilityCalculator
Tests all calculation methods with real Singapore utility rates
"""

import unittest
from decimal import Decimal
from utility_calculator import UtilityCalculator


class TestUtilityCalculator(unittest.TestCase):
    """Test suite for UtilityCalculator"""
    
    def setUp(self):
        """Initialize calculator for each test"""
        self.calc = UtilityCalculator()
    
    # =========================================================================
    # ELECTRICITY TESTS
    # =========================================================================
    
    def test_electricity_usage_normal(self):
        """Test normal electricity usage calculation"""
        usage = self.calc.calculate_electricity_usage(1245.5, 1200.0)
        self.assertEqual(usage, Decimal("45.50"))
    
    def test_electricity_usage_zero(self):
        """Test when no electricity used"""
        usage = self.calc.calculate_electricity_usage(1200.0, 1200.0)
        self.assertEqual(usage, Decimal("0.00"))
    
    def test_electricity_usage_negative(self):
        """Test negative usage (meter reset) returns zero"""
        usage = self.calc.calculate_electricity_usage(1100.0, 1200.0)
        self.assertEqual(usage, Decimal("0.00"))
    
    def test_electricity_usage_with_none(self):
        """Test handling of None values"""
        usage = self.calc.calculate_electricity_usage(1245.5, None)
        self.assertEqual(usage, Decimal("1245.50"))
    
    def test_electricity_charge_calculation(self):
        """Test electricity charge with default rate"""
        charge = self.calc.calculate_electricity_charge(45.5)
        expected = Decimal("45.5") * Decimal("0.2674")
        self.assertEqual(charge, expected.quantize(Decimal("0.01")))
    
    def test_electricity_charge_custom_rate(self):
        """Test electricity charge with custom rate"""
        charge = self.calc.calculate_electricity_charge(45.5, 0.30)
        self.assertEqual(charge, Decimal("13.65"))
    
    def test_electricity_charge_zero_usage(self):
        """Test charge with zero usage"""
        charge = self.calc.calculate_electricity_charge(0)
        self.assertEqual(charge, Decimal("0.00"))
    
    # =========================================================================
    # WATER TESTS
    # =========================================================================
    
    def test_water_usage_normal(self):
        """Test normal water usage calculation"""
        usage = self.calc.calculate_water_usage(58.5, 50.0)
        self.assertEqual(usage, Decimal("8.50"))
    
    def test_water_usage_zero(self):
        """Test when no water used"""
        usage = self.calc.calculate_water_usage(50.0, 50.0)
        self.assertEqual(usage, Decimal("0.00"))
    
    def test_water_usage_negative(self):
        """Test negative usage (meter reset) returns zero"""
        usage = self.calc.calculate_water_usage(40.0, 50.0)
        self.assertEqual(usage, Decimal("0.00"))
    
    def test_water_charge_with_breakdown(self):
        """Test water charge with new breakdown structure"""
        charges = self.calc.calculate_water_charge(8.3, 1.43, 1.09)
        
        self.assertEqual(charges["water_usage_charge"], Decimal("11.87"))
        self.assertEqual(charges["waterborne_tax"], Decimal("9.05"))
        self.assertAlmostEqual(float(charges["water_conservation_tax"]), 5.94, places=1)
        self.assertAlmostEqual(float(charges["total_water"]), 26.85, places=1)
    
    def test_water_charge_zero_usage(self):
        """Test charge with zero usage"""
        charges = self.calc.calculate_water_charge(0)
        self.assertEqual(charges["total_water"], Decimal("0.00"))
    
    def test_water_tax_calculation(self):
        """Test water tax (50% of base)"""
        tax = self.calc.calculate_water_tax(10.0)
        self.assertEqual(tax, Decimal("5.00"))
    
    def test_water_tax_zero(self):
        """Test tax with zero base"""
        tax = self.calc.calculate_water_tax(0)
        self.assertEqual(tax, Decimal("0.00"))
    
    # =========================================================================
    # TAX & SURCHARGE TESTS
    # =========================================================================
    
    def test_gst_calculation(self):
        """Test GST (9%) calculation"""
        gst = self.calc.calculate_gst(100.0, 0.09)
        self.assertEqual(gst, Decimal("9.00"))
    
    def test_gst_default_rate(self):
        """Test GST with default rate"""
        gst = self.calc.calculate_gst(100.0)
        self.assertEqual(gst, Decimal("9.00"))
    
    def test_gst_zero_subtotal(self):
        """Test GST with zero subtotal"""
        gst = self.calc.calculate_gst(0)
        self.assertEqual(gst, Decimal("0.00"))
    
    def test_total_bill_calculation(self):
        """Test total bill with tax and surcharge"""
        # Electricity: 12.16, Water: 30.94, Water tax: 5.00
        # Subtotal: 48.10
        # Tax (9%): 4.33
        # Total: 48.10 + 4.33 + 0.50 = 52.93
        total = self.calc.calculate_total_bill(12.16, 30.94, 5.00)
        self.assertAlmostEqual(float(total), 52.93, places=1)
    
    def test_total_bill_custom_surcharge(self):
        """Test total bill with custom surcharge"""
        total = self.calc.calculate_total_bill(10.0, 10.0, 0, 0.09, 1.00)
        # Subtotal: 20.00, Tax: 1.80, Total: 21.80 + 1.00 = 22.80
        self.assertAlmostEqual(float(total), 22.80, places=1)
    
    # =========================================================================
    # FULL BILL BREAKDOWN TESTS
    # =========================================================================
    
    def test_bill_breakdown_full_scenario(self):
        """Test complete bill breakdown with all fields"""
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=1245.5,
            electricity_previous=1200.0,
            electricity_rate=0.2674,
            water_current=58.5,
            water_previous=50.0,
            water_usage_rate=1.43,
            water_waterborne_tax_rate=1.09,
        )
        
        self.assertIsNotNone(bill)
        self.assertEqual(bill["electricity"]["usage"], 45.5)
        self.assertEqual(bill["water"]["usage"], 8.5)
        self.assertIn("total", bill)
        self.assertIn("gst", bill)
        self.assertIn("water_usage_charge", bill["water"])
        self.assertIn("waterborne_tax", bill["water"])
        self.assertIn("water_conservation_tax", bill["water"])
    
    def test_bill_breakdown_electricity_only(self):
        """Test bill breakdown with only electricity"""
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=1100.0,
            electricity_previous=1000.0,
        )
        
        self.assertIsNotNone(bill)
        self.assertEqual(bill["electricity"]["usage"], 100.0)
        self.assertEqual(bill["water"]["usage"], 0.0)
    
    def test_bill_breakdown_zero_readings(self):
        """Test bill breakdown with zero readings"""
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=0,
            electricity_previous=0,
            water_current=0,
            water_previous=0,
        )
        
        self.assertIsNotNone(bill)
        self.assertEqual(bill["total"], 0.50)  # Only surcharge
    
    # =========================================================================
    # UTILITY METHODS TESTS
    # =========================================================================
    
    def test_format_currency_normal(self):
        """Test currency formatting"""
        formatted = UtilityCalculator.format_currency(12.345)
        self.assertEqual(formatted, "12.35")
    
    def test_format_currency_none(self):
        """Test currency formatting with None"""
        formatted = UtilityCalculator.format_currency(None)
        self.assertEqual(formatted, "0.00")
    
    def test_format_currency_zero(self):
        """Test currency formatting with zero"""
        formatted = UtilityCalculator.format_currency(0)
        self.assertEqual(formatted, "0.00")
    
    def test_format_currency_large_number(self):
        """Test currency formatting with large number"""
        formatted = UtilityCalculator.format_currency(1234.567)
        self.assertEqual(formatted, "1234.57")
    
    def test_validate_readings_normal(self):
        """Test validation with normal readings"""
        is_valid, error = UtilityCalculator.validate_readings(1245, 1200)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_readings_meter_reset(self):
        """Test validation with meter reset"""
        is_valid, error = UtilityCalculator.validate_readings(1100, 1200)
        self.assertFalse(is_valid)
        self.assertIn("decreased", error.lower())
    
    def test_validate_readings_negative(self):
        """Test validation with negative reading"""
        is_valid, error = UtilityCalculator.validate_readings(-100, 1200)
        self.assertFalse(is_valid)
        self.assertIn("negative", error.lower())
    
    def test_validate_readings_same(self):
        """Test validation with same readings"""
        is_valid, error = UtilityCalculator.validate_readings(1200, 1200)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    # =========================================================================
    # REAL-WORLD SCENARIOS
    # =========================================================================
    
    def test_scenario_first_month_estimate(self):
        """
        Scenario: First month - estimating from manual baseline
        Readings: Elec 1200 kWh, Water 50 m³ (baseline)
        """
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=1200,
            electricity_previous=0,  # First month
            water_current=50,
            water_previous=0,  # First month
        )
        
        self.assertIsNotNone(bill)
        self.assertEqual(bill["electricity"]["usage"], 1200.0)
        self.assertEqual(bill["water"]["usage"], 50.0)
    
    def test_scenario_normal_billing(self):
        """
        Scenario: Normal second month billing
        """
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=1250,
            electricity_previous=1200,
            water_current=60,
            water_previous=50,
        )
        
        self.assertIsNotNone(bill)
        self.assertEqual(bill["electricity"]["usage"], 50.0)
        self.assertEqual(bill["water"]["usage"], 10.0)
        self.assertGreater(bill["total"], 0)
    
    def test_scenario_meter_reset_detected(self):
        """
        Scenario: Meter reset detected (no error, but usage is 0)
        """
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=100,
            electricity_previous=1200,  # Meter reset
            water_current=10,
            water_previous=50,  # Meter reset
        )
        
        self.assertIsNotNone(bill)
        self.assertEqual(bill["electricity"]["usage"], 0.0)  # Flagged as 0
        self.assertEqual(bill["water"]["usage"], 0.0)  # Flagged as 0
    
    def test_scenario_high_usage_month(self):
        """
        Scenario: High usage month (e.g., summer)
        """
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=1300,
            electricity_previous=1150,
            water_current=80,
            water_previous=50,
        )
        
        self.assertIsNotNone(bill)
        self.assertEqual(bill["electricity"]["usage"], 150.0)
        self.assertEqual(bill["water"]["usage"], 30.0)
        self.assertGreater(bill["total"], 50)  # Should be significant


class TestIntegrationWithOrchestratorData(unittest.TestCase):
    """Test calculator with data from orchestrator workflow"""
    
    def setUp(self):
        self.calc = UtilityCalculator()
    
    def test_with_ocr_extracted_readings(self):
        """
        Simulate OCR extracted readings from meter images
        """
        # Simulated OCR results
        ocr_readings = {
            "electricity": 1245.5,
            "water": 58.5,
        }
        
        bill = self.calc.calculate_bill_breakdown(
            electricity_current=ocr_readings["electricity"],
            electricity_previous=1200.0,
            water_current=ocr_readings["water"],
            water_previous=50.0,
        )
        
        self.assertIsNotNone(bill)
        self.assertIn("total", bill)
    
    def test_with_pdf_extracted_readings(self):
        """
        Simulate PDF extracted readings from SP bill
        """
        # Simulated PDF extraction results
        pdf_readings = {
            "electricity_current": 1245.5,
            "electricity_previous": 1200.0,
            "water_current": 58.5,
            "water_previous": 50.0,
        }
        
        bill = self.calc.calculate_bill_breakdown(**pdf_readings)
        
        self.assertIsNotNone(bill)
        self.assertGreater(bill["total"], 0)


if __name__ == "__main__":
    unittest.main()
