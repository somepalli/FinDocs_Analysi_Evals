"""Retrieval strategies and result contracts.

The package initializer intentionally stays side-effect free. Index storage
returns retrieval schemas, so importing both packages eagerly would create a
cycle before either module has finished initializing.
"""
