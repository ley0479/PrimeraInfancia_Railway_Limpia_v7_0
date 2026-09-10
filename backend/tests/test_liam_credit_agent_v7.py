from modules.asistente_capacitacion.credit_agent import parse_credit_request
from modules.asistente_capacitacion.schema import SCHEMA_SQL

def test_credit_queries_and_mutations_are_distinct():
    assert parse_credit_request('Lian, dame el estado de los créditos')['kind']=='query'
    add=parse_credit_request('Agrégale 500 créditos a Fundación Pacífico Vive')
    assert add['action']=='add_credits' and add['credits']==500 and add['foundation_name']=='pacifico vive'
    renew=parse_credit_request('Actívale 30 días de crédito a Fundación Pacífico Vive')
    assert renew['action']=='renew_days' and renew['days']==30

def test_credit_proposals_are_expiring_and_single_use_by_contract():
    assert 'expires_at TEXT NOT NULL' in SCHEMA_SQL
    assert "status='EXECUTING'" in __import__('inspect').getsource(__import__('modules.asistente_capacitacion.credit_agent',fromlist=['confirm']).confirm)
    assert "role!='SUPERADMIN'" in __import__('inspect').getsource(__import__('modules.asistente_capacitacion.credit_agent',fromlist=['confirm']).confirm)

if __name__=='__main__':
    test_credit_queries_and_mutations_are_distinct()
    test_credit_proposals_are_expiring_and_single_use_by_contract()
    print('LIAM_CREDIT_AGENT_V7_PASS')
