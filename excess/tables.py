"""
Definitions of Redshift tables used by duolingo-jeeves.

NOTE: This module requires sqlalchemy.
"""

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.types import BigInteger, DateTime, String

METADATA = MetaData(schema='duolingo_jeeves')

"""
Table for tickets exported from Zendesk.
"""
ZENDESK_TICKET_TABLE = Table('zendesk_ticket', METADATA,
    Column('user_id', BigInteger, info={'encode': 'LZO'}, primary_key=True),
    Column('created_at', DateTime, info={'encode': 'LZO'}, primary_key=True),

    Column('subject', String(256), info={'encode': 'LZO'}),
    Column('description', String(16536), info={'encode': 'LZO'}),

    Column('category_labels', String(512), info={'encode': 'LZO'}),
    Column('metadata', String(16536), info={'encode': 'LZO'}),

    redshift_diststyle='KEY',
    redshift_distkey='user_id',
    redshift_sortkey='created_at',
)
