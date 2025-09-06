#!/usr/bin/env python3
"""
Test script to demonstrate the modularized Logthon application.

This script shows how the different modules work together and can be used
independently, following the SOLID principles.
"""

import asyncio
from logthon.app import get_app
from logthon.models import LogSubmission
from logthon.storage import log_storage
from logthon.websocket_manager import websocket_manager
from logthon.config import config


async def test_modular_functionality():
    """Test the modular functionality of the Logthon application."""
    
    print("🐍 Testing Modularized Logthon Application")
    print("=" * 50)
    
    # Test 1: Application Creation
    print("\n1. Testing Application Creation...")
    app, initial_entry = get_app()
    print(f"   ✓ Application created successfully")
    print(f"   ✓ Initial log entry: {initial_entry.message}")
    
    # Test 2: Configuration
    print("\n2. Testing Configuration...")
    print(f"   ✓ Server host: {config.server.host}")
    print(f"   ✓ Server port: {config.server.port}")
    print(f"   ✓ Services configured: {config.get_all_service_names()}")
    print(f"   ✓ CDP Client color: {config.get_service_color('cdp-client')}")
    
    # Test 3: Log Storage
    print("\n3. Testing Log Storage...")
    test_log = LogSubmission(
        service='test-service',
        level='INFO',
        message='Test log from modular application',
        metadata={'modular_test': True}
    )
    
    log_entry = log_storage.add_log_entry(test_log)
    print(f"   ✓ Log entry added: {log_entry.message}")
    
    logs = log_storage.get_logs(limit=5)
    print(f"   ✓ Retrieved {len(logs)} log entries")
    
    counts = log_storage.get_log_counts()
    print(f"   ✓ Log counts: {counts}")
    
    # Test 4: WebSocket Manager
    print("\n4. Testing WebSocket Manager...")
    connection_info = websocket_manager.get_connection_info()
    print(f"   ✓ Active connections: {connection_info['active_connections']}")
    print(f"   ✓ Max connections: {connection_info['max_connections']}")
    
    # Test broadcasting without connections (should not fail)
    await websocket_manager.broadcast_log_entry(log_entry)
    print(f"   ✓ WebSocket broadcast test completed")
    
    # Test 5: Storage Info
    print("\n5. Testing Storage Information...")
    storage_info = log_storage.get_storage_info()
    for service, info in storage_info.items():
        print(f"   ✓ {service}: {info['count']} logs (max: {info['max_size']})")
    
    print("\n" + "=" * 50)
    print("🎉 All modular tests passed successfully!")
    print("\nThe application follows SOLID principles:")
    print("  • Single Responsibility: Each module has one clear purpose")
    print("  • Open/Closed: Easy to extend without modifying existing code")
    print("  • Liskov Substitution: Modules can be replaced independently")
    print("  • Interface Segregation: Clean, focused interfaces")
    print("  • Dependency Inversion: High-level modules don't depend on low-level details")


if __name__ == "__main__":
    asyncio.run(test_modular_functionality())
