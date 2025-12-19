import time

import bcrypt
import pytest
from commondao import connect

from lessweb import Bridge
from lessweb.ioc import APP_CONFIG_KEY
from lessweb.utils import absolute_ref
from shared.error_middleware import error_middleware
from shared.jwt_gateway import JwtGateway, JwtGatewayMiddleware
from shared.lessweb_commondao import MysqlConn, commondao_bean
from shared.redis_plugin import redis_bean


class TestAdminController:
    """Admin controller e2e tests"""

    @pytest.fixture
    async def app_client(self, aiohttp_client):
        """Create test app with real database connection"""
        # Create Bridge instance with real config
        bridge = Bridge('config')
        bridge.beans(commondao_bean, redis_bean)
        # Register middlewares explicitly (not via scan)
        # Order matters: error_middleware should be first to catch exceptions
        bridge.middlewares(error_middleware, JwtGatewayMiddleware, MysqlConn)
        # Scan 'src' will auto-load JwtGateway from admin_controller.py
        bridge.scan('src')
        bridge.ready()

        client = await aiohttp_client(bridge.app)
        return client

    @pytest.fixture
    async def test_admin_cleanup(self, app_client):
        """Setup and cleanup test admin data"""
        client = app_client
        timestamp = str(int(time.time() * 1000))

        # Track created test admin usernames for cleanup
        created_usernames = []

        def track_creation(username: str):
            """Helper to track test admin for cleanup"""
            if username not in created_usernames:
                created_usernames.append(username)

        # Get database config
        mysql_config = client.app[APP_CONFIG_KEY]['mysql'].copy()
        mysql_config['port'] = int(mysql_config['port'])

        # Cleanup before tests
        async with connect(**mysql_config) as db:
            await db.execute_mutation(
                'DELETE FROM tbl_admin WHERE username LIKE :pattern',
                {'pattern': 'test_admin_%'}
            )

        yield {
            'timestamp': timestamp,
            'client': client,
            'track_creation': track_creation,
            'created_usernames': created_usernames,
            'mysql_config': mysql_config
        }

        # Cleanup after tests
        async with connect(**mysql_config) as db:
            for username in created_usernames:
                await db.execute_mutation(
                    'DELETE FROM tbl_admin WHERE username = :username',
                    {'username': username}
                )

    @pytest.fixture
    async def create_test_admin(self, test_admin_cleanup):
        """Create a test admin user in database"""
        test_data = test_admin_cleanup
        timestamp = test_data['timestamp']
        username = f"test_admin_{timestamp}"
        password = "test_password_123"

        # Hash password using bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert test admin into database
        mysql_config = test_data['mysql_config']
        async with connect(**mysql_config) as db:
            # Use execute_mutation with explicit SQL to insert admin
            await db.execute_mutation(
                '''INSERT INTO tbl_admin (username, password_hash, email, is_active)
                   VALUES (:username, :password_hash, :email, :is_active)''',
                {
                    'username': username,
                    'password_hash': password_hash,
                    'email': f"{username}@example.com",
                    'is_active': 1  # 1 for active, 0 for inactive
                }
            )
            # Commit the transaction to ensure data is persisted
            await db.commit()
            # Get the last inserted ID using lastrowid method
            admin_id = db.lastrowid()

        test_data['track_creation'](username)

        return {
            **test_data,
            'username': username,
            'password': password,
            'admin_id': admin_id
        }

    @pytest.mark.asyncio
    async def test_login_admin_success(self, create_test_admin):
        """Test admin login with correct credentials"""
        test_data = create_test_admin
        client = test_data['client']
        username = test_data['username']
        password = test_data['password']

        # Login with correct credentials
        resp = await client.post('/login/admin', json={
            'username': username,
            'password': password
        })

        assert resp.status == 200
        data = await resp.json()

        # Verify response structure
        assert 'token' in data
        assert 'admin_id' in data
        assert 'username' in data

        # Verify response content
        assert data['username'] == username
        assert data['admin_id'] == test_data['admin_id']
        assert isinstance(data['token'], str)
        assert len(data['token']) > 0

    @pytest.mark.asyncio
    async def test_login_admin_invalid_username(self, test_admin_cleanup):
        """Test admin login with invalid username"""
        client = test_admin_cleanup['client']

        # Login with non-existent username
        resp = await client.post('/login/admin', json={
            'username': 'nonexistent_admin',
            'password': 'any_password'
        })

        assert resp.status == 400
        resp_text = await resp.text()
        assert 'Invalid username or password' in resp_text

    @pytest.mark.asyncio
    async def test_login_admin_invalid_password(self, create_test_admin):
        """Test admin login with wrong password"""
        test_data = create_test_admin
        client = test_data['client']
        username = test_data['username']

        # Login with wrong password
        resp = await client.post('/login/admin', json={
            'username': username,
            'password': 'wrong_password'
        })

        assert resp.status == 400
        resp_text = await resp.text()
        assert 'Invalid username or password' in resp_text

    @pytest.mark.asyncio
    async def test_login_admin_inactive_account(self, test_admin_cleanup):
        """Test admin login with inactive account"""
        test_data = test_admin_cleanup
        client = test_data['client']
        timestamp = test_data['timestamp']
        username = f"test_admin_inactive_{timestamp}"
        password = "test_password_123"

        # Create inactive admin
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        mysql_config = test_data['mysql_config']

        async with connect(**mysql_config) as db:
            await db.execute_mutation(
                '''INSERT INTO tbl_admin (username, password_hash, email, is_active)
                   VALUES (:username, :password_hash, :email, :is_active)''',
                {
                    'username': username,
                    'password_hash': password_hash,
                    'email': f"{username}@example.com",
                    'is_active': 0  # 0 for inactive, 1 for active
                }
            )
            # Commit the transaction to ensure data is persisted
            await db.commit()

        test_data['track_creation'](username)

        # Try to login with inactive account
        resp = await client.post('/login/admin', json={
            'username': username,
            'password': password
        })

        assert resp.status == 400
        resp_text = await resp.text()
        assert 'Account is not active' in resp_text

    @pytest.mark.asyncio
    async def test_get_admin_me_success(self, create_test_admin):
        """Test getting current admin info with valid token"""
        test_data = create_test_admin
        client = test_data['client']
        username = test_data['username']
        password = test_data['password']

        # First login to get token
        login_resp = await client.post('/login/admin', json={
            'username': username,
            'password': password
        })
        assert login_resp.status == 200
        login_data = await login_resp.json()
        token = login_data['token']

        # Get current admin info
        resp = await client.get('/admin/me', headers={
            'Authorization': f'Bearer {token}'
        })

        assert resp.status == 200
        data = await resp.json()

        # Verify response structure
        assert 'id' in data
        assert 'username' in data
        assert 'email' in data
        assert 'is_active' in data
        assert 'create_time' in data
        assert 'update_time' in data

        # Verify response content
        assert data['id'] == test_data['admin_id']
        assert data['username'] == username
        assert data['email'] == f"{username}@example.com"
        assert data['is_active'] is True

        # Verify password_hash is NOT in response
        assert 'password_hash' not in data

    @pytest.mark.asyncio
    async def test_get_admin_me_no_token(self, test_admin_cleanup):
        """Test getting current admin info without token"""
        client = test_admin_cleanup['client']

        # Try to access without token
        resp = await client.get('/admin/me')

        # Should be unauthorized (401)
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_get_admin_me_invalid_token(self, test_admin_cleanup):
        """Test getting current admin info with invalid token"""
        client = test_admin_cleanup['client']

        # Try to access with invalid token
        resp = await client.get('/admin/me', headers={
            'Authorization': 'Bearer invalid_token_here'
        })

        # Should be unauthorized (401)
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_get_admin_me_expired_token(self, create_test_admin):
        """Test getting current admin info with expired token"""
        test_data = create_test_admin
        client = test_data['client']

        # Get JwtGateway from app to create expired token
        jwt_gateway: JwtGateway = client.app[absolute_ref(JwtGateway)]

        # Create token that expires immediately
        expired_token = jwt_gateway.encrypt_jwt(
            user_id=str(test_data['admin_id']),
            subject='ADMIN',
            expire_at=int(time.time()) - 3600  # Expired 1 hour ago
        )

        # Try to access with expired token
        resp = await client.get('/admin/me', headers={
            'Authorization': f'Bearer {expired_token}'
        })

        # Should be unauthorized (401)
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_get_admin_me_after_logout(self, create_test_admin):
        """Test getting current admin info after logout"""
        test_data = create_test_admin
        client = test_data['client']
        username = test_data['username']
        password = test_data['password']

        # Login to get token
        login_resp = await client.post('/login/admin', json={
            'username': username,
            'password': password
        })
        assert login_resp.status == 200
        login_data = await login_resp.json()
        token = login_data['token']

        # Get JwtGateway to perform logout
        jwt_gateway: JwtGateway = client.app[absolute_ref(JwtGateway)]

        # Logout by deleting Redis key
        await jwt_gateway.logout(
            user_id=str(test_data['admin_id']),
            user_role='ADMIN'
        )

        # Try to access after logout
        resp = await client.get('/admin/me', headers={
            'Authorization': f'Bearer {token}'
        })

        # Should be unauthorized (401) because Redis login state is gone
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_default_admin_credentials(self, test_admin_cleanup):
        """Test login with default admin credentials from migration"""
        client = test_admin_cleanup['client']

        # Try to login with default admin (username: admin, password: admin123)
        resp = await client.post('/login/admin', json={
            'username': 'admin',
            'password': 'admin123'
        })

        # Should succeed if the default admin exists
        assert resp.status == 200
        data = await resp.json()
        assert data['username'] == 'admin'
        assert 'token' in data

    @pytest.mark.asyncio
    async def test_jwt_token_validation_flow(self, create_test_admin):
        """Test complete JWT token validation flow"""
        test_data = create_test_admin
        client = test_data['client']
        username = test_data['username']
        password = test_data['password']

        # Step 1: Login
        login_resp = await client.post('/login/admin', json={
            'username': username,
            'password': password
        })
        assert login_resp.status == 200
        login_data = await login_resp.json()
        token = login_data['token']

        # Step 2: Verify Redis login state exists
        jwt_gateway: JwtGateway = client.app[absolute_ref(JwtGateway)]
        is_logged_in = await jwt_gateway.is_logged_in(
            user_id=str(test_data['admin_id']),
            user_role='ADMIN'
        )
        assert is_logged_in is True

        # Step 3: Access protected endpoint successfully
        resp1 = await client.get('/admin/me', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp1.status == 200

        # Step 4: Logout
        await jwt_gateway.logout(
            user_id=str(test_data['admin_id']),
            user_role='ADMIN'
        )

        # Step 5: Verify Redis login state is gone
        is_logged_in = await jwt_gateway.is_logged_in(
            user_id=str(test_data['admin_id']),
            user_role='ADMIN'
        )
        assert is_logged_in is False

        # Step 6: Access protected endpoint fails after logout
        resp2 = await client.get('/admin/me', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp2.status == 401

    @pytest.mark.asyncio
    async def test_multiple_login_sessions(self, create_test_admin):
        """Test that multiple logins maintain the same login state"""
        test_data = create_test_admin
        client = test_data['client']
        username = test_data['username']
        password = test_data['password']

        # First login
        resp1 = await client.post('/login/admin', json={
            'username': username,
            'password': password
        })
        assert resp1.status == 200
        data1 = await resp1.json()
        token1 = data1['token']

        # Second login (same user)
        resp2 = await client.post('/login/admin', json={
            'username': username,
            'password': password
        })
        assert resp2.status == 200
        data2 = await resp2.json()
        token2 = data2['token']

        # Both tokens should be valid
        me_resp1 = await client.get('/admin/me', headers={
            'Authorization': f'Bearer {token1}'
        })
        assert me_resp1.status == 200

        me_resp2 = await client.get('/admin/me', headers={
            'Authorization': f'Bearer {token2}'
        })
        assert me_resp2.status == 200

        # Verify both return same admin info
        me_data1 = await me_resp1.json()
        me_data2 = await me_resp2.json()
        assert me_data1['id'] == me_data2['id']
        assert me_data1['username'] == me_data2['username']
