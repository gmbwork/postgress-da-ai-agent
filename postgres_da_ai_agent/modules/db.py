import psycopg2
from psycopg2 import sql

class PostgresManager:

    def __init__(self, url=None):
        self.conn = None
        if url:
            self.connect_with_url(url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def connect_with_url(self, url):
        self.conn = psycopg2.connect(url)

    def upsert(self, table_name, _dict):
        with self.conn.cursor() as cursor:
            columns = _dict.keys()
            values = tuple(_dict.values())
            conflict_columns = [k for k in columns if k != 'id']
            insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(map(sql.Placeholder, columns))
            )
            update = sql.SQL("ON CONFLICT (id) DO UPDATE SET {}").format(
                sql.SQL(', ').join(sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in conflict_columns)
            )
            query = insert + update
            cursor.execute(query, values)
            self.conn.commit()

    def delete(self, table_name, _id):
        with self.conn.cursor() as cursor:
            query = sql.SQL("DELETE FROM {} WHERE id = %s").format(sql.Identifier(table_name))
            cursor.execute(query, (_id,))
            self.conn.commit()

    def get(self, table_name, _id):
        with self.conn.cursor() as cursor:
            query = sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(table_name))
            cursor.execute(query, (_id,))
            return cursor.fetchone()

    def get_all(self, table_name):
        with self.conn.cursor() as cursor:
            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
            cursor.execute(query)
            return cursor.fetchall()

    def run_sql(self, sql_statement):
        with self.conn.cursor() as cursor:
            cursor.execute(sql_statement)
            self.conn.commit()

    def get_table_definitions(self, table_name):
        with self.conn.cursor() as cursor:
            query = "SELECT column_name, data_type, character_maximum_length, column_default, is_nullable FROM information_schema.columns WHERE table_name = %s"
            cursor.execute(query, (table_name,))
            columns = cursor.fetchall()
            return columns

    def get_table_names(self):
        with self.conn.cursor() as cursor:
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

    def get_table_definition_for_prompt(self):
        table_names = self.get_table_names()
        table_definitions = []
        for table_name in table_names:
            table_definition = self.get_table_definitions(table_name)
            table_definition_str = f"CREATE TABLE {table_name} (\n"
            for column in table_definition:
                column_name, data_type, char_max_length, column_default, is_nullable = column
                if char_max_length:
                    data_type = f"{data_type}({char_max_length})"
                default_str = f" DEFAULT {column_default}" if column_default else ""
                nullable_str = " NOT NULL" if is_nullable == "NO" else ""
                table_definition_str += f"  {column_name} {data_type}{default_str}{nullable_str},\n"
            table_definition_str = table_definition_str.rstrip(",\n") + "\n);\n"
            table_definitions.append(table_definition_str)
        return "\n".join(table_definitions)