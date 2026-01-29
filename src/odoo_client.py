import xmlrpc.client
import ssl
from .config import ODOO_URL, logger

class OdooClient:
    def __init__(self):
        self.url = ODOO_URL
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')

    def authenticate(self, db, username, password):
        try:
            uid = self.common.authenticate(db, username, password, {})
            return uid
        except Exception as e:
            logger.error(f"Odoo Auth Error: {e}")
            return None

    def search_prs(self, db, uid, password, domain, offset=0, limit=5):
        try:
            # Fields as defined in PRD (partner_id removed as it doesn't exist)
            fields = ['name', 'requested_by', 'state', 'date_start', 'estimated_cost']
            return self.models.execute_kw(
                db, uid, password,
                'purchase.request', 'search_read',
                [domain],
                {
                    'fields': fields,
                    'limit': limit,
                    'offset': offset,
                    'order': 'id desc'
                }
            )
        except Exception as e:
            logger.error(f"Odoo Search Error: {e}")
            raise e

    def get_pr_details(self, db, uid, password, pr_id):
        try:
            fields = [
                'name', 'description', 'requested_by', 'assigned_to', 
                'date_start', 'estimated_cost', 
                'currency_id', 'state', 'company_id',
                'line_ids'  # Fetch IDs of the lines
            ]
            results = self.models.execute_kw(
                db, uid, password,
                'purchase.request', 'read',
                [[int(pr_id)]],
                {'fields': fields}
            )
            
            if not results:
                return None
            
            pr = results[0]
            
            # Fetch line details if any
            line_ids = pr.get('line_ids', [])
            if line_ids:
                line_fields = ['product_id', 'name', 'product_qty', 'estimated_cost']
                lines = self.models.execute_kw(
                    db, uid, password,
                    'purchase.request.line', 'read',
                    [line_ids],
                    {'fields': line_fields}
                )
                pr['lines'] = lines
            else:
                pr['lines'] = []

            return pr
        except Exception as e:
            logger.error(f"Odoo Read Error: {e}")
            return None

odoo_client = OdooClient()
