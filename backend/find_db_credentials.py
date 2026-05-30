#!/usr/bin/env python3
"""
Test different credential combinations to find the correct one
"""
import asyncio
import asyncpg

# Try different common credential combinations
CREDENTIAL_OPTIONS = [
    # Expected credentials from config.py
    {
        'host': 'localhost',
        'port': 5432,
        'user': 'raiuser',
        'password': 'raipassword',
        'database': 'rai_platform',
        'name': 'Default config (raiuser/raipassword/rai_platform)'
    },
    # Common Docker setup
    {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'rai_platform',
        'name': 'Docker default (postgres/postgres/rai_platform)'
    },
    # Another common setup
    {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'raipassword',
        'database': 'rai_platform',
        'name': 'Mixed (postgres/raipassword/rai_platform)'
    },
    # Check if database name is different
    {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'postgres',
        'name': 'Default postgres database'
    },
]

async def test_credentials():
    print("="*70)
    print("TESTING POSTGRESQL CREDENTIALS")
    print("="*70)
    print()
    
    working_config = None
    
    for idx, config in enumerate(CREDENTIAL_OPTIONS, 1):
        name = config.pop('name')
        print(f"[{idx}/{len(CREDENTIAL_OPTIONS)}] Testing: {name}")
        print(f"    User: {config['user']} | DB: {config['database']}")
        
        try:
            conn = await asyncpg.connect(**config, timeout=3)
            
            # Get version
            version = await conn.fetchval('SELECT version()')
            
            # List databases
            databases = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false")
            db_list = [db['datname'] for db in databases]
            
            await conn.close()
            
            print(f"    ✅ SUCCESS!")
            print(f"    PostgreSQL: {version.split(',')[0]}")
            print(f"    Available databases: {', '.join(db_list)}")
            print()
            
            working_config = config
            break
            
        except asyncpg.exceptions.InvalidPasswordError:
            print(f"    ❌ Invalid password")
            print()
        except asyncpg.exceptions.InvalidCatalogNameError:
            print(f"    ❌ Database '{config['database']}' does not exist")
            print()
        except asyncpg.exceptions.InvalidAuthorizationSpecificationError:
            print(f"    ❌ User '{config['user']}' does not exist")
            print()
        except asyncpg.exceptions.ConnectionRefusedError:
            print(f"    ❌ Connection refused")
            print()
        except Exception as e:
            print(f"    ❌ Error: {e}")
            print()
    
    print("="*70)
    
    if working_config:
        print("✅ FOUND WORKING CREDENTIALS!")
        print("="*70)
        print()
        print("Your database is accessible with:")
        print(f"  Host:     {working_config['host']}")
        print(f"  Port:     {working_config['port']}")
        print(f"  User:     {working_config['user']}")
        print(f"  Password: {working_config['password']}")
        print(f"  Database: {working_config['database']}")
        print()
        
        # Check if credentials match expected
        if (working_config['user'] != 'raiuser' or 
            working_config['password'] != 'raipassword' or 
            working_config['database'] != 'rai_platform'):
            
            print("⚠️  These credentials DON'T match your config.py!")
            print()
            print("SOLUTION: Create a .env file")
            print("-" * 70)
            
            db_url = f"postgresql+asyncpg://{working_config['user']}:{working_config['password']}@{working_config['host']}:{working_config['port']}/{working_config['database']}"
            
            env_content = f"""# Save this as: D:\\Rubiscape\\Rubiscape\\backend\\.env

DATABASE_URL={db_url}

# Optional: Add other settings
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
"""
            
            print(env_content)
            print("-" * 70)
            print()
            print("To create the .env file:")
            print("  1. Copy the content above")
            print("  2. Save to: D:\\Rubiscape\\Rubiscape\\backend\\.env")
            print("  3. Run: python seed_data.py")
            print()
        else:
            print("✅ Credentials match config.py - you're all set!")
            print()
            print("Next steps:")
            print("  1. python seed_data.py")
            print("  2. python run_initial_analysis.py")
            print()
        
    else:
        print("❌ NO WORKING CREDENTIALS FOUND")
        print("="*70)
        print()
        print("Your PostgreSQL container is running but not accessible.")
        print()
        print("Try these steps:")
        print()
        print("1. Check Docker container environment:")
        print("   docker exec rai_postgres env | findstr POSTGRES")
        print()
        print("2. Access container directly:")
        print("   docker exec -it rai_postgres psql -U postgres")
        print()
        print("3. Or restart with known credentials:")
        print("   docker stop rai_postgres")
        print("   docker rm rai_postgres")
        print("   docker run -d --name rai_postgres \\")
        print("     -e POSTGRES_USER=raiuser \\")
        print("     -e POSTGRES_PASSWORD=raipassword \\")
        print("     -e POSTGRES_DB=rai_platform \\")
        print("     -p 5432:5432 postgres:14")
        print()

if __name__ == "__main__":
    asyncio.run(test_credentials())
