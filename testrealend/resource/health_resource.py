from flask_restful import Resource
from extension.extension import db


class HealthCheckResource(Resource):
    """Health check endpoint for monitoring and load balancers."""

    def get(self):
        health = {
            'status': 'healthy',
            'service': 'geodata-security-system',
            'version': '1.0.0',
        }

        # Check database connectivity
        try:
            db.session.execute(db.text('SELECT 1'))
            health['database'] = 'connected'
        except Exception as e:
            health['status'] = 'degraded'
            health['database'] = f'error: {str(e)[:100]}'

        status_code = 200 if health['status'] == 'healthy' else 503
        return health, status_code
