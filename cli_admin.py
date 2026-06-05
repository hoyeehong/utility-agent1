#!/usr/bin/env python3
"""
CLI Admin Tool - Manage tariff rates

Usage:
    python cli_admin.py get-rates              # Show current rates
    python cli_admin.py update-rate electricity 0.2750
    python cli_admin.py history electricity
    python cli_admin.py cache-status
"""

import sys
import os
from decimal import Decimal
from datetime import date
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tariff_rate_manager import TariffRateManager
from logger import logger


def get_supabase_client():
    """Initialize Supabase client"""
    from supabase import create_client
    import os
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_KEY environment variables not set")
        return None
    
    return create_client(url, key)


def show_current_rates():
    """Display current rates"""
    supabase = get_supabase_client()
    if not supabase:
        return
    
    manager = TariffRateManager(supabase)
    rates = manager.get_all_current_rates()
    
    print("\n" + "=" * 70)
    print("CURRENT TARIFF RATES")
    print("=" * 70)
    
    print(f"\n🔌 Electricity Rate:      ${rates['electricity']:.4f} per kWh")
    print(f"💧 Water Usage Rate:      ${rates['water_usage']:.2f} per m³")
    print(f"💧 Waterborne Tax Rate:   ${rates['water_waterborne']:.2f} per m³")
    
    print("\n" + "=" * 70)


def update_rate(rate_type: str, new_rate_value: float, source: Optional[str] = None):
    """Update a tariff rate"""
    supabase = get_supabase_client()
    if not supabase:
        return
    
    manager = TariffRateManager(supabase)
    
    # Validate rate type
    valid_types = ['electricity', 'water_usage', 'water_waterborne']
    if rate_type not in valid_types:
        print(f"❌ Invalid rate type: {rate_type}")
        print(f"   Valid types: {', '.join(valid_types)}")
        return
    
    new_rate = Decimal(str(new_rate_value))
    
    # Use provided source or prompt user
    if source is None:
        source = input("Enter source (e.g., 'SP Energy Q2 2024'): ").strip()
        if not source:
            source = "manual"
    
    # Confirm before updating
    current_rates = manager.get_all_current_rates()
    old_rate = current_rates.get(rate_type)
    
    print("\n" + "=" * 70)
    print(f"UPDATE RATE: {rate_type.replace('_', ' ').title()}")
    print("=" * 70)
    print(f"Old rate:  ${old_rate:.4f}" if rate_type == 'electricity' else f"Old rate:  ${old_rate:.2f}")
    print(f"New rate:  ${new_rate:.4f}" if rate_type == 'electricity' else f"New rate:  ${new_rate:.2f}")
    print(f"Source:    {source}")
    print(f"Date:      {date.today()}")
    
    confirm = input("\n✓ Confirm update? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Update cancelled")
        return
    
    success = manager.update_rate(
        rate_type,
        new_rate,
        source=source,
        effective_date=date.today()
    )
    
    if success:
        print(f"\n✅ Rate updated successfully!")
        print(f"   {rate_type.replace('_', ' ').title()}: ${new_rate:.4f}")
    else:
        print("❌ Failed to update rate")


def show_rate_history(rate_type: str):
    """Display rate change history"""
    supabase = get_supabase_client()
    if not supabase:
        return
    
    manager = TariffRateManager(supabase)
    history = manager.get_rate_history(rate_type, limit=20)
    
    if not history:
        print(f"❌ No history found for {rate_type}")
        return
    
    print("\n" + "=" * 70)
    print(f"RATE HISTORY: {rate_type.replace('_', ' ').title()}")
    print("=" * 70)
    print(f"{'Date':<12} {'Rate':<12} {'Source':<25} {'Status':<15}")
    print("-" * 70)
    
    for entry in history:
        effective = entry['effective_date']
        expiry = entry['expiry_date']
        rate = entry['rate_value']
        source = entry['source'][:24]
        
        # Determine status
        today = date.today().isoformat()
        if expiry is None:
            status = "ACTIVE" if effective <= today else "PENDING"
        else:
            if today < effective:
                status = "PENDING"
            elif today <= expiry:
                status = "ACTIVE"
            else:
                status = "EXPIRED"
        
        print(f"{effective:<12} ${float(rate):<11.4f} {source:<25} {status:<15}")
    
    print("=" * 70)


def show_cache_status():
    """Display cache status"""
    supabase = get_supabase_client()
    if not supabase:
        return
    
    manager = TariffRateManager(supabase)
    status = manager.get_cache_status()
    
    print("\n" + "=" * 70)
    print("CACHE STATUS")
    print("=" * 70)
    print(f"Cached rates: {status['cached_rates']}")
    
    if status['entries']:
        print("\nCached entries:")
        for rate_type, data in status['entries'].items():
            age_sec = data['age_seconds']
            age_min = age_sec / 60
            
            if age_min < 1:
                age_str = f"{age_sec:.0f}s ago"
            elif age_min < 60:
                age_str = f"{age_min:.0f}m ago"
            else:
                age_str = f"{age_min/60:.1f}h ago"
            
            print(f"  {rate_type:<20} ${data['value']:<10} {age_str}")
    
    print("=" * 70)


def clear_cache():
    """Clear cache"""
    supabase = get_supabase_client()
    if not supabase:
        return
    
    manager = TariffRateManager(supabase)
    manager.clear_cache()
    print("✅ Cache cleared")


def show_help():
    """Display help message"""
    print("""
Tariff Rate Manager CLI
=======================

Usage:
    python cli_admin.py COMMAND [ARGS]

Commands:
    get-rates              Show current rates
    update-rate TYPE RATE  Update a rate (TYPE: electricity, water_usage, water_waterborne)
    history TYPE           Show rate change history
    cache-status           Show cache status
    clear-cache            Clear in-memory cache
    help                   Show this help message

Examples:
    # Show current rates
    python cli_admin.py get-rates
    
    # Update electricity rate to 0.2750 per kWh
    python cli_admin.py update-rate electricity 0.2750
    
    # View water usage rate history
    python cli_admin.py history water_usage
    
    # Check cache status
    python cli_admin.py cache-status

Environment Variables:
    SUPABASE_URL           Supabase project URL
    SUPABASE_KEY           Supabase API key

Rate Types:
    electricity            SP Energy rate (SGD/kWh)
    water_usage            PUB water usage rate (SGD/m³)
    water_waterborne       PUB waterborne tax rate (SGD/m³)
""")


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "get-rates":
        show_current_rates()
    
    elif command == "update-rate":
        if len(sys.argv) < 4:
            print("❌ Usage: python cli_admin.py update-rate TYPE RATE")
            print("   Example: python cli_admin.py update-rate electricity 0.2750")
            return
        
        rate_type = sys.argv[2]
        try:
            new_rate = float(sys.argv[3])
        except ValueError:
            print(f"❌ Invalid rate value: {sys.argv[3]}")
            return
        
        source = sys.argv[4] if len(sys.argv) > 4 else None
        update_rate(rate_type, new_rate, source)
    
    elif command == "history":
        if len(sys.argv) < 3:
            print("❌ Usage: python cli_admin.py history TYPE")
            print("   Example: python cli_admin.py history electricity")
            return
        
        rate_type = sys.argv[2]
        show_rate_history(rate_type)
    
    elif command == "cache-status":
        show_cache_status()
    
    elif command == "clear-cache":
        clear_cache()
    
    elif command == "help" or command == "-h" or command == "--help":
        show_help()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("   Run 'python cli_admin.py help' for usage information")


if __name__ == "__main__":
    main()
