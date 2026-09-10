"""Usa PyMySQL como driver MySQL quando mysqlclient não estiver disponível."""

try:
    import MySQLdb  # noqa: F401
except ImportError:  # pragma: no cover
    import pymysql

    pymysql.install_as_MySQLdb()
