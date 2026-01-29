from datetime import datetime
import dateparser
import re

def parse_query(user_input: str) -> dict:
    """
    Parse user query into Odoo domain and metadata.
    Ref: PRD Appendix A
    """
    if not user_input:
        return {'domain': [], 'filters_applied': {}, 'keywords': []}

    tokens = user_input.split()
    domain = []
    keywords = []
    filters = {}
    
    for token in tokens:
        if ':' in token:
            try:
                key, value = token.split(':', 1)
                
                if key == 'status':
                    # Odoo purchase.request state mapping if needed, or exact match
                    domain.append(('state', '=', value.lower()))
                    filters['status'] = value
                    
                elif key == 'vendor':
                    # domain.append(('partner_id.name', 'ilike', value))
                    # filters['vendor'] = value
                    pass # Field not in model
                    
                elif key == 'requester':
                    domain.append(('requested_by.name', 'ilike', value))
                    filters['requester'] = value

                elif key == 'date':
                    if '..' in value:
                        start_str, end_str = value.split('..')
                        start = dateparser.parse(start_str)
                        end = dateparser.parse(end_str)
                        if start and end:
                            domain.append(('date_start', '>=', start.strftime('%Y-%m-%d')))
                            domain.append(('date_start', '<=', end.strftime('%Y-%m-%d')))
                            filters['date'] = f"{start_str} to {end_str}"
                    else:
                        date = dateparser.parse(value)
                        if date:
                            domain.append(('date_start', '=', date.strftime('%Y-%m-%d')))
                            filters['date'] = value
                            
                elif key == 'amount':
                    if '..' in value:
                        min_amt, max_amt = value.split('..')
                        domain.append(('estimated_cost', '>=', float(min_amt)))
                        domain.append(('estimated_cost', '<=', float(max_amt)))
                        filters['amount'] = f"{min_amt} to {max_amt}"
                    elif value.startswith('>'):
                         domain.append(('estimated_cost', '>', float(value[1:])))
                         filters['amount'] = value
                    elif value.startswith('<'):
                         domain.append(('estimated_cost', '<', float(value[1:])))
                         filters['amount'] = value
                    else:
                         domain.append(('estimated_cost', '=', float(value)))
                         filters['amount'] = value
            except ValueError:
                continue
                    
        else:
            keywords.append(token)
    
    # Add keyword search (OR logic on name/description)
    if keywords:
        search_term = " ".join(keywords)
        # Odoo Polish notation for OR. 
        domain.append('|')
        domain.append(('name', 'ilike', search_term))
        domain.append(('description', 'ilike', search_term))
    
    return {
        'domain': domain,
        'keywords': keywords,
        'filters_applied': filters
    }
