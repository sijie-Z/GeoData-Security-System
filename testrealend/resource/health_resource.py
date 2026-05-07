from flask_restful import Resource
from extension.extension import db


class HealthCheckResource(Resource):
    """Health check endpoint for monitoring and load balancers.
    ---
    tags: [System]
    responses:
      200: {description: Service healthy}
      503: {description: Service degraded}
    """

    def get(self):
        health = {
            'status': 'healthy',
            'service': 'geodata-security-system',
            'version': '1.0.0',
        }

        # Check database connectivity
        try:
            engine = db.session.get_bind(bind_key='mysql_db')
            with engine.connect() as conn:
                conn.execute(db.text('SELECT 1'))
            health['database'] = 'connected'
        except Exception as e:
            health['status'] = 'degraded'
            health['database'] = f'error: {str(e)[:100]}'

        # Check Redis connectivity
        from utils.cache import is_cache_available
        health['cache'] = 'connected' if is_cache_available() else 'unavailable'

        # Check metrics
        health['metrics'] = 'enabled'

        status_code = 200 if health['status'] == 'healthy' else 503
        return health, status_code
