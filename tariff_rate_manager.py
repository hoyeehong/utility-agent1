"""
Tariff Rate Manager - Manages dynamic electricity and water tariff rates

Features:
- Fetch rates from Supabase database
- In-memory caching with configurable TTL
- Fallback to hardcoded defaults
- Complete audit trail of rate changes
"""

from typing import Optional, Dict, List
from decimal import Decimal
from datetime import datetime, date, timedelta
from logger import logger


class TariffRateManager:
    """
    Manages dynamic electricity and water tariff rates
    
    Provides:
    - Cached rate lookups (fast, <10ms)
    - Database persistence (Supabase)
    - Fallback to hardcoded defaults
    - Admin methods for rate updates
    """
    
    def __init__(self, supabase_client=None, cache_ttl_hours: int = 24):
        """
        Initialize tariff rate manager
        
        Args:
            supabase_client: Supabase client instance (optional)
            cache_ttl_hours: Cache time-to-live in hours (default 24)
        """
        self.supabase = supabase_client
        self.cache_ttl_hours = cache_ttl_hours
        self.cache: Dict = {}
        
        # Hardcoded fallback rates
        self.FALLBACK_RATES = {
            'electricity': Decimal("0.2674"),
            'water_usage': Decimal("1.43"),
            'water_waterborne': Decimal("1.09"),
        }
        
        logger.info(f"TariffRateManager initialized (TTL: {cache_ttl_hours}h)")
    
    def get_current_rate(self, rate_type: str, cached: bool = True) -> Decimal:
        """
        Get current tariff rate
        
        Args:
            rate_type: 'electricity', 'water_usage', or 'water_waterborne'
            cached: Use in-memory cache if available (default True)
        
        Returns:
            Decimal rate value, or fallback if unavailable
        
        Example:
            >>> manager = TariffRateManager(supabase)
            >>> rate = manager.get_current_rate('electricity')
            >>> print(rate)
            Decimal('0.2674')
        """
        # Check cache first
        if cached and rate_type in self.cache:
            cached_data = self.cache[rate_type]
            if not self._is_cache_expired(cached_data):
                logger.debug(f"Cache hit for {rate_type}")
                return cached_data['value']
        
        # Try to fetch from database
        rate = self._fetch_from_database(rate_type)
        
        if rate is not None:
            # Cache the result
            self.cache[rate_type] = {
                'value': rate,
                'fetched_at': datetime.now(),
            }
            logger.info(f"Fetched {rate_type} from DB: {rate}")
            return rate
        else:
            # Fall back to hardcoded default
            fallback = self.FALLBACK_RATES.get(rate_type)
            logger.warning(
                f"Using fallback rate for {rate_type}: {fallback} "
                f"(DB fetch failed or unavailable)"
            )
            return fallback
    
    def get_all_current_rates(self) -> Dict[str, Decimal]:
        """
        Get all current rates
        
        Returns:
            Dictionary of all rate types with current values
        
        Example:
            >>> rates = manager.get_all_current_rates()
            >>> print(rates)
            {
                'electricity': Decimal('0.2674'),
                'water_usage': Decimal('1.43'),
                'water_waterborne': Decimal('1.09'),
            }
        """
        return {
            'electricity': self.get_current_rate('electricity'),
            'water_usage': self.get_current_rate('water_usage'),
            'water_waterborne': self.get_current_rate('water_waterborne'),
        }
    
    def _fetch_from_database(self, rate_type: str) -> Optional[Decimal]:
        """
        Fetch current rate from Supabase
        
        Queries for the most recent active rate:
        - effective_date <= today
        - expiry_date >= today OR expiry_date IS NULL
        
        Returns None if DB unavailable or no active rate found
        """
        if not self.supabase:
            logger.debug(f"Supabase client not configured, skipping DB fetch")
            return None
        
        try:
            today = date.today()
            
            # Query active rate for rate_type
            response = self.supabase.table('tariff_rates').select(
                'id, rate_value, effective_date, expiry_date, source'
            ).eq(
                'rate_type', rate_type
            ).lte(
                'effective_date', today.isoformat()
            ).execute()
            
            if response.data:
                # Find most recent active rate
                active_rates = [
                    r for r in response.data
                    if r['expiry_date'] is None or r['expiry_date'] >= today.isoformat()
                ]
                
                if active_rates:
                    # Sort by effective_date descending, get most recent
                    latest = sorted(
                        active_rates,
                        key=lambda x: x['effective_date'],
                        reverse=True
                    )[0]
                    
                    logger.debug(
                        f"Found active rate for {rate_type}: {latest['rate_value']} "
                        f"(effective: {latest['effective_date']}, source: {latest['source']})"
                    )
                    return Decimal(str(latest['rate_value']))
            
            logger.warning(f"No active rate found in DB for {rate_type}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch rate from DB for {rate_type}: {e}")
            return None
    
    def _is_cache_expired(self, cached_data: Dict) -> bool:
        """Check if cached data is older than TTL"""
        if 'fetched_at' not in cached_data:
            return True
        
        age = datetime.now() - cached_data['fetched_at']
        expired = age.total_seconds() > (self.cache_ttl_hours * 3600)
        
        if expired:
            logger.debug(f"Cache expired (age: {age.total_seconds():.0f}s)")
        
        return expired
    
    def update_rate(
        self,
        rate_type: str,
        new_rate: Decimal,
        source: str = "manual",
        effective_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
    ) -> bool:
        """
        Admin method to update tariff rates in database
        
        Args:
            rate_type: 'electricity', 'water_usage', or 'water_waterborne'
            new_rate: New rate value
            source: How rate was obtained (default "manual")
            effective_date: When rate becomes active (default today)
            expiry_date: When rate expires (default None = ongoing)
        
        Returns:
            True if successful, False if failed
        
        Example:
            >>> manager.update_rate(
            ...     'electricity',
            ...     Decimal('0.2750'),
            ...     source='SP Energy Q2 2024',
            ...     effective_date=date(2024, 4, 1),
            ... )
            True
        """
        if not self.supabase:
            logger.error("Cannot update rate: Supabase client not configured")
            return False
        
        if effective_date is None:
            effective_date = date.today()
        
        try:
            # Validate rate type
            if rate_type not in self.FALLBACK_RATES:
                logger.error(f"Invalid rate_type: {rate_type}")
                return False
            
            # Validate rate is positive
            if new_rate <= 0:
                logger.error(f"Rate must be positive, got {new_rate}")
                return False
            
            # Insert new rate into database
            response = self.supabase.table('tariff_rates').insert({
                'rate_type': rate_type,
                'rate_value': str(new_rate),
                'effective_date': effective_date.isoformat(),
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                'source': source,
                'last_updated_at': datetime.now().isoformat(),
            }).execute()
            
            # Invalidate cache
            if rate_type in self.cache:
                del self.cache[rate_type]
                logger.debug(f"Cache invalidated for {rate_type}")
            
            logger.info(
                f"✅ Updated {rate_type} to {new_rate} "
                f"(effective: {effective_date}, source: {source})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to update rate in DB: {e}")
            return False
    
    def get_rate_history(self, rate_type: str, limit: int = 10) -> List[Dict]:
        """
        Get historical rate changes
        
        Args:
            rate_type: 'electricity', 'water_usage', or 'water_waterborne'
            limit: Maximum number of records to return
        
        Returns:
            List of rate records with dates and sources
        
        Example:
            >>> history = manager.get_rate_history('electricity')
            >>> for entry in history:
            ...     print(f"{entry['effective_date']}: {entry['rate_value']} ({entry['source']})")
        """
        if not self.supabase:
            logger.warning("Cannot fetch history: Supabase client not configured")
            return []
        
        try:
            response = self.supabase.table('tariff_rates').select(
                '*'
            ).eq(
                'rate_type', rate_type
            ).order(
                'effective_date', desc=True
            ).limit(limit).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Failed to fetch rate history: {e}")
            return []
    
    def clear_cache(self) -> None:
        """Clear in-memory cache"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_status(self) -> Dict:
        """
        Get current cache status
        
        Returns:
            Dictionary with cache statistics
        
        Example:
            >>> status = manager.get_cache_status()
            >>> print(status)
            {
                'cached_rates': 3,
                'entries': {
                    'electricity': {'cached_at': '2024-06-05T16:30:00', 'age_seconds': 120},
                    ...
                }
            }
        """
        entries = {}
        now = datetime.now()
        
        for rate_type, data in self.cache.items():
            age = (now - data['fetched_at']).total_seconds()
            entries[rate_type] = {
                'value': str(data['value']),
                'cached_at': data['fetched_at'].isoformat(),
                'age_seconds': age,
            }
        
        return {
            'cached_rates': len(entries),
            'entries': entries,
        }
